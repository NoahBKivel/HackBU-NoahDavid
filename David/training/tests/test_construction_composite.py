"""Verify composite assembly without generating agent trajectories."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

from intent_training.constructions.composite import build, generation_requests


def event(seq, tool=None):
    return {"seq": seq, "type": "tool_completed" if tool else "session_started",
            "ts": "", "new_items": [], "action": {
                "tool": tool, "args": {"file_path": "fixture.py"}, "result_text": "",
                "is_error": False, "file_changes": [{"path": "fixture.py", "op": "edit",
                    "patch": [{"lines": ["-old", "+new"]}]}]} if tool else {},
            "agent_text": "", "agent_thinking": "", "todos": [], "turn": {}}


@pytest.fixture
def base():
    events = [event(1), event(4, "Edit"), event(9, "Edit")]
    events[0]["new_items"] = [{"kind": "user_instruction", "id": "I1", "text": "Preserve checks."}]
    events[-1]["agent_text"] = "Future evidence must be absent."
    side = {"source_labels": [{"question": "M4", "value": True, "event_seq": 4,
                               "basis": "visible", "origin": "rule"}],
            "reasoning": {"1": "Earlier.", "4": "Original action.", "9": "Future."},
            "outcomes": {"reward": 1}}
    return events, side, {"source": "fixture", "trajectory_id": "trajectory",
                          "source_record_id": "row", "group_id": "group", "pair_id": "pair"}


def request(base, tmp_path, **kwargs):
    return list(generation_requests(*base, requests_path=tmp_path / "requests.jsonl", **kwargs))[0]


def test_request_uses_only_known_evidence_and_persists_once(base, tmp_path):
    original = deepcopy(base)
    first = request(base, tmp_path)
    assert request(base, tmp_path) == first
    assert first["refs"]["event_seqs"] == [1, 4]
    assert "Future evidence must be absent" not in first["prompt"]
    assert len((tmp_path / "requests.jsonl").read_text().splitlines()) == 1
    assert base == original


@pytest.mark.parametrize("length", [2, 3])
def test_pair_cuts_and_invalidated_labels(base, tmp_path, length):
    original = deepcopy(base)
    req = request(base, tmp_path)
    response = {"edits": [event(i, "Edit") for i in range(length)]}
    pairs = list(build(*base, generated_texts={req["id"]: json.dumps(response)}))
    positive, negative = pairs
    assert positive[0][:-1] == negative[0]
    assert len(positive[0]) == length + 1
    for intended, (events, side, meta) in zip((True, False), pairs):
        assert meta["cut_seq"] == events[-1]["seq"]
        assert (meta["group_id"], meta["pair_id"]) == ("group", "pair")
        assert side["source_labels"] == []
        assert side["reasoning"] == {"1": "Earlier."}
        assert "outcomes" not in side
        assert side["construction"]["intended"] == {"L2": intended}
    assert base == original


def test_no_generation_or_known_visible_violation_means_no_output(base, tmp_path):
    assert list(build(*base)) == []
    base[1]["source_labels"][0]["basis"] = "outcome"
    assert list(generation_requests(*base, requests_path=tmp_path / "requests.jsonl")) == []


def test_attempt_limit_and_execution_evidence_rejected(base, tmp_path):
    for attempt in (0, 4, True):
        with pytest.raises(ValueError):
            list(build(*base, attempt=attempt))
    assert request(base, tmp_path, attempt=2)["id"] != request(base, tmp_path)["id"]
    req = request(base, tmp_path)
    edits = [event(1, "Edit"), event(2, "Edit")]
    edits[-1]["action"]["result_text"] = "Invented execution result."
    with pytest.raises(ValueError):
        list(build(*base, generated_texts={req["id"]: {"edits": edits}}))


def test_review_proof_is_separate_from_source_labels_and_preserves_lineage(base, tmp_path):
    base[1]["source_labels"] = []
    base[1]["construction"] = {"type": "constraint", "intended": {"M2": True}, "attempt": 1}
    base[2]["source"] = "swe_chat"
    proof = {"question": "M4", "value": True, "event_seq": 4, "basis": "review",
             "evidence": {"old_string": "it", "new_string": "it.skip"}}
    req = request(base, tmp_path, known_violation=proof)
    pair = list(build(*base, known_violation=proof,
                      generated_texts={req["id"]: {"edits": [event(1, "Edit"), event(2, "Edit")]}}))
    assert pair[0][1]["source_labels"] == []
    assert pair[0][1]["construction"]["base_proof"] == proof
    assert pair[0][1]["construction"]["lineage"] == base[1]["construction"]
    base[2]["source"] = "unapproved"
    with pytest.raises(ValueError):
        list(generation_requests(*base, known_violation=proof, requests_path=tmp_path / "other.jsonl"))
