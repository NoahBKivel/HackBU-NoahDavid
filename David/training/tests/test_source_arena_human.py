"""Verify human Arena filtering, grouping, visibility and reasoning isolation."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.sources.arena_human import convert, eligible
from monitor_format import validate_events


def _message(role, text):
    return {"role": role, "content": [{"type": "text", "text": text}]}


def test_both_bad_retains_two_teacher_labelled_branches(tmp_path):
    conversation = [_message("user", "Implement a parser."),
                    _message("assistant", "Earlier attempt."),
                    _message("user", "Retain blank lines."),
                    _message("assistant", "Final answer.")]
    conversation[-1]["reasoning_content"] = "Private reasoning."
    row = dict(id="fixture", is_code=True, winner="both_bad", conversation_a=conversation,
               conversation_b=conversation, evaluation_session_id="fixture-session")
    excluded = dict(row, id="excluded", is_code=False, category_tag={"if_v0.1": {"if": False}})
    (tmp_path / "rows-000000.json").write_text(json.dumps({"rows": [
        {"row_idx": 0, "row": row, "truncated_cells": []},
        {"row_idx": 1, "row": excluded, "truncated_cells": []},
    ]}), encoding="utf-8")
    output = list(convert(tmp_path))
    assert len(output) == 2
    assert output[0][2]["pair_id"] == output[1][2]["pair_id"]
    assert output[0][2]["trajectory_id"] != output[1][2]["trajectory_id"]
    for events, side, meta in output:
        validate_events(events)
        assert events[-1]["type"] == "turn_completed"
        assert events[-1]["turn"]["reason"] == "answer"
        assert [e["new_items"][0]["text"] for e in events if e["new_items"]] == [
            "Implement a parser.", "Retain blank lines."]
        assert side["reasoning"] == {"4": "Private reasoning."}
        assert all(e["agent_thinking"] == "" for e in events)
        assert "Private reasoning." not in json.dumps(events)
        assert side["source_labels"] == []
        assert side["outcomes"]["winner"] == "both_bad"
        assert side["outcomes"]["basis"] == "outcome"
        assert meta["objective"] == ["M1", "G1"]


def test_if_tag_and_boolean_filter():
    assert eligible({"category_tag": {"if_v0.1": {"if": True}}})
    assert not eligible({"is_code": "false"})


def test_truncated_and_multimodal_pairs_are_excluded(tmp_path):
    row = dict(id="image", is_code=True, conversation_a=[_message("user", "See image."),
               {"role": "assistant", "content": [{"type": "image", "image": "image"}]}],
               conversation_b=[_message("user", "See image."), _message("assistant", "Answer.")])
    (tmp_path / "rows-000000.json").write_text(json.dumps({"rows": [
        {"row_idx": 0, "row": row, "truncated_cells": []},
        {"row_idx": 1, "row": dict(row, id="truncated"), "truncated_cells": ["conversation_a"]},
    ]}), encoding="utf-8")
    assert list(convert(tmp_path)) == []
