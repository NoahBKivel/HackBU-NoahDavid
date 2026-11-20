"""Verify ATIF call matching, final-claim filtering and outcome isolation."""

from copy import deepcopy
import json

from intent_training.sources.terminal_bench_science import convert, map_trial
from monitor_format import validate_events


def trial():
    """Build a small inert conversation with multiple calls in one ATIF step."""
    return {"agent": "Claude Code", "trial_id": "trial", "task_name": "science/task",
            "trial": {"reward": 0}, "trajectory": {"steps": [
                {"step_id": 1, "source": "user", "message": "<!-- harbor-canary GUID hidden -->\nSolve the task."},
                {"step_id": 2, "source": "agent", "message": "Inspecting.", "reasoning_content": "Private reasoning.",
                 "tool_calls": [
                     {"tool_call_id": "a", "function_name": "Read", "arguments": {"file_path": "/app/input"}, "extra": {"raw_arguments": {"duplicate": True}}},
                     {"tool_call_id": "b", "function_name": "AskUserQuestion", "arguments": {"question": "Use the full data?"}}],
                 "observation": {"results": [
                     {"source_call_id": "b", "content": "Yes, use the full data."},
                     {"source_call_id": "a", "content": "<!-- task-canary GUID hidden -->\ninput", "extra": {"tool_result_is_error": True}}]}},
                {"step_id": 3, "source": "agent", "message": "The task is finished."}
            ]}}


def test_whole_stream_and_hint_isolation(tmp_path):
    """Results match IDs, reasoning stays private and reward never becomes truth."""
    import gzip
    with gzip.open(tmp_path / "trial.jsonl.gz", "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(trial()) + "\n")
    events, side, meta = next(convert(tmp_path))
    validate_events(events)
    assert len(events) == 4
    assert events[1]["action"]["result_text"].strip() == "input"
    assert events[1]["action"]["is_error"]
    assert events[2]["action"]["result_text"] == "Yes, use the full data."
    assert events[-1]["type"] == "turn_completed"
    assert side["reasoning"] == {"2": "Private reasoning."}
    assert all(not e["agent_thinking"] for e in events)
    assert side["source_labels"] == []
    assert side["outcome_hints"][0]["basis"] == "outcome"
    assert side["outcome_hints"][0]["value"] == 0
    assert "canary" not in json.dumps(events)
    assert "raw_arguments" not in json.dumps(events)
    assert meta["cut_seq"] == events[-1]["seq"]


def test_drop_mid_work_and_keep_honest_failure():
    """An unfinished tool run cannot supply a final claim."""
    raw = trial()
    unfinished = deepcopy(raw)
    unfinished["trajectory"]["steps"].pop()
    assert map_trial(unfinished)[1] == "mid_work_ending"
    raw["trajectory"]["steps"][-1]["message"] = "The solver is incomplete and could not pass."
    value, reason = map_trial(raw)
    assert reason == "accepted"
    assert "benign" in value[1]["slice_candidates"]
    assert value[1]["outcome_hints"][0]["basis"] == "outcome"
