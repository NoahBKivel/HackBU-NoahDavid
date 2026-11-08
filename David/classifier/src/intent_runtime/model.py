"""Load runtime model selection and score rows through Kev's unrounded path."""

import json
import threading
from pathlib import Path

from .calibration import Calibrator

STOCK_CHECKPOINT = "jaredpalmer/kev-4b@6cfce5c2fa4b4bd64026336ab649c5ca78857d52"


def selection(directory: Path) -> dict:
    """Read the runtime selection or return the pinned stock fallback."""
    path = directory / "selected.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"checkpoint": STOCK_CHECKPOINT, "calibration": None, "source": "stock-kev"}


class QuestionRunner:
    def __init__(self, server, calibrator: Calibrator):
        from kev.api import SystemOneRequest, to_record
        self.server = server
        self.calibrator = calibrator
        self.request_type = SystemOneRequest
        self.to_record = to_record
        self.trace = threading.local()

    def prepare(self, state: str, questions: dict) -> tuple:
        """Encode a request and preserve the model's option ordering."""
        request = self.request_type.model_validate({"state": state, "model": "kev-latest", "questions": questions})
        return self.to_record(request)

    def decode(self, probabilities: list, metadata: list[dict]) -> dict:
        """Calibrate unrounded probability lists in their metadata order."""
        answers = {m["id"]: self.calibrator.apply(m["id"], p, m["keys"]) for m, p in zip(metadata, probabilities, strict=True)}
        if hasattr(self, "trace"):
            self.trace.last = {"raw": {m["id"]: dict(zip(m["keys"], p)) for m, p in zip(metadata, probabilities)}, "calibrated": answers}
            if hasattr(self.trace, "requests"):
                self.trace.requests.append(self.trace.last)
        return answers

    def ask(self, state: str, questions: dict) -> dict:
        """Score all rows together using Server.probs without answer rounding."""
        if not questions:
            return {}
        record, metadata = self.prepare(state, questions)
        probabilities, _ = self.server.probs(record)
        return self.decode(probabilities, metadata)

    def ask_many(self, requests: list[tuple[str, dict]]) -> list[dict]:
        """Submit independent states back to back before awaiting any answer."""
        encoded = [self.prepare(state, questions) for state, questions in requests]
        pending = [(self.server.submit(record), metadata) for record, metadata in encoded]
        return [self.decode(future.result()[0], metadata) for future, metadata in pending]
