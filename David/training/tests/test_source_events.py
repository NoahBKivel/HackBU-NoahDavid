"""Check shared source normalization and inert streaming readers."""

import json
from pathlib import Path
import sys

import pytest

TRAINING = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRAINING / "src"))
sys.path.insert(0, str(TRAINING.parent))

from intent_training.sources.events import event, from_messages, instruction, message, tool
from intent_training.sources.reading import rows
from monitor_format import validate_event, validate_events
from monitor_format.schema import is_cut_point


def test_anthropic_preserves_tools_text_questions_and_turns():
    events, reasoning = from_messages([
        {"role": "user", "content": "First task"},
        {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "private thought"},
            {"type": "text", "text": "I will read."},
            {"type": "tool_use", "id": "r", "name": "Read", "input": {"path": "a"}},
            {"type": "text", "text": "A question."},
            {"type": "tool_use", "id": "q", "name": "AskUserQuestion", "input": {}}]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "r", "content": "file text"},
            {"type": "tool_result", "tool_use_id": "q", "content": "Keep every line.\nYes."},
            {"type": "text", "text": "Second task"}]},
        {"role": "assistant", "content": "Done"},
        {"role": "user", "content": "Third task"},
        {"role": "assistant", "content": "Another answer"},
    ])
    validate_events(events)
    assert [item["seq"] for item in events] == list(range(1, 8))
    assert events[1]["agent_text"] == "I will read."
    assert events[2]["agent_text"] == "A question."
    assert events[2]["action"]["result_text"] == "Keep every line.\nYes."
    assert not is_cut_point(events[1]) and not is_cut_point(events[2])
    assert events[3]["new_items"][0]["text"] == "Second task"
    assert events[4]["turn"] == {"reason": "answer"}
    assert events[5]["new_items"][0]["text"] == "Third task"
    assert reasoning == {"2": "private thought"}
    assert all(item["agent_thinking"] == "" for item in events)


def test_openai_multiple_calls_and_missing_result():
    events, reasoning = from_messages([
        {"role": "assistant", "content": "Checking", "reasoning_content": "hidden", "tool_calls": [
            {"id": "a", "function": {"name": "Bash", "arguments": '{"command":"rm a"}'}},
            {"id": "b", "function": {"name": "custom", "arguments": "invalid"}}]},
        {"role": "tool", "tool_call_id": "a", "content": "permission denied", "is_error": True},
        {"role": "assistant", "content": "Could not finish"},
    ])
    validate_events(events)
    assert events[0]["action"]["is_error"] is True
    assert "file_changes" not in events[0]["action"]
    assert events[1]["action"]["result_text"] == ""
    assert events[1]["action"]["args"] == {"raw": "invalid"}
    assert events[1]["agent_text"] == ""
    assert reasoning == {"1": "hidden"}


def test_required_fields_and_schema_boundaries():
    validate_event(instruction("Do it", documents={"RULES.md": "rules"}))
    validate_event(message("answer", 2))
    patch = [{"path": "a", "op": "edit", "patch": [{"lines": ["-old", "+new"]}]}]
    validate_event(tool("Edit", {}, "", 3, file_changes=patch))
    with pytest.raises(ValueError):
        tool("Bash", {}, "", 3, file_changes=patch)
    with pytest.raises(ValueError):
        validate_event(tool("Edit", {}, "", 3, file_changes=[{"path": "a", "op": "edit", "patch": "diff"}]))
    bad = event(4, "turn_completed")
    with pytest.raises(ValueError):
        validate_event(bad)
    del bad["agent_thinking"]
    with pytest.raises(ValueError):
        validate_event(bad)


@pytest.mark.parametrize("suffix", [".json", ".jsonl", ".parquet"])
def test_reader_formats(tmp_path, suffix):
    expected = [{"id": 1, "content": "a"}, {"id": 2, "content": "b"}]
    path = tmp_path / ("records" + suffix)
    if suffix == ".parquet":
        import pyarrow as pa
        import pyarrow.parquet as pq
        pq.write_table(pa.Table.from_pylist(expected), path)
    else:
        path.write_text(json.dumps(expected) if suffix == ".json" else
                        "\n".join(json.dumps(row) for row in expected), encoding="utf-8")
    assert list(rows(path)) == expected


def test_reader_yields_prefix_before_malformed_tail_and_skips_cache(tmp_path):
    for suffix, content in [(".jsonl", '{"id":1}\ninvalid'), (".json", '[{"id":1}, invalid]')]:
        path = tmp_path / ("records" + suffix)
        path.write_text(content, encoding="utf-8")
        iterator = rows(path)
        assert next(iterator) == {"id": 1}
        with pytest.raises(ValueError):
            next(iterator)
        path.unlink()
    hidden = tmp_path / ".cache"
    hidden.mkdir()
    (hidden / "broken.json").write_text("invalid", encoding="utf-8")
    (tmp_path / "valid.json").write_text('{"id": 2}', encoding="utf-8")
    assert list(rows(tmp_path)) == [{"id": 2}]


def test_reader_handles_json_chunks_and_rejects_code(tmp_path):
    path = tmp_path / "large.json"
    expected = [{"text": "x" * 70000}, {"text": "last"}]
    path.write_text(json.dumps(expected), encoding="utf-8")
    assert list(rows(path)) == expected
    code = tmp_path / "dataset.py"
    code.write_text("raise RuntimeError('never execute')", encoding="utf-8")
    with pytest.raises(ValueError):
        list(rows(code))
