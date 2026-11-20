"""Record optimizer-step order and losses for continuation checks."""

import json
from pathlib import Path
from typing import Any

_pending: dict[str, dict[str, Any]] = {}


def observe(directory: str, step: int, variants: list[Any], terms: dict[str, float],
            normalizer: float) -> None:
    """Accumulate request order and normalized loss for the current optimizer step."""
    row = _pending.setdefault(directory, {"step": step, "records": [], "loss": 0.0})
    if row["step"] != step:
        raise ValueError("An optimizer trace step was not closed.")
    row["records"].extend(variant.request_id for variant in variants)
    row["loss"] += terms["ce"] / normalizer


def finish(directory: str, step: int) -> None:
    """Append a completed optimizer step to its persistent trace."""
    row = _pending.pop(directory)
    if row["step"] != step:
        raise ValueError("The optimizer trace closed a different step.")
    with (Path(directory) / "step-trace.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row) + "\n")
