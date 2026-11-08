"""Prepare additional grouped development records and report measured coverage."""

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from intent_training.assemble.balance import question_counts
from .freeze import _excluded
from .grouping import assert_split_integrity, grouped_records

INTENT = frozenset({"M1", "M7", "L4", "G1"})
INTENT_SOURCES = frozenset({"swe_chat", "helpsteer3", "misalignment_atlas", "goal_flip", "goal_splice", "in3"})


def _ids(record):
    meta = record.get("_meta", {})
    return {str(value) for field in ("source_id", "source_record_id", "trajectory_id", "conversation_id", "task_id", "record_id", "exposure_id", "group_id")
            for value in (meta.get(field), record.get(field)) if value is not None}


def _precision(count):
    positives = count["positives"]
    negatives = count["rows"] - positives
    if not positives or not negatives:
        return None
    auc = .8
    q1, q2 = auc / (2 - auc), 2 * auc * auc / (1 + auc)
    return math.sqrt((auc * (1 - auc) + (positives - 1) * (q1 - auc * auc)
                      + (negatives - 1) * (q2 - auc * auc)) / (positives * negatives))


def _floors(records, questions):
    """Require precision for every option of choice and score questions."""
    binary = question_counts(records)
    result = {}
    for question in sorted(questions):
        rows = [row for record in records for key, row in record["questions"].items()
                if key.split("#", 1)[0] == question]
        categorical = [row for row in rows if row.get("type") in {"choice", "score"}]
        if categorical:
            if len(categorical) != len(rows):
                raise ValueError("A question cannot mix categorical and binary rows.")
            options = None
            for row in categorical:
                criteria = row["criteria"]
                current = list(criteria) if isinstance(criteria, dict) else [item.split(":", 1)[0] for item in criteria]
                if options is not None and current != options:
                    raise ValueError("A categorical question has inconsistent options.")
                options = current
            classes = {}
            for index, option in enumerate(options):
                count = {"rows": len(rows), "positives": sum(row["label"] == (index if row["type"] == "score" else option) for row in rows)}
                se = _precision(count)
                classes[str(option)] = {**count, "hanley_mcneil_se": se, "passed": se is not None and se <= .035}
            result[question] = {"options": classes, "passed": all(item["passed"] for item in classes.values())}
        else:
            count = binary.get(question, {"rows": 0, "positives": 0})
            se = _precision(count)
            result[question] = {**count, "hanley_mcneil_se": se, "passed": se is not None and se <= .035}
    return result


def prepare(train, population, topups, probe, *, seed, questions, exclusions=()):
    """Sample a separate natural population, then add separately identified top-ups."""
    probe_ids = set().union(*(_ids(row) for row in list(probe) + list(exclusions)))
    for record in train + population + topups:
        if _excluded(record.get("_meta", {})) or _ids(record) & probe_ids:
            raise ValueError("A held-out source or probe identifier entered the development inputs.")
    train_ids = set().union(*(_ids(record) for record in train))
    if any(_ids(record) & train_ids for record in population + topups):
        raise ValueError("A source or exposure identifier crosses a split.")
    # Check the complete candidate pool before sampling, including unused groups.
    def check(train_rows, dev_rows):
        copies = deepcopy({"train": train_rows, "dev": dev_rows})
        for rows in copies.values():
            for row in rows:
                row.get("_meta", {}).pop("split", None)
        return assert_split_integrity(copies)
    check(train, population + topups)
    groups = grouped_records(population)
    ordered = sorted(groups, key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest())
    train_groups = len(grouped_records(train))
    required_groups = math.ceil(train_groups / 9)
    chosen = ordered[:required_groups]
    base = [deepcopy(row) for key in chosen for row in groups[key]]
    extra = deepcopy(topups)
    for name, rows in (("base_dev", base), ("dev_topup", extra)):
        for row in rows:
            row.setdefault("_meta", {})["split"] = name
    check(train, base + extra)
    dev_groups = grouped_records(base + extra)
    eligible = [key for key, rows in dev_groups.items() if any(
        row.get("_meta", {}).get("source") in INTENT_SOURCES for row in rows)]
    eligible.sort(key=lambda key: hashlib.sha256(f"{seed}:intent:{key}".encode()).hexdigest())
    intent = []
    for key in eligible:
        if len(intent) >= 200 and all(item["passed"] for item in _floors(intent, INTENT).values()):
            break
        intent.extend(deepcopy(dev_groups[key]))
    report = {"train_groups": train_groups, "population_groups": len(groups), "required_base_groups": required_groups,
              "base_groups": len(chosen), "base_records": len(base),
              "topup_records": len(extra), "intent_records": len(intent), "base_prevalence": question_counts(base),
              "dev_floors": _floors(base + extra, questions), "intent_floors": _floors(intent, INTENT)}
    report["passed"] = bool(train_groups) and len(chosen) == required_groups and all(x["passed"] for x in report["dev_floors"].values()) and all(x["passed"] for x in report["intent_floors"].values()) and len(intent) >= 200
    return {"base_dev": base, "dev_topup": extra, "intent": intent}, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("train", "population", "topups", "probe", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--questions", nargs="+", required=True)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()
    def read(path):
        with open(path, encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]
    exclusions = [row for path in args.exclude for row in read(path)]
    splits, manifest = prepare(read(args.train), read(args.population), read(args.topups), read(args.probe), seed=args.seed, questions=args.questions, exclusions=exclusions)
    manifest["inputs"] = {name: {"path": getattr(args, name), "sha256": hashlib.sha256(Path(getattr(args, name)).read_bytes()).hexdigest()}
                          for name in ("train", "population", "topups", "probe")}
    manifest["exclusions"] = [{"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()} for path in args.exclude]
    dest = Path(args.output)
    dest.mkdir(parents=True, exist_ok=True)
    for name, rows in splits.items():
        with (dest / (name + ".jsonl")).open("x", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with (dest / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
