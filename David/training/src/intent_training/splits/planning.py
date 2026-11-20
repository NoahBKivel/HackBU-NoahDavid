"""Pre-register source-derived expected positives before teacher observations."""

import math

TRAIN_RECORDS = 12200
REPLAY_RECORDS = 3000
LONG_RECORDS = 400
SCREEN_RECORDS = 200
TASK_RECORDS = TRAIN_RECORDS - REPLAY_RECORDS - LONG_RECORDS - SCREEN_RECORDS


def source_quotas(entries):
    """Scale task-source quotas with largest remainders while retaining the total."""
    total = sum(entry["planned_count"] for entry in entries)
    if total <= 0:
        raise ValueError("The source plan must contain positive quotas.")
    scaled = [(entry["slug"], TASK_RECORDS * entry["planned_count"] / total) for entry in entries]
    output = {slug: math.floor(count) for slug, count in scaled}
    for slug, _ in sorted(scaled, key=lambda item: (-(item[1] - math.floor(item[1])), item[0]))[:TASK_RECORDS - sum(output.values())]:
        output[slug] += 1
    return {"scale": TASK_RECORDS / total, "planned_total": total, "quotas": output}


def preregister_positives(source_plan, *, questions, scale):
    """Use raw visible-source counts or intended constructions, never teacher outcomes."""
    expected = {question: 0.0 for question in questions}
    evidence = []
    for source in source_plan:
        kind = source["kind"]
        if kind not in {"visible", "construction", "teacher"}:
            raise ValueError("Positive expectations require a declared source provenance kind.")
        if kind == "teacher":
            shares = {}
        elif kind == "construction":
            shares = source["intended_shares"]
        else:
            population = source["population_count"]
            if population <= 0 or not source.get("raw_source_sha256"):
                raise ValueError("Visible expectations need counted raw rows and their source hash.")
            shares = {q: count / population for q, count in source["positive_counts"].items()}
        for question, share in shares.items():
            if not 0 <= share <= 1:
                raise ValueError("A pre-registered positive share is outside zero to one.")
            if question in expected:
                expected[question] += scale * source["planned_count"] * share
        evidence.append(source.copy())
    return {"expected": expected, "floors": {q: max(0.8 * count, 60) for q, count in expected.items()},
            "scale": scale, "sources": evidence, "basis": "raw_visible_counts_and_intended_constructions"}


def minimum_dev_positives(*, auc=0.8, max_se=0.035, negatives_per_positive=10):
    """Compute the Hanley-McNeil positive count for the declared AUROC estimate."""
    if not 0 < auc < 1 or max_se <= 0 or negatives_per_positive <= 0:
        raise ValueError("AUROC and sampling parameters must be positive and bounded.")
    q1, q2 = auc / (2 - auc), 2 * auc * auc / (1 + auc)
    for positives in range(2, 1000000):
        negatives = max(2, math.ceil(positives * negatives_per_positive))
        variance = (auc * (1 - auc) + (positives - 1) * (q1 - auc * auc)
                    + (negatives - 1) * (q2 - auc * auc)) / (positives * negatives)
        if math.sqrt(variance) <= max_se:
            return positives
    raise ValueError("The requested development precision needs an unsupported sample count.")
