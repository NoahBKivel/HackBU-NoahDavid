"""Verify independent evidence and monitor class semantics in positive plans."""

from fractions import Fraction

import pytest

from intent_training.assemble.positive_plan import distribute, is_positive, preregister


def test_semantics_and_floor_exclusions():
    assert is_positive("G1", False)
    assert not is_positive("G1", True)
    assert is_positive("G2", "broken")
    assert is_positive("G2", "not done")
    assert not is_positive("G2", "done")
    plan = preregister([], scale=Fraction(1), blockers=[])
    assert plan["floors"]["M5"] == 60
    assert not {"SCR", "M8", "D1", "D3", "D2", "L7", "D5"} & plan["floors"].keys()


def test_exact_expectation_and_unfixed_evidence_prevents_seal():
    entry = {"id": "paired", "kind": "construction", "part": "task",
             "effective_nplan": "300", "positive_shares": {"L2": "1/2"}, "evidence_fixed": False}
    plan = preregister([entry], scale=Fraction(860, 1063), blockers=[])
    assert plan["status"] == "provisional"
    assert Fraction(plan["expected_exact"]["L2"]) == Fraction(129000, 1063)
    assert plan["floors"]["L2"] == float(Fraction(103200, 1063))


def test_teacher_outcomes_cannot_be_used_as_plan_evidence():
    entry = {"id": "teacher", "kind": "teacher", "part": "task",
             "effective_nplan": 100, "positive_shares": {"M5": "1/2"}}
    with pytest.raises(ValueError, match="must remain zero"):
        preregister([entry], scale=Fraction(1), blockers=[])


def test_rounding_preserves_count_without_dataset_duplication():
    allocation = distribute(7, {"a": Fraction(1), "b": Fraction(1), "c": Fraction(1)})
    assert allocation == {"a": 3, "b": 2, "c": 2}
