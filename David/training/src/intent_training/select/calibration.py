"""Fit temperature and prior offsets on natural-prevalence dev records."""

from collections import defaultdict
from typing import Any, Iterable

import numpy as np

from .metrics import probabilities


def _targets(rows: list[dict[str, Any]], options: list[str]) -> np.ndarray:
    values = []
    for row in rows:
        if row["options"] != options:
            raise ValueError("Calibration option order must be identical.")
        values.append(row.get("target", [float(row["label"] == option) for option in options]))
    result = np.asarray(values, dtype=float)
    if result.shape != (len(rows), len(options)) or not np.isfinite(result).all() or (result < 0).any():
        raise ValueError("Targets must be finite nonnegative class distributions.")
    if not np.allclose(result.sum(axis=1), 1):
        raise ValueError("Every target must sum to one.")
    return result


def prior_offset(train: list[dict[str, Any]], dev: list[dict[str, Any]],
                 options: list[str]) -> float | dict[str, float]:
    """Calculate finite class prior offsets with half a pseudocount per class."""
    if not train or not dev:
        raise ValueError("Training and natural-prevalence dev targets are required.")
    train_rate = (_targets(train, options).sum(axis=0) + 0.5) / (len(train) + 0.5 * len(options))
    dev_rate = (_targets(dev, options).sum(axis=0) + 0.5) / (len(dev) + 0.5 * len(options))
    offset = np.log(dev_rate) - np.log(train_rate)
    if options == ["false", "true"]:
        return float(offset[1] - offset[0])
    return dict(zip(options, offset.tolist()))


def _offset_vector(options: list[str], offset: float | dict[str, float]) -> np.ndarray:
    if isinstance(offset, dict):
        if set(offset) != set(options):
            raise ValueError("Calibration offsets must name every option exactly.")
        values = np.array([offset[option] for option in options], dtype=float)
    else:
        if options != ["false", "true"]:
            raise ValueError("A scalar calibration offset requires false/true options.")
        values = np.array([0, offset], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Calibration offsets must be finite.")
    return values


def calibrated_probabilities(logits: list[float], options: list[str],
                             parameters: dict[str, Any]) -> list[float]:
    """Apply temperature before prior offset using the serving handoff format."""
    temperature = float(parameters["T"])
    if not np.isfinite(temperature) or temperature < 1 or len(logits) != len(options):
        raise ValueError("Temperature must be finite and at least one, with aligned options.")
    return probabilities((np.array(logits) / temperature + _offset_vector(options, parameters["b"])).tolist())


def fit_question(rows: list[dict[str, Any]], *, offset: float | dict[str, float] | None = None,
                 jointly_fit_offset: bool = False) -> dict[str, Any]:
    """Minimize soft-target NLL with temperature constrained to at least one."""
    from scipy.optimize import minimize
    from scipy.special import logsumexp

    if not rows or any(not row.get("is_base_dev", False) for row in rows):
        raise ValueError("Fit calibration only on nonempty base dev, excluding top-ups.")
    options = rows[0]["options"]
    targets = _targets(rows, options)
    logits = np.asarray([row["logits"] for row in rows], dtype=float)
    if logits.shape != targets.shape or not np.isfinite(logits).all():
        raise ValueError("Calibration logits and targets must be finite and aligned.")
    fixed = np.zeros(len(options)) if offset is None else _offset_vector(options, offset)

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        inverse_temperature = parameters[0]
        biases = np.r_[0, parameters[1:]] if jointly_fit_offset else fixed
        adjusted = logits * inverse_temperature + biases
        log_probs = adjusted - logsumexp(adjusted, axis=1, keepdims=True)
        difference = (np.exp(log_probs) - targets) / len(rows)
        gradient = [float((difference * logits).sum())]
        if jointly_fit_offset:
            gradient.extend(difference[:, 1:].sum(axis=0))
        return -float((targets * log_probs).sum()), np.asarray(gradient)

    initial = np.r_[1.0, np.zeros(len(options) - 1)] if jointly_fit_offset else np.array([1.0])
    bounds = [(np.finfo(float).eps, 1.0)] + ([(None, None)] * (len(options) - 1) if jointly_fit_offset else [])
    result = minimize(objective, initial, method="L-BFGS-B", jac=True, bounds=bounds,
                      options={"maxiter": 2000, "ftol": 1e-12, "gtol": 1e-8})
    if not result.success or not np.isfinite(result.fun):
        raise ValueError(f"Calibration optimization failed: {result.message}")
    biases = np.r_[0, result.x[1:]] if jointly_fit_offset else fixed
    bias: float | dict[str, float] = float(biases[1] - biases[0]) if options == ["false", "true"] else dict(zip(options, biases.tolist()))
    return {"T": float(1 / result.x[0]), "b": bias}


def fit_calibration(dev_rows: Iterable[dict[str, Any]], train_rows: Iterable[dict[str, Any]] = (),
                    *, stock: bool = False) -> dict[str, dict[str, Any]]:
    """Fit one handoff transform per base question using base dev only."""
    dev: dict[str, list[dict[str, Any]]] = defaultdict(list)
    train: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dev_rows:
        if row.get("is_base_dev") and "~neg" not in row["question_id"]:
            dev[row["question_id"].split("#", 1)[0]].append(row)
    for row in train_rows:
        if "~neg" not in row["question_id"]:
            train[row["question_id"].split("#", 1)[0]].append(row)
    if not dev:
        raise ValueError("No base dev calibration rows exist.")
    return {question: fit_question(rows, jointly_fit_offset=stock,
                                   offset=None if stock else prior_offset(train[question], rows, rows[0]["options"]))
            for question, rows in dev.items()}
