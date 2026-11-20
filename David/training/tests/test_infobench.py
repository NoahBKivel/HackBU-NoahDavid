"""Check source fidelity and refuse missing generator evidence."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.sources.infobench import convert, generation_id, generation_requests
from monitor_format import split_units, validate_events


@pytest.fixture
def row():
    # This is the inspected source row, not an authored agent answer.
    return {"id": "user_oriented_task_205", "input": "Language: Python\nFunction: input",
            "instruction": "Given a programming language and the name of a function, write a command to show how to use the function.",
            "decomposed_questions": ["Does the generated text include a command?"],
            "question_label": [["Format"]]}


def prepare(tmp_path, row):
    raw_dir = tmp_path / "data/downloads/infobench"
    raw_dir.mkdir(parents=True)
    (raw_dir / "rows.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    return raw_dir


def test_requests_preserve_input_and_hide_teacher_hints(tmp_path, row):
    request, = generation_requests(prepare(tmp_path, row))
    assert request["prompt"] == row["instruction"] + "\n\n" + row["input"]
    assert row["decomposed_questions"][0] not in request["prompt"]
    assert request["refs"][0]["source_record_id"] == row["id"]
    changed = dict(row, input=row["input"] + "\n")
    assert generation_id(changed) != request["id"]


def test_missing_response_does_not_fabricate_a_record(tmp_path, row):
    assert list(convert(prepare(tmp_path, row))) == []


def test_empty_response_is_rejected(tmp_path, row):
    raw_dir = prepare(tmp_path, row)
    responses = tmp_path / "data/generation/responses"
    responses.mkdir(parents=True)
    (responses / (generation_id(row) + ".json")).write_text('{"text":""}', encoding="utf-8")
    with pytest.raises(ValueError, match="nonempty"):
        list(convert(raw_dir))


def test_actual_central_responses_preserve_units_and_hint_provenance():
    records = list(convert(ROOT / "data/downloads/infobench"))
    if not records:
        pytest.skip("The central generator has not supplied source responses yet.")
    for events, side, meta in records:
        validate_events(events)
        original = events[0]["new_items"][0]["text"]
        assert side["requirement_units"] == split_units(original, "[I1]")
        assert side["source_labels"] == []
        assert all(hint["basis"] == "outcome" for hint in side["teacher_hints"])
        assert all(not event["agent_thinking"] for event in events)
        assert meta["cut_seq"] == events[-1]["seq"]
        assert events[-1]["turn"]["reason"] == "answer"
