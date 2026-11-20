"""Keep generated calls separate from expected calls and outcome hints."""

import json
import pytest

from intent_training.sources.agentjudge import convert


def test_empty_download_produces_no_records(tmp_path):
    assert list(convert(tmp_path)) == []


def test_access_report_is_not_a_trajectory(tmp_path):
    (tmp_path / "access.json").write_text('{"errors": ["DNS failed"]}')
    assert list(convert(tmp_path)) == []


def test_expected_calls_are_never_agent_evidence(tmp_path):
    (tmp_path / "tasks.jsonl").write_text(json.dumps({"expected_tool_calls": [{"name": "expected"}]}))
    assert list(convert(tmp_path)) == []


def test_generated_calls_have_no_invented_result_or_visible_score(tmp_path):
    row = {"id": "task", "difficulty": "easy", "user_query": "Check settings.",
           "available_tools": [], "generated_tool_calls": [
               {"function": {"name": "check_settings", "arguments": {"limit": 5}}}],
           "expected_tool_calls": [{"name": "other"}], "score_query_coverage": 0.5}
    (tmp_path / "model.jsonl").write_text(json.dumps(row))
    events, side, meta = next(convert(tmp_path))
    assert events[-1]["action"]["tool"] == "check_settings"
    assert events[-1]["action"]["result_text"] == ""
    assert side["source_labels"] == []
    assert side["outcomes"]["score_query_coverage"] == 0.5
    assert meta["cut_kind"] == "unspecified"
    assert all(event["agent_thinking"] == "" for event in events)


def test_missing_directory_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError):
        list(convert(tmp_path / "absent"))
