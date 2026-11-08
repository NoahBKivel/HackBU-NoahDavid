"""Compare unrounded serving probabilities against the training forward."""

import math
from typing import Any, Iterable


def _indexed(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    output = {}
    for row in rows:
        row = dict(row)
        if "probabilities" not in row and "logits" in row:
            logits = row["logits"]
            if not logits or any(not math.isfinite(value) for value in logits):
                raise ValueError("The training forward must provide finite raw logits.")
            exponential = [math.exp(value - max(logits)) for value in logits]
            row["probabilities"] = [value / sum(exponential) for value in exponential]
        key = (str(row["record_id"]), str(row["question_id"]))
        if key in output or "~neg" in key[1]:
            raise ValueError("Parity needs distinct served base-question rows.")
        options, ps = row["options"], row["probabilities"]
        if (len(options) != len(ps) or len(options) < 2 or len(set(options)) != len(options)
                or any(not math.isfinite(p) or p <= 0 or p > 1 for p in ps)
                or abs(sum(ps) - 1) > 1e-5):
            raise ValueError("Parity requires unrounded, positive probability vectors.")
        output[key] = row
    return output


def _coordinates(row: dict[str, Any]) -> list[float]:
    options, ps = row["options"], row["probabilities"]
    if set(options) == {"false", "true"}:
        return [math.log(ps[options.index("true")]) - math.log(ps[options.index("false")])]
    return [math.log(p) for p in ps]


def compare_serving_paths(selected_training: Iterable[dict[str, Any]],
                          selected_serving: Iterable[dict[str, Any]],
                          stock_training: Iterable[dict[str, Any]],
                          stock_serving: Iterable[dict[str, Any]], *,
                          selected_hardware_pair: tuple[str, str],
                          stock_hardware_pair: tuple[str, str],
                          expected_records: int = 300) -> dict[str, Any]:
    """Apply the stock-relative serving-path gap gate on the same development records."""
    if selected_hardware_pair != stock_hardware_pair or not all(selected_hardware_pair):
        raise ValueError("Both candidates must use the same named training/serving hardware pair.")
    indexed = [_indexed(rows) for rows in (selected_training, selected_serving, stock_training, stock_serving)]
    keys = set(indexed[0])
    if not keys or any(set(rows) != keys for rows in indexed[1:]):
        raise ValueError("Parity paths must score exactly the same record/question keys.")
    record_count = len({key[0] for key in keys})
    if record_count != expected_records:
        raise ValueError("Parity requires the complete development-record sample.")
    selected_gaps, stock_gaps = [], []
    for key in sorted(keys):
        observations = [rows[key] for rows in indexed]
        if any(row["options"] != observations[0]["options"] for row in observations[1:]):
            raise ValueError("All paths must retain the same option ordering.")
        if any(row.get("temperature") != 1.0 for row in observations):
            raise ValueError("Parity compares raw paths loaded with temperature one.")
        coordinates = [_coordinates(row) for row in observations]
        selected_gaps.extend(abs(a - b) for a, b in zip(coordinates[0], coordinates[1]))
        stock_gaps.extend(abs(a - b) for a, b in zip(coordinates[2], coordinates[3]))
    selected_gap = sum(selected_gaps) / len(selected_gaps)
    stock_gap = sum(stock_gaps) / len(stock_gaps)
    return {"n": record_count, "question_rows": len(keys), "coordinates": len(selected_gaps),
            "selected_mean_absolute_gap": selected_gap, "stock_mean_absolute_gap": stock_gap,
            "limit": 1.5 * stock_gap, "pass": selected_gap <= 1.5 * stock_gap,
            "hardware_pair": list(selected_hardware_pair), "temperature": 1.0}
