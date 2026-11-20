"""Keep linked records in the same optimizer step."""

from collections import defaultdict
import math
from typing import Any


def linked_units(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Collect transitively linked pair and sibling records in encounter order."""
    roots = list(range(len(records)))

    def find(index: int) -> int:
        while roots[index] != index:
            roots[index] = roots[roots[index]]
            index = roots[index]
        return index

    def join(left: int, right: int) -> None:
        roots[find(right)] = find(left)

    labels: dict[tuple[str, str], int] = {}
    ids = {str(record.get("_meta", {}).get("id")): i for i, record in enumerate(records)
           if record.get("_meta", {}).get("id") is not None}
    for i, record in enumerate(records):
        meta = record.get("_meta", {})
        for field in ("pair_id", "sibling_group", "sibling_id"):
            if meta.get(field) is not None:
                key = field, str(meta[field])
                if key in labels:
                    join(i, labels[key])
                else:
                    labels[key] = i
        for field in ("parent_id", "sibling_of"):
            if str(meta.get(field)) in ids:
                join(i, ids[str(meta[field])])
    units: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for i, record in enumerate(records):
        units[find(i)].append(record)
    return list(units.values())


def optimizer_groups(records: list[dict[str, Any]], effective_batch: int) -> list[list[dict[str, Any]]]:
    """Place linked units intact into exactly ceil(record count / batch) steps."""
    if effective_batch < 1:
        raise ValueError("The effective batch must be positive.")
    if not records:
        return []
    units = linked_units(records)
    count = math.ceil(len(records) / effective_batch)
    if len(units) < count:
        raise ValueError("Too few independent linked units for the required optimizer-step count.")
    if any(len(unit) > effective_batch for unit in units):
        raise ValueError("A linked unit exceeds the required effective batch size.")
    groups: list[list[dict[str, Any]]] = [[] for _ in range(count)]
    loads = [0] * count
    for unit in sorted(units, key=len, reverse=True):
        available = [i for i, load in enumerate(loads) if load + len(unit) <= effective_batch]
        if not available:
            raise ValueError("Linked units cannot be packed by the deterministic planner into the required optimizer-step count.")
        index = max(available, key=lambda i: (loads[i], -i))
        groups[index].extend(unit)
        loads[index] += len(unit)
    return groups


def microbatch_plan(native: Any, records: list[dict[str, Any]], args: Any,
                    world: int, rank: int, pairs: Any = None,
                    shapes: dict[int, Any] | None = None) -> list[tuple[list[dict], int, bool]]:
    """Plan bounded passes without separating linked records across optimizer steps."""
    if world != 1 or rank != 0:
        raise ValueError("Linked decision training supports the specified single GPU only.")
    if not records:
        return []
    if shapes is None:
        import json
        shapes = {id(record): [(len(json.dumps(record["state"], ensure_ascii=False)),
                               [len(json.dumps(q, ensure_ascii=False))
                                for q in record["questions"].values()])]
                  for record in records}
    cap = args.pass_tokens_max if args.length_sort else 0

    def cost(items: list[dict[str, Any]]) -> int:
        return native.pass_tokens([shape for record in items for shape in shapes[id(record)]], args.shared_prefix)

    if cap and any(cost([record]) > cap for record in records):
        raise ValueError("A single record exceeds the measured padded-token cap.")
    result = []
    for group in optimizer_groups(records, args.batch * args.accum):
        ordered = sorted(group, key=lambda record: cost([record]), reverse=True) if args.length_sort else group
        physical_limit = args.batch * args.accum if cap else args.batch
        runs_count = min(len(group), math.ceil(len(group) / physical_limit))
        runs = native.balanced_runs(ordered, runs_count, cost)
        while cap and max(map(cost, runs)) > cap:
            runs_count += 1
            runs = native.balanced_runs(ordered, runs_count, cost)
        result.extend((run, len(group), i == len(runs) - 1) for i, run in enumerate(runs))
    return result
