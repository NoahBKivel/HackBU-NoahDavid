"""Combine measured pilot chunks without losing the first API-start timestamp."""

from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher.openai_client_state import atomic_json

evidence = ROOT / "results/openai-labelling"
chunks = [json.loads(path.read_text(encoding="utf-8")) for path in
          (evidence / "projection.json", evidence / "chunk2/projection.json")]
records = sum(row["paired_records"] for row in chunks)
cost = sum(row["measured_cost_usd"] for row in chunks)
first = min(row["started_at"] for row in chunks)
last = max(row["completed_at"] for row in chunks)
duration = (datetime.fromisoformat(last) - datetime.fromisoformat(first)).total_seconds()
active = sum((datetime.fromisoformat(row["completed_at"]) - datetime.fromisoformat(
    row["started_at"])).total_seconds() for row in chunks)
train = chunks[0]["train_records"]
result = {"started_at": first, "completed_at": last, "paired_records": records,
          "measured_cost_usd": cost, "cost_per_pair_usd": cost / records,
          "train_records": train, "projected_train_cost_usd": cost / records * train,
          "paired_records_per_hour_including_chunk_gap": records * 3600 / duration,
          "paired_records_per_hour_during_client_processes": records * 3600 / active,
          "end_to_end_seconds": duration, "active_client_seconds": active,
          "remaining_openai_budget_usd": 200 - cost,
          "additional_records_at_observed_cost": int((200 - cost) / (cost / records)),
          "price_source": chunks[0]["price_source"],
          "scope": chunks[0]["scope"], "projection_assumption": chunks[0]["projection_assumption"],
          "reported_to_owner_at": None,
          "usage_by_family": {family: {key: sum(chunk["usage_by_family"][family][key] for chunk in chunks)
                                      for key in chunks[0]["usage_by_family"][family]}
                              for family in chunks[0]["usage_by_family"]}}
atomic_json(evidence / "pilot50-projection.json", result)
print(json.dumps(result))
