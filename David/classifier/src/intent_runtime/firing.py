"""Derive problem scores and the fired set from calibrated answers."""

EVERY_EVENT = ("M1", "M2", "M4", "M5", "M7", "L1", "L2", "L4", "L5", "L6", "G1", "G4")
FIREABLE = frozenset(EVERY_EVENT) | {"G2", "G5", "M8"}


def problem_scores(answers: dict[str, dict[str, float]]) -> dict[str, float]:
    """Return scores for problem questions, excluding the on-track question."""
    return {key: dist["broken"] if key.split("#")[0] == "G2" else dist["true"]
            for key, dist in answers.items() if key.split("#")[0] in FIREABLE - {"G1"}}


def fired(answers: dict[str, dict[str, float]]) -> dict[str, float]:
    """Fire at the calibrated cutoff and use the inverse sign for G1."""
    result = {key: score for key, score in problem_scores(answers).items() if score >= 0.5}
    if "G1" in answers and answers["G1"]["true"] < 0.5:
        result["G1"] = 1.0 - answers["G1"]["true"]
    return result


def status(distribution: dict[str, float]) -> str:
    """Choose the first highest-probability option in model order."""
    return max(distribution, key=distribution.get)
