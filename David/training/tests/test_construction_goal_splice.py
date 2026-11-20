"""Check splice isolation, generated-event validation and intended polarity."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

from intent_training.constructions.goal_splice import build, generation_requests, main
from monitor_format import validate_events


@pytest.fixture
def base():
    event = {"seq": 1, "type": "session_started", "ts": "", "new_items": [
        {"kind": "user_instruction", "id": "I1", "text": "Fix the parser bug."}],
        "action": {}, "agent_text": "", "agent_thinking": "", "todos": [], "turn": {}}
    future = {**deepcopy(event), "seq": 2, "new_items": [], "agent_text": "FUTURE_SENTINEL"}
    return [event, future], {"reasoning": {"1": "Observed input.", "2": "FUTURE_REASONING"},
                           "outcomes": {"reward": 1}, "source_labels": []}, {
        "source": "fixture", "trajectory_id": "trajectory", "task_id": "task",
        "group_id": "group", "pair_id": "existing_pair", "prefix_seq": 1}


def test_requests_use_only_retained_prefix_and_are_deterministic(base):
    events, side, meta = base
    jobs = list(generation_requests(*base))
    assert len(jobs) == 2
    assert jobs == list(generation_requests(events, side, meta))
    assert all("FUTURE" not in json.dumps(job) for job in jobs)
    assert all(job["refs"]["event_seqs"] == [1] for job in jobs)
    assert len({job["id"] for job in jobs}) == len(jobs)
    assert list(generation_requests(*base, attempt=2))[0]["id"] != jobs[0]["id"]


def test_pair_preserves_grouping_and_g1_polarity_without_source_labels(base):
    original = deepcopy(base)
    jobs = list(generation_requests(*base))
    supplied = {job["id"]: json.dumps({"messages": ["A fixture choice.", "A fixture plan.", "A fixture next action."]}) for job in jobs}
    outputs = list(build(*base, generated_texts=supplied))
    assert len(outputs) == 2
    assert base == original
    for events, side, meta in outputs:
        validate_events(events)
        assert len(events) == 4
        assert events[0] == base[0][0]
        assert all(event["action"] == {} for event in events[1:])
        assert all(not event["agent_thinking"] for event in events[1:])
        assert side["reasoning"] == {"1": "Observed input."}
        assert side["source_labels"] == []
        assert "outcomes" not in side
        assert set(side) == {"reasoning", "source_labels", "construction"}
        assert meta["cut_seq"] == events[-1]["seq"]
        assert meta["objective"] == ["L4", "L1", "G1"]
        for key in ("trajectory_id", "task_id", "group_id", "pair_id"):
            assert meta[key] == base[2][key]
    assert outputs[0][1]["construction"]["intended"] == {"L4": True, "L1": True, "G1": False}
    assert outputs[1][1]["construction"]["intended"] == {"L4": False, "L1": False, "G1": True}


@pytest.mark.parametrize("response", [{"messages": ["Only one."]}, {"messages": ["a", "b", ""]},
                                      {"messages": ["a", "b", "c"], "action": {}}, "invalid json"])
def test_malformed_generated_continuation_is_rejected(base, response):
    job = next(generation_requests(*base))
    with pytest.raises(ValueError):
        list(build(*base, generated_texts={job["id"]: response}))


def test_generation_is_required_and_retries_are_bounded(base):
    assert list(build(*base)) == []
    for attempt in (0, 4, True):
        with pytest.raises(ValueError):
            list(generation_requests(*base, attempt=attempt))


def test_provider_fences_and_assistant_message_objects_preserve_text(base):
    job = next(generation_requests(*base))
    text = json.dumps({"messages": [{"role": "assistant", "content": "Fixture one."},
                                    {"kind": "assistant_message", "text": "Fixture two."}, "Fixture three."]})
    outputs = list(build(*base, generated_texts={job["id"]: "```json\n" + text + "\n```"}))
    assert [event["agent_text"] for event in outputs[0][0][1:]] == ["Fixture one.", "Fixture two.", "Fixture three."]


@pytest.mark.parametrize("message", [{"role": "user", "content": "Unauthorized fixture."},
                                    {"role": "assistant", "content": "Fixture.", "tool_calls": []}])
def test_provider_message_objects_cannot_inject_users_or_tool_evidence(base, message):
    job = next(generation_requests(*base))
    with pytest.raises(ValueError):
        list(build(*base, generated_texts={job["id"]: {"messages": [message] * 3}}))


@pytest.mark.parametrize("wrapped", [False, True])
def test_lossless_preamble_and_benign_message_metadata(base, wrapped):
    job = next(generation_requests(*base))
    payload = json.dumps({"messages": [{"message": "First fixture.", "role": "assistant"},
                                       {"message_id": "A2", "text": "Second fixture.", "type": "text"},
                                       {"text": "Third fixture.", "artifacts": []}]})
    response = "Here is the requested JSON.\n" + ("```json\n" + payload + "\n```" if wrapped else payload)
    output = list(build(*base, generated_texts={job["id"]: response}))[0]
    assert [event["agent_text"] for event in output[0][1:]] == ["First fixture.", "Second fixture.", "Third fixture."]


def test_lossless_rescue_rejects_ambiguity_and_nonempty_artifacts(base):
    job = next(generation_requests(*base))
    payload = json.dumps({"messages": ["a", "b", "c"]})
    bad = ["```json\n" + payload + "\n```\n```json\n" + payload + "\n```",
           {"messages": [{"text": "Fixture.", "artifacts": ["tool result"]}] * 3},
           {"messages": [{"text": "Fixture.", "content": "Different fixture."}] * 3}]
    for response in bad:
        with pytest.raises(ValueError):
            list(build(*base, generated_texts={job["id"]: response}))


def test_visible_prefix_violation_is_rejected_but_future_is_not(base):
    events, side, meta = deepcopy(base)
    side["source_labels"] = [{"question": "G1", "value": False, "basis": "visible", "event_seq": 2}]
    assert len(list(generation_requests(events, side, meta))) == 2
    side["source_labels"][0]["event_seq"] = 1
    with pytest.raises(ValueError):
        list(generation_requests(events, side, meta))


def test_runner_deduplicates_trajectories_and_archives_side(base, tmp_path, monkeypatch):
    events, side, meta = deepcopy(base)
    meta["source"] = "open_swe"
    side["outcome_hints"] = {"reward": "Original result."}
    record = {"events": events, "side": side, "meta": meta}
    folder = tmp_path / "data/converted"
    folder.mkdir(parents=True)
    (folder / "open_swe.jsonl").write_text((json.dumps(record) + "\n") * 2, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["goal_splice", "--root", str(tmp_path), "--base-limit", "2"])
    main()
    report = json.loads((tmp_path / "results/constructions/goal_splice.json").read_text())
    assert report["base_count"] == 1
    assert report["request_count"] == 2
    assert report["duplicate_base_count"] == 1
    archived = json.loads((tmp_path / "data/constructions/goal_splice-base-side.jsonl").read_text())
    assert "outcome_hints" in archived["side_fields"]
    assert archived["source_path"] == str(Path("data/converted/open_swe.jsonl"))
    assert archived["line"] == 1
    assert len(archived["side_sha256"]) == 64
    assert "side" not in archived
