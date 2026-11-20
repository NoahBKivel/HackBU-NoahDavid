"""Test evidence boundaries, independent dispatch and measured vote instruments."""

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

import pytest
from monitor_format import fill_question
from intent_training.teacher import prepare_record, requirement_records, diagnostic_record
from intent_training.teacher import batches, prompt, validate_vote, agreement_report
from intent_training.teacher.dispatch import INSTRUCTIONS
from intent_training.teacher.relabel import request_relabel


def record():
    return {"record_id": "trace:cut", "state": "LATEST EVENT E2: answer",
            "questions": {"M2": dict(fill_question("M2"), label=True),
                          "M1~neg": dict(fill_question("M1~neg"), label=False)},
            "_meta": {"source": "fixture", "cut_seq": 2}}


def test_future_and_intentions_never_reach_teacher():
    prepared = prepare_record(record(), {"reasoning": {"1": "past", "3": "future"},
        "construction": {"intended": {"M2": True}}, "outcomes": {"tests": "future"},
        "source_labels": [{"question": "M2", "value": True, "event_seq": 3, "basis": "visible"},
                          {"question": "M2", "value": True, "event_seq": 4, "basis": "outcome"}]})
    assert prepared["teacher_side"]["reasoning"] == {"1": "past"}
    assert len(prepared["teacher_side"]["source_labels"]) == 1
    assert set(prepared["questions"]) == {"M2"}
    assert "label" not in prepared["questions"]["M2"]
    assert "construction" not in prepared["teacher_side"]


def test_instruction_block_is_verbatim():
    spec = (ROOT.parent / "docs/TRAINING-SPEC.md").read_text(encoding="utf-8")
    block = spec.split("### 8.2 Labelling instructions (given to every vote)", 1)[1].split("### 8.3", 1)[0].strip()
    assert INSTRUCTIONS == block


def test_batches_isolate_sources_and_respect_limit():
    rows = []
    for i in range(43):
        item = prepare_record(record())
        item["record_id"] = str(i)
        item["source"] = "a" if i < 38 else "b"
        rows.append(item)
    grouped = list(batches(rows, count_tokens=len, input_limit=100000, batch_size=20))
    assert [len(batch["records"]) for batch in grouped] == [20, 18, 5]
    for batch in grouped:
        assert len({row["source"] for row in batch["records"]}) == 1
    with pytest.raises(ValueError, match="single record"):
        list(batches(rows, count_tokens=len, input_limit=10))


def test_provenance_and_uncertainty_validation():
    batch = next(batches([prepare_record(record())], count_tokens=len, input_limit=100000))
    vote = {"record_id": "trace:cut", "batch_id": batch["batch_id"],
            "model_family": "sol", "model": "gpt-6.1-sol", "pass": "main",
            "input_sha256": batch["input_sha256"], "votes": {"M2": "cant_tell"},
            "evidence": {"M2": "The visible action leaves the requirement unresolved."}}
    assert validate_vote(vote, batch, "sol") == vote
    bad = deepcopy(vote)
    bad["votes"]["M2"] = 0.5
    with pytest.raises(ValueError):
        validate_vote(bad, batch, "sol")
    bad = deepcopy(vote)
    bad["model_family"] = "terra"
    with pytest.raises(ValueError):
        validate_vote(bad, batch, "sol")
    assert INSTRUCTIONS in prompt(batch, "sol", "output.jsonl")
    inline = prompt(batch, "sol")
    assert INSTRUCTIONS in inline
    assert "Use no local tools" in inline
    assert "Return only the JSON array" in inline


def test_requirement_selection_is_separate_and_diagnostics_follow_resolved_labels():
    units = [{"source": "I1", "position": 1, "text": "Keep the public API."}]
    rf = requirement_records("trace:cut", "fixture", units)
    assert rf[0]["parent_record_id"] == "trace:cut"
    assert list(rf[0]["questions"]) == ["RF"]
    localized = diagnostic_record(record(), {}, stage="localization", detailed_event_seqs=[1, 2])
    assert set(localized["questions"]) == {"D1#E1", "D1#E2", "D5"}
    assert "stated requirement" in localized["questions"]["D1#E1"]["instructions"]
    d2 = diagnostic_record(record(), {}, stage="requirements_diagnostic", detailed_event_seqs=[1, 2], requirements=units)
    assert "E2" in d2["questions"]["D2#R1"]["instructions"]
    benign = record()
    benign["questions"]["M2"]["label"] = False
    assert diagnostic_record(benign, {}, stage="localization", detailed_event_seqs=[2]) is None


def test_empty_positive_class_is_unmeasured_and_uncertainty_counted():
    report = agreement_report([("M2", False, False), ("G1", False, True),
                               ("M5", "cant_tell", True)])
    assert report["M2"]["positive_specific_agreement"] is None
    assert report["G1"]["positive_specific_agreement"] == 0
    assert report["M5"]["cant_tell_rate"] == 0.5
    assert report["M5"]["tightening_required"] is True


def test_relabel_requires_tightening_and_permits_one_attempt():
    instrument = {"tightening_required": True}
    with pytest.raises(ValueError):
        request_relabel("M5", instrument, "")
    first = request_relabel("M5", instrument, "Quote the visible claim and contradicting check.")
    assert first["action"] == "relabel_once"
    assert request_relabel("M5", instrument, "More details", [first])["labels_stand"] is True
