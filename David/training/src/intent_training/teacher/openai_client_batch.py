"""Reserve and reconcile finite lower-priority OpenAI Batch requests."""

from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4

from filelock import FileLock

from intent_training.prepare.records import scan
from .claims import claim_batch, complete_claim
from .dispatch import MODELS, digest, encoded
from .openai_client import request_body, validate_response
from .openai_client_state import OpenAIBudget, atomic_json, claim_votes, usage_cost


TERMINAL = {"completed", "cancelled", "expired", "failed"}


def batch_rates(pricing, family):
    """Derive discounted rates from the current standard pricing artifact."""
    rates = deepcopy(pricing["models"][MODELS[family]])
    for tier in ("short", "long"):
        rates[tier] = {key: value / 2 for key, value in rates[tier].items()}
    return rates


def eligible(batch, family, control):
    """Require explicit private approval for every model-visible record."""
    if family not in MODELS or digest(batch["records"]) != batch["input_sha256"]:
        raise ValueError("The frozen input or model family is invalid.")
    identities = [row["record_id"] for row in batch["records"]]
    if not identities or len(set(identities)) != len(identities):
        raise ValueError("The frozen records must have unique identities.")
    for record in batch["records"]:
        policy = control.get(record["record_id"], {})
        meta = policy.get("_meta", {})
        families = {"sol"} if policy.get("allocation") == "single_sol" else {"sol", "terra"}
        tags = {str(meta.get(key, "")).lower() for key in ("priority", "slice", "pool")}
        if (policy.get("allocation") not in {"single_sol", "paired"}
                or meta.get("validated_length") != 8191
                or family not in families or "c" in tags or "rare" in tags
                or bool(meta.get("construction")) or bool(meta.get("construction_type"))
                or str(meta.get("record_kind", "")).lower() == "construction"
                or meta.get("rare") is True or meta.get("priority") == "high"):
            raise ValueError("Batch requires explicitly eligible lower-priority control records.")


