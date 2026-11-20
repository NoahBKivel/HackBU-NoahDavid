"""Verify negative caps preserve evidence and leave sibling rows unprotected."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from monitor_format import fill_question
from intent_training.assemble import add_twins, balance_cap, pack_siblings
from intent_training.kevpatch.grouping import optimizer_groups


def record(index, *, positive=False, **meta):
    return add_twins({"state": str(index), "questions": {
        "M1": dict(fill_question("M1"), label=positive),
        "M2": dict(fill_question("M2"), label=False)},
        "_meta": {"source": "source", "record_id": str(index), **meta}})


def test_cap_keeps_all_positives_targets_pairs_and_records_but_not_sibling_exemption():
    rows = [record(0, positive=True)]
    rows += [record(i, objective=["M2"], sibling_group="siblings") for i in range(1, 51)]
    rows += [record(51, pair_id="real_pair", objective=["M2"]), record(52, objective=["M1"])]
    capped, metrics = balance_cap(rows, seed=7)
    assert len(capped) == len(rows)
    assert all("M2" in item["questions"] for item in capped[1:51])
    assert "M1" in capped[51]["questions"] and "M1" in capped[52]["questions"]
    incidental = sum("M1" in item["questions"] for item in capped[1:51])
    assert incidental == 10
    assert metrics["collected"]["M1"]["rows"] == len(rows)
    assert metrics["post_cap"]["M1"]["rows"] == incidental + 3
    assert metrics["post_cap"]["M1"]["rate"] > metrics["collected"]["M1"]["rate"]
    assert all(("M1" in item["questions"]) == ("M1~neg" in item["questions"]) for item in capped)
    assert balance_cap(rows, seed=7)[0] == capped


def test_no_record_disappears_and_severity_correction_never_capped():
    rows = [record(i) for i in range(5)]
    rows[0]["questions"].update(D5=dict(fill_question("D5"), label=0),
        L7=dict(fill_question("L7", correction="Check the work."), label="ignored"))
    capped, _ = balance_cap(rows, seed=3)
    assert all(item["questions"] for item in capped)
    assert {"D5", "L7"} <= capped[0]["questions"].keys()


def test_native_replay_questions_and_labels_are_preserved():
    native = {"state": {"ticket": "native"}, "questions": {
        "native_a": {"type": "noul", "instructions": "Native question A", "label": False},
        "native_b": {"type": "choice", "criteria": {"one": "", "two": ""}, "label": "two"}},
        "_meta": {"source": "kev_replay", "native_record": True, "record_kind": "replay"}}
    capped, _ = balance_cap([native], seed=2)
    assert capped == [native]


def test_sibling_packing_uses_fit_decision_and_preserves_state_twins_and_optimizer_step():
    original = record(0)
    original["questions"]["M4"] = dict(fill_question("M4"), label=False)
    calls = []
    def fits(item):
        calls.append(tuple(item["questions"]))
        return len(item["questions"]) <= 2
    siblings = pack_siblings(original, fits=fits)
    assert len(siblings) == 2
    assert all(item["state"] == original["state"] for item in siblings)
    assert set(siblings[0]["questions"]) == {"M1", "M1~neg"}
    assert {key for item in siblings for key in item["questions"]} == set(original["questions"])
    assert len({item["_meta"]["sibling_group"] for item in siblings}) == 1
    assert len(optimizer_groups(siblings, 16)) == 1
    assert any(len(call) == 3 for call in calls)
    with pytest.raises(ValueError, match="fit test"):
        pack_siblings(original, fits=lambda item: False)


def test_already_fitting_record_needs_only_one_actual_packing_fit_check():
    original = record(0)
    calls = []
    packed = pack_siblings(original, fits=lambda item: calls.append(item) or True)
    assert packed == [original] and packed[0] is not original
    assert len(calls) == 1
