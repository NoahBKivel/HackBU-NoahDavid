"""Select candidates by paired group uncertainty and intent discrimination."""

from collections import defaultdict
from typing import Any

import numpy as np

from .metrics import macro_auroc, probabilities, question_aurocs


def _key(row: dict[str, Any]) -> tuple[str, str]:
    return row["record_id"], row["question_id"]


def _plans(rows: list[dict[str, Any]]) -> list[list[tuple[np.ndarray, np.ndarray, np.ndarray]]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        if "~neg" not in row["question_id"]:
            grouped[row["question_id"].split("#", 1)[0]].append(index)
    plans = []
    for indices in grouped.values():
        options = rows[indices[0]]["options"]
        selected = [options.index("true")] if options == ["false", "true"] else range(len(options))
        distributions = np.asarray([probabilities(rows[index]["logits"]) for index in indices])
        classes = []
        for option in selected:
            order = np.argsort(distributions[:, option], kind="stable")
            ordered = np.asarray(indices)[order]
            scores = distributions[order, option]
            starts = np.r_[0, np.flatnonzero(np.diff(scores)) + 1]
            positives = np.array([rows[index]["label"] == options[option] for index in ordered])
            classes.append((ordered, starts, positives))
        plans.append(classes)
    return plans


def _sampled_score(plans: list[list[tuple[np.ndarray, np.ndarray, np.ndarray]]],
                   counts: np.ndarray) -> float:
    questions = []
    for classes in plans:
        areas = []
        for order, starts, positives in classes:
            weights = counts[order]
            pos = np.add.reduceat(weights * positives, starts)
            neg = np.add.reduceat(weights * ~positives, starts)
            if not pos.sum() or not neg.sum():
                raise ValueError("AUROC requires both positive and negative labels.")
            concordant = np.sum(pos * (np.cumsum(neg) - 0.5 * neg))
            areas.append(float(concordant / (pos.sum() * neg.sum())))
        questions.append(float(np.mean(areas)))
    return float(np.mean(questions))


def select_candidate(candidates: dict[str, list[dict[str, Any]]], *, stock: str,
                     resamples: int = 1000, seed: int = 1) -> dict[str, Any]:
    """Keep candidates within one paired bootstrap SE and rank them on intent."""
    if stock not in candidates or not candidates or resamples < 2:
        raise ValueError("Stock and at least two bootstrap resamples are required.")
    names = list(candidates)
    reference = {_key(row): row for row in candidates[names[0]]}
    if len(reference) != len(candidates[names[0]]):
        raise ValueError("A candidate has duplicate record/question rows.")
    aligned = {}
    for name, rows in candidates.items():
        lookup = {_key(row): row for row in rows}
        if len(lookup) != len(rows) or lookup.keys() != reference.keys():
            raise ValueError("All candidates must score the same unique dev rows.")
        for key, row in lookup.items():
            other = reference[key]
            fields = ("group_id", "options", "label", "is_intent", "is_base_dev")
            if any(row.get(field) != other.get(field) for field in fields):
                raise ValueError("Candidate labels, groups and dev membership must match.")
        aligned[name] = [lookup[key] for key in reference]
    scores = {name: macro_auroc(rows) for name, rows in aligned.items()}
    intent = {name: macro_auroc(rows, intent_only=True) for name, rows in aligned.items()}
    best = max(names, key=lambda name: scores[name])
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(aligned[names[0]]):
        groups[row["group_id"]].append(index)
    keys = list(groups)
    if len(keys) < 2:
        raise ValueError("Group bootstrap requires at least two independent dev groups.")
    rng = np.random.default_rng(seed)
    row_groups = np.empty(len(reference), dtype=int)
    for index, group in enumerate(keys):
        row_groups[groups[group]] = index
    plans = {name: _plans(rows) for name, rows in aligned.items()}
    differences: dict[str, list[float]] = {name: [] for name in names}
    rejected = 0
    for attempt in range(resamples * 100):
        multiplicity = np.bincount(rng.integers(len(keys), size=len(keys)), minlength=len(keys))
        counts = multiplicity[row_groups]
        try:
            sampled = {name: _sampled_score(plan, counts) for name, plan in plans.items()}
        except ValueError as error:
            if "requires both positive and negative" not in str(error):
                raise
            rejected += 1
            continue
        for name in names:
            differences[name].append(sampled[best] - sampled[name])
        if len(differences[best]) == resamples:
            break
    if len(differences[best]) != resamples:
        raise ValueError("Too few bootstrap samples contain every question class.")
    standard_errors = {name: float(np.std(values, ddof=1)) for name, values in differences.items()}
    kept = [name for name in names if scores[best] - scores[name] <= standard_errors[name] + 1e-12]
    ranked = sorted(kept, key=lambda name: -intent[name])
    pick_order = ranked + ([stock] if stock not in ranked else [])
    return {"selected": ranked[0], "best_dev": best, "kept": kept, "pick_order": pick_order,
            "dev_auroc": scores, "intent_auroc": intent, "paired_difference_se": standard_errors,
            "per_question_auroc": {name: question_aurocs(rows) for name, rows in aligned.items()},
            "resamples": resamples, "rejected_degenerate_resamples": rejected, "seed": seed,
            "dev_groups": len(groups), "question_rows": len(reference)}
