"""Recover explicitly delegated delivery failures under a separate internal spend ceiling."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from filelock import FileLock
from intent_training.teacher.claims import batch_claim_path
from intent_training.teacher.openai_client_live import PairedLiveClient
from intent_training.teacher.openai_client_state import BudgetExhausted, OpenAIBudget
from openai_label import load_key


class RecoveryBudget(OpenAIBudget):
    """Reserve recovery calls against both the global and internal caps."""

    def reserve(self, amount, **metadata):
        with FileLock(str(self.ledger.with_name("recovery-spend.lock"))):
            rows = self._rows()
            owned = {row["call_id"] for row in rows if row.get("recovery_group") == "delivery"}
            latest = {row["call_id"]: row for row in rows if row.get("call_id") in owned}
            exposure = sum(float(row.get("cost_usd", row.get("reserved_charge_usd", 0)))
                           for row in latest.values())
            if exposure + amount > 10:
                raise BudgetExhausted("The authorized delivery recovery ceiling has no room.")
            return super().reserve(amount, recovery_group="delivery", **metadata)

    def settle(self, call_id, cost, **metadata):
        return super().settle(call_id, cost, recovery_group="delivery", **metadata)


def main():
    """Submit only explicitly named, quiescent single-slot batches."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--batch", action="append", required=True)
    args = parser.parse_args()
    wanted = set(args.batch)
    client = PairedLiveClient(key=load_key(args.env_file),
        pricing=json.loads((ROOT / "openai-label-pricing.json").read_text(encoding="utf-8")),
        ledger=ROOT / "results/openai-spend.jsonl", claims=ROOT / "data/votes/claims",
        stop_file=ROOT / "results/openai-labelling/STOP_ADMISSIONS", max_concurrency=1)
    client.budget = RecoveryBudget(ROOT / "results/openai-spend.jsonl")
    with args.queue.open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            batch = item["batch"]
            if batch["batch_id"] not in wanted:
                continue
            claim = json.loads(batch_claim_path(client.claims, batch).read_text(encoding="utf-8"))
            if (batch["pass"] != "main" or claim["required_families"] != ["sol"]
                    or claim["families"]["sol"]["status"] != "pending"
                    or Path(item["outputs"]["sol"]).exists()):
                raise ValueError("Recovery requires an uncompleted single main slot and absent output.")
            if any(row.get("status") == "reserved" and row.get("batch_id") == batch["batch_id"]
                   for row in {row["call_id"]: row for row in client.budget._rows()}.values()):
                raise ValueError("An unsettled prior request prevents recovery.")
            print(json.dumps(client.vote(item, "sol", claim["owner"])), flush=True)
            wanted.remove(batch["batch_id"])
            if not wanted:
                return
    if wanted:
        raise ValueError("A requested recovery batch was not present in the canonical queue.")


if __name__ == "__main__":
    main()
