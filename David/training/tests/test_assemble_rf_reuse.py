"""Require real canonical receipts and exact unit proof before RF alias reuse."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.assemble.receipts import canonical_payload
from intent_training.assemble.rf_reuse import reuse
from intent_training.assemble.stream import queue_votes
from intent_training.teacher.claims import batch_claim_path, validated_rf_slots
from intent_training.teacher.dispatch import digest, MODELS, SONNET_MODEL
from intent_training.assemble.labels import collect_votes
from intent_training.teacher.prepare import requirement_records
from intent_training.teacher.rf_cache import rf_decision_hash


def setup(tmp_path, actual="sol"):
    unit = {"source": "[I1]", "position": 1, "text": "Keep the API."}
    original = requirement_records("canonical", "open_swe", [unit])[0]
    row = canonical_payload(original)
    batch = {"batch_id": "rf-cache", "input_sha256": digest([row]), "source": "open_swe",
             "pass": "requirements", "records": [row]}
    output, queue, claims = tmp_path / "actual.jsonl", tmp_path / "queue.jsonl", tmp_path / "claims"
    claims.mkdir()
    vote = {"record_id": row["record_id"], "batch_id": batch["batch_id"], "input_sha256": batch["input_sha256"],
            "pass": "requirements", "model_family": "sol", "model": MODELS["sol"],
            "votes": {"RF": True}, "evidence": {"RF": "The visible sentence constrains the work."}}
    if actual == "sonnet":
        vote.update(model_family="sonnet", model=SONNET_MODEL, actual_model=SONNET_MODEL, vote_slot="sol")
    output.write_text(json.dumps(vote) + "\n", encoding="utf-8")
    queue.write_text(json.dumps({"batch": batch, "outputs": {"sol": str(output)}}) + "\n", encoding="utf-8")
    claim = {"batch_id": batch["batch_id"], "input_sha256": batch["input_sha256"], "owner": "actual-owner",
             "record_ids": [row["record_id"]], "required_families": ["sol"], "families": {"sol": {
                 "status": "completed", "vote_output": str(output), "completed_at": datetime.now(timezone.utc).isoformat()}}}
    if actual == "sonnet":
        claim["families"]["sol"].update(actual_model=SONNET_MODEL, vote_slot="sol")
        assert collect_votes([vote])[row["record_id"]]["RF"]["sol"] is True
    claim_path = batch_claim_path(claims, batch)
    claim_path.write_text(json.dumps(claim), encoding="utf-8")
    alias = requirement_records("alias", "open_swe", [unit])[0]
    alias["_meta"] = {"source": "open_swe", "construction": "constraint"}
    link = {"record_id": alias["record_id"], "parent_record_id": "alias", "unit_id": "R1", "unit": unit,
            "canonical_record_id": row["record_id"], "canonical_record_sha256": digest(row),
            "canonical_batch_id": batch["batch_id"], "canonical_frozen_input_sha256": batch["input_sha256"],
            "judgment_content_hash": rf_decision_hash(row), "required_families": ["sol"],
            "content_sha256": digest({"state": row["state"], "questions": row["questions"]})}
    collection = queue_votes(queue, passes={"requirements"}, claims_dir=claims)
    collection["rf_aliases"] = {alias["record_id"]: link}
    return collection, alias, claims, claim_path


@pytest.mark.parametrize("actual", ["sol", "sonnet"])
def test_alias_uses_authorized_canonical_receipt_without_forging_envelope(tmp_path, actual):
    collection, alias, claims, _ = setup(tmp_path, actual)
    assert reuse(collection, alias, claims_dir=claims, repository=tmp_path)
    assert collection["votes"][alias["record_id"]]["sol"] == {"RF": True}
    assert collection["origins"][alias["record_id"]]["sol"]["canonical_record_id"] == "canonical:unit:1"
    assert len(list(tmp_path.glob("*.jsonl"))) == 2


def test_changed_exact_unit_text_is_not_reused(tmp_path):
    collection, alias, claims, _ = setup(tmp_path)
    alias = deepcopy(alias)
    alias["unit"]["text"] = "Change the API."
    with pytest.raises(ValueError, match="exact frozen parent unit"):
        reuse(collection, alias, claims_dir=claims, repository=tmp_path)


def test_unclaimed_actual_vote_cannot_authorize_alias(tmp_path):
    collection, alias, claims, claim_path = setup(tmp_path)
    claim_path.unlink()
    assert not reuse(collection, alias, claims_dir=claims, repository=tmp_path)


def test_rf_claim_quorum_requires_complete_valid_output(tmp_path):
    collection, _, claims, claim_path = setup(tmp_path)
    batch = next(iter(collection["batches"].values()))
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    assert validated_rf_slots(claims, batch, claim) == ("sol",)
    output = Path(claim["families"]["sol"]["vote_output"])
    vote = json.loads(output.read_text(encoding="utf-8"))
    vote["input_sha256"] = "wrong"
    output.write_text(json.dumps(vote) + "\n", encoding="utf-8")
    assert validated_rf_slots(claims, batch, claim) == ()


def test_direct_rf_ready_requires_actual_receipt(tmp_path):
    collection, _, claims, claim_path = setup(tmp_path)
    batch = next(iter(collection["batches"].values()))
    prepared = dict(batch["records"][0], _meta={"source": "open_swe", "construction": "constraint"})
    sys.path.insert(0, str(ROOT / "scripts"))
    from assemble_followups import ready
    assert ready(collection, prepared, claims_dir=claims, repository=tmp_path)
    collection.pop("validated_rf_claim_cache", None)
    claim_path.unlink()
    assert not ready(collection, prepared, claims_dir=claims, repository=tmp_path)


def test_rf_instruments_count_secondary_without_inventing_agreement(tmp_path):
    from intent_training.assemble.instruments import policy_instruments, combine_instruments
    collection, _, _, _ = setup(tmp_path)
    batch = next(iter(collection["batches"].values()))
    row = dict(batch["records"][0], _meta={"source": "open_swe", "construction": "constraint"})
    report = policy_instruments([row], {row["record_id"]: {"RF": {"terra": True}}})
    assert report["RF"]["single_terra_rows"] == 1
    assert report["RF"]["paired_rows"] == 0
    assert combine_instruments(report)["RF"]["total_rows"] == 1


def test_required_family_change_is_rejected(tmp_path):
    collection, alias, claims, _ = setup(tmp_path)
    collection["rf_aliases"][alias["record_id"]]["required_families"] = ["sol", "terra"]
    with pytest.raises(ValueError, match="exact frozen parent unit"):
        reuse(collection, alias, claims_dir=claims, repository=tmp_path)
