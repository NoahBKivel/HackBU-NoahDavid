"""Keep explicitly reserved development task groups out of training."""

import json
from pathlib import Path


def load_reservations():
    folder = Path(__file__).resolve().parents[3] / "data/exclusions"
    result = []
    for path in sorted(folder.glob("dev-*-reservations.jsonl")):
        with path.open(encoding="utf-8") as handle:
            result.extend(json.loads(line) for line in handle if line.strip())
    return result


def reserved(record, reservations):
    meta = record.get("_meta", {})
    for item in reservations:
        if meta.get("source") != item["source"]:
            continue
        if item.get("task_id") is not None and meta.get("task_id") == item["task_id"]:
            return True
        if meta.get("trajectory_id") in item.get("trajectory_ids", []):
            return True
        if item.get("pair_id") is not None and meta.get("pair_id") == item["pair_id"]:
            return True
    return False
