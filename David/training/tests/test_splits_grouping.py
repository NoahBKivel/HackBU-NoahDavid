"""Reject planted pair leakage and preserve transitive stable assignments."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.splits import add_dev_topups, assert_split_integrity, grouped_records, split_records
from intent_training.splits import preregister_positives, source_quotas


def record(index, **meta):
    return {"state": str(index), "questions": {"M2": {"type": "noul", "instructions": "Question?", "label": False}},
            "_meta": {"source": "source", "trajectory_id": str(index), **meta}}


def test_pair_trajectory_task_links_are_transitive_and_order_independent():
    rows = [record(0, pair_id="p"), record(1, pair_id="p", task_id="t"), record(2, task_id="t")]
    rows += [record(i) for i in range(3, 20)]
    assert sorted(map(len, grouped_records(rows).values()))[-1] == 3
    split = split_records(rows, seed=11)
    reversed_split = split_records(rows[::-1], seed=11)
    locations = lambda data: {r["state"]: name for name, records in data.items() for r in records}
    assert locations(split) == locations(reversed_split)
    assert len({locations(split)[str(i)] for i in range(3)}) == 1
    assert sum(map(len, split.values())) == len(rows)


def test_planted_pair_leak_is_rejected():
    a, b = record(0, pair_id="p"), record(1, pair_id="p")
    with pytest.raises(ValueError, match="crosses a split"):
        assert_split_integrity({"train": [a], "base_dev": [b]})


def test_source_fallback_and_identical_input_cannot_leak():
    a, b = record(0), record(1)
    del a["_meta"]["trajectory_id"]
    del b["_meta"]["trajectory_id"]
    assert len(grouped_records([a, b])) == 1
    duplicate = deepcopy(a)
    duplicate["_meta"] = {"source": "other", "trajectory_id": "another"}
    duplicate["questions"]["M2"]["label"] = True
    with pytest.raises(ValueError, match="crosses a split"):
        assert_split_integrity({"train": [a], "base_dev": [duplicate]})


def test_topups_are_separate_from_base_dev_and_cannot_touch_training():
    split = split_records([record(i) for i in range(20)], seed=3)
    base = deepcopy(split["base_dev"])
    result = add_dev_topups(split, [record(50)])
    assert result["base_dev"] == base
    assert result["dev_topup"][0]["_meta"]["split"] == "dev_topup"
    with pytest.raises(ValueError, match="crosses a split"):
        add_dev_topups(split, [deepcopy(split["train"][0])])


def test_quotas_and_positive_floor_never_use_observed_teacher_positives():
    quotas = source_quotas([{"slug": "a", "planned_count": 400}, {"slug": "b", "planned_count": 200}])
    assert sum(quotas["quotas"].values()) == 8600
    plan = preregister_positives([
        {"source": "raw", "kind": "visible", "planned_count": 200, "population_count": 50,
         "positive_counts": {"M2": 25}, "raw_source_sha256": "counted-hash"},
        {"source": "teacher", "kind": "teacher", "planned_count": 400, "teacher_positives": {"M5": 400}}],
        questions=["M2", "M5"], scale=.8)
    assert plan["expected"] == {"M2": 80, "M5": 0}
    assert plan["floors"] == {"M2": 64, "M5": 60}
