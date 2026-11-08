"""Build deterministic transitively linked train and development groups."""

from collections import defaultdict
from copy import deepcopy
import hashlib
import math

from intent_training.assemble.labels import record_digest


def grouped_records(records):
    """Join pair, trajectory, task and sibling relationships transitively."""
    roots = list(range(len(records)))
    def find(index):
        while roots[index] != index:
            roots[index] = roots[roots[index]]
            index = roots[index]
        return index
    def join(a, b):
        roots[find(b)] = find(a)
    seen = {}
    for index, record in enumerate(records):
        meta = record.get("_meta", {})
        keys = [(field, str(meta[field]) if field in {"pair_id", "sibling_group", "group_id"}
                 else (str(meta.get("source", "")), str(meta[field]))) for field in
                ("pair_id", "trajectory_id", "task_id", "sibling_group", "group_id",
                 "source_id", "source_record_id", "exposure_id") if meta.get(field) is not None]
        if not any(field in {"pair_id", "trajectory_id", "task_id"} for field, _ in keys):
            if not meta.get("source"):
                raise ValueError("An ungrouped record needs its source as the fallback group.")
            keys.append(("source", str(meta["source"])))
        # Identical model inputs must not leak across the split, even with different labels.
        keys.append(("input", record_digest({"state": record["state"], "questions": {
            key: {k: v for k, v in row.items() if k not in {"label", "target"}}
            for key, row in record["questions"].items()}})))
        for key in keys:
            if key in seen:
                join(index, seen[key])
            else:
                seen[key] = index
    groups = defaultdict(list)
    for index, record in enumerate(records):
        groups[find(index)].append(record)
    result = {}
    for group in groups.values():
        chosen = None
        for field in ("pair_id", "trajectory_id", "task_id", "source"):
            values = sorted({str(r.get("_meta", {})[field]) for r in group
                             if r.get("_meta", {}).get(field) is not None})
            if values:
                chosen = field + ":" + values[0]
                break
        digest = hashlib.sha256("\n".join(sorted(record_digest(r) for r in group)).encode()).hexdigest()
        result[chosen + ":" + digest] = group
    return result


def split_records(records, *, seed, dev_fraction=0.1):
    """Assign base development groups before any prevalence-altering top-ups."""
    if not 0 < dev_fraction < 1:
        raise ValueError("The development fraction must lie between zero and one.")
    groups = grouped_records(deepcopy(records))
    ordered = sorted(groups, key=lambda group: hashlib.sha256(f"{seed}:{group}".encode()).hexdigest())
    count = math.ceil(len(ordered) * dev_fraction)
    dev_groups = set(ordered[:count])
    result = {"train": [], "base_dev": []}
    for group_id in ordered:
        split = "base_dev" if group_id in dev_groups else "train"
        for record in groups[group_id]:
            meta = record.setdefault("_meta", {})
            meta["group_id"] = group_id
            meta["split"] = split
            result[split].append(record)
    assert_split_integrity(result)
    return result


def assert_split_integrity(splits):
    """Reject a leaked transitive group, including planted pair leaks."""
    records = []
    destinations = {}
    for split, members in splits.items():
        for record in members:
            records.append(record)
            destinations[id(record)] = split
            declared = record.get("_meta", {}).get("split")
            if declared is not None and declared != split and not (split == "dev" and declared in {"base_dev", "dev_topup"}):
                raise ValueError("A record's declared split differs from its destination.")
    for group in grouped_records(records).values():
        if len({destinations[id(record)] for record in group}) != 1:
            raise ValueError("A linked pair, sibling, trajectory, task or source group crosses a split.")
    return {"groups": len(grouped_records(records)), "records": len(records), "cross_split_groups": 0}


def add_dev_topups(splits, records):
    """Attach rare-question top-ups without changing natural base-dev prevalence."""
    result = deepcopy(splits)
    topups = deepcopy(records)
    for record in topups:
        record.setdefault("_meta", {})["split"] = "dev_topup"
    result["dev_topup"] = topups
    # Top-ups may share base-dev groups, but must never share a training group.
    assert_split_integrity({"train": result["train"], "dev": result.get("base_dev", []) + topups})
    return result
