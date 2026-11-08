"""Compute per-question discrimination from uncalibrated decision logits."""

import math
from collections import defaultdict
from typing import Any, Iterable

import numpy as np


def probabilities(logits: list[float]) -> list[float]:
    """Convert finite logits to stable normalized probabilities."""
    values = np.asarray(logits, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Each question needs at least two finite logits.")
    values = np.exp(values - values.max())
    return (values / values.sum()).tolist()


def auroc(labels: Iterable[bool], scores: Iterable[float]) -> float:
    """Compute exact rank AUROC, giving tied scores half credit."""
    y, score = np.asarray(list(labels), dtype=bool), np.asarray(list(scores), dtype=float)
    if y.shape != score.shape or y.ndim != 1 or not np.isfinite(score).all():
        raise ValueError("Labels and finite scores must be aligned vectors.")
    positive = int(y.sum())
    negative = len(y) - positive
    if not positive or not negative:
        raise ValueError("AUROC requires both positive and negative labels.")
    order = np.argsort(score, kind="stable")
    sorted_score, sorted_y = score[order], y[order]
    boundaries = np.r_[0, np.flatnonzero(np.diff(sorted_score)) + 1, len(y)]
    rank_sum = 0.0
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        rank_sum += float(sorted_y[start:end].sum()) * (start + 1 + end) / 2
    return (rank_sum - positive * (positive + 1) / 2) / (positive * negative)


def question_aurocs(rows: Iterable[dict[str, Any]], *, intent_only: bool = False) -> dict[str, float]:
    """Average option AUROCs within each base question, excluding training twins."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        question = row["question_id"]
        if "~neg" in question:
            continue
        base = question.split("#", 1)[0]
        if intent_only and (not row.get("is_intent") or base not in {"M1", "M7", "L4", "G1"}):
            continue
        grouped[base].append(row)
    if not grouped:
        raise ValueError("No served question rows are available.")
    result = {}
    for question, values in grouped.items():
        options = values[0]["options"]
        if any(row["options"] != options for row in values):
            raise ValueError(f"Option order differs within {question}.")
        distributions = [probabilities(row["logits"]) for row in values]
        selected = [options.index("true")] if options == ["false", "true"] else range(len(options))
        result[question] = float(np.mean([
            auroc([row["label"] == options[index] for row in values], [p[index] for p in distributions])
            for index in selected
        ]))
    return result


def macro_auroc(rows: Iterable[dict[str, Any]], *, intent_only: bool = False) -> float:
    """Average base-question AUROCs with equal weight per question."""
    result = float(np.mean(list(question_aurocs(rows, intent_only=intent_only).values())))
    if not math.isfinite(result):
        raise ValueError("The discrimination score is not finite.")
    return result
