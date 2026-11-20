"""Check document preservation, budget admission and isolated construction intent."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

from intent_training.constructions.overflow_screen import build, generation_requests
from monitor_format import build_instructions, collect_documents, render_screen, validate_events


@pytest.fixture(scope="module")
def tokenizer():
    from tokenizers import Tokenizer
    actual = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    return lambda text, add_special_tokens=False: SimpleNamespace(
        input_ids=actual.encode(text, add_special_tokens=add_special_tokens).ids)


def fixture():
    event = {"seq": 1, "type": "tool_completed", "ts": "", "new_items": [
        {"kind": "user_instruction", "id": "I1", "text": "Repair the parser."},
        {"kind": "project_doc", "path": "POLICY.md", "text":
         "# Development\nPreserve public interfaces.\n\n# Review\nExplain changes clearly.\n"}],
        "action": {"tool": "Edit", "args": {"file_path": "src/parser.py"},
                   "result_text": "", "is_error": False}, "agent_text": "",
        "agent_thinking": "", "todos": [], "turn": {}}
    return [event], {"reasoning": {"1": "Observed evidence.", "2": "Future evidence."},
                     "source_labels": [{"question": "M2", "value": False, "event_seq": 1}]}, {
        "source": "fixture", "source_record_id": "tiny", "trajectory_id": "group",
        "licence": "fixture", "pair_id": "existing"}


def test_lossless_sections_and_isolated_intent(tokenizer):
    events, side, meta = fixture()
    original = deepcopy((events, side, meta))
    outputs = list(build(events, side, meta, tokenizer=tokenizer, budget=2048))
    assert len(outputs) == 2
    for variant, new_side, new_meta in outputs:
        validate_events(variant)
        construction = new_side["construction"]
        sections = [section for batch in construction["screen_sections"] for section in batch]
        assert "".join(section["text"] for section in sections) == collect_documents(variant)[0]["text"]
        assert collect_documents(variant)[0]["text"].startswith(collect_documents(events)[0]["text"])
        assert new_meta["pair_id"] == "existing"
        assert new_meta["group_id"] == "group"
        assert new_side["reasoning"] == {"1": "Observed evidence."}
        assert new_side["source_labels"] == []
        assert set(key.split("#")[1] for key in construction["intended"]) == {construction["inserted_section"]}
        for batch in construction["screen_sections"]:
            _, fits = render_screen(build_instructions(variant), batch, variant, 1, 2048, tokenizer=tokenizer)
            assert fits
    assert len(outputs[0][1]["construction"]["intended"]) == 1
    assert len(outputs[1][1]["construction"]["intended"]) == 2
    assert (events, side, meta) == original


@pytest.mark.parametrize("attempt", [0, 4, True, 1.5])
def test_attempt_limit(tokenizer, attempt):
    with pytest.raises(ValueError):
        list(build(*fixture(), tokenizer=tokenizer, attempt=attempt))


def test_real_document_required(tokenizer):
    events, side, meta = fixture()
    events[0]["new_items"] = events[0]["new_items"][:1]
    assert list(build(events, side, meta, tokenizer=tokenizer)) == []
    with pytest.raises(ValueError, match="source identity"):
        list(build(events, side, meta, tokenizer=tokenizer,
                   document={"path": "fake.md", "text": "No provenance."}))
    with pytest.raises(ValueError, match="tokenizer"):
        list(build(events, side, meta))
    assert list(generation_requests(events, side, meta)) == []
    events, side, meta = fixture()
    events[0]["action"]["is_error"] = True
    assert list(build(events, side, meta, tokenizer=tokenizer)) == []


def test_multiple_screen_batches_preserve_section_ids(tokenizer):
    events, side, meta = fixture()
    events[0]["new_items"][1]["text"] = "".join(
        f"# Clause {index}\n" + "Keep the documented interface stable. " * 12 + "\n\n"
        for index in range(30))
    outputs = list(build(events, side, meta, tokenizer=tokenizer, budget=1024))
    for _, variant_side, _ in outputs:
        batches = variant_side["construction"]["screen_sections"]
        assert len(batches) > 1
        ids = [section["id"] for batch in batches for section in batch]
        assert len(ids) == len(set(ids))
