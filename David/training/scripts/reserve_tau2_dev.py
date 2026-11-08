"""Reserve whole tau2 task groups for development before training selection."""

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "data/converted/tau2.jsonl"
    groups = defaultdict(list)
    trajectory_tasks = defaultdict(set)
    for line in source.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        meta = row["meta"]
        if meta["source"] != "tau2":
            raise ValueError("A different source entered the tau2 reservation.")
        groups[meta["task_id"]].append(row)
        trajectory_tasks[meta["trajectory_id"]].add(meta["task_id"])
    if any(len(tasks) != 1 for tasks in trajectory_tasks.values()):
        raise ValueError("A tau2 trajectory spans multiple task groups.")
    ordered = sorted(groups, key=lambda key: hashlib.sha256(("dev:tau2:" + key).encode()).hexdigest())
    selected = set(ordered[:math.ceil(len(ordered) / 10)])
    remaining = Counter(row["meta"]["slice"] for task, rows in groups.items() if task not in selected for row in rows)
    plan = json.loads((ROOT / "src/intent_training/sources/entries/tau2.json").read_text(encoding="utf-8"))
    if any(remaining[item["name"]] < item["planned_count"] for item in plan["slices"]):
        raise ValueError("The remaining source cannot satisfy its existing slice plan.")
    rows = [row for task in ordered if task in selected for row in groups[task]]
    destination = ROOT / "data/dev_candidates/tau2.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            row["meta"]["split"] = "dev"
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    exclusion = ROOT / "data/exclusions/dev-tau2-reservations.jsonl"
    exclusion.parent.mkdir(parents=True, exist_ok=True)
    with exclusion.open("x", encoding="utf-8", newline="\n") as stream:
        for task in sorted(selected):
            stream.write(json.dumps({"source": "tau2", "task_id": task,
                                     "trajectory_ids": sorted({row["meta"]["trajectory_id"] for row in groups[task]})}) + "\n")
    report = {"source": "tau2", "all_task_groups": len(groups), "reserved_task_groups": len(selected),
              "reserved_records": len(rows), "reserved_slices": dict(Counter(row["meta"]["slice"] for row in rows)),
              "remaining_records_by_slice": dict(remaining), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "candidates_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
              "exclusions_sha256": hashlib.sha256(exclusion.read_bytes()).hexdigest(),
              "candidates": str(destination), "exclusions": str(exclusion)}
    path = ROOT / "results/sources/tau2-dev-reservation.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
