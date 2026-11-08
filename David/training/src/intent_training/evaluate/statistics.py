"""Paired accuracy intervals with complete group resampling."""

from collections import defaultdict
import math
import random
from statistics import NormalDist
from typing import Any, Iterable


def proportion_interval(successes: int, total: int, confidence: float = 0.95) -> dict[str, Any]:
    """Return a Wilson interval and its explicitly counted denominator."""
    if total <= 0 or not 0 <= successes <= total or not 0 < confidence < 1:
        raise ValueError("A proportion needs valid counts and confidence.")
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return {"n": total, "successes": successes, "value": p,
            "interval": [max(0.0, centre - radius), min(1.0, centre + radius)],
            "confidence": confidence, "interval_method": "Wilson"}


def _quantile(values: list[float], fraction: float) -> float:
    position = (len(values) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    return values[low] + (position - low) * (values[high] - values[low])


def paired_accuracy(items: Iterable[dict[str, Any]], *, resamples: int = 10000,
                    seed: int = 1, confidence: float = 0.95) -> dict[str, Any]:
    """Bootstrap tuned minus stock accuracy by resampling entire paired groups."""
    rows = list(items)
    if not rows or resamples < 2 or not 0 < confidence < 1:
        raise ValueError("A paired interval needs observations and at least two resamples.")
    groups: dict[str, list[tuple[int, int]]] = defaultdict(list)
    keys: set[tuple[str, str]] = set()
    for row in rows:
        if any(row.get(field) is None or str(row[field]) == "" for field in ("record_id", "question_id", "group_id")):
            raise ValueError("Paired observations require explicit record, question and group identities.")
        key = (str(row["record_id"]), str(row["question_id"]))
        if key in keys:
            raise ValueError("Repeated record/question would change the evaluation denominator.")
        keys.add(key)
        selected, stock = row["selected_correct"], row["stock_correct"]
        if type(selected) is not bool or type(stock) is not bool:
            raise ValueError("Correctness observations must be booleans.")
        group = str(row["group_id"])
        if not group:
            raise ValueError("Every paired observation requires a group identifier.")
        groups[group].append((int(selected), int(stock)))
    totals = [(sum(a - b for a, b in group), len(group)) for group in groups.values()]
    generator = random.Random(seed)
    distribution = []
    for _ in range(resamples):
        sample = generator.choices(totals, k=len(totals))
        distribution.append(sum(delta for delta, _ in sample) / sum(n for _, n in sample))
    distribution.sort()
    tail = (1 - confidence) / 2
    selected_count = sum(row["selected_correct"] for row in rows)
    stock_count = sum(row["stock_correct"] for row in rows)
    return {"n": len(rows), "groups": len(groups), "selected_accuracy": selected_count / len(rows),
            "stock_accuracy": stock_count / len(rows), "difference": (selected_count - stock_count) / len(rows),
            "interval": [_quantile(distribution, tail), _quantile(distribution, 1 - tail)],
            "confidence": confidence, "interval_method": "paired group bootstrap percentile",
            "resamples": resamples, "seed": seed}
