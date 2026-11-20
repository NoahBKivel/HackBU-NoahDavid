"""Check cross-client ownership and complete judgment-input cache identity."""

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
import pytest
from intent_training.teacher.claims import claim_batch, complete_claim, teacher_input_hash


def batch():
    return {"batch_id": "source-main-identity", "input_sha256": "frozen-content",
            "records": [{"record_id": "item", "state": "Visible state", "questions": {},
                         "teacher_side": {"reasoning": {}, "source_labels": []}}]}


def test_exclusive_claims_prevent_cross_client_duplicate_calls(tmp_path):
    frozen = batch()
    assert claim_batch(tmp_path, frozen, "sol", "collaboration") is not None
    assert claim_batch(tmp_path, frozen, "sol", "api") is None
    assert claim_batch(tmp_path, frozen, "terra", "api") is not None
    with pytest.raises(ValueError, match="owner"):
        complete_claim(tmp_path, frozen, "sol", "api", "output.jsonl")
    completed = complete_claim(tmp_path, frozen, "sol", "collaboration", "output.jsonl")
    assert completed["status"] == "completed"
    assert claim_batch(tmp_path, frozen, "sol", "api") is None


def test_full_input_hash_changes_for_visible_side_or_metadata_changes():
    original = batch()["records"][0]
    for field, value in (("state", "Changed state"), ("purpose", "rf_training"),
                         ("teacher_side", {"reasoning": {"1": "Changed reasoning"}, "source_labels": []})):
        changed = deepcopy(original)
        changed[field] = value
        assert teacher_input_hash(changed) != teacher_input_hash(original)
    assert teacher_input_hash(dict(reversed(list(original.items())))) == teacher_input_hash(original)
