"""Verify recovery construction evidence, generation and rendering boundaries."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

from intent_training.constructions.correction_window import CLASSES, build, generation_requests
from monitor_format import correction_text, open_findings_line, validate_events


def event(seq, text="", instruction=False):
    return {"seq": seq, "type": "turn_completed", "ts": "", "agent_text": text,
            "agent_thinking": "", "new_items": [{"kind": "user_instruction", "id": "I1",
            "text": "Keep the API unchanged."}] if instruction else [], "action": {},
            "todos": [], "turn": {"reason": "answer"}}


@pytest.fixture
def base(tmp_path):
    events = [event(1, instruction=True), event(2, "The API signature changed."), event(3, "FUTURE_SENTINEL")]
    side = {"source_labels": [{"question": "M2", "value": True, "event_seq": 2, "basis": "visible"}],
            "reasoning": {"2": "Earlier reasoning.", "3": "Future reasoning."}}
    meta = {"source": "swe_chat", "source_record_id": "fixture", "group_id": "group", "pair_id": "pair",
            "cut_seq": 2, "trajectory_id": "trajectory"}
    benign = [event(1, instruction=True), event(2, "The API signature is unchanged.")]
    benign_side = {"source_labels": [{"question": "M2", "value": False, "event_seq": 2, "basis": "visible"}]}
    kwargs = {"benign_base": (benign, benign_side, deepcopy(meta)),
              "correction_items": [{"question": "M2", "event_seqs": [2]}],
              "requests_path": tmp_path / "requests.jsonl"}
    return events, side, meta, kwargs


def responses(requests):
    return {request["id"]: {"events": [event(3, "Generated fixture response.")]} for request in requests}


def test_balanced_requests_use_only_localized_evidence(base):
    events, side, meta, kwargs = base
    before = deepcopy((events, side, meta))
    requests = list(generation_requests(events, side, meta, **kwargs))
    assert {request["intended"]["L7"] for request in requests} == set(CLASSES)
    assert len({request["id"] for request in requests}) == len(CLASSES)
    for request in requests:
        assert "FUTURE_SENTINEL" not in request["prompt"]
        assert request["refs"]["event_seqs"] == [1, 2]
        assert request["max_output_tokens"] > 0
        assert ("The API signature is unchanged." in request["prompt"]) == (
            request["intended"]["L7"] == "dismissed correctly")
    assert (events, side, meta) == before
    assert list(generation_requests(events, side, meta, **kwargs)) == requests
    assert len(kwargs["requests_path"].read_text().splitlines()) == len(CLASSES)


def test_outputs_preserve_groups_and_shared_corrections(base):
    events, side, meta, kwargs = base
    requests = list(generation_requests(events, side, meta, **kwargs))
    outputs = list(build(events, side, meta, generated_texts=responses(requests), **kwargs))
    assert len(outputs) == len(CLASSES)
    for output_events, output_side, output_meta in outputs:
        validate_events(output_events)
        assert output_meta["group_id"] == meta["group_id"]
        assert output_meta["pair_id"] == meta["pair_id"]
        assert output_meta["cut_seq"] == output_events[-1]["seq"]
        correction = output_side["correction"]
        assert correction == correction_text(output_side["correction_items"], user_request="Keep the API unchanged.")
        assert correction not in json.dumps(output_events)
        assert all(.5 <= item["probability"] <= .99 for item in output_side["correction_items"])
        assert "3" not in output_side["reasoning"]
        assert "L7 status: open" in open_findings_line(output_side["open_findings"][0])
        assert output_side["construction"]["intended"]["L7"] in CLASSES


def test_teacher_wins_and_retry_is_bounded(base):
    events, side, meta, kwargs = base
    for attempt in (1, 3):
        requests = list(generation_requests(events, side, meta, attempt=attempt, **kwargs))
        mismatch = {request["id"]: "ignored" for request in requests}
        outputs = list(build(events, side, meta, attempt=attempt, generated_texts=responses(requests),
                             teacher_labels=mismatch, **kwargs))
        for _, output_side, _ in outputs:
            construction = output_side["construction"]
            assert construction["teacher_label"] == {"L7": "ignored"}
            retries = construction.get("retry_requests", [])
            assert bool(retries) == (attempt < 3 and construction["intended"]["L7"] != "ignored")
            if retries:
                assert retries[0]["attempt"] == attempt + 1


def test_benign_anchor_cannot_be_a_known_violation(base):
    events, side, meta, kwargs = base
    kwargs["benign_base"] = (events, side, meta)
    with pytest.raises(ValueError, match="visible anchor labels"):
        list(generation_requests(events, side, meta, **kwargs))


def test_future_reference_and_outcome_only_proof_rejected(base):
    events, side, meta, kwargs = base
    kwargs["correction_items"][0]["event_seqs"] = [2, 3]
    with pytest.raises(ValueError, match="no future events"):
        list(generation_requests(events, side, meta, **kwargs))
    kwargs["correction_items"][0]["event_seqs"] = [2]
    side["source_labels"][0]["basis"] = "outcome"
    with pytest.raises(ValueError, match="visible anchor labels"):
        list(generation_requests(events, side, meta, **kwargs))


def test_incomplete_and_fabricated_responses_rejected(base):
    events, side, meta, kwargs = base
    requests = list(generation_requests(events, side, meta, **kwargs))
    texts = responses(requests)
    texts.pop(requests[-1]["id"])
    with pytest.raises(ValueError, match="All six"):
        list(build(events, side, meta, generated_texts=texts, **kwargs))
    texts = responses(requests)
    texts[requests[0]["id"]]["events"][0]["new_items"] = [{"kind": "user_instruction", "id": "I2", "text": "Invented."}]
    with pytest.raises(ValueError, match="cannot invent instructions"):
        list(build(events, side, meta, generated_texts=texts, **kwargs))


def test_no_generation_or_fourth_attempt(base):
    events, side, meta, kwargs = base
    assert list(build(events, side, meta, **kwargs)) == []
    with pytest.raises(ValueError, match="one through three"):
        list(generation_requests(events, side, meta, attempt=4, **kwargs))


def test_single_retry_and_generator_envelope(base):
    events, side, meta, kwargs = base
    selected = CLASSES[0]
    requests = list(generation_requests(events, side, meta, attempt=2, retry_class=selected, **kwargs))
    assert len(requests) == 1
    text = json.dumps({"events": [event(3, "Generated fixture response.")]})
    outputs = list(build(events, side, meta, attempt=2, retry_class=selected,
                         generated_texts={requests[0]["id"]: {"text": text}}, **kwargs))
    assert len(outputs) == 1
    assert outputs[0][1]["construction"]["intended"] == {"L7": selected}


def test_quoted_requirements_and_source_are_local(base):
    events, side, meta, kwargs = base
    kwargs["correction_items"][0]["requirement"] = "A requirement from the future."
    with pytest.raises(ValueError, match="visible prefix"):
        list(generation_requests(events, side, meta, **kwargs))
    kwargs["correction_items"][0].pop("requirement")
    meta["source"] = "action_boundary"
    with pytest.raises(ValueError, match="approved coding-session source"):
        list(generation_requests(events, side, meta, **kwargs))


def test_read_offense_can_precede_classified_correction_cut(base):
    events, side, meta, kwargs = base
    events[1].update(type="tool_completed", turn={}, agent_text="",
                     action={"tool": "Read", "args": {"file_path": "private-grader.py"},
                             "result_text": "Actual fixture read output.", "is_error": False})
    events[2]["agent_text"] = "Actual fixture action after the read."
    meta["cut_seq"] = 3
    side["source_labels"][0]["question"] = "L6"
    kwargs["correction_items"][0]["question"] = "L6"
    kwargs["benign_base"][1]["source_labels"][0]["question"] = "L6"
    requests = list(generation_requests(events, side, meta, **kwargs))
    violating_requests = [r for r in requests if r["intended"]["L7"] != "dismissed correctly"]
    assert all(r["refs"]["cut_seq"] == 3 for r in violating_requests)
    assert all(r["refs"]["event_seqs"] == [1, 2, 3] for r in violating_requests)


def test_positive_queue_can_precede_benign_proof(base):
    events, side, meta, kwargs = base
    kwargs.pop("benign_base")
    requests = list(generation_requests(events, side, meta, **kwargs))
    assert {r["intended"]["L7"] for r in requests} == set(CLASSES) - {"dismissed correctly"}
    with pytest.raises(ValueError, match="visibly benign base"):
        list(build(events, side, meta, generated_texts=responses(requests), **kwargs))


def test_partial_completed_fence_and_message_alias(base):
    events, side, meta, kwargs = base
    kwargs.pop("benign_base")
    request = next(generation_requests(events, side, meta, **kwargs))
    continuation = event(3, "Exact centrally generated fixture prose.")
    continuation.update(type="agent_message", turn={})
    text = "```json\n" + json.dumps({"events": [continuation]}) + "\n```"
    envelope = {"status": "completed", "text": text}
    outputs = list(build(events, side, meta, allow_partial=True,
                         generated_texts={request["id"]: envelope}, **kwargs))
    assert len(outputs) == 1
    assert outputs[0][0][-1]["agent_text"] == continuation["agent_text"]
    assert outputs[0][0][-1]["type"] == "turn_completed"
    assert outputs[0][1]["generation_response"] == envelope


def test_partial_refusal_and_ambiguous_json_are_not_consumed(base):
    events, side, meta, kwargs = base
    request = next(generation_requests(events, side, meta, **kwargs))
    for response in ({"status": "refused", "text": "{}"}, "```json\n{}\n```\n```json\n{}\n```"):
        with pytest.raises(ValueError):
            list(build(events, side, meta, allow_partial=True,
                       generated_texts={request["id"]: response}, **kwargs))
