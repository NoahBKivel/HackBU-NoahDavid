"""Score records through Kev's checkpoint loader and unrounded serving interface."""

from contextlib import contextmanager
import hashlib
import json
import math
from typing import Any, Iterator


@contextmanager
def serving_checkpoint(path: str, device: str, *, dtype: Any = None,
                       merge: bool = True) -> Iterator[Any]:
    """Load the real serving path at temperature one and close its model thread."""
    from kev.checkpoint import Checkpoint, LoadOptions
    from kev.serve import Server

    checkpoint = Checkpoint(path)
    options = LoadOptions(dtype=dtype, merge=merge, temperature=1.0, attn="sdpa")
    tokenizer, model = checkpoint.load(device, options)
    server = Server(checkpoint, tokenizer, model, device)
    try:
        yield server
    finally:
        server.close()


def serving_probabilities(server: Any, record: dict[str, Any], *,
                          record_id: str | None = None) -> list[dict[str, Any]]:
    """Score a labelled request through Server.probs without API probability rounding."""
    from kev.api import SystemOneRequest, to_record

    request = {"state": record["state"], "questions": {
        key: {name: value for name, value in question.items() if name in {"type", "instructions", "criteria"}}
        for key, question in record["questions"].items() if "~neg" not in key}}
    normalized, metadata = to_record(SystemOneRequest.model_validate(request))
    probabilities, statistics = server.probs(normalized)
    if statistics["state_tokens_used"] != statistics["state_tokens"]:
        raise ValueError("Serving truncated the state.")
    if len(probabilities) != len(metadata):
        raise ValueError("Serving omitted question rows.")
    identity = record_id or record.get("_meta", {}).get("id")
    if identity is None:
        identity = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    output = []
    for meta, vector in zip(metadata, probabilities):
        if any(not math.isfinite(value) for value in vector):
            raise ValueError("Serving produced non-finite probabilities.")
        output.append({"record_id": str(identity), "question_id": meta["id"], "options": meta["keys"],
                       "probabilities": vector, "temperature": 1.0})
    return output


def demo_check(server: Any, events: list[dict[str, Any]], *, cut_seq: int, b_state: int,
               calibration: dict[str, Any]) -> dict[str, Any]:
    """Render the offending demo event and test calibrated every-event problem scores."""
    from monitor_format import EVERY_EVENT, build_instructions, collect_documents, fill_question, render_state, validate_events
    from intent_training.select.calibration import calibrated_probabilities

    validate_events(events)
    visible = [event for event in events if event["seq"] <= cut_seq]
    state, _, fits = render_state(build_instructions(visible), collect_documents(visible), visible,
                                 cut_seq, [], b_state, tokenizer=server.tok)
    if not fits:
        raise ValueError("The demo's instruction/document prefix requires an overflow screen.")
    questions = {question: fill_question(question) for question in EVERY_EVENT if question != "G1"}
    scored = serving_probabilities(server, {"state": state, "questions": questions})
    calibrated = {}
    for row in scored:
        question = row["question_id"]
        parameters = calibration[question]
        logits = [math.log(p) if p > 0 else -math.inf for p in row["probabilities"]]
        calibrated[question] = calibrated_probabilities(logits, row["options"], parameters)[row["options"].index("true")]
    fired = [question for question, probability in calibrated.items() if probability >= 0.5]
    return {"pass": bool(fired), "cut_seq": cut_seq, "problem_probabilities": calibrated,
            "fired": fired, "state_sha256": hashlib.sha256(state.encode()).hexdigest(),
            "entry_point": "kev.serve.Server.probs", "temperature": 1.0}
