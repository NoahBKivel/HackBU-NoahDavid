"""Convert unrounded model probabilities to calibrated distributions."""

import math
from collections.abc import Mapping, Sequence


class Calibrator:
    def __init__(self, parameters: Mapping[str, dict] | None, shipped_temperature: float):
        self.parameters = parameters or {}
        self.shipped_temperature = shipped_temperature

    def apply(self, key: str, probabilities: Sequence[float], options: Sequence[str]) -> dict[str, float]:
        """Apply question temperature and offsets in model option order."""
        config = self.parameters.get(key.split("#")[0], {})
        temperature = float(config.get("T", self.shipped_temperature))
        if temperature <= 0 or not math.isfinite(temperature):
            raise ValueError("Calibration temperature must be positive and finite.")
        offset = config.get("b", 0.0)
        if len(probabilities) != len(options):
            raise ValueError("Model probabilities and option keys differ in length.")
        logits = [math.log(float(p)) / temperature if p > 0 else -math.inf for p in probabilities]
        if isinstance(offset, Mapping):
            logits = [z + float(offset.get(option, 0.0)) for z, option in zip(logits, options)]
        elif len(logits) == 2:
            logits[1] += float(offset)
        elif offset:
            raise ValueError("Choice calibration requires per-option offsets.")
        maximum = max(logits)
        weights = [math.exp(z - maximum) for z in logits]
        total = sum(weights)
        return {key: weight / total for key, weight in zip(options, weights)}
