"""Check exact group selection and immutable bytes at the launch boundary."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.assemble.freeze import exact_groups, file_reference, publish_freeze, receipt_instruments, select_records
from intent_training.splits.freeze import _serialized


def row(identity, positive=True):
    return {"state": identity, "questions": {"M2": {"type": "noul", "instructions": "Check", "label": positive}},
            "_meta": {"record_id": identity, "source": "cheatbench", "trajectory_id": identity}}


def test_exact_selection_keeps_group_and_prefers_priority_evidence():
    pair = [row("a"), row("b")]
    negative = [row("c", False)]
    positive = [row("d")]
    chosen = exact_groups([negative, pair, positive], 3, floors={"M2": 60}, seed=7)
    assert {record["state"] for record in chosen} == {"a", "b", "d"}
    with pytest.raises(ValueError, match="exactly"):
        exact_groups([pair], 1, floors={}, seed=7)


def fixture_manifest(splits, inputs):
    return {"passed": True, "inputs": {str(path): file_reference(path) for path in inputs},
            "receipt_inputs": [], "record_counts": {key: len(rows) for key, rows in splits.items()},
            "outputs": {key: {"sha256": hashlib.sha256(_serialized(rows)).hexdigest()}
                        for key, rows in splits.items()}}


def test_atomic_frozen_bytes_require_authority_and_actual_bound_sources(tmp_path):
    source = tmp_path / "source.json"
    source.write_bytes(b"source\r\n")
    splits = {"train": [row("unicode \u03b1\nstate")]}
    manifest = fixture_manifest(splits, [source])
    target = tmp_path / "frozen"
    with pytest.raises(PermissionError):
        publish_freeze(splits, manifest, target)
    source.write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="source input changed"):
        publish_freeze(splits, manifest, target, authorized=True)
    assert not target.exists()
    manifest = fixture_manifest(splits, [source])
    result = publish_freeze(splits, manifest, target, authorized=True)
    raw = Path(result["train"]).read_bytes()
    assert b"\r\n" not in raw
    assert result["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["training_lines"] == len(raw.splitlines()) == 1
    assert json.loads((target / "manifest.json").read_bytes()) == manifest
    with pytest.raises(FileExistsError):
        publish_freeze(splits, manifest, target, authorized=True)


def test_post_gate_record_mutation_cannot_publish(tmp_path):
    splits = {"train": [row("a")]}
    manifest = fixture_manifest(splits, [])
    changed = deepcopy(splits)
    changed["train"][0]["questions"]["M2"]["label"] = False
    with pytest.raises(ValueError, match="rows changed"):
        publish_freeze(changed, manifest, tmp_path / "frozen", authorized=True)
    assert not (tmp_path / "frozen").exists()


def test_instruments_read_all_passes_and_logical_slots_for_siblings(tmp_path):
    record = row("parent:sibling:0")
    path = tmp_path / "receipt.jsonl"
    vote = {"record_id": "parent", "batch_id": "main", "input_sha256": "actual-input",
            "model_family": "terra", "vote_slot": "sol", "votes": {"M2": "yes"}}
    path.write_text(json.dumps(vote) + "\n", encoding="utf-8")
    record["_meta"]["teacher_vote_origins"] = {"sol": {"output": str(path),
        "batch_id": "main", "input_sha256": "actual-input"}}
    measured, references = receipt_instruments([record])
    assert measured["M2"]["single_sol_rows"] == 1
    assert measured["M2"]["paired_rows"] == 0
    assert measured["M2"]["cant_tell_rate"] is None
    assert references[0]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    vote["input_sha256"] = "different"
    path.write_text(json.dumps(vote) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no matching"):
        receipt_instruments([record])


def test_native_suites_have_exact_whole_group_allocations():
    records = []
    for suite in ("decision-v7", "hard-v1", "tasksource"):
        record = row(suite)
        record["_meta"].update(source="tasksource" if suite == "tasksource" else "kev_replay",
                                record_kind="replay", suite=suite, native_record=True)
        records.append(record)
    config = {"expected": {"train": 3, "replay": 3, "screen": 0, "long": 0},
              "source_quotas": {"kev_replay": 2, "tasksource": 1},
              "replay_quotas": {"decision-v7": 1, "hard-v1": 1, "tasksource": 1}}
    selected, _ = select_records(records, composition=config, preregistration={"floors": {}}, seed=1)
    assert len(selected) == 3
    with pytest.raises(ValueError, match="unique stable"):
        select_records(records + records, composition=config, preregistration={"floors": {}}, seed=1)


def test_joint_selection_preserves_linked_task_and_explicit_screen_counts():
    task, screen, spare = row("paired-task"), row("paired-screen"), row("spare", False)
    for record in (task, screen):
        record["_meta"].update(source="open_swe", pair_id="shared-pair")
    screen["_meta"].update(record_kind="screen", construction="overflow_screen")
    spare["_meta"].update(source="open_swe")
    config = {"expected": {"train": 2, "screen": 1},
              "source_quotas": {"task": {"open_swe": 1}, "screen": {"open_swe": 1}}}
    chosen, _ = select_records([task, screen, spare], composition=config,
                               preregistration={"floors": {"M2": 60}}, seed=1)
    assert {record["state"] for record in chosen} == {"paired-task", "paired-screen"}
    assert {record["_meta"]["record_kind"] for record in chosen} == {"task", "screen"}
    impossible = deepcopy(config)
    impossible["expected"]["screen"] = 0
    impossible["source_quotas"] = {"task": {"open_swe": 2}}
    with pytest.raises(ValueError, match="exact joint"):
        select_records([task, screen, spare], composition=impossible,
                       preregistration={"floors": {}}, seed=1)


def test_flat_source_quotas_and_whole_groups_obey_part_totals_together():
    task, screen, another = row("task"), row("screen"), row("another")
    task["_meta"].update(source="open_swe", pair_id="pair")
    screen["_meta"].update(source="open_swe", pair_id="pair", construction="overflow_screen")
    config = {"expected": {"train": 3, "screen": 1},
              "source_quotas": {"open_swe": 2, "cheatbench": 1}}
    chosen, _ = select_records([task, screen, another], composition=config,
                               preregistration={"floors": {}}, seed=4)
    assert len(chosen) == 3
    assert sum(record["_meta"]["record_kind"] == "screen" for record in chosen) == 1


def test_naturally_overflowing_task_is_not_an_explicit_screen_allocation():
    record = row("natural-overflow")
    record["_meta"].update(record_kind="screen", source="open_swe")
    config = {"expected": {"train": 1, "screen": 0},
              "source_quotas": {"task": {"open_swe": 1}}}
    chosen, _ = select_records([record], composition=config,
                               preregistration={"floors": {}}, seed=1)
    assert chosen[0]["_meta"]["record_kind"] == "task"
    assert record["_meta"]["record_kind"] == "screen"
