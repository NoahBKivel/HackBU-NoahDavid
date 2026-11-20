"""Reserve and settle generation costs under the shared Anthropic cap."""

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
from filelock import FileLock
from .request_io import atomic_json

MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5")


def usage_cost(model: str, usage: dict) -> float:
    """Price standard global inference, including cache creation and reads."""
    if model not in MODELS:
        raise ValueError("The generation model is not authorized.")
    if usage.get("service_tier") not in (None, "standard") or usage.get("speed") not in (None, "standard"):
        raise ValueError("The response needs a different price schedule.")
    if usage.get("inference_geo") not in (None, "global"):
        raise ValueError("The response needs geographic pricing.")
    inp, out = int(usage["input_tokens"]), int(usage["output_tokens"])
    cache = usage.get("cache_creation") or {}
    short = int(cache.get("ephemeral_5m_input_tokens") or 0)
    long = int(cache.get("ephemeral_1h_input_tokens") or 0)
    created = int(usage.get("cache_creation_input_tokens") or 0)
    read = int(usage.get("cache_read_input_tokens") or 0)
    if created != short + long:
        raise ValueError("Cache creation duration is unavailable.")
    tools = usage.get("server_tool_use") or {}
    if any(tools.values()):
        raise ValueError("Server tool pricing is unavailable.")
    if model == MODELS[0]:
        rate = .1 if inp + created + read <= 100000 else .5
        output_rate, read_rate = rate * 5, rate * .1
    else:
        rate, output_rate, read_rate = 2, 10, .1
    return (inp * rate + out * output_rate + short * rate * 1.25 + long * rate * 2 + read * read_rate) / 1000000


class Spending:
    """Serialize reservations with the existing agent-run ledger contract."""

    def __init__(self, root: Path):
        self.root = root
        self.folder = root / "results/generation"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / "reservations.json"
        self.lock = root / "results/spend.lock"
        self.guard = RLock()

    def state(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def exposure(self, state: dict) -> float:
        ledger = self.root / "results/spend.jsonl"
        used = sum(float(row.get("cost_usd") if row.get("cost_usd") is not None else row.get("reserved_charge_usd", 0))
                   for row in (json.loads(line) for line in ledger.read_text().splitlines() if line.strip())) if ledger.exists() else 0
        runs = self.root / "results/agent-runs/reservations.json"
        run_state = json.loads(runs.read_text()) if runs.exists() else {}
        return used + sum(row["maximum_usd"] for rows in (state, run_state) for row in rows.values() if "charged_usd" not in row)

    def reserve(self, job_id: str, maximum: float, request_hash: str, *,
                requested_model: str | None = None, category: str = "generation",
                category_cap: float | None = None, headroom: float = 0) -> str | None:
        """Assign the less-used model and reserve before any network request."""
        with self.guard, FileLock(str(self.lock), timeout=60):
            state = self.state()
            budget = json.loads((self.root / "results/budget.json").read_text())
            used = sum(row.get("charged_usd", row["maximum_usd"]) for row in state.values())
            if job_id in state or used + maximum > budget["generation_reserve_usd"]:
                return None
            if category_cap is not None:
                category_used = sum(row.get("charged_usd", row["maximum_usd"]) for row in state.values()
                                    if row.get("category", "generation") == category)
                if category_used + maximum > category_cap:
                    return None
            ceiling = budget["total_cap_usd"] - budget.get("provider_margin_usd", 0)
            if self.exposure(state) + maximum + headroom > ceiling:
                return None
            model = requested_model or min(MODELS, key=lambda name: sum(row["model"] == name
                and row.get("category", "generation") == category for row in state.values()))
            if model not in MODELS:
                raise ValueError("The requested Anthropic model is not authorized.")
            state[job_id] = {"maximum_usd": maximum, "model": model, "category": category, "request_hash": request_hash,
                             "reserved_at": datetime.now(timezone.utc).isoformat()}
            atomic_json(self.path, state)
            return model

    def settle(self, job_id: str, cost: float | None, usage: dict, status: str) -> float:
        """Retain the full reservation when actual billing cannot be established."""
        with self.guard, FileLock(str(self.lock), timeout=60):
            state = self.state()
            row = state[job_id]
            if "charged_usd" in row:
                return self.exposure(state)
            charged = row["maximum_usd"] if cost is None else cost
            record = {"job_id": job_id, "category": row.get("category", "generation"), "model": row["model"],
                      "cost_usd": cost, "reserved_charge_usd": charged, "usage": usage,
                      "status": status, "timestamp": datetime.now(timezone.utc).isoformat()}
            with (self.root / "results/spend.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")
            row.update(charged_usd=charged, actual_cost_known=cost is not None, status=status)
            atomic_json(self.path, state)
            return self.exposure(state)
