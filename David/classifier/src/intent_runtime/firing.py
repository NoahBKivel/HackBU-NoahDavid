"""Derive problem scores and the fired set from calibrated answers."""

from David.monitor_format import EVERY_EVENT
FIREABLE = frozenset(EVERY_EVENT) | {"G2", "G5", "M8"}
FIRING_THRESHOLD = 0.70


def problem_scores(answers: dict[str, dict[str, float]]) -> dict[str, float]:
    """Return scores for problem questions, excluding the on-track question."""
    return {key: dist["broken"] if key.split("#")[0] == "G2" else dist["true"]
            for key, dist in answers.items() if key.split("#")[0] in FIREABLE - {"G1"}}


def fired(answers: dict[str, dict[str, float]]) -> dict[str, float]:
    """Fire at the calibrated cutoff and use the inverse sign for G1."""
    result = {key: score for key, score in problem_scores(answers).items() if score >= FIRING_THRESHOLD}
    if "G1" in answers and 1.0 - answers["G1"]["true"] >= FIRING_THRESHOLD:
        result["G1"] = 1.0 - answers["G1"]["true"]
    return result


def status(distribution: dict[str, float]) -> str:
    """Choose the first highest-probability option in model order."""
    return max(distribution, key=distribution.get)
