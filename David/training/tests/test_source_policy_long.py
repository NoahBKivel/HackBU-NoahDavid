"""Exercise native policy preservation, genuine rule labels and exclusion checks."""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from intent_training.sources import policy_long


@pytest.fixture(scope="module")
def cache(tmp_path_factory):
    path = tmp_path_factory.mktemp("native_policies")
    policy_long.prepare(path, count=2, seed="test_native_policy_train")
    return path


def test_original_native_questions_labels_and_source_survive_padding(cache):
    rows = list(policy_long.convert(cache))
    assert len(rows) == 2
    for events, side, meta in rows:
        original, native = side["original_native_record"], side["native_record"]
        assert events == []
        assert native["questions"] == original["questions"]
        assert native["_meta"] == original["_meta"]
        assert native["_meta"]["source"] == "hard_long_policy"
        assert meta["native"] is True and meta["objective"] == []
        assert meta["split"] == "train"
        assert 16384 <= meta["state_tokens"] <= 32767
        assert 0 <= meta["relevant_position"] < meta["document_count"]
        assert meta["source_record_id"] not in meta["padding_policy_ids"]


@pytest.mark.parametrize("field,value", [("split", "development"), ("licence", "unknown"),
                                         ("fresh_instances", False), ("revision", "untrusted")])
def test_provenance_rejects_heldout_unknown_licence_and_stale_code(cache, tmp_path, field, value):
    manifest = json.loads((cache / "manifest.json").read_text())
    manifest[field] = value
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="provenance"):
        list(policy_long.convert(tmp_path))


def test_rule_solver_rejects_tampered_original_label(cache):
    record = json.loads((cache / "native_train.jsonl").read_text().splitlines()[0])
    workspace = Path(__file__).resolve().parents[1]
    solve = policy_long.trusted(workspace)[2]
    question = record["questions"]["outcome"]
    question["label"] = next(key for key in question["criteria"] if key != question["label"])
    with pytest.raises(ValueError, match="solver"):
        policy_long.labels(record, solve)


def test_mutated_cached_source_rejected(cache, tmp_path):
    for name in ("manifest.json", "native_train.jsonl"):
        (tmp_path / name).write_bytes((cache / name).read_bytes())
    with (tmp_path / "native_train.jsonl").open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="hash"):
        list(policy_long.convert(tmp_path))
