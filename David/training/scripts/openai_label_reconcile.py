"""Reconcile an ended API queue without releasing uncertain or foreign ownership."""

from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher.claims import claim_path, teacher_input_hash
from intent_training.teacher.openai_client_state import OpenAIBudget, atomic_json, vote_keys, utc_now

evidence = ROOT / "results/openai-labelling/limit-8191-constructions152"
progress = json.loads((evidence / "progress.json").read_text(encoding="utf-8"))
entries = json.loads((ROOT / "data/votes/limit-8191/api-constructions152/manifest.json").read_text(encoding="utf-8"))
by_batch = {entry["batch_id"]: entry for entry in entries if entry["model_family"] == "sol"}
claims = ROOT / "data/votes/claims"
unowned = []
covered = []
uncertain = []
for result in progress["results"]:
    if "error" not in result:
        continue
    entry = by_batch[result["batch_id"]]
    path = Path(entry["input"])
    batch = json.loads((path if path.is_absolute() else ROOT / path).read_text(encoding="utf-8"))
    for record in batch["records"]:
        single = dict(batch, records=[record])
        keys = vote_keys(single, "sol")
        states = [json.loads((claims / (key + ".json")).read_text(encoding="utf-8"))
                  for key in keys if (claims / (key + ".json")).exists()]
        identity = {"record_id": record["record_id"], "teacher_input_sha256": teacher_input_hash(record)}
        if len(states) == len(keys) and all(state.get("status") == "completed" for state in states):
            covered.append(dict(identity, vote_outputs=sorted({state.get("output", "") for state in states})))
        elif not states:
            unowned.append(record)
        else:
            uncertain.append(dict(identity, statuses=dict(Counter(state.get("status") for state in states))))
    shared_path = claim_path(claims, batch["batch_id"], "sol", batch["input_sha256"])
    if shared_path.exists() and result["error"] == "One or more votes already have an owner.":
        shared = json.loads(shared_path.read_text(encoding="utf-8"))
        if shared.get("owner") == "openai-direct" and shared.get("status") == "claimed":
            shared.update(status="failed_preflight_overlap", no_request_sent=True,
                          updated_at=utc_now(), resolution="Reconciled after queue process exit.")
            atomic_json(shared_path, shared)
budget = OpenAIBudget(ROOT / "results/openai-spend.jsonl")
latest = {row["call_id"]: row for row in budget._rows() if row.get("provider") == "openai"}
actual = sum(row.get("cost_usd", 0) for row in latest.values() if row["status"] == "settled")
reserved = [row for row in latest.values() if row["status"] == "reserved"]
report = {"observed_at": utc_now(), "queue_completed_at": progress["updated_at"],
          "queue_success_calls": sum("error" not in row for row in progress["results"]),
          "queue_success_records": sum(row.get("records", 0) for row in progress["results"] if "error" not in row),
          "covered_overlap_records": covered, "unowned_records": len(unowned),
          "uncertain_records": uncertain, "active_calls": progress["inflight_calls"],
          "pending_calls": progress["remaining_calls"], "actual_spend_usd": actual,
          "outstanding_reserved_usd": sum(row["reserved_charge_usd"] for row in reserved),
          "outstanding_reservations": len(reserved), "budget_remaining_usd": 200 - budget.exposure()}
atomic_json(evidence / "reconciliation.json", report)
destination = ROOT / "data/votes/limit-8191/api152_reconciled_unowned.jsonl"
destination.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in unowned), encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key not in {"covered_overlap_records", "uncertain_records"}},
                 ensure_ascii=False))
print(json.dumps({"covered_overlap_records": len(covered), "uncertain_records": len(uncertain),
                  "unowned_path": str(destination)}))
