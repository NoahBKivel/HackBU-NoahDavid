"""Generate agent text with real Anthropic responses and durable accounting."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import hashlib
from pathlib import Path
import time
from typing import Any
from filelock import FileLock
from .request_io import DirectMessages, atomic_json, credential_markers, fingerprint, load_requests
from .spending import Spending, usage_cost


class Generator:
    """Process a persistent request queue without manufacturing missing responses."""

    def __init__(self, root: Path, client: Any = None, retry_failed: bool = False,
                 approved_prompt_sha256: str | None = None, construction_budget: bool = False,
                 requested_model: str | None = None):
        self.root = root.resolve()
        self.client = client
        self.retry_failed = retry_failed
        self.approved_prompt_sha256 = approved_prompt_sha256
        self.construction_budget = construction_budget
        self.requested_model = requested_model
        self.spending = Spending(self.root)
        self.output = self.root / "data/generation/responses"
        self.output.mkdir(parents=True, exist_ok=True)

    def generate(self, request: dict) -> dict:
        """Preserve complete response usage and hold uncertain charges conservatively."""
        identifier = request["id"]
        if self.approved_prompt_sha256 and hashlib.sha256(request["prompt"].encode()).hexdigest() != self.approved_prompt_sha256:
            raise ValueError("The prompt differs from the explicitly approved fingerprint.")
        if credential_markers(self.root, json.dumps(request, ensure_ascii=False)):
            return {"id": identifier, "status": "credential_marker_blocked"}
        destination = self.output / (identifier + ".json")
        with FileLock(str(self.spending.folder / (identifier + ".lock")), timeout=30):
            if destination.exists():
                saved = json.loads(destination.read_text(encoding="utf-8"))
                if saved.get("request_hash") != fingerprint(request):
                    raise ValueError("A completed request identifier was reused.")
                if saved.get("stop_reason") == "refusal":
                    return {"id": identifier, "status": "refused"}
                return {"id": identifier, "status": "cached"}
            # UTF-8 byte count exceeds the possible text-token count. The larger
            # Haiku tariff and Sonnet tariff bound either model before assignment.
            job_id = identifier
            prior = self.spending.state()
            if identifier in prior and prior[identifier]["request_hash"] != fingerprint(request) and not (self.approved_prompt_sha256 or self.retry_failed):
                raise ValueError("A reserved request identifier was reused.")
            previous = [row for key, row in prior.items()
                        if key == identifier or key.startswith(identifier + ".attempt")]
            if any(row.get("status") == "refused" for row in previous):
                return {"id": identifier, "status": "refused"}
            if identifier in prior and self.retry_failed:
                attempt = 1
                while job_id in prior:
                    job_id = identifier + ".attempt" + str(attempt)
                    attempt += 1
            output_limit = request["max_output_tokens"]
            if request["purpose"] == "agentif_next_message":
                output_limit = max(output_limit, 4096)
            if request["purpose"] == "omission_alignment":
                output_limit = max(output_limit, 4096)
            if identifier.startswith("userbench-"):
                output_limit = max(output_limit, 1024)
            for previous_id in prior:
                if previous_id == identifier or previous_id.startswith(identifier + ".attempt"):
                    incomplete = self.spending.folder / (previous_id + ".incomplete.json")
                    if incomplete.exists():
                        previous = json.loads(incomplete.read_text(encoding="utf-8"))
                        output_limit = max(output_limit, min(32768, previous.get("effective_max_output_tokens", request["max_output_tokens"]) * 2))
            maximum = ((len(request["prompt"].encode("utf-8")) + 4096) * 2 + output_limit * 10) / 1000000
            model = self.spending.reserve(job_id, maximum, fingerprint(request),
                category="construction_generation" if self.construction_budget else "generation",
                category_cap=25 if self.construction_budget else None, requested_model=self.requested_model)
            if model is None:
                return {"id": identifier, "status": "not_started"}
            usage, cost = {}, None
            try:
                if self.client is None:
                    client = DirectMessages()
                else:
                    client = self.client
                for attempt in range(3):
                    try:
                        settings = {}
                        if output_limit <= 128 or identifier.startswith("userbench-") or request["purpose"] in {"correction_window", "composite"}:
                            settings["thinking"] = {"type": "disabled" if model == "claude-haiku-5-5" else "between_tools"}
                        response = client.messages.create(model=model, max_tokens=output_limit,
                                                           messages=[{"role": "user", "content": request["prompt"]}],
                                                           service_tier="standard_only", inference_geo="global", **settings)
                        break
                    except Exception as error:
                        # Rejected rate-limit and overload requests are safe to
                        # retry. Ambiguous connection failures retain their reserve.
                        retryable = getattr(error, "status_code", None) in (429, 529) or getattr(error, "preconnection_dns_failure", False)
                        if not retryable or attempt == 2:
                            raise
                        time.sleep(2 ** attempt)
                usage = response.usage.model_dump(mode="json")
                try:
                    cost = usage_cost(model, usage)
                except (ValueError, KeyError, TypeError):
                    pass
                content = response.content
                text = content if isinstance(content, str) else "".join(block.text for block in content if getattr(block, "type", None) == "text")
                status = ("refused" if response.stop_reason == "refusal" else
                          "completed" if text and response.stop_reason != "max_tokens" else "incomplete")
                record = {"id": identifier, "text": text, "model": model, "usage": usage,
                          "cost_usd": cost, "request_hash": fingerprint(request),
                          "effective_max_output_tokens": output_limit,
                          "stop_reason": response.stop_reason, "response_id": response.id, "status": status}
                if status == "completed":
                    atomic_json(destination, record)
                else:
                    atomic_json(self.spending.folder / (job_id + "." + status + ".json"), record)
            except Exception as error:
                # Exception strings may contain credentials or signed URLs.
                status = "failed"
                causes = []
                current = error
                while current is not None and len(causes) < 8:
                    causes.append({"type": type(current).__name__, "errno": getattr(current, "connection_errno", getattr(current, "errno", None))})
                    current = current.__cause__
                atomic_json(self.spending.folder / (job_id + ".error.json"),
                            {"id": identifier, "error_type": type(error).__name__, "causes": causes})
            exposure = self.spending.settle(job_id, cost, usage, status)
            budget = json.loads((self.root / "results/budget.json").read_text())
            if exposure >= .9 * budget["total_cap_usd"]:
                atomic_json(self.spending.folder / "cost-alert.json", {"exposure_usd": exposure, "threshold_fraction": .9})
                print(json.dumps({"alert": "Anthropic spending has reached the owner alert threshold.", "exposure_usd": exposure}), flush=True)
            return {"id": identifier, "status": status, "model": model, "cost_usd": cost}

    def run_once(self, workers: int = 4, limit: int | None = None, request_id: str | None = None,
                 sources: list[str] | None = None) -> list[dict]:
        """Process one queue snapshot with a bounded worker pool."""
        if not 1 <= workers <= 32:
            raise ValueError("Generation workers must be between one and thirty-two.")
        requests = load_requests(self.root, sources)
        if request_id is not None:
            requests = [request for request in requests if request["id"] == request_id]
            if not requests:
                raise ValueError("The selected request identifier does not exist.")
        if limit is not None:
            requests = requests[:limit]
        def process(request: dict) -> dict:
            result = self.generate(request)
            for _ in range(2):
                if not self.retry_failed or result["status"] != "incomplete":
                    break
                result = self.generate(request)
            return result

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = []
            pending = [pool.submit(process, request) for request in requests]
            consecutive_failures = 0
            for future in as_completed(pending):
                if future.cancelled():
                    continue
                result = future.result()
                results.append(result)
                consecutive_failures = consecutive_failures + 1 if result["status"] == "failed" else 0
                if len(results) % workers == 0:
                    batch = results[-workers:]
                    atomic_json(self.spending.folder / "latest-run.json", {"requests": len(requests), "results": results})
                    print(json.dumps({"batch_finished": len(batch), "statuses": {status: sum(row["status"] == status for row in batch) for status in {row["status"] for row in batch}}}), flush=True)
                if consecutive_failures >= workers:
                    for waiting in pending:
                        waiting.cancel()
        atomic_json(self.spending.folder / "latest-run.json", {"requests": len(requests), "results": results})
        return results
