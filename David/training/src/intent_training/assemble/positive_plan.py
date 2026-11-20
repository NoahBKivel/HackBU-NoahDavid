"""Compute positive expectations from a fixed plan and independent evidence."""

from fractions import Fraction
from typing import Any


POSITIVE_QUESTIONS = ("M1", "M2", "M4", "M5", "M7", "L1", "L2", "L4", "L5", "L6", "G1", "G2", "G4", "G5", "RF")
REPORTED_QUESTIONS = ("SCR", "M8", "D1", "D3", "D2")


def is_positive(question: str, value: Any) -> bool:
    """Recognize the monitor's positive class without conflating choice classes."""
    if question == "G1":
        return value is False or value == "no"
    if question == "G2":
        return value in ("broken", "not done")
    return value is True or value == "yes"


def distribute(total: int, weights: dict[str, Fraction]) -> dict[str, int]:
    """Allocate a fixed count by largest remainders with stable tie breaking."""
    if total < 0 or not weights or any(value < 0 for value in weights.values()):
        raise ValueError("Allocation needs nonnegative counts and weights.")
    denominator = sum(weights.values())
    if denominator <= 0:
        raise ValueError("Allocation weights must have positive mass.")
    exact = {key: total * value / denominator for key, value in weights.items()}
    result = {key: value.numerator // value.denominator for key, value in exact.items()}
    order = sorted(exact, key=lambda key: (-(exact[key] - result[key]), key))
    for key in order[:total - sum(result.values())]:
        result[key] += 1
    return result


def redistribute_shortfalls(quotas: dict[str, int], capacities: dict[str, int],
                           weights: dict[str, Fraction]) -> dict[str, int]:
    """Redistribute unavailable records proportionally within one objective."""
    if quotas.keys() != capacities.keys() or quotas.keys() != weights.keys():
        raise ValueError("Quota, capacity and weight entries must identify the same sources.")
    if any(value < 0 for value in quotas.values()) or any(value < 0 for value in capacities.values()):
        raise ValueError("Quotas and capacities must be nonnegative.")
    result = {key: min(quotas[key], capacities[key]) for key in quotas}
    remaining = sum(quotas.values()) - sum(result.values())
    while remaining:
        active = {key: weights[key] for key in quotas if result[key] < capacities[key] and weights[key] > 0}
        if not active:
            raise ValueError("The objective's prepared capacity cannot absorb its quota shortfall.")
        mass = sum(active.values())
        saturated = [key for key, weight in active.items()
                     if remaining * weight / mass >= capacities[key] - result[key]]
        if saturated:
            for key in saturated:
                amount = capacities[key] - result[key]
                result[key] += amount
                remaining -= amount
        else:
            additions = distribute(remaining, active)
            for key, amount in additions.items():
                result[key] += amount
            remaining = 0
    return result


def preregister(entries: list[dict[str, Any]], *, scale: Fraction,
                blockers: list[str]) -> dict[str, Any]:
    """Calculate floors from declared evidence, refusing a false seal."""
    expected = {question: Fraction(0) for question in POSITIVE_QUESTIONS + REPORTED_QUESTIONS}
    pending = list(blockers)
    for entry in entries:
        kind = entry["kind"]
        if kind not in {"dataset_visible", "construction", "teacher", "generated", "native"}:
            raise ValueError("Each planned source needs an explicit provenance kind.")
        shares = entry.get("positive_shares", {})
        if kind in {"teacher", "generated", "native"} and any(Fraction(str(v)) for v in shares.values()):
            raise ValueError("Teacher and generated source positive shares must remain zero.")
        if kind in {"dataset_visible", "construction"} and not entry.get("evidence_fixed"):
            pending.append(f"Unfixed positive-share evidence: {entry['id']}.")
        for question, share in shares.items():
            share = Fraction(str(share))
            if not 0 <= share <= 1:
                raise ValueError("A source positive share must be between zero and one.")
            if question in expected:
                multiplier = scale if entry["part"] == "task" else Fraction(1)
                expected[question] += multiplier * Fraction(str(entry["effective_nplan"])) * share
    values = {question: float(value) for question, value in expected.items()}
    return {"status": "sealed" if not pending else "provisional", "blockers": sorted(set(pending)),
            "scale": float(scale), "scale_exact": str(scale),
            "expected": values, "expected_exact": {q: str(v) for q, v in expected.items()},
            "floors": {q: float(max(Fraction(4, 5) * expected[q], 60)) for q in POSITIVE_QUESTIONS},
            "reported_questions": list(REPORTED_QUESTIONS),
            "excluded_positive_floor_questions": ["L7", "D5"], "sources": entries}
