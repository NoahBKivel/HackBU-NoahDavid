"""Supply honestly attributed auxiliary votes through the shared queue contract."""

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError, URLError
from filelock import FileLock

from .claims import claim_batch_once, finish_family, batch_claim_path
from .dispatch import digest, encoded, SONNET_MODEL
from .openai_client import AdaptiveConcurrency, validate_response
from .openai_client_transport import memory_request
from ..generation.request_io import atomic_json, credential_markers
from ..generation.spending import Spending, usage_cost

AUXILIARY = {"requirements", "localization", "traceability", "requirements_diagnostic"}


class AnthropicAuxiliaryClient:
    """Reuse exact validation, ownership and conservative provider accounting."""

    def __init__(self, root: Path, maximum: int = 32):
        self.root = root.resolve()
        self.claims = self.root / "data/votes/claims"
        self.owner = "anthropic-auxiliary"
        self.spending = Spending(self.root)
        self.capacity = AdaptiveConcurrency(maximum, initial=maximum)
        self.stop = threading.Event()
        self.output = self.root / "results/anthropic-labelling"
        self.output.mkdir(parents=True, exist_ok=True)

    def body(self, batch: dict) -> dict:
        """Preserve frozen evidence and cache the existing fixed teacher instructions."""
        cap = (256 if batch["pass"].startswith("requirements") else 768) * len(batch["records"])
        original = memory_request(batch, "sol", cap)
        system = []
        for item in original["input"][:-1]:
            content = item["content"]
            text = content if isinstance(content, str) else "".join(part["text"] for part in content)
            system.append({"type": "text", "text": text, "cache_control": {"type": "ephemeral"}})
        system[0]["text"] += "\nEvery vote also includes vote_slot and actual_model copied exactly from provenance."
        payload = json.loads(original["input"][-1]["content"])
        payload["provenance"].update(vote_slot="sol", actual_model=SONNET_MODEL,
                                     model=SONNET_MODEL, model_family="sonnet")
        return {"model": SONNET_MODEL, "system": system,
                "messages": [{"role": "user", "content": encoded(payload)}],
                "thinking": {"type": "between_tools"}, "output_config": {"effort": "low"},
                "max_tokens": cap, "service_tier": "standard_only", "inference_geo": "global"}

    def _headers(self, headers: dict) -> dict:
        values = {key.lower(): value for key, value in headers.items()}
        result = {"retry-after": values.get("retry-after", "5")}
        for source, destination in [("requests", "requests"), ("input-tokens", "tokens")]:
            remaining = values.get("anthropic-ratelimit-" + source + "-remaining")
            reset = values.get("anthropic-ratelimit-" + source + "-reset")
            if remaining is not None:
                result["x-ratelimit-remaining-" + destination] = remaining
            if reset:
                try:
                    delay = max(0, (datetime.fromisoformat(reset.replace("Z", "+00:00")) - datetime.now(timezone.utc)).total_seconds())
                    result["x-ratelimit-reset-" + destination] = str(delay)
                except ValueError:
                    pass
        return result

    def vote(self, item: dict) -> dict:
        """Claim once, reserve before transport, then validate every supplied vote."""
        batch = item["batch"]
        result = {"batch_id": batch["batch_id"], "pass": batch["pass"]}
        if self.stop.is_set():
            return dict(result, status="stopped")
        if batch["pass"] not in AUXILIARY or item.get("required_families", ["sol"]) != ["sol"]:
            return dict(result, status="ineligible")
        if digest(batch["records"]) != batch["input_sha256"]:
            raise ValueError("The canonical frozen input changed before dispatch.")
        body = self.body(batch)
        if credential_markers(self.root, encoded(body)):
            return dict(result, status="credential_marker_blocked")
        wire = encoded(body).encode("utf-8")
        maximum = ((len(wire) + 4096) * 2.5 + body["max_tokens"] * 10) / 1e6
        job = "label." + batch["batch_id"]
        self.capacity.enter()
        cost, usage, headers, reserved = None, {}, {}, False
        status = "uncertain"
        try:
            model = self.spending.reserve(job, maximum, sha256(wire).hexdigest(),
                requested_model=SONNET_MODEL, category="anthropic_labels", category_cap=80, headroom=25)
            if model is None:
                return dict(result, status="budget_or_existing")
            reserved = True
            claim = claim_batch_once(self.claims, batch, self.owner, ["sol"])
            if claim is None:
                cost, status = 0.0, "already_owned"
                return dict(result, status=status)
            request = Request("https://api.anthropic.com/v1/messages", data=wire, method="POST",
                headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"})
            opener = build_opener(ProxyHandler({}))
            for attempt in range(6):
                try:
                    with opener.open(request, timeout=300) as response:
                        headers = self._headers(dict(response.headers))
                        value = json.load(response)
                    break
                except HTTPError as error:
                    headers = self._headers(dict(error.headers))
                    if error.code == 429 and attempt < 5:
                        self.capacity.leave(headers, limited=True)
                        self.capacity.enter()
                        continue
                    if error.code < 500 and error.code != 408:
                        cost = 0.0
                    if error.code in {400, 401, 403}:
                        self.stop.set()
                    raise RuntimeError("The Anthropic label request was rejected.") from None
            usage = value["usage"]
            cost = usage_cost(SONNET_MODEL, usage)
            if value.get("stop_reason") == "refusal":
                status = "refused"
                return dict(result, status=status, cost_usd=cost)
            if value.get("stop_reason") != "end_turn":
                status = "incomplete"
                return dict(result, status=status, cost_usd=cost)
            text = "".join(part["text"] for part in value["content"] if part.get("type") == "text")
            checked_batch = dict(batch, model_overrides={"sol": SONNET_MODEL})
            normalized = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}
            votes = validate_response(normalized, checked_batch, "sol")
            output = Path(item["outputs"]["sol"])
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_name(output.name + ".anthropic.tmp")
            temporary.write_text("".join(encoded(vote) + "\n" for vote in votes), encoding="utf-8")
            temporary.replace(output)
            finish_family(self.claims, checked_batch, self.owner, "sol", output, actual_model=SONNET_MODEL)
            status = "completed"
            return dict(result, status=status, records=len(votes), cost_usd=cost, usage=usage)
        except URLError as error:
            self.stop.set()
            reason = getattr(error, "reason", None)
            no_request = isinstance(reason, PermissionError) and getattr(reason, "winerror", None) == 10013
            if no_request:
                cost, status = 0.0, "not_sent"
                path = batch_claim_path(self.claims, batch)
                with FileLock(str(path) + ".lock", timeout=60):
                    if path.exists():
                        claim = json.loads(path.read_text())
                        if claim.get("owner") == self.owner and claim.get("status") == "claimed":
                            path.unlink()
            return dict(result, status=status, error_type=type(error).__name__,
                        connection_errno=getattr(reason, "errno", None),
                        connection_winerror=getattr(reason, "winerror", None), no_request_sent=no_request)
        except Exception as error:
            return dict(result, status="failed", error_type=type(error).__name__, cost_usd=cost)
        finally:
            if reserved:
                self.spending.settle(job, cost, usage, status)
            self.capacity.leave(headers, tokens_used=int(usage.get("input_tokens", 0)))

    def run(self, queue: Path, allowed: set[str]) -> dict:
        """Continuously replace completed calls without writing model prompt files."""
        started = datetime.now(timezone.utc).isoformat()
        results = []
        active = {}
        with ThreadPoolExecutor(max_workers=self.capacity.maximum) as pool, queue.open(encoding="utf-8") as rows:
            exhausted = False
            while active or not exhausted:
                while not exhausted and not self.stop.is_set() and len(active) < self.capacity.limit:
                    line = rows.readline()
                    if not line:
                        exhausted = True
                        break
                    item = json.loads(line)
                    if item["batch"]["batch_id"] not in allowed:
                        continue
                    active[pool.submit(self.vote, item)] = item["batch"]["batch_id"]
                if not active:
                    break
                done, _ = wait(active, timeout=10, return_when=FIRST_COMPLETED)
                for future in done:
                    active.pop(future)
                    result = future.result()
                    results.append(result)
                    print(json.dumps(result), flush=True)
                atomic_json(self.output / "progress.json", {"started_at": started, "inflight": len(active),
                    "completed_records": sum(row.get("records", 0) for row in results), "results": results})
        return {"started_at": started, "results": results}
