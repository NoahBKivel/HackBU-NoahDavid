"""Verify constraint pairs preserve real evidence and isolate prefix labels."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

TRAINING = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRAINING / "src"))
sys.path.insert(0, str(TRAINING.parent))

from intent_training.constructions.constraint import build
from intent_training.sources.events import instruction, tool
from monitor_format import validate_events


def base():
    return [instruction("Repair the application."),
            tool("Edit", {"file_path": "src/one.py"}, "Applied.", 2),
            tool("Read", {"file_path": "src/two.py"}, "existing content", 3),
            tool("Write", {"file_path": "src/two.py"}, "Written.", 4)]


def test_pairs_preserve_actions_and_grouping():
    events = base()
    side = {"reasoning": {"4": "original reasoning"},
            "source_labels": [{"question": "M2", "value": False, "event_seq": 4,
                               "basis": "visible", "origin": "rule"}]}
    meta = {"source": "swe_chat", "trajectory_id": "sample", "pair_id": "original"}
    original = deepcopy((events, side, meta))
    negative, positive = list(build(events, side, meta))
    assert (events, side, meta) == original
    assert negative[2]["cut_seq"] == 2
    assert positive[2]["cut_seq"] == 4
    for output, intended in ((negative, False), (positive, True)):
        stream, output_side, output_meta = output
        validate_events(stream)
        assert output_meta["base_pair_id"] == "original"
        assert output_meta["pair_id"] == output_meta["construction_pair_id"]
        assert output_side["source_labels"] == []
        assert output_side["construction"]["base_source_labels"] == side["source_labels"]
        assert output_side["construction"]["intended"] == {"M2": intended, "D2": intended}
        assert output_side["construction"]["requirement"] in stream[0]["new_items"][0]["text"]
        assert [value["action"] for value in stream] == [value["action"] for value in events[:len(stream)]]
    assert negative[2]["construction_pair_id"] == positive[2]["construction_pair_id"]


def test_project_documents_preserve_execution_and_order():
    result = list(build(base(), {}, {}, location="project_document", document_path="RULES.md",
                        project_documents=[{"path": "article.md", "text": "Context only."}],
                        document_position=0))
    items = result[1][0][0]["new_items"]
    assert items[0]["text"] == base()[0]["new_items"][0]["text"]
    assert [item["path"] for item in items[1:]] == ["RULES.md", "article.md"]
    assert result[1][1]["construction"]["requirement_source"] == "RULES.md"


def test_no_pair_for_failed_edits_or_repeated_same_path():
    events = base()[:2]
    events.append(tool("Edit", {"file_path": "src/one.py"}, "Applied.", 3))
    events.append(tool("Write", {"file_path": "src/two.py"}, "Failed.", 4, is_error=True))
    assert list(build(events, {}, {})) == []


@pytest.mark.parametrize("attempt", [0, 4, True])
def test_retry_cap(attempt):
    with pytest.raises(ValueError):
        list(build(base(), {}, {}, attempt=attempt))


def test_teacher_labels_are_preserved():
    side = {"teacher_labels": {"M2": False}}
    positive = list(build(base(), side, {}, attempt=3))[1]
    assert positive[1]["teacher_labels"] == side["teacher_labels"]
    assert positive[1]["construction"]["attempt"] == 3


def test_missing_instruction_is_rejected():
    with pytest.raises(ValueError):
        list(build(base()[1:], {}, {}))
