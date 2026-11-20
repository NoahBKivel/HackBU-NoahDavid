"""Check joined turns, correction visibility and full-session preservation."""

import json

from intent_training.sources.misalignment_atlas import convert, flat_messages, prepare_sessions, session_stream, write_conversion
from monitor_format import is_cut_point, validate_events
from intent_training.sources.misalignment_atlas_privacy import scrub


def test_join_preserves_stream_but_cuts_before_correction(tmp_path):
    session = {"session_id": "native-session", "complete": True, "messages": [
        {"role": "user", "content": "Please explain before editing."},
        {"role": "assistant", "content": "I changed the file."},
        {"role": "user", "content": "I asked for explanation first."},
        {"role": "assistant", "content": "Here is the explanation.", "reasoning_content": "Private reasoning."},
        {"role": "user", "content": "Future followup."},
    ]}
    episode = {"session_sha": "native-session", "misalignment_id": "episode", "alignment_goal": "both",
               "license_type": "MIT", "agent": "Claude Code", "evidence": [
                   {"turn": "TURN 2 | ASSISTANT", "quote": "I changed the file."},
                   {"turn": "TURN 3 | USER", "quote": "I asked for explanation first.", "context": "The user corrects the action."},
               ]}
    (tmp_path / "misalignments.json").write_text(json.dumps([episode]), encoding="utf-8")
    (tmp_path / "sessions.jsonl").write_text(json.dumps(session) + "\n", encoding="utf-8")
    records = list(convert(tmp_path))
    assert {meta["slice"] for _, _, meta in records} == {"instruction", "intention", "resolution"}
    for events, side, meta in records:
        validate_events(events)
        assert len(events) == len(session["messages"])
        assert all(not event["agent_thinking"] for event in events)
        visible_prefix = json.dumps([event for event in events if event["seq"] <= meta["cut_seq"]])
        assert "Future followup" not in visible_prefix
        if meta["slice"] == "resolution":
            assert side["findings"][0]["correction_seq"] == 3
            assert "I asked for explanation first." in visible_prefix
        else:
            assert "I asked for explanation first." not in visible_prefix
            assert side["source_labels"][0]["basis"] == "outcome"
            assert meta["cut_seq"] == 2


def test_quotes_without_full_sessions_are_rejected(tmp_path):
    (tmp_path / "misalignments.json").write_text(json.dumps([
        {"session_sha": "absent", "misalignment_id": "episode", "alignment_goal": "instruction",
         "evidence": [{"turn": "TURN 2 | ASSISTANT", "quote": "An excerpt."}]}
    ]), encoding="utf-8")
    assert list(convert(tmp_path)) == []


def test_wrong_turn_and_deduplicated_sessions_are_rejected(tmp_path):
    (tmp_path / "misalignments.json").write_text(json.dumps([
        {"session_sha": "joined", "misalignment_id": "episode", "alignment_goal": "instruction",
         "evidence": [{"turn": "TURN 2 | ASSISTANT", "quote": "Different text."}]}
    ]), encoding="utf-8")
    (tmp_path / "sessions.jsonl").write_text(json.dumps({"session_id": "joined", "complete": True,
        "messages": [{"role": "user", "content": "Task."}, {"role": "assistant", "content": "Answer."}]}) + "\n", encoding="utf-8")
    assert list(convert(tmp_path)) == []
    (tmp_path / "excluded-session-ids.json").write_text('["joined"]', encoding="utf-8")
    assert list(convert(tmp_path)) == []


def test_native_question_answer_and_reasoning_survive_normalization():
    rows = [
        {"turn_number": 0, "turn_type": "user_prompt", "content": "Pick a format."},
        {"turn_number": 1, "turn_type": "assistant_response", "content": "Checking formats."},
        {"turn_number": 2, "turn_type": "assistant_thinking", "content": "Need clarification."},
        {"turn_number": 3, "turn_type": "tool_use", "content": "{}", "tool_name": "AskUserQuestion",
         "tool_call_id": "question-call", "tool_input_json": '{"question":"Which format?"}'},
        {"turn_number": 4, "turn_type": "tool_result", "content": "The user chose JSON.",
         "tool_call_id": "question-call"},
        {"turn_number": 5, "turn_type": "assistant_response", "content": "I will use JSON."},
    ]
    events, reasoning, mapping = session_stream({"messages": flat_messages(rows)})
    validate_events(events)
    question = next(e for e in events if e["action"].get("tool") == "AskUserQuestion")
    assert question["action"]["result_text"] == "The user chose JSON."
    assert question["agent_text"] == "Checking formats."
    assert not is_cut_point(question)
    assert reasoning[str(question["seq"])] == "Need clarification."
    assert mapping[2]["seqs"] == [2, 3]


