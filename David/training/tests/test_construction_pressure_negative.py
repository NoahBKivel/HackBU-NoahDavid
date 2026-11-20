"""Check pressure edits, independent benign evidence and event preservation."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

from intent_training.constructions.pressure_negative import build, INTENDED, PRESSURES
from intent_training.sources.events import instruction, message, tool


@pytest.fixture
def base():
    events = [instruction("Check the calculation."),
              tool("Read", {"file_path": "calculate.py"}, "value = 2", 2),
              tool("Bash", {"command": "python calculate.py"}, "2", 3),
              message("The calculation returned 2.", 4)]
    labels = [{"question": question, "value": value, "event_seq": seq,
               "basis": "visible", "origin": "independent review"}
              for seq in (3, 4) for question, value in INTENDED.items()]
    return events, {"source_labels": labels, "outcomes": {"reward": 1}}, {
        "source": "fixture", "trajectory_id": "run", "source_record_id": "row",
        "group_id": "group", "pair_id": "pair"}


def test_only_original_instruction_changes_and_inputs_are_immutable(base):
    original = deepcopy(base)
    variants = list(build(*base))
    assert len(variants) == len(PRESSURES)
    assert base == original
    for events, side, meta in variants:
        pressure = side["construction"]["pressure"]
        assert events[0]["new_items"][0]["text"] == (
            base[0][0]["new_items"][0]["text"] + "\n\n" + PRESSURES[pressure])
        events[0]["new_items"][0]["text"] = base[0][0]["new_items"][0]["text"]
        assert events == base[0]
        assert side["construction"]["intended"] == INTENDED
        assert INTENDED["G1"] is True
        assert all(value is False for key, value in INTENDED.items() if key != "G1")
        assert "source_labels" not in side
        assert side["construction"]["base_source_labels"] == base[1]["source_labels"]
        assert meta["group_id"] == base[2]["group_id"]
        assert meta["pair_id"] == base[2]["pair_id"]


@pytest.mark.parametrize("mutation", ["missing", "outcome", "conflict", "unattributed"])
def test_insufficient_or_conflicting_benign_evidence_is_rejected(base, mutation):
    labels = base[1]["source_labels"]
    if mutation == "missing":
        labels.pop()
    elif mutation == "outcome":
        labels[-1]["basis"] = "outcome"
    elif mutation == "conflict":
        labels.append(dict(labels[-1], value=True))
    else:
        labels[-1]["origin"] = ""
    assert list(build(*base)) == []


def test_teacher_evidence_is_accepted_without_becoming_source_labels(base):
    labels = base[1].pop("source_labels")
    for label in labels:
        label["basis"] = "teacher"
    assert list(build(*base)) == []
    result = list(build(*base, teacher_labels=labels, pressure="audit"))
    assert len(result) == 1
    assert result[0][1]["construction"]["benign_basis"]
    assert "source_labels" not in result[0][1]


def test_only_target_cut_requires_teacher_labels(base):
    base[1]["source_labels"] = [label for label in base[1]["source_labels"]
                                if label["event_seq"] == base[0][-1]["seq"]]
    assert len(list(build(*base))) == len(PRESSURES)


@pytest.mark.parametrize("attempt", [0, 4, True, 1.5])
def test_attempt_limit(base, attempt):
    with pytest.raises(ValueError):
        list(build(*base, attempt=attempt))


def test_cut_excludes_future_and_cannot_end_at_a_read(base):
    base[2]["cut_seq"] = 3
    events, _, meta = next(build(*base, pressure="deadline", attempt=3))
    assert events[-1]["seq"] == meta["cut_seq"] == 3
    base[2]["cut_seq"] = 2
    assert list(build(*base)) == []


def test_missing_first_instruction_and_unknown_pressure_are_rejected(base):
    with pytest.raises(ValueError):
        list(build(*base, pressure="score"))
    base[0][0]["new_items"][0]["id"] = "I2"
    assert list(build(*base)) == []
