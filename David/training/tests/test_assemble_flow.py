"""Exercise ordered requirement and diagnostic passes before final admission."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent), str(ROOT / "vendor/kev")]

from monitor_format import EVERY_EVENT, fill_question
from intent_training.assemble.admission import admit_record
from intent_training.assemble.flow import assembly_context, merge_pass, next_pass, resolve_requirements, route
from intent_training.prepare.records import load_tokenizer
from intent_training.assemble.siblings import kev_fit


@pytest.fixture(scope="module")
def tokenizer():
    return load_tokenizer(ROOT / "data/tokenizer")


def test_original_native_optional_wording_keeps_original_labels_and_fits(tokenizer):
    record = {"state": "The original replay input.", "questions": {"original": {"type": "noul", "label": True}},
              "_meta": {"source": "kev_replay", "record_id": "native-original", "native_record": True,
                        "record_kind": "replay"}}
    siblings = admit_record(record, None, tokenizer=tokenizer, fits=kev_fit(tokenizer))
    assert len(siblings) == 1
    assert siblings[0]["questions"] == record["questions"]
    assert siblings[0]["_meta"]["encoder_admitted"] is True


def fixture(*, answer=True, violation=True):
    questions = {key: dict(fill_question(key), label=key == "G1" or (key == "M2" and violation)) for key in EVERY_EVENT}
    if answer:
        questions["G5"] = dict(fill_question("G5"), label=False)
    record = {"state": "USER INSTRUCTIONS\nKeep the API.\nPROJECT DOCUMENTS\n(none)\nRUN LEDGER\n[E1] Edit\nLATEST EVENT\n[E2] MESSAGE",
        "questions": questions, "_meta": {"record_id": "parent", "source": "open_swe", "slice": "claim",
        "construction": "constraint", "cut_seq": 2, "validated_length": 8191,
        "teacher_vote_families": {key: ["sol"] for key in questions}}}
    context = {"events": [{"seq": 1, "type": "tool_completed"},
        {"seq": 2, "type": "turn_completed" if answer else "tool_completed", "turn": {"reason": "answer"} if answer else {}}],
        "side": {"construction": {"type": "constraint"}}, "detailed_event_seqs": [1, 2],
        "requirement_units": [{"source": "[I1]", "position": 1, "text": "Keep the API."},
                              {"source": "[I1]", "position": 2, "text": "This repository contains code."}]}
    return record, context


def requirements(record, context):
    return resolve_requirements(record, context, {
        "parent:unit:1": {"RF": {"sol": True}}, "parent:unit:2": {"RF": {"sol": False}}})


def test_requirements_then_g2_then_localization_then_d2_and_admission(tokenizer):
    record, context = fixture()
    pending = next_pass(record, context, tokenizer=tokenizer)
    assert pending["stage"] == "requirements" and len(pending["records"]) == 2
    accepted = requirements(record, context)
    assert len(accepted["accepted"]) == 1 and accepted["accepted"][0]["id"] == "R1"
    assert "RF" not in record["questions"]
    g2 = next_pass(record, context, requirements=accepted, tokenizer=tokenizer)
    assert g2["stage"] == "main_completion" and set(g2["records"][0]["questions"]) == {"G2#R1"}
    original = deepcopy(record["questions"])
    record, _ = merge_pass(record, g2["records"][0], {"G2#R1": {"sol": "not done"}}, context=context)
    assert all(record["questions"][key] == value for key, value in original.items())
    localization = next_pass(record, context, requirements=accepted, tokenizer=tokenizer)
    assert localization["stage"] == "localization"
    assert set(localization["records"][0]["questions"]) == {"D1#E1", "D1#E2", "D5"}
    record, _ = merge_pass(record, localization["records"][0], {
        "D1#E1": {"sol": False}, "D1#E2": {"sol": False}, "D5": {"sol": "significant"}}, context=context)
    d2 = next_pass(record, context, requirements=accepted, tokenizer=tokenizer)
    assert d2["stage"] == "requirements_diagnostic"
    assert "E2" in d2["records"][0]["questions"]["D2#R1"]["instructions"]
    record, _ = merge_pass(record, d2["records"][0], {"D2#R1": {"sol": True}}, context=context)
    assert next_pass(record, context, requirements=accepted, tokenizer=tokenizer)["stage"] == "complete"
    siblings = admit_record(record, context, requirements=accepted, tokenizer=tokenizer,
                            fits=lambda item: len(item["questions"]) <= 6)
    assert len(siblings) > 1 and all(sibling["state"] == record["state"] for sibling in siblings)
    rows = {key: row for sibling in siblings for key, row in sibling["questions"].items()}
    assert rows["G1~neg"]["label"] is False
    assert set(record["questions"]) <= set(rows)
    assert all(sibling["_meta"]["dependent_questions_complete"] for sibling in siblings)
    assert all(sibling["_meta"]["encoder_admitted"] for sibling in siblings)


def test_missing_rf_votes_cannot_create_partial_accepted_requirements(tokenizer):
    record, context = fixture()
    with pytest.raises(ValueError, match="teacher votes"):
        resolve_requirements(record, context, {"parent:unit:1": {"RF": {"sol": True}}})
    with pytest.raises(ValueError, match="requirements"):
        admit_record(record, context, tokenizer=tokenizer, fits=lambda item: True)


def test_rf_single_secondary_and_two_actual_slots_preserve_votes():
    record, context = fixture()
    record["_meta"].pop("construction")
    result = resolve_requirements(record, context, {
        "parent:unit:1": {"RF": {"terra": True}},
        "parent:unit:2": {"RF": {"sol": True, "terra": False}}})
    assert result["audits"][0]["allocation"] == "rf_single"
    assert len(result["accepted"]) == 2
    assert result["audits"][1]["unused_votes"] == {}


def test_pending_main_relabel_still_prepares_requirement_selection(tokenizer):
    record, context = fixture()
    record["_meta"]["main_relabel_complete"] = False
    assert next_pass(record, context, tokenizer=tokenizer)["stage"] == "requirements"


def test_nonanswer_without_requirement_violation_skips_unneeded_rf(tokenizer):
    record, context = fixture(answer=False, violation=False)
    assert next_pass(record, context, tokenizer=tokenizer)["stage"] == "complete"
    record["questions"]["M4"]["label"] = True
    assert next_pass(record, context, tokenizer=tokenizer)["stage"] == "localization"


def test_empty_requirement_set_does_not_wait_for_a_nonexistent_rf_vote(tokenizer):
    record, context = fixture(violation=False)
    context["requirement_units"] = []
    assert next_pass(record, context, tokenizer=tokenizer)["stage"] == "complete"


def test_screen_routes_only_section_pairs_and_never_event_diagnostics(tokenizer):
    item = {"state": "DOCUMENT SECTIONS\n[S1] Keep the API.", "questions": {
        key: dict(fill_question(key.split("#")[0], section_id="S1"), label=True) for key in ("SCR#S1", "M8#S1")},
        "_meta": {"source": "screen_fixture", "label_bases": ["V"], "record_kind": "screen",
                  "teacher_vote_families": {"SCR#S1": ["sol"], "M8#S1": ["sol"]}}}
    assert next_pass(item, None, tokenizer=tokenizer)["stage"] == "complete"
    bad = deepcopy(item)
    del bad["questions"]["M8#S1"]
    with pytest.raises(ValueError, match="both SCR and M8"):
        route(bad)
    bad["questions"]["M2"] = dict(fill_question("M2"), label=True)
    with pytest.raises(ValueError, match="only SCR and M8"):
        route(bad)


def test_changed_state_and_overwriting_resolved_labels_are_rejected(tokenizer):
    record, context = fixture()
    g2 = next_pass(record, context, requirements=requirements(record, context), tokenizer=tokenizer)["records"][0]
    bad = deepcopy(g2)
    bad["state"] += " Hidden change."
    with pytest.raises(ValueError, match="identity or state"):
        merge_pass(record, bad, {"G2#R1": {"sol": "done"}}, context=context)
    record, _ = merge_pass(record, g2, {"G2#R1": {"sol": "done"}}, context=context)
    with pytest.raises(ValueError, match="replace an already"):
        merge_pass(record, g2, {"G2#R1": {"sol": "broken"}}, context=context)


def test_missing_teacher_provenance_blocks_otherwise_complete_admission(tokenizer):
    record, context = fixture(answer=False, violation=False)
    record["_meta"]["teacher_vote_families"].pop("M2")
    with pytest.raises(ValueError, match="required teacher provenance"):
        admit_record(record, context, tokenizer=tokenizer, fits=lambda item: True)


def test_overflow_construction_cannot_silently_train_as_an_ordinary_event(tokenizer):
    record, context = fixture(answer=False, violation=False)
    record["_meta"]["construction"] = "overflow_screen"
    with pytest.raises(ValueError, match="only SCR and M8"):
        next_pass(record, context, tokenizer=tokenizer)


def test_private_context_projection_preserves_required_evidence_and_excludes_future():
    record, context = fixture()
    context.update(record_id="parent", _meta=record["_meta"])
    context["side"].update(raw_source_record={"future": "not evidence"}, reasoning={"1": "visible reasoning", "3": "future reasoning"},
        source_labels=[{"question": "M2", "basis": "visible", "event_seq": 3, "value": True},
                       {"question": "M2", "basis": "outcome", "event_seq": 3, "value": False}])
    before = deepcopy(context)
    projected = assembly_context(context)
    assert context == before
    assert projected["side"]["reasoning"] == {"1": "visible reasoning"}
    assert projected["side"]["source_labels"] == [context["side"]["source_labels"][1]]
    assert "raw_source_record" not in projected["side"]
    assert projected["requirement_units"] == context["requirement_units"]
    assert projected["events"][0]["seq"] == record["_meta"]["cut_seq"]


def test_nonanswer_localization_runs_alongside_rf_but_d2_waits_for_requirements(tokenizer):
    record, context = fixture(answer=False, violation=True)
    step = next_pass(record, context, tokenizer=tokenizer)
    assert step["stage"] == "localization" and len(step["requirements_records"]) == 2
    record, _ = merge_pass(record, step["records"][0], {
        "D1#E1": {"sol": True}, "D1#E2": {"sol": False}, "D5": {"sol": "minor"}}, context=context)
    assert next_pass(record, context, tokenizer=tokenizer)["stage"] == "requirements"
    assert next_pass(record, context, requirements=requirements(record, context), tokenizer=tokenizer)["stage"] == "requirements_diagnostic"


def test_rf_window_projection_does_not_require_an_event_cut():
    record, context = fixture()
    context.update(record_id="rf_window", _meta=record["_meta"], events=[])
    with pytest.raises(ValueError, match="actual cut"):
        assembly_context(context)
    assert assembly_context(context, event_required=False)["events"] == []
