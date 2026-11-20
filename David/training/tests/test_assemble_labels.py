"""Exercise label resolution against independent votes and contrary evidence."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from monitor_format import fill_question
from intent_training.assemble import add_twins, collect_votes, positive, resolve_record, resolve_votes, validate_twins


@pytest.mark.parametrize("a,b,target", [(True, False, .5), (True, "cant_tell", .75),
    (False, "cant_tell", .25), ("cant_tell", "cant_tell", .5)])
def test_uncertain_votes_keep_arithmetic_mean_and_positive_ties(a, b, target):
    for key in ("M1", "G1"):
        row = resolve_votes(key, fill_question(key), a, b)
        assert row["target"] == {"false": 1 - target, "true": target}
        assert row["label"] == (target > .5 if key == "G1" else target >= .5)
        if target == .5:
            assert positive(key, row["label"])


@pytest.mark.parametrize("key,value", [("M1", True), ("G1", False)])
def test_agreed_votes_have_hard_labels_only(key, value):
    assert resolve_votes(key, fill_question(key), value, value)["label"] is value
    assert "target" not in resolve_votes(key, fill_question(key), value, value)


def test_choice_positive_wins_tie_and_other_ties_follow_sol():
    row = fill_question("G2", requirement_text="Keep the API.")
    resolved = resolve_votes("G2#R1", row, "done", "broken")
    assert resolved["label"] == "broken"
    assert resolved["target"]["done"] == resolved["target"]["broken"] == .5
    assert resolve_votes("G2#R1", row, "not done", "broken")["label"] == "not done"
    assert resolve_votes("D5", fill_question("D5"), "significant", "serious")["label"] == 1


def test_requirement_annotation_binds_by_exact_text_after_rf_filtering():
    record = {"state": "answer", "questions": {"G2#R1": fill_question("G2", requirement_text="Keep the API.")},
              "_meta": {"cut_seq": 2, "requirement_bindings": {"G2#R1": "Keep the API."}}}
    labels = [{"question": "G2", "value": value, "basis": "visible", "event_seq": 2,
               "requirement_text": text} for text, value in (("Rejected first unit.", "broken"), ("Keep the API.", "done"))]
    resolved, audit = resolve_record(record, {"G2#R1": {"sol": "broken"}}, source_labels=labels, allocation_mode="single_sol")
    assert resolved["questions"]["G2#R1"]["label"] == "done"
    assert len(audit["clashes"]) == 1


def test_visible_labels_override_only_their_question_and_log_each_clashing_vote():
    record = {"state": "visible", "questions": {"M2": fill_question("M2"), "M4": fill_question("M4")},
              "_meta": {"source": "source", "cut_seq": 2}}
    votes = {"M2": {"sol": False, "terra": True}, "M4": {"sol": True, "terra": True}}
    resolved, audit = resolve_record(record, votes, allocation_mode="paired", source_labels=[
        {"question": "M2", "value": True, "basis": "visible", "event_seq": 2},
        {"question": "M2", "value": False, "basis": "outcome", "event_seq": 8},
        {"question": "M4", "value": False, "basis": "outcome", "event_seq": 8}])
    assert resolved["questions"]["M2"]["label"] is True
    assert "target" not in resolved["questions"]["M2"]
    assert resolved["questions"]["M4"]["label"] is True
    assert {clash["question"] for clash in audit["clashes"]} == {"M2", "M4"}
    assert "label" not in record["questions"]["M2"]


def test_construction_yields_and_retry_stops_after_third_attempt():
    record = {"state": "x", "questions": {"M2": fill_question("M2")}}
    votes = {"M2": {"sol": False, "terra": False}}
    for attempt in (1, 2, 3):
        resolved, audit = resolve_record(record, votes, allocation_mode="paired", construction={"attempt": attempt, "intended": {"M2": True}})
        assert resolved["questions"]["M2"]["label"] is False
        assert audit["retry_requests"][0]["retry"] is (attempt < 3)


def test_only_four_twins_derived_with_flipped_targets_and_detect_flipped_label():
    record = {"state": "x", "questions": {key: resolve_votes(key, fill_question(key), True, False)
              for key in ("M1", "L1", "L4", "G1", "M2")}}
    resolved = add_twins(record)
    assert {key for key in resolved["questions"] if "~neg" in key} == {key + "~neg" for key in ("M1", "L1", "L4", "G1")}
    validate_twins(resolved)
    planted = deepcopy(resolved)
    planted["questions"]["M1~neg"]["label"] = planted["questions"]["M1"]["label"]
    with pytest.raises(ValueError, match="inconsistent label"):
        validate_twins(planted)


def test_teacher_envelopes_reject_hash_mismatch_and_missing_votes():
    envelope = {"record_id": "row", "pass": "main", "model_family": "sol", "input_sha256": "same",
                "votes": {"M2": True}}
    other = dict(envelope, model_family="terra", votes={"M2": False})
    assert collect_votes([envelope, other]) == {"row": {"M2": {"sol": True, "terra": False}}}
    with pytest.raises(ValueError, match="different input hashes"):
        collect_votes([envelope, dict(other, input_sha256="different")])
    with pytest.raises(ValueError, match="voted twice"):
        collect_votes([envelope, envelope])
    with pytest.raises(ValueError, match="both teacher"):
        resolve_record({"questions": {"M2": fill_question("M2")}}, {"M2": {"sol": True}}, allocation_mode="paired")


def test_merged_cut_labels_override_first_slice_and_conflicts_block_assembly():
    record = {"state": "visible", "questions": {"M2": fill_question("M2")}, "_meta": {
        "cut_seq": 2, "merged_cut_source_labels": [{"question": "M2", "value": True,
                                                   "basis": "visible", "event_seq": 2}]}}
    votes = {"M2": {"sol": False, "terra": False}}
    resolved, _ = resolve_record(record, votes, allocation_mode="paired")
    assert resolved["questions"]["M2"]["label"] is True
    record["_meta"]["source_label_conflicts"] = [{"question": "M2"}]
    with pytest.raises(ValueError, match="Conflicting visible source labels"):
        resolve_record(record, votes)


def test_merged_cut_labels_override_first_slice_and_conflicts_block_assembly():
    record = {"state": "visible", "questions": {"M2": fill_question("M2")}, "_meta": {
        "cut_seq": 2, "merged_cut_source_labels": [{"question": "M2", "value": True,
                                                   "basis": "visible", "event_seq": 2}]}}
    votes = {"M2": {"sol": False, "terra": False}}
    resolved, _ = resolve_record(record, votes)
    assert resolved["questions"]["M2"]["label"] is True
    record["_meta"]["source_label_conflicts"] = [{"question": "M2"}]
    with pytest.raises(ValueError, match="Conflicting visible source labels"):
        resolve_record(record, votes)
