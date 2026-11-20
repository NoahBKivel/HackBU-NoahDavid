"""Choose intact linked groups under exact composition and source allocations."""

from collections import Counter, defaultdict
import hashlib

from .labels import positive, record_digest
from .native import original_native


def composition_kind(record):
    """Distinguish explicit screen constructions from overflowing task records."""
    if original_native(record):
        return record["_meta"]["record_kind"]
    meta = record["_meta"]
    marker = meta.get("construction") or meta.get("construction_type")
    if isinstance(marker, dict):
        marker = marker.get("type")
    return "screen" if str(marker).replace("-", "_") == "overflow_screen" else "task"


def _rank(group, floors, seed):
    score = sum(1 / max(1, floors.get(key.split("#", 1)[0], 1))
                for row in group if not original_native(row)
                for key, question in row["questions"].items()
                if "~neg" not in key and positive(key, question["label"]))
    digest = hashlib.sha256((str(seed) + ":" + record_digest(group)).encode()).hexdigest()
    return -score / len(group), digest


def exact_groups(groups, count, *, floors, seed):
    """Prefer priority evidence while preserving exact complete-group line counts."""
    ordered = sorted(groups, key=lambda group: _rank(group, floors, seed))
    mask = (1 << (count + 1)) - 1
    reachable = [0] * (len(ordered) + 1)
    reachable[-1] = 1
    for index in range(len(ordered) - 1, -1, -1):
        reachable[index] = (reachable[index + 1] | reachable[index + 1] << len(ordered[index])) & mask
    if not (reachable[0] >> count) & 1:
        raise ValueError(f"Complete groups cannot supply exactly {count} training lines.")
    selected, remaining = [], count
    for index, group in enumerate(ordered):
        size = len(group)
        if size <= remaining and (reachable[index + 1] >> (remaining - size)) & 1:
            selected.extend(group)
            remaining -= size
    return selected


def _allocations(composition):
    expected = composition["expected"]
    parts = {kind: expected.get(kind, 0) for kind in ("replay", "long", "screen")}
    parts["task"] = expected["train"] - sum(parts.values())
    if min(parts.values()) < 0:
        raise ValueError("The composition has a negative task allocation.")
    sources = composition.get("source_quotas", {})
    nested = bool(sources) and all(isinstance(value, dict) for value in sources.values())
    targets = {("part", kind): count for kind, count in parts.items()}
    if sources:
        if nested:
            if any(sum(sources.get(kind, {}).values()) != count for kind, count in parts.items()):
                raise ValueError("Source allocations differ from the declared composition parts.")
            targets = {("source_part", kind, source): count for kind, allocations in sources.items()
                       for source, count in allocations.items()}
        else:
            if sum(sources.values()) != expected["train"]:
                raise ValueError("Source allocations must sum to the declared training line count.")
            targets.update({("source", source): count for source, count in sources.items()})
    suites = composition.get("replay_quotas", {})
    if suites:
        if sum(suites.values()) != parts["replay"]:
            raise ValueError("Native replay suite allocations must sum to the replay count.")
        targets.update({("suite", suite): count for suite, count in suites.items()})
    def coordinates(record):
        meta, kind = record["_meta"], composition_kind(record)
        result = [("source_part", kind, meta["source"])] if nested else [("part", kind)]
        if sources and not nested:
            result.append(("source", meta["source"]))
        if kind == "replay" and suites:
            result.append(("suite", meta.get("suite", meta["source"])))
        return result
    return targets, coordinates


def joint_groups(groups, *, composition, floors, seed):
    """Select whole groups jointly wherever their quota coordinates overlap."""
    targets, coordinates = _allocations(composition)
    vectors = [Counter(key for record in group for key in coordinates(record)) for group in groups]
    available = sum(vectors, Counter())
    if any(available[key] < count for key, count in targets.items()):
        raise ValueError("An allocation has too few eligible complete group lines.")
    neighbors = defaultdict(set)
    for vector in vectors:
        for key in vector:
            neighbors[key].update(vector)
    remaining, selected = set(neighbors), []
    while remaining:
        component, frontier = set(), {min(remaining)}
        while frontier:
            component.update(frontier)
            frontier = set().union(*(neighbors[key] for key in frontier)) - component
        remaining -= component
        indices = [index for index, vector in enumerate(vectors) if component.intersection(vector)]
        if len(component) == 1:
            key = next(iter(component))
            selected.extend(exact_groups([groups[index] for index in indices], targets.get(key, 0),
                                         floors=floors, seed=seed))
            continue
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
        from scipy.sparse import csc_matrix
        keys = sorted(component)
        row_indices, col_indices, values = [], [], []
        lookup = {key: index for index, key in enumerate(keys)}
        ordered = sorted(indices, key=lambda index: _rank(groups[index], floors, seed))
        for column, index in enumerate(ordered):
            for key, count in vectors[index].items():
                row_indices.append(lookup[key]); col_indices.append(column); values.append(count)
        matrix = csc_matrix((values, (row_indices, col_indices)), shape=(len(keys), len(ordered)), dtype=float)
        counts = np.array([targets.get(key, 0) for key in keys], dtype=float)
        objective = np.array([_rank(groups[index], floors, seed)[0] * len(groups[index])
                              + (rank + 1) / (len(ordered) + 1) * 1e-8
                              for rank, index in enumerate(ordered)])
        result = milp(objective, integrality=np.ones(len(ordered)), bounds=Bounds(0, 1),
                      constraints=LinearConstraint(matrix, counts, counts),
                      options={"mip_rel_gap": 0.0})
        if not result.success or result.x is None:
            raise ValueError("Complete groups cannot supply the exact joint allocations.")
        chosen = [ordered[index] for index, value in enumerate(result.x) if value > 0.5]
        measured = sum((vectors[index] for index in chosen), Counter())
        if any(measured[key] != targets.get(key, 0) for key in keys):
            raise ValueError("The integer solution differs from the exact joint allocations.")
        selected.extend(record for index in chosen for record in groups[index])
    measured = Counter(key for record in selected for key in coordinates(record))
    if any(measured[key] != count for key, count in targets.items()):
        raise ValueError("Selected line counts differ from their declared allocations.")
    return selected
