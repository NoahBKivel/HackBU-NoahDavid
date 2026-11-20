"""Count unique policy-complete main inputs from the existing continuous queue."""

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher.claims import batch_claim_path, teacher_input_hash

parser = argparse.ArgumentParser()
parser.add_argument("--queue", type=Path, required=True)
parser.add_argument("--as-of", required=True)
parser.add_argument("--window-minutes", type=float, default=10)
parser.add_argument("--claims", type=Path, default=ROOT / "data/votes/claims")
args = parser.parse_args()
end = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
start = end - timedelta(minutes=args.window_minutes)
ready = {}
queued = set()
active_batches = Counter()
def queue_lines(path):
    with path.open(encoding="utf-8") as handle:
        yield from handle

for line in queue_lines(args.queue):
    if not line.endswith("\n"):
        break
    if not line.strip():
        continue
    item = json.loads(line)
    batch = item["batch"]
    if batch["pass"] != "main":
        continue
    hashes = [teacher_input_hash(record) for record in batch["records"]]
    queued.update(hashes)
    path = batch_claim_path(args.claims, batch)
    if not path.exists():
        continue
    claim = json.loads(path.read_text(encoding="utf-8"))
    required = claim["required_families"]
    families = claim["families"]
    if any(families[family]["status"] != "completed" for family in required):
        active_batches[claim["owner"]] += 1
        continue
    completed = max(datetime.fromisoformat(families[family]["completed_at"]) for family in required)
    if completed > end:
        continue
    policy = "paired" if set(required) == {"sol", "terra"} else "single_sol"
    for fingerprint in hashes:
        if fingerprint not in ready or completed < ready[fingerprint][0]:
            ready[fingerprint] = (completed, policy)
recent = Counter(policy for completed, policy in ready.values() if start <= completed <= end)
total = Counter(policy for _, policy in ready.values())
print(json.dumps({"window_start": start.isoformat(), "window_end": end.isoformat(),
    "window_minutes": args.window_minutes, "main_queued_unique": len(queued),
    "main_complete_in_queue": len(ready), "main_complete_by_policy": dict(total),
    "new_main_complete": sum(recent.values()), "new_main_by_policy": dict(recent),
    "main_records_per_hour": sum(recent.values()) * 60 / args.window_minutes,
    "owned_incomplete_main_batches": dict(active_batches),
    "scope": "Main only, full batch family completion; RF and diagnostics excluded; no partial-vote estimates."}))
