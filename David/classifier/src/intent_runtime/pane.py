"""Compute the Pane readings without rounding probabilities."""

from .firing import problem_scores


def readings(answers: dict, history: list[float]) -> dict:
    """Compute risk, flags and the drift change over up to five preceding readings."""
    scores = problem_scores(answers)
    risk = max(scores.values(), default=0.0)
    drift = 1.0 - answers["G1"]["true"] if "G1" in answers else None
    rate = None
    if drift is not None:
        window = min(5, len(history))
        if window:
            rate = (drift - history[-window]) / window
        history.append(drift)
    return {"risk": risk, "flagged": risk >= 0.5, "drift": drift, "drift_rate": rate}