class BatchLabeller:
    """Keep uncertain submissions reserved until per-request evidence resolves them."""

    def __init__(self, *, pricing, ledger, claims):
        self.pricing = pricing
        self.budget = OpenAIBudget(Path(ledger))
        self.claims = Path(claims)

    def prepare(self, entries, control, directory, *, family, max_usd=5.0,
                max_requests=100, max_output_tokens=16000, lower_priority=False):
        """Claim and reserve a finite single-model subset before any upload."""
        if (not lower_priority or not 0 < max_usd <= 5
                or not 0 < max_requests <= 100 or max_output_tokens <= 0):
            raise ValueError("Batch subset limits must be positive and within their allowed caps.")
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=False)
        plan = {"owner": "openai-batch-" + uuid4().hex, "family": family,
                "model": MODELS[family], "completion_window": "24h", "items": [],
                "claims": str(self.claims.resolve()), "ledger": str(self.budget.ledger.resolve()),
                "pricing": self.pricing, "state": "preparing", "reserved_usd": 0.0}
        atomic_json(directory / "plan.json", plan)
        rates = batch_rates(self.pricing, family)
        wire_lines = []
        for entry in entries:
            if len(plan["items"]) >= max_requests:
                break
            batch = entry["batch"]
            eligible(batch, family, control)
            body = request_body(batch, family, max_output_tokens)
            scan(body)
            worst = rates["long"]
            amount = ((len(encoded(body).encode("utf-8")) + 4096)
                      * max(worst["input"], worst["cache_write_30m"])
                      + max_output_tokens * worst["output"]) / 1_000_000
            if plan["reserved_usd"] + amount > max_usd:
                continue
            output = Path(entry["output"]).resolve()
            if output.exists():
                continue
            identity = {"batch_id": batch["batch_id"], "family": family,
                        "input_sha256": batch["input_sha256"]}
            custom_id = digest(identity)
            if claim_batch(self.claims, batch, family, plan["owner"]) is None:
                continue
            with claim_votes(self.claims, batch, family, plan["owner"]) as claim:
                call_id = self.budget.reserve(amount, **identity, model=MODELS[family],
                                              transport="batch", custom_id=custom_id)
                claim.update(call_id=call_id, status="uncertain")
            item = dict(identity, custom_id=custom_id, call_id=call_id, batch=batch,
                        output=str(output), reserved_usd=amount, settled=False)
            plan["items"].append(item)
            plan["reserved_usd"] += amount
            wire_lines.append({"custom_id": custom_id, "method": "POST",
                               "url": "/v1/responses", "body": body})
            atomic_json(directory / "plan.json", plan)
        if not plan["items"]:
            raise ValueError("No eligible unowned requests fit the Batch subset.")
        content = "".join(encoded(line) + "\n" for line in wire_lines)
        (directory / "input.jsonl").write_text(content, encoding="utf-8")
        plan.update(state="prepared", input_digest=digest(content))
        atomic_json(directory / "plan.json", plan)
        return plan

    def submit(self, directory, client):
        """Upload once and retain reservations if the create outcome is uncertain."""
        directory = Path(directory)
        with FileLock(str(directory / "operation.lock")):
            plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
            if plan["state"] != "prepared":
                raise ValueError("Only a prepared batch can be submitted once.")
            content = (directory / "input.jsonl").read_text(encoding="utf-8")
            if digest(content) != plan["input_digest"]:
                raise ValueError("The prepared Batch input changed.")
            self._check_paths(plan)
            plan["state"] = "upload_uncertain"
            atomic_json(directory / "plan.json", plan)
            with (directory / "input.jsonl").open("rb") as handle:
                uploaded = client.files.create(file=handle, purpose="batch")
            plan.update(input_file_id=uploaded.id, state="submit_uncertain")
            atomic_json(directory / "plan.json", plan)
            result = client.batches.create(input_file_id=uploaded.id, endpoint="/v1/responses",
                                           completion_window="24h", metadata={"owner": plan["owner"]})
            plan.update(batch_id=result.id, state="submitted")
            atomic_json(directory / "plan.json", plan)
            return result.model_dump()

    def _check_paths(self, plan):
        if (plan["ledger"] != str(self.budget.ledger.resolve())
                or plan["claims"] != str(self.claims.resolve())):
            raise ValueError("The Batch ledger or ownership directory changed.")

    def collect(self, directory, status, artifacts):
        """Charge all measured work, then validate votes independently of output order."""
        directory = Path(directory)
        with FileLock(str(directory / "operation.lock")):
            plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
            self._check_paths(plan)
            if status.get("id") != plan.get("batch_id"):
                raise ValueError("The remote batch identity differs from the plan.")
            indexed = {item["custom_id"]: item for item in plan["items"]}
            lines = []
            for field in ("output_file_id", "error_file_id"):
                file_id = status.get(field)
                if file_id:
                    if file_id not in artifacts:
                        raise ValueError("Every advertised output and error artifact is required.")
                    content = artifacts[file_id]
                    atomic_json(directory / (field + ".json"), {"id": file_id, "content": content})
                    lines.extend(json.loads(line) for line in content.splitlines() if line.strip())
            seen = set()
            for line in lines:
                key = line["custom_id"]
                if key not in indexed or key in seen:
                    raise ValueError("The Batch output has unknown or duplicate custom identities.")
                seen.add(key)
            failures = []
            for line in lines:
                item = indexed[line["custom_id"]]
                response = line.get("response") or {}
                body = response.get("body") or {}
                usage = body.get("usage")
                error = line.get("error") or {}
                unexecuted = (status.get("status") in TERMINAL and not response
                              and error.get("code") in {"batch_expired", "batch_cancelled"})
                if not item["settled"] and (usage is not None or unexecuted):
                    cost = (usage_cost(usage, batch_rates(plan["pricing"], item["family"]))
                            if usage is not None else 0.0)
                    # Ledger append precedes the plan; recover a crash by inspecting the ledger.
                    with self.budget.lock:
                        prior = [r for r in self.budget._rows() if r.get("call_id") == item["call_id"]]
                    if prior[-1]["status"] == "reserved":
                        self.budget.settle(item["call_id"], cost, transport="batch", usage=usage,
                                           batch_id=status["id"], custom_id=item["custom_id"])
                    item["settled"] = True
                    atomic_json(directory / "plan.json", plan)
                if item.get("completed") or response.get("status_code") != 200 or usage is None:
                    continue
                try:
                    votes = validate_response(body, item["batch"], item["family"])
                except (ValueError, KeyError, TypeError) as error:
                    failures.append({"custom_id": item["custom_id"], "error": type(error).__name__})
                    continue
                output = Path(item["output"])
                output.parent.mkdir(parents=True, exist_ok=True)
                text = "".join(encoded(vote) + "\n" for vote in votes)
                if output.exists() and output.read_text(encoding="utf-8") != text:
                    raise FileExistsError("The vote output contains different existing results.")
                temporary = output.with_suffix(output.suffix + ".batch.tmp")
                temporary.write_text(text, encoding="utf-8")
                temporary.replace(output)
                from .claims import claim_path
                shared = json.loads(claim_path(self.claims, item["batch_id"], item["family"],
                                               item["input_sha256"]).read_text(encoding="utf-8"))
                if shared["status"] != "completed":
                    complete_claim(self.claims, item["batch"], item["family"], plan["owner"], output)
                item["completed"] = True
                atomic_json(directory / "plan.json", plan)
            plan.update(remote_status=status, validation_failures=failures)
            atomic_json(directory / "plan.json", plan)
            return {"completed": sum(bool(i.get("completed")) for i in plan["items"]),
                    "outstanding": sum(not i["settled"] for i in plan["items"]),
                    "invalid": len(failures), "status": status.get("status")}