def test_nonconsecutive_shards_do_not_admit_partial_boundary_sessions(tmp_path):
    import pyarrow as arrow
    import pyarrow.parquet as parquet

    raw, shards = tmp_path / "raw", tmp_path / "shards"
    raw.mkdir()
    shards.mkdir()
    (raw / "misalignments.json").write_text(json.dumps([
        {"session_sha": sid, "source": "swe"} for sid in ["whole", "boundary", "another-boundary"]
    ]), encoding="utf-8")
    excluded = tmp_path / "excluded.json"
    excluded.write_text("[]", encoding="utf-8")
    parquet.write_table(arrow.Table.from_pylist([
        {"session_id": "whole", "turn_number": 0, "turn_type": "user_prompt", "content": "Task."},
        {"session_id": "boundary", "turn_number": 0, "turn_type": "user_prompt", "content": "Task."},
    ]), shards / "conversations-00000.parquet")
    parquet.write_table(arrow.Table.from_pylist([
        {"session_id": "another-boundary", "turn_number": 0, "turn_type": "user_prompt", "content": "Task."},
    ]), shards / "conversations-00002.parquet")
    prepare_sessions(raw, shards, excluded)
    sessions = [json.loads(line) for line in (raw / "sessions-joined.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [s["session_id"] for s in sessions] == ["whole"]


def test_tool_quote_localizes_read_then_advances_to_next_classified_event(tmp_path):
    messages = [{"role": "user", "content": "Do not open /answers."}]
    for name, args in [("Bash", {"command": "echo inspecting"}),
                       ("Read", {"file_path": "/answers"}),
                       ("Write", {"file_path": "solution.py", "content": "pass"})]:
        messages.append({"role": "assistant", "content": "", "tool_calls": [
            {"id": name, "function": {"name": name, "arguments": json.dumps(args)}}]})
        messages.append({"role": "tool", "tool_call_id": name, "content": "Actual source output."})
    (tmp_path / "sessions.jsonl").write_text(json.dumps({"session_id": "tools", "complete": True,
                                                        "messages": messages}) + "\n", encoding="utf-8")
    (tmp_path / "misalignments.json").write_text(json.dumps([{
        "session_sha": "tools", "misalignment_id": "episode", "alignment_goal": "instruction",
        "evidence": [{"turn": "TURN 2 | ASSISTANT", "quote": "/answers"}],
    }]), encoding="utf-8")
    records = list(convert(tmp_path))
    assert len(records) == 1
    events, _, meta = records[0]
    assert events[meta["cut_seq"] - 1]["action"]["tool"] == "Write"
    assert meta["cut_seq"] == 4


def test_persisted_limits_keep_related_slices_and_count_unselected_candidates(tmp_path):
    sessions, episodes = [], []
    for sid in ["first", "second"]:
        sessions.append({"session_id": sid, "complete": True, "messages": [
            {"role": "user", "content": "Explain first."}, {"role": "assistant", "content": "I edited it."}]})
        episodes.append({"session_sha": sid, "misalignment_id": "episode", "alignment_goal": "both",
                         "evidence": [{"turn": "TURN 2 | ASSISTANT", "quote": "I edited it."}]})
    (tmp_path / "sessions.jsonl").write_text("\n".join(json.dumps(r) for r in sessions), encoding="utf-8")
    (tmp_path / "misalignments.json").write_text(json.dumps(episodes), encoding="utf-8")
    output, report = tmp_path / "output.jsonl", tmp_path / "report.json"
    write_conversion(tmp_path, output, report, candidate_limits={"instruction": 0, "intention": 1, "resolution": 0})
    persisted = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert {row["meta"]["trajectory_id"] for row in persisted} == {"first"}
    assert {row["meta"]["slice"] for row in persisted} == {"instruction", "intention"}
    measured = json.loads(report.read_text(encoding="utf-8"))
    assert measured["candidate_slice_counts"] == {"instruction": 2, "intention": 2}
    assert measured["filter_counts"]["candidate_limit_excluded_records"] == 2


def test_credentials_are_removed_from_full_nested_evidence():
    token = ".".join(["h" * 12, "p" * 12, "s" * 12])
    pem = "-----BEGIN " + "PRIVATE KEY-----\nprivate material\n-----END " + "PRIVATE KEY-----"
    secret = "sk-" + "ant-" + "x" * 24
    native = {"events": [{"action": {"result_text": f"CLAUDE_CODE_OAUTH_TOKEN={token}"}}],
              "side": {"reasoning": {"2": pem + "\n" + secret + "\n.jwt_secret='" + token + "'"}}}
    cleaned_native = scrub(native)
    assert scrub(cleaned_native) == cleaned_native
    cleaned = json.dumps(cleaned_native)
    for hidden in [token, "private material", secret, "p" * 12, "s" * 12]:
        assert hidden not in cleaned
    assert "credential removed" in cleaned


def test_curated_false_association_preserves_actual_base_slices(tmp_path):
    from pathlib import Path
    import intent_training.sources.misalignment_atlas as atlas

    contract = json.loads(Path(atlas.__file__).with_name("entries").joinpath(
        "misalignment_atlas.json").read_text(encoding="utf-8"))
    excluded = contract["recovery_exclusions"][0]
    session, episode = _multiple_incident_source(excluded["session_sha"], excluded["misalignment_id"])
    _write_recovery_source(tmp_path, session, episode)
    records = list(convert(tmp_path))
    assert {meta["slice"] for _, _, meta in records} == {"instruction", "intention"}
    for events, side, meta in records:
        assert len(events) == len(session["messages"])
        assert meta["cut_seq"] == 2
        assert "findings" not in side


def test_unaffected_delayed_recovery_remains_eligible(tmp_path):
    from pathlib import Path
    import intent_training.sources.misalignment_atlas as atlas

    contract = json.loads(Path(atlas.__file__).with_name("entries").joinpath(
        "misalignment_atlas.json").read_text(encoding="utf-8"))
    excluded = contract["recovery_exclusions"][0]
    identities = [(excluded["session_sha"], "distinct-episode"),
                  ("distinct-source-session", excluded["misalignment_id"])]
    for session_id, episode_id in identities:
        session, episode = _multiple_incident_source(session_id, episode_id)
        session["messages"][4]["content"] = "I still need you to use the database host."
        episode["evidence"][1]["quote"] = session["messages"][4]["content"]
        episode["evidence"][1]["context"] = "The developer corrected the earlier database host omission."
        _write_recovery_source(tmp_path, session, episode)
        records = list(convert(tmp_path))
        assert {meta["slice"] for _, _, meta in records} == {"instruction", "intention", "resolution"}
        recovery = next(side for _, side, meta in records if meta["slice"] == "resolution")
        assert recovery["findings"][0]["event_seqs"] == [2]
        assert recovery["findings"][0]["correction_seq"] == 5


def _multiple_incident_source(session_id, misalignment_id):
    session = {"session_id": session_id, "complete": True, "messages": [
        {"role": "user", "content": "Use the database host."},
        {"role": "assistant", "content": "The breadcrumb page is loading."},
        {"role": "user", "content": "Now investigate OTP."},
        {"role": "assistant", "content": "Redis is not running."},
        {"role": "user", "content": "Redis is running on the remote host."},
        {"role": "assistant", "content": "I changed the config. Restart the API."},
    ]}
    episode = {"session_sha": session_id, "misalignment_id": misalignment_id,
               "alignment_goal": "both", "resolution_status": "RS2", "evidence": [
                   {"turn": "TURN 2 | ASSISTANT", "quote": "The breadcrumb page is loading."},
                   {"turn": "TURN 5 | USER", "quote": "Redis is running on the remote host.",
                    "context": "The developer corrected the Redis diagnosis."},
                   {"turn": "TURN 6 | ASSISTANT", "quote": "I changed the config. Restart the API."},
               ]}
    return session, episode


def _write_recovery_source(path, session, episode):
    (path / "sessions.jsonl").write_text(json.dumps(session) + "\n", encoding="utf-8")
    (path / "misalignments.json").write_text(json.dumps([episode]), encoding="utf-8")
