"""Persist independent vote ownership and conservative OpenAI spend reservations."""

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import time
from pathlib import Path
from uuid import uuid4

from filelock import FileLock


class BudgetExhausted(RuntimeError):
    """Signal that no additional request may be admitted under the spend cap."""


def utc_now() -> str:
    """Return a timezone-qualified timestamp for measured call events."""
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: object) -> None:
    """Replace a JSON artifact only after its complete contents are written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def vote_keys(batch: dict, family: str) -> list[str]:
    """Identify individual question votes by their complete frozen teacher input."""
    keys = []
    for record in batch["records"]:
        frozen = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        for question in record["questions"]:
            material = json.dumps([frozen, question, family, batch.get("instruction_supplement", "")],
                                  ensure_ascii=False)
            keys.append(sha256(material.encode("utf-8")).hexdigest())
    return keys


@contextmanager
def claim_votes(root: Path, batch: dict, family: str, owner: str):
    """Claim every question atomically and retain completed or uncertain ownership."""
    root.mkdir(parents=True, exist_ok=True)
    keys = vote_keys(batch, family)
    paths = [root / (key + ".json") for key in keys]
    with FileLock(str(root / "claims.lock")):
        if any(path.exists() for path in paths):
            raise FileExistsError("One or more votes already have an owner.")
        for path in paths:
            atomic_json(path, {"owner": owner, "family": family, "batch_id": batch["batch_id"],
                               "input_sha256": batch["input_sha256"], "status": "owned",
                               "claimed_at": utc_now()})
    state = {"status": "uncertain"}
    try:
        yield state
    finally:
        with FileLock(str(root / "claims.lock")):
            for path in paths:
                value = json.loads(path.read_text(encoding="utf-8"))
                value.update(state, updated_at=utc_now())
                atomic_json(path, value)


class OpenAIBudget:
    """Enforce a provider-specific cap including uncertain and concurrent requests."""

    def __init__(self, ledger: Path, cap_usd: float = 200.0):
        self.ledger = ledger
        self.cap = cap_usd
        self.lock = FileLock(str(ledger.with_name("spend.lock")), timeout=60)
        ledger.parent.mkdir(parents=True, exist_ok=True)

    def _rows(self) -> list[dict]:
        if not self.ledger.exists():
            return []
        with self._open("r") as handle:
            content = handle.read()
        return [json.loads(line) for line in content.splitlines()
                if line.strip()]

    def _open(self, mode):
        for attempt in range(10):
            try:
                return self.ledger.open(mode, encoding="utf-8")
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(.05 * (attempt + 1))

    def _append(self, value: dict) -> None:
        with self._open("a") as handle:
            handle.write(json.dumps(dict(value, provider="openai", currency="USD", at=utc_now())) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def exposure(self) -> float:
        """Count actual settled costs and every outstanding worst-case reservation."""
        calls = {}
        for row in self._rows():
            if row.get("provider") == "openai" and row.get("call_id"):
                calls[row["call_id"]] = row
        return sum(float(row.get("cost_usd", row.get("reserved_charge_usd", 0)))
                   for row in calls.values())

    def reserve(self, amount: float, **metadata) -> str:
        """Reject a request before dispatch if worst-case exposure exceeds the cap."""
        if amount < 0:
            raise ValueError("A reservation cannot be negative.")
        with self.lock:
            if self.exposure() + amount > self.cap:
                raise BudgetExhausted("The OpenAI spend cap has no room for this request.")
            call_id = uuid4().hex
            self._append(dict(metadata, call_id=call_id, status="reserved", reserved_charge_usd=amount))
            return call_id

    def settle(self, call_id: str, cost: float, **metadata) -> None:
        """Append measured usage while preserving every prior reservation row."""
        with self.lock:
            prior = [row for row in self._rows() if row.get("call_id") == call_id]
            if not prior or prior[-1].get("status") != "reserved":
                raise ValueError("The request has no unsettled reservation.")
            if cost < 0 or cost > float(prior[-1]["reserved_charge_usd"]) + 1e-9:
                raise ValueError("Measured cost exceeds the conservative request reservation.")
            self._append(dict(metadata, call_id=call_id, status="settled", cost_usd=cost))


def usage_cost(usage: dict, rates: dict) -> float:
    """Price disjoint ordinary, cached-read, cached-write and output usage tokens."""
    total = int(usage["input_tokens"])
    output = int(usage["output_tokens"])
    details = usage.get("input_tokens_details", {})
    cached = int(details.get("cached_tokens", 0))
    written = int(details.get("cache_write_tokens", 0))
    ordinary = total - cached - written
    if min(ordinary, output, cached, written) < 0:
        raise ValueError("Token usage categories are inconsistent.")
    rate = rates["long" if total > rates["long_threshold_tokens"] else "short"]
    return (ordinary * rate["input"] + cached * rate["cached_input"]
            + written * rate["cache_write_30m"] + output * rate["output"]) / 1_000_000
