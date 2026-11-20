"""Verify single-Sol targets and policy-specific instrument denominators."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from monitor_format import fill_question
from intent_training.assemble import balance_cap, original_native, policy_instruments, resolve_record
from intent_training.splits.teacher_fallback import teacher_passed


def record(key, identity="row", **meta):
    kwargs = {"requirement_text": "Keep the requirement."} if key.startswith("G2") else {}
    return {"state": "Observed state", "questions": {key: fill_question(key.split("#")[0], **kwargs)},
            "_meta": {"record_id": identity, "source": "visible_fixture", "label_bases": ["V"], **meta}}


@pytest.mark.parametrize("key,sol,label,target", [("G1", "cant_tell", False, .5),
    ("M2", "cant_tell", True, .5), ("M2", False, False, None), ("M2", True, True, None)])
def test_single_sol_binary_targets_and_g1_tie(key, sol, label, target):
    result, audit = resolve_record(record(key), {key: {"sol": sol}})
    row = result["questions"][key]
    assert row["label"] is label
    assert row.get("target") == (None if target is None else {"false": 1 - target, "true": target})
    assert audit["allocation"] == "single_sol"
    assert result["_meta"]["teacher_vote_families"][key] == ["sol"]


@pytest.mark.parametrize("key,sol,terra,label", [("M2", False, True, False),
    ("G2#R1", "done", "broken", "done"), ("D5", "minor", "serious", 0)])
def test_available_terra_never_changes_single_target_and_remains_auditable(key, sol, terra, label):
    result, audit = resolve_record(record(key), {key: {"sol": sol, "terra": terra}})
    assert result["questions"][key]["label"] == label
    assert "target" not in result["questions"][key]
    assert audit["unused_votes"][key] == {"terra": terra}


def test_paired_source_still_requires_both_votes_and_preserves_mean():
    item = record("M2", source="open_swe", slice="claim", label_bases=[])
    with pytest.raises(ValueError, match="both teacher"):
        resolve_record(item, {"M2": {"sol": False}})
    result, audit = resolve_record(item, {"M2": {"sol": False, "terra": True}})
    assert result["questions"]["M2"]["label"] is True
    assert result["questions"]["M2"]["target"] == {"false": .5, "true": .5}
    assert audit["allocation"] == "paired"


def test_construction_overrides_paired_base_and_diagnostic_inherits_private_type():
    main = record("M2", source="open_swe", label_bases=[])
    result, _ = resolve_record(main, {"M2": {"sol": False}}, construction={"type": "priority", "intended": {"M2": True}})
    assert result["questions"]["M2"]["label"] is False
    diagnostic = record("D5", **result["_meta"])
    resolved, audit = resolve_record(diagnostic, {"D5": {"sol": "significant"}})
    assert audit["allocation"] == "single_sol"
    assert resolved["questions"]["D5"]["label"] == 1


def test_paired_only_instruments_exclude_single_cant_tell_and_extra_terra():
    rows = [record("M2", "pair_a", source="open_swe", slice="claim", label_bases=[]),
            record("M2", "pair_b", source="open_swe", slice="claim", label_bases=[]),
            record("M2", "single_a"), record("M2", "single_b"), record("RF", "single_rf")]
    votes = {"pair_a": {"M2": {"sol": True, "terra": True}},
             "pair_b": {"M2": {"sol": "cant_tell", "terra": False}},
             "single_a": {"M2": {"sol": "cant_tell", "terra": True}},
             "single_b": {"M2": {"sol": False}}, "single_rf": {"RF": {"sol": "cant_tell"}}}
    report = policy_instruments(rows, votes)
    assert report["M2"]["rows"] == report["M2"]["paired_rows"] == 2
    assert report["M2"]["single_sol_rows"] == 2 and report["M2"]["total_rows"] == 4
    assert report["M2"]["cant_tell_votes"] == 1 and report["M2"]["cant_tell_rate"] == .25
    assert report["M2"]["positive_specific_agreement"] == 1
    assert report["M2"]["single_sol_cant_tell_votes"] == 1 and report["M2"]["unused_terra_rows"] == 1
    assert report["RF"]["paired_rows"] == 0 and report["RF"]["cant_tell_rate"] is None
    assert teacher_passed("RF", report["RF"])


def test_native_rf_task_requires_sol_and_source_annotation_remains_final():
    item = record("RF", native_record=True, record_kind="task", cut_seq=0,
        merged_cut_source_labels=[{"question": "RF", "value": True, "basis": "visible", "event_seq": 0}])
    assert not original_native(item)
    with pytest.raises(ValueError, match="Sol for single"):
        resolve_record(item, {})
    result, audit = resolve_record(item, {"RF": {"sol": False}})
    assert result["questions"]["RF"]["label"] is True and audit["clashes"]
    assert original_native(record("RF", native_record=True, record_kind="replay"))


def test_screen_targets_protect_scr_and_m8_despite_inherited_objectives():
    item = {"state": "screen", "questions": {key: {"type": "noul", "label": False} for key in ("SCR#S1", "M8#S1")},
            "_meta": {"source": "open_swe", "record_kind": "screen", "objective": ["M5", "G5"]}}
    kept, _ = balance_cap([item], seed=1)
    assert kept[0]["questions"] == item["questions"]
    assert kept[0]["_meta"]["objective"] == ["M8", "SCR"]


def test_visible_label_provenance_survives_resolution_for_instrument_allocation():
    item = record("M2", source="unmapped_visible_fixture", label_bases=[])
    votes = {"M2": {"sol": False}}
    resolved, _ = resolve_record(item, votes, source_labels=[
        {"question": "M2", "value": True, "basis": "visible", "event_seq": 0}])
    assert resolved["questions"]["M2"]["label"] is True
    report = policy_instruments([resolved], {"row": votes})
    assert report["M2"]["single_sol_rows"] == 1 and report["M2"]["paired_rows"] == 0
