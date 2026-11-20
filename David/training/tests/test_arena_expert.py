"""Verify safe decoding and preference-only side evidence."""

import json
from pathlib import Path
import sys

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE.parent))

from intent_training.sources.arena_expert import convert, decode_conversation
from monitor_format import validate_events


def conversation(answer, context="Keep the literal } { text."):
    return ("[{'role': 'user', 'content': array([{'type':'text', 'text':" + repr(context)
            + ", 'image':None}], dtype=object)}\n"
            + "{'role':'assistant', 'content': array([{'type':'text', 'text':" + repr(answer)
            + ", 'image':None}], dtype=object), 'num_tokens': 1.0}]")


def save(tmp_path, row):
    (tmp_path / "rows-000000.json").write_text(json.dumps({"rows": [{"row_idx": 0,
        "row": row, "truncated_cells": []}]}), encoding="utf-8")


def test_both_bad_is_hint_and_pair_stays_together(tmp_path):
    save(tmp_path, dict(id="pair", winner="both_bad", conversation_a=conversation("First."),
                        conversation_b=conversation("Second.")))
    records = list(convert(tmp_path))
    assert len(records) == 2
    assert records[0][2]["pair_id"] == records[1][2]["pair_id"]
    assert records[0][2]["trajectory_id"] != records[1][2]["trajectory_id"]
    for events, side, meta in records:
        validate_events(events)
        assert events[0]["new_items"][0]["text"] == "Keep the literal } { text."
        assert events[0]["new_items"][0]["id"] == "I1"
        assert events[-1]["turn"] == {"reason": "answer"}
        assert all(event["agent_thinking"] == "" for event in events)
        assert not side["source_labels"]
        assert side["outcomes"]["expert_vote"] == "both_bad"
        assert side["outcomes"]["basis"] == "outcome"
        assert meta["objective"] == ["M1", "G1"]
    assert [record[0][-1]["agent_text"] for record in records] == ["First.", "Second."]


def test_nonliteral_calls_are_never_executed():
    with pytest.raises(ValueError, match="nonliteral"):
        decode_conversation("[__import__('os').system('untrusted')]")


def test_each_candidate_retains_its_own_context(tmp_path):
    save(tmp_path, dict(id="pair", winner="model_a", conversation_a=conversation("First."),
                        conversation_b=conversation("Second.", "Different request.")))
    records = list(convert(tmp_path))
    assert records[0][0][0]["new_items"][0]["text"] == "Keep the literal } { text."
    assert records[1][0][0]["new_items"][0]["text"] == "Different request."


def test_nontext_content_drops_whole_pair(tmp_path):
    text = conversation("First.").replace("'type':'text'", "'type':'image'", 1)
    save(tmp_path, dict(id="pair", winner="model_a", conversation_a=text,
                        conversation_b=conversation("Second.")))
    assert list(convert(tmp_path)) == []
