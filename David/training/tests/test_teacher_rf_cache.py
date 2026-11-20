import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.teacher.dispatch import _batch, digest
from intent_training.teacher.rf_cache import deduplicate_rf, rf_decision_hash, snapshot_input


def rf(rid, parent, *, context=None):
    row = {"record_id": rid, "parent_record_id": parent, "unit_id": "R1",
           "unit": {"source": "I1", "position": 0, "text": "Use English."},
           "state": "Use English.", "questions": {"RF": {"type": "noul"}},
           "teacher_side": {"reasoning": {}, "source_labels": []},
           "source": "example", "purpose": "requirement_selection", "pass": "requirements"}
    if context is not None:
        row["row_context"] = context
    return row


def visible(row):
    return {key: value for key, value in row.items()
            if key not in {"parent_record_id", "unit_id", "unit"}}


def lines(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_exact_reuse_keeps_all_links_and_context_is_not_dropped(tmp_path):
    source = tmp_path / "input.jsonl"
    rows = [rf("a", "p1"), rf("b", "p2"), rf("c", "p3", context="different")]
    lines(source, rows)
    result = deduplicate_rf(source, tmp_path / "queue", tmp_path / "cache", visible=visible,
                            required_families=lambda row: ("sol",), claims_directory=tmp_path / "claims")
    assert result["counts"]["new_canonical"] == 2
    aliases = [json.loads(line) for line in open(result["fanout"], encoding="utf-8")]
    assert [row["parent_record_id"] for row in aliases] == ["p1", "p2", "p3"]
    assert aliases[0]["canonical_record_id"] == aliases[1]["canonical_record_id"] == "a"
    assert aliases[2]["canonical_record_id"] == "c"
    assert aliases[1]["unit"] == rows[1]["unit"]


def test_queued_reuse_across_allocations_preserves_actual_input_hash(tmp_path):
    canonical = visible(rf("old", "oldparent"))
    batch = _batch("example", "requirements", [canonical])
    queue = tmp_path / "queue"
    lines(queue, [{"batch": batch, "required_families": ["sol", "terra"]}])
    source = tmp_path / "input"
    lines(source, [rf("new", "parent")])
    result = deduplicate_rf(source, queue, tmp_path / "paired", visible=visible,
                            required_families=lambda row: ("sol", "terra"), claims_directory=tmp_path / "claims")
    alias = json.loads(open(result["fanout"], encoding="utf-8").readline())
    assert result["counts"]["new_canonical"] == 0
    assert alias["canonical_record_id"] == "old"
    assert alias["canonical_frozen_input_sha256"] == batch["input_sha256"]
    assert alias["canonical_record_sha256"] == digest(canonical)
    single = deduplicate_rf(source, queue, tmp_path / "single", visible=visible,
                            required_families=lambda row: ("sol",), claims_directory=tmp_path / "claims")
    assert single["counts"]["new_canonical"] == 0


def test_snapshot_survives_source_replacement_and_main_is_never_cached(tmp_path):
    source = tmp_path / "source"
    lines(source, [rf("a", "p")])
    frozen, fingerprint = snapshot_input(source, tmp_path / "snapshots")
    before = frozen.read_bytes()
    source.write_text("changed\n", encoding="utf-8")
    assert frozen.read_bytes() == before
    assert frozen.stem == fingerprint
    with pytest.raises(ValueError):
        rf_decision_hash(dict(visible(rf("a", "p")), **{"pass": "main", "purpose": "rf_training"}))
