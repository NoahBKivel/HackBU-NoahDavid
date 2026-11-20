"""Check preference pairing and separation of visible evidence from vote hints."""

import json
from pathlib import Path
import sys

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE.parent))

from intent_training.sources.repochat import convert, write_conversion
from monitor_format import validate_events


def fixture_row():
    """Return a small synthetic preference with source-like conversation fields."""
    return {"conv_ids": "{'conv_id_a': 'first', 'conv_id_b': 'second'}",
        "full_conversation_a": [
            {"role": "user", "content": "Repository context: x = 1. Explain x."},
            {"role": "assistant", "content": "x is one.", "reasoning_content": "Read the assignment."}],
        "full_conversation_b": [
            {"role": "user", "content": "Repository context: x = 2. Explain x."},
            {"role": "assistant", "content": "I cannot tell."}],
        "winner": "both_bad", "both_bad": True, "left": False, "right": False,
        "tie": False, "github_link": "https://github.com/example/example"}


def test_pair_and_outcome_boundaries(tmp_path):
    row = fixture_row()
    (tmp_path / "rows.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    records = list(convert(tmp_path))
    assert len(records) == 2
    first, second = records
    assert first[2]["pair_id"] == second[2]["pair_id"]
    assert first[2]["source_record_id"] != second[2]["source_record_id"]
    for events, side, meta in records:
        validate_events(events)
        assert len(events) == 2
        assert events[-1]["turn"]["reason"] == "answer"
        assert not any(event["agent_thinking"] for event in events)
        assert side["source_labels"] == []
        assert side["outcomes"]["both_bad"] is True
        assert side["outcomes"]["basis"] == "outcome"
        assert meta["cut_seq"] == events[-1]["seq"]
        assert "task_id" not in meta
    assert first[1]["reasoning"] == {"2": "Read the assignment."}
    assert second[0][0]["new_items"][0]["text"] == row["full_conversation_b"][0]["content"]
    assert list(convert(tmp_path))[0][2] == first[2]


def test_persisted_counts_and_hashes(tmp_path):
    (tmp_path / "rows.jsonl").write_text(json.dumps(fixture_row()) + "\n", encoding="utf-8")
    output, report = tmp_path / "converted.jsonl", tmp_path / "report.json"
    result = write_conversion(tmp_path, output, report)
    assert result["counts"]["source_rows"] == 1
    assert result["counts"]["converted_records"] == 2
    assert result["filters"]["vote_derived_positive_labels"] == 0
    assert len(result["output"]["sha256"]) == 64
    assert len(output.read_text(encoding="utf-8").splitlines()) == 2
