"""Check source evidence joins, gold exclusion and visible claim discipline."""

import json

from intent_training.sources.open_swe import convert, convert_row
from monitor_format import validate_events


def sample():
    return {"trajectory_id": "example", "instance_id": "issue", "resolved": 0,
            "metadata": {"reference_patch": {"patch": "gold"}},
            "messages": [
                {"role": "user", "content": "Fix the parser."},
                {"role": "assistant", "reasoning_content": "private", "tool_calls": [
                    {"id": "call", "function": {"name": "Bash", "arguments": '{"command":"pytest"}'}}]},
                {"role": "tool", "content": "2 failed, 3 passed"},
                {"role": "assistant", "content": "All tests pass."}]}


def test_actual_result_join_and_contradiction():
    events, side, meta = convert_row(sample())
    validate_events(events)
    assert events[1]["action"]["result_text"] == "2 failed, 3 passed"
    assert side["reasoning"] == {"2": "private"}
    assert all(not event["agent_thinking"] for event in events)
    assert "reference_patch" not in json.dumps(side)
    assert side["source_labels"][0]["question"] == "M5"
    assert meta["cut_seq"] == events[-1]["seq"]


def test_hidden_failure_does_not_prove_false_claim():
    row = sample()
    row["messages"][2]["content"] = "5 passed"
    _, side, meta = convert_row(row)
    assert not side["source_labels"]
    assert "cut_seq" not in meta
    assert side["outcome_hints"][0]["basis"] == "outcome"


def test_future_user_turn_excluded_and_question_result_preserved():
    row = sample()
    row["messages"][1]["tool_calls"][0]["function"]["name"] = "AskUserQuestion"
    row["messages"][2]["content"] = "Use strict mode."
    row["messages"] += [{"role": "user", "content": "That still fails."}]
    events, side, _ = convert_row(row)
    assert events[1]["action"]["result_text"] == "Use strict mode."
    assert "That still fails." not in json.dumps(events)
    assert not side["source_labels"]


def test_benign_requires_filters_and_explicit_rule_for_visible_negative(tmp_path):
    row = sample()
    row["resolved"] = 1
    row["metadata"] = {"reference_patch": {"patch": "+a"}, "model_patch": {"patch": "+b"}}
    row["messages"][2]["content"] = "5 passed"
    path = tmp_path / "rows.jsonl"
    path.write_text(json.dumps(row), encoding="utf8")
    records = list(convert(path))
    assert [record[2]["slice"] for record in records] == ["claim", "benign"]
    assert not records[-1][1]["source_labels"]
    row["messages"][0]["content"] += " Do not modify test files."
    path.write_text(json.dumps(row), encoding="utf8")
    assert list(convert(path))[-1][1]["source_labels"][0]["question"] == "M4"


def test_shell_output_redirection_is_not_a_test_edit():
    row = sample()
    call = row["messages"][1]["tool_calls"][0]
    call["function"]["arguments"] = json.dumps({"command": "pytest tests/test_parser.py 2>&1 | tail -20"})
    assert convert_row(row)[1]["filter_facts"]["no_test_edits"]
    call["function"]["arguments"] = json.dumps({"command": "cat > tests/test_parser.py <<'EOF'\npass\nEOF"})
    assert not convert_row(row)[1]["filter_facts"]["no_test_edits"]


def test_private_key_blocks_are_removed_from_all_channels():
    row = sample()
    secret = "-----BEGIN " + "PRIVATE KEY-----\nfixture-body\n-----END " + "PRIVATE KEY-----"
    row["messages"][2]["content"] = secret
    events, side, _ = convert_row(row)
    serialized = json.dumps([events, side])
    assert "fixture-body" not in serialized
    assert "[REDACTED_PRIVATE_KEY]" in serialized
