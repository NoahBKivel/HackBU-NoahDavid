"""Measure paired main-record throughput across both teacher execution paths."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.teacher.claims import claim_path, teacher_input_hash
from intent_training.teacher.openai_client_state import atomic_json


def main() -> int:
    """Count unique current-input pairs by the later family's persisted completion time."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--claims", type=Path, default=ROOT / "data/votes/claims")
    parser.add_argument("--window-minutes", type=float, default=15)
    parser.add_argument("--as-of")
    parser.add_argument("--train-records", type=int, default=12200)
    parser.add_argument("--single-sol", action="store_true")
    parser.add_argument("--validated-index", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "results/openai-labelling/combined-rate.json")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc)
    start = now - timedelta(minutes=args.window_minutes)
    entries = json.loads(args.manifest.read_text(encoding="utf-8"))
    batches = {entry["batch_id"]: entry["input"] for entry in entries}
    complete = {}
    active_calls = 0
    unknown_timestamps = 0
    current_hashes = set()
    for batch_id, batch_path in batches.items():
        batch = json.loads(Path(batch_path).read_text(encoding="utf-8"))
        if batch["pass"] != "main":
            continue
        current_hashes.update(teacher_input_hash(record) for record in batch["records"])
        families = {}
        for family in (("sol",) if args.single_sol else ("sol", "terra")):
            path = claim_path(args.claims, batch_id, family, batch["input_sha256"])
            if not path.exists():
                continue
            claim = json.loads(path.read_text(encoding="utf-8"))
            if claim.get("claimed_at") and datetime.fromisoformat(claim["claimed_at"]) > now:
                continue
            if claim["status"] == "completed":
                families[family] = claim
            else:
                active_calls += 1
        required = {"sol"} if args.single_sol else {"sol", "terra"}
        if not required <= set(families):
            continue
        families = {family: families[family] for family in required}
        if not all(claim.get("completed_at") for claim in families.values()):
            unknown_timestamps += len(batch["records"])
            continue
        paired_at = max(datetime.fromisoformat(claim["completed_at"]) for claim in families.values())
        if paired_at > now:
            continue
        for record in batch["records"]:
            key = teacher_input_hash(record)
            complete[key] = min(complete.get(key, paired_at), paired_at)
    indexed_completions = 0
    if args.single_sol and args.validated_index and args.validated_index.exists():
        with args.validated_index.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                key = row.get("teacher_input_sha256")
                if row.get("model_family") != "sol" or key not in current_hashes:
                    continue
                observed = datetime.fromisoformat(row["validated_at"])
                if observed > now:
                    continue
                complete[key] = min(complete.get(key, observed), observed)
                indexed_completions += 1
    recent = sum(start <= stamp <= now for stamp in complete.values())
    per_hour = recent * 60 / args.window_minutes
    remaining = max(0, args.train_records - len(complete))
    result = {"measured_at": now.isoformat(), "window_start": start.isoformat(),
              "allocation": "single_sol" if args.single_sol else "paired",
              "new_unique_complete_main_records": recent,
              "complete_main_records_per_hour": per_hour,
              "unique_complete_main_records": len(complete),
              "validated_index_records_admitted": indexed_completions,
              "window_minutes": args.window_minutes, "new_unique_paired_main_records": recent,
              "paired_main_records_per_hour": per_hour, "unique_paired_main_records": len(complete),
              "owned_uncompleted_main_calls": active_calls,
              "paired_records_without_completion_time": unknown_timestamps,
              "projected_remaining_hours": remaining / per_hour if per_hour else None,
              "scope": "Current supplied manifest, main votes only; RF selection and relabels excluded."}
    if args.single_sol:
        for key in ("new_unique_paired_main_records", "paired_main_records_per_hour", "unique_paired_main_records"):
            result[key] = None
    atomic_json(args.output, result)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
