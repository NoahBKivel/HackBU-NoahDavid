"""Drain paired judgement batches through independent concurrent API requests."""

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from hashlib import sha256
import json
from pathlib import Path
import threading
import time
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .claims import claim_next, finish_family
from .dispatch import MODELS, encoded
from .openai_client import AdaptiveConcurrency, validate_response
from .openai_client_state import BudgetExhausted, OpenAIBudget, usage_cost, utc_now
from .openai_client_transport import memory_request
from intent_training.prepare.records import scan


class PairedLiveClient:
    """Keep one batch owner and separate provider rate control for both teachers."""

    def __init__(self, *, key, pricing, ledger, claims, stop_file, max_concurrency=64):
        self.key = key
        self.pricing = pricing
        self.budget = OpenAIBudget(Path(ledger))
        self.claims = Path(claims)
        self.stop_file = Path(stop_file)
        self.stop_event = threading.Event()
        self.capacity = {family: AdaptiveConcurrency(max_concurrency, initial=max_concurrency)
                         for family in MODELS}

    def stopped(self):
        return self.stop_event.is_set() or self.stop_file.exists()

    def vote(self, item, family, owner):
        batch = item["batch"]
        body = memory_request(batch, family)
        scan(body)
        wire = encoded(body).encode("utf-8")
        rates = self.pricing["models"][MODELS[family]]
        maximum = ((len(wire) + 4096) * max(rates["long"]["input"], rates["long"]["cache_write_30m"])
                   + body["max_output_tokens"] * rates["long"]["output"]) / 1_000_000
        capacity = self.capacity[family]
        capacity.enter()
        headers = {}
        usage = None
        call_id = None
        limited = False
        try:
            if self.stopped():
                return {"status": "not_admitted", "batch_id": batch["batch_id"], "family": family}
            call_id = self.budget.reserve(maximum, model=MODELS[family], family=family,
                batch_id=batch["batch_id"], records=len(batch["records"]), transport="shared_reasoning",
                request_sha256=sha256(wire).hexdigest(), request_utf8_bytes=len(wire))
            started = utc_now()
            request = Request("https://api.openai.com/v1/responses", data=wire, method="POST",
                              headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"})
            for attempt in range(8):
                if self.stopped():
                    self.budget.settle(call_id, 0.0, no_request_sent=True, failure="admission_stopped")
                    return {"status": "not_admitted", "batch_id": batch["batch_id"], "family": family}
                try:
                    with urlopen(request, timeout=300) as response:
                        headers = dict(response.headers)
                        value = json.load(response)
                    break
                except HTTPError as error:
                    headers = dict(error.headers)
                    try:
                        detail = json.loads(error.read()).get("error", {})
                    except (ValueError, OSError):
                        detail = {}
                    provider_code = detail.get("code")
                    provider_type = detail.get("type")
                    quota_blocked = (provider_code in {"insufficient_quota", "credit_balance_exhausted"}
                                     or provider_type == "insufficient_quota")
                    if quota_blocked:
                        self.stop_event.set()
                    if error.code == 429:
                        print(json.dumps({"batch_id": batch["batch_id"], "family": family,
                            "http_status": 429, "provider_error_code": provider_code,
                            "provider_error_type": provider_type}), flush=True)
                    limited = error.code == 429
                    if limited and not quota_blocked and attempt < 7:
                        capacity.leave(headers, limited=True)
                        capacity.enter()
                        limited = False
                        continue
                    if error.code < 500 and error.code != 408:
                        self.budget.settle(call_id, 0.0, http_status=error.code, failure="request_rejected",
                            model=MODELS[family], family=family, batch_id=batch["batch_id"],
                            provider_error_code=provider_code, provider_error_type=provider_type)
                        raise RuntimeError(f"OpenAI HTTP {error.code}: {provider_code}; rejected request charged zero.") from None
                    raise RuntimeError(f"OpenAI HTTP {error.code}; unresolved requests retain reservations.") from None
                except URLError as error:
                    if isinstance(error.reason, socket.gaierror):
                        if attempt < 7:
                            time.sleep(min(attempt + 1, 5))
                            continue
                        self.budget.settle(call_id, 0.0, failure="dns_preconnection", no_request_sent=True)
                    raise
            usage = value["usage"]
            cost = usage_cost(usage, rates)
            completed = utc_now()
            self.budget.settle(call_id, cost, model=MODELS[family], family=family, usage=usage,
                batch_id=batch["batch_id"], records=len(batch["records"]), response_id=value.get("id"),
                started_at=started, completed_at=completed, price_source=self.pricing["source"],
                request_sha256=sha256(wire).hexdigest(), request_utf8_bytes=len(wire),
                service_tier=value.get("service_tier"), transport="shared_reasoning")
            votes = validate_response(value, batch, family)
            output = Path(item["outputs"][family])
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_suffix(output.suffix + ".tmp")
            temporary.write_text("".join(encoded(vote) + "\n" for vote in votes), encoding="utf-8")
            temporary.replace(output)
            finish_family(self.claims, batch, owner, family, output)
            return {"status": "completed", "batch_id": batch["batch_id"], "family": family,
                    "records": len(votes), "cost_usd": cost, "completed_at": completed}
        except BudgetExhausted:
            self.stop_event.set()
            raise
        finally:
            tokens = int(usage["input_tokens"]) + int(usage["output_tokens"]) if usage else 0
            capacity.leave(headers, limited, tokens)

    def run(self, queue, owner="openai-continuous", *, idle_timeout=0, excluded_questions=()):
        active = {}
        last_work = time.monotonic()
        completed_records = 0
        with ThreadPoolExecutor(max_workers=sum(cap.maximum for cap in self.capacity.values())) as pool:
            while active or not self.stopped():
                while not self.stopped() and len(active) < sum(cap.limit for cap in self.capacity.values()):
                    item = claim_next(queue, self.claims, owner, allowed_allocations=("paired",), resume_owned=True,
                                      excluded_questions=excluded_questions)
                    if item is None:
                        break
                    if set(item["required_families"]) != {"sol", "terra"}:
                        raise ValueError("The standard API queue admits paired judgement only.")
                    last_work = time.monotonic()
                    for family in ("sol", "terra"):
                        if (item["claim"]["families"][family]["status"] == "completed"
                                or item["claim"]["families"][family].get("delegated_to")):
                            continue
                        latest = {row["call_id"]: row for row in self.budget._rows()
                                  if row.get("provider") == "openai"}
                        if any(row.get("status") == "reserved" and row.get("batch_id") == item["batch"]["batch_id"]
                               and row.get("family") == family for row in latest.values()):
                            print(json.dumps({"batch_id": item["batch"]["batch_id"], "family": family,
                                              "error": "Unsettled prior call prevents duplicate admission."}), flush=True)
                            continue
                        active[pool.submit(self.vote, item, family, owner)] = item
                if not active:
                    if self.stopped() or (idle_timeout and time.monotonic() - last_work >= idle_timeout):
                        break
                    time.sleep(.25)
                    continue
                ready, _ = wait(active, timeout=.25, return_when=FIRST_COMPLETED)
                for future in ready:
                    item = active.pop(future)
                    try:
                        result = future.result()
                    except Exception as error:
                        result = {"batch_id": item["batch"]["batch_id"], "error_type": type(error).__name__,
                                  "error": str(error)}
                    if result.get("status") == "completed":
                        completed_records += result["records"]
                    print(json.dumps(result), flush=True)
        return completed_records
