"""Exercise development isolation and measured coverage."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.splits.dev import _floors, prepare


def row(index, **meta):
    return {"state": str(index), "questions": {"M1": {"label": bool(index % 2)}},
            "_meta": {"source": "swe_chat", "trajectory_id": str(index), **meta}}


def test_additional_base_and_planted_leaks():
    train = [row(100)]
    pool = [row(i) for i in range(20)]
    result, manifest = prepare(train, pool, [], [], seed="seed", questions=["M1"])
    assert manifest["base_groups"] == 1
    assert len(result["base_dev"]) == 1 and len(train) == 1
    assert not manifest["passed"]
    with pytest.raises(ValueError, match="held-out"):
        prepare(train, pool, [], [{"source": "swe_chat", "record_id": "1"}], seed="seed", questions=["M1"])
    leaked = deepcopy(pool[0])
    leaked["_meta"]["trajectory_id"] = "100"
    with pytest.raises(ValueError, match="crosses a split"):
        prepare(train, [leaked], [], [], seed="seed", questions=["M1"])


def test_source_local_identifiers_do_not_collide_between_datasets():
    train = [row(100)]
    candidate = row(101, source="in3", trajectory_id="100")
    result, _ = prepare(train, [candidate], [], [], seed="seed", questions=["M1"])
    assert len(result["base_dev"]) == 1


def test_categorical_floor_requires_each_option():
    rows = [{"questions": {"Q": {"type": "choice", "criteria": {"a": "A", "b": "B", "c": "C"},
                                     "label": "a" if i < 400 else "b"}}} for i in range(800)]
    floor = _floors(rows, ["Q"])["Q"]
    assert floor["options"]["a"]["passed"]
    assert not floor["options"]["c"]["passed"]
    assert not floor["passed"]
