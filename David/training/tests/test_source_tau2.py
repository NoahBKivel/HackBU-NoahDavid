"""Exercise embedded task joins and narrowly grounded tau2 evidence."""

import json

from monitor_format import validate_events
from intent_training.sources.tau2 import convert


def test_embedded_join_cut_and_reasoning(tmp_path):
    policy = "Before changing the database obtain explicit user confirmation (yes)."
    sim = {"id": "run", "task_id": "task", "messages": [
        {"role": "user", "content": "Change my address."},
        {"role": "assistant", "content": "Checking.", "reasoning_content": "Private plan.",
         "tool_calls": [{"id": "read", "name": "get_user_details", "arguments": {}}]},
        {"role": "tool", "id": "read", "content": "Old address."},
        {"role": "assistant", "tool_calls": [{"id": "write", "name": "modify_user_address", "arguments": {}}]},
        {"role": "tool", "id": "write", "content": "Address changed."},
        {"role": "assistant", "content": "Address changed."},
        {"role": "user", "content": "That was the wrong address."},
        {"role": "assistant", "content": "Future recovery."}],
        "reward_info": {"nl_assertions": [{"met": False}],
                        "communicate_checks": [{"info": "changed", "met": True}]}}
    bundle = {"info": {"environment_info": {"domain_name": "retail", "policy": policy}},
              "tasks": [{"id": "task", "marker": "embedded"}], "simulations": [sim]}
    (tmp_path / "run.json").write_text(json.dumps(bundle))
    records = list(convert(tmp_path))
    assert len(records) == 2
    events, side, meta = records[0]
    validate_events(events)
    assert side["embedded_task"]["marker"] == "embedded"
    assert events[meta["cut_seq"] - 1]["agent_text"] == "Address changed."
    assert side["reasoning"] and all(not e["agent_thinking"] for e in events)
    assert not side["source_labels"]
    assert side["source_hints"][0]["basis"] == "outcome"
    assert side["communication_checks"][0]["visible_substring_match"]
    assert events[2]["action"]["result_text"] == "Old address."
    assert events[2]["action"]["tool"] == "Read"
    _, order_side, order_meta = records[1]
    assert order_side["source_labels"][0]["question"] == "L5"
    assert order_meta["cut_seq"] < meta["cut_seq"]


def test_explicit_yes_and_ask_answers_survive(tmp_path):
    bundle = {"info": {"environment_info": {"domain_name": "retail", "policy": "Confirm yes before changes."}},
              "tasks": [{"id": "task"}], "simulations": [{"id": "run", "task_id": "task", "messages": [
        {"role": "user", "content": "Yes, change it."},
        {"role": "assistant", "tool_calls": [{"id": "ask", "name": "AskUserQuestion", "arguments": {}}]},
        {"role": "tool", "id": "ask", "content": "The user's exact answer."},
        {"role": "assistant", "tool_calls": [{"id": "w", "name": "modify_user_address", "arguments": {}}]},
        {"role": "tool", "id": "w", "content": "Done."},
        {"role": "assistant", "content": "Done."}]}]}
    (tmp_path / "run.json").write_text(json.dumps(bundle))
    records = list(convert(tmp_path))
    assert not records[1][1]["source_labels"]
    assert records[0][0][2]["action"]["result_text"] == "The user's exact answer."
