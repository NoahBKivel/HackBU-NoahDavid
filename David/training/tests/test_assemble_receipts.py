"""Verify canonical receipt selection and truthful logical-slot overrides."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.assemble import collect_votes
from intent_training.assemble.receipts import resolve_duplicate_receipts
from intent_training.assemble.stream import completed_votes, queue_votes
from intent_training.teacher.claims import batch_claim_path, claim_path
from intent_training.teacher.dispatch import MODELS, digest


def envelope(batch, value, *, slot="sol", actual="sol"):
    return {"record_id": "row", "batch_id": batch["batch_id"], "input_sha256": batch["input_sha256"],
            "pass": batch["pass"], "model_family": actual, "model": MODELS[actual],
            "vote_slot": slot, "actual_model": MODELS[actual], "votes": {"M2": value},
            "evidence": {"M2": "The visible edit changes the requested requirement."}}


def setup_duplicates(tmp_path):
    row = {"record_id": "row", "state": "Visible edit", "source": "open_swe", "pass": "main",
           "questions": {"M2": {"type": "noul", "instructions": "Does the edit break the requirement?"}},
           "teacher_side": {"reasoning": {}, "source_labels": []}}
    claims = tmp_path / "claims"
    claims.mkdir()
    entries = []
    times = [datetime.now(timezone.utc) - timedelta(seconds=1), datetime.now(timezone.utc)]
    for index, answer in enumerate((True, False)):
        batch = {"batch_id": str(index), "input_sha256": digest([row]), "source": "open_swe", "pass": "main", "records": [row]}
        source, output = tmp_path / f"input-{index}.json", tmp_path / f"votes-{index}.jsonl"
        source.write_text(json.dumps(batch), encoding="utf-8")
        value = envelope(batch, answer)
        output.write_text(json.dumps([value]) if index == 0 else json.dumps(value) + "\n", encoding="utf-8")
        entries.append({"input": str(source), "output": str(output), "model_family": "sol"})
        claim = {"batch_id": batch["batch_id"], "input_sha256": batch["input_sha256"], "owner": "authorized_worker",
                 "model_family": "sol", "record_ids": ["row"], "status": "completed", "vote_output": str(output),
                 "completed_at": times[index].isoformat()}
        claim_path(claims, batch["batch_id"], "sol", batch["input_sha256"]).write_text(json.dumps(claim), encoding="utf-8")
    manifest, queue = tmp_path / "manifest.json", tmp_path / "queue.jsonl"
    manifest.write_text(json.dumps(entries), encoding="utf-8")
    queue.write_text("", encoding="utf-8")
    collected = {"prepared": {"row": row}, "votes": {"row": {"sol": {"M2": False}}},
                 "origins": {}, "blocked": {"row"}, "errors": [{"record_id": "row", "error": "Conflicting duplicate."}]}
    contexts = {"row": {"_meta": {"source": "open_swe", "construction": "constraint"}}}
    return row, claims, manifest, queue, collected, contexts


def test_first_authorized_completed_receipt_wins_without_averaging(tmp_path):
    row, claims, manifest, queue, collected, contexts = setup_duplicates(tmp_path)
    result = resolve_duplicate_receipts(collected, manifests=[manifest], queue=queue, canonical={"row": row},
        contexts=contexts, claims_dir=claims, repository=tmp_path)
    assert not result["blocked"] and result["votes"]["row"]["sol"]["M2"] is True
    assert result["receipt_resolution"]["later_duplicate_audit"][0]["votes"]["M2"] is False
    assert result["origins"]["row"]["sol"]["claim_owner"] == "authorized_worker"


def test_different_private_evidence_cannot_be_reused_despite_identical_state(tmp_path):
    row, claims, manifest, queue, collected, contexts = setup_duplicates(tmp_path)
    canonical = deepcopy(row)
    canonical["teacher_side"]["reasoning"] = {"1": "Different private evidence."}
    result = resolve_duplicate_receipts(collected, manifests=[manifest], queue=queue, canonical={"row": canonical},
        contexts=contexts, claims_dir=claims, repository=tmp_path)
    assert result["blocked"] == {"row"} and not result["receipt_resolution"]["resolved"]


def test_unambiguous_old_vote_is_also_held_when_canonical_private_evidence_changes(tmp_path):
    row, claims, manifest, queue, collected, contexts = setup_duplicates(tmp_path)
    collected["blocked"] = set()
    collected["errors"] = []
    canonical = deepcopy(row)
    canonical["teacher_side"]["source_labels"] = [{"basis": "visible", "question": "M2", "value": True}]
    result = resolve_duplicate_receipts(collected, manifests=[manifest], queue=queue, canonical={"row": canonical},
        contexts=contexts, claims_dir=claims, repository=tmp_path)
    assert result["blocked"] == {"row"}
    assert "current canonical full input" in result["errors"][0]["error"]


def test_valid_legacy_json_array_is_normalized_without_new_votes(tmp_path):
    _, _, manifest, _, _, _ = setup_duplicates(tmp_path)
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    manifest.write_text(json.dumps(entries[:1]), encoding="utf-8")
    result = completed_votes([manifest], repository=tmp_path)
    assert result["votes"]["row"]["sol"]["M2"] is True and not result["errors"]


def test_authoritative_nonmain_override_keeps_actual_model_and_logical_slot(tmp_path):
    row = {"record_id": "row", "state": "Visible edit", "source": "open_swe", "pass": "localization",
           "questions": {"M2": {"type": "noul", "instructions": "Does the edit break the requirement?"}}, "teacher_side": {}}
    batch = {"batch_id": "override", "input_sha256": digest([row]), "pass": "localization", "records": [row], "source": "open_swe"}
    output, queue, claims = tmp_path / "votes.jsonl", tmp_path / "queue.jsonl", tmp_path / "claims"
    claims.mkdir()
    vote = envelope(batch, True, actual="terra")
    output.write_text(json.dumps(vote) + "\n", encoding="utf-8")
    queue.write_text(json.dumps({"batch": batch, "outputs": {"sol": str(output)}}) + "\n", encoding="utf-8")
    claim = {"batch_id": batch["batch_id"], "input_sha256": batch["input_sha256"], "owner": "authorized_worker",
             "record_ids": ["row"], "required_families": ["sol"], "families": {"sol": {"status": "completed",
                 "vote_output": str(output), "vote_slot": "sol", "actual_model": MODELS["terra"],
                 "completed_at": datetime.now(timezone.utc).isoformat()}}}
    batch_claim_path(claims, batch).write_text(json.dumps(claim), encoding="utf-8")
    result = queue_votes(queue, passes={"localization"}, claims_dir=claims)
    assert not result["errors"] and result["votes"]["row"]["sol"]["M2"] is True
    assert result["origins"]["row"]["sol"]["actual_model"] == MODELS["terra"]
    assert collect_votes([vote])["row"]["M2"]["sol"] is True
    # An adopted receipt may point to an existing validated file instead of the allocated output.
    queue.write_text(json.dumps({"batch": batch, "outputs": {"sol": str(tmp_path / "unwritten.jsonl")}}) + "\n", encoding="utf-8")
    adopted = queue_votes(queue, passes={"localization"}, claims_dir=claims)
    assert not adopted["errors"] and adopted["votes"]["row"]["sol"]["M2"] is True
    revised = deepcopy(batch)
    revised["batch_id"] = "revised-wording"
    revised["records"][0]["questions"]["M2"]["instructions"] = "Does this exact visible change violate the requirement?"
    revised["input_sha256"] = digest(revised["records"])
    revised_output = tmp_path / "revised.jsonl"
    revised_output.write_text(json.dumps(envelope(revised, False, actual="terra")) + "\n", encoding="utf-8")
    revised_claim = deepcopy(claim)
    revised_claim.update(batch_id=revised["batch_id"], input_sha256=revised["input_sha256"])
    revised_claim["families"]["sol"]["vote_output"] = str(revised_output)
    batch_claim_path(claims, revised).write_text(json.dumps(revised_claim), encoding="utf-8")
    with queue.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"batch": revised, "outputs": {"sol": str(revised_output)}}) + "\n")
    epochs = queue_votes(queue, passes={"localization"}, claims_dir=claims)
    sys.path.insert(0, str(ROOT / "scripts"))
    from assemble_followups import ready
    revised_private = dict(revised["records"][0], _meta={"source": "open_swe", "construction": "constraint"})
    original_private = dict(row, _meta={"source": "open_swe", "construction": "constraint"})
    assert ready(epochs, revised_private)
    assert epochs["votes"]["row"]["sol"]["M2"] is False
    assert ready(epochs, original_private)
    assert epochs["votes"]["row"]["sol"]["M2"] is True


def test_unauthorized_earlier_owner_is_not_selected_for_its_label(tmp_path):
    row, claims, manifest, queue, collected, contexts = setup_duplicates(tmp_path)
    entry = json.loads(manifest.read_text(encoding="utf-8"))[0]
    batch = json.loads(Path(entry["input"]).read_text(encoding="utf-8"))
    path = claim_path(claims, batch["batch_id"], "sol", batch["input_sha256"])
    claim = json.loads(path.read_text(encoding="utf-8"))
    claim["owner"] = ""
    path.write_text(json.dumps(claim), encoding="utf-8")
    result = resolve_duplicate_receipts(collected, manifests=[manifest], queue=queue, canonical={"row": row},
        contexts=contexts, claims_dir=claims, repository=tmp_path)
    assert result["votes"]["row"]["sol"]["M2"] is False
    assert result["receipt_resolution"]["receipt_errors"]


def test_authorized_actual_terra_can_fill_main_primary_with_completed_claim(tmp_path):
    row = {"record_id": "row", "state": "Visible edit", "source": "open_swe", "pass": "main",
           "questions": {"M2": {"type": "noul", "instructions": "Does it violate the requirement?"}}, "teacher_side": {}}
    batch = {"batch_id": "main_override", "input_sha256": digest([row]), "pass": "main", "records": [row], "source": "open_swe"}
    output, queue, claims = tmp_path / "votes.jsonl", tmp_path / "queue.jsonl", tmp_path / "claims"
    claims.mkdir()
    output.write_text(json.dumps(envelope(batch, True, actual="terra")) + "\n", encoding="utf-8")
    queue.write_text(json.dumps({"batch": batch, "outputs": {"sol": str(output)}}) + "\n", encoding="utf-8")
    claim = {"batch_id": batch["batch_id"], "input_sha256": batch["input_sha256"], "owner": "authorized_worker",
             "record_ids": ["row"], "required_families": ["sol"], "families": {"sol": {"status": "completed",
                 "vote_output": str(output), "vote_slot": "sol", "actual_model": MODELS["terra"]}}}
    batch_claim_path(claims, batch).write_text(json.dumps(claim), encoding="utf-8")
    result = queue_votes(queue, passes={"main"}, claims_dir=claims)
    assert result["votes"]["row"]["sol"]["M2"] is True
    assert not result["errors"]
