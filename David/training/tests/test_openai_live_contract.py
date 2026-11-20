"""Check lossless side transport and exclusive ownership of paired batches."""

from concurrent.futures import ThreadPoolExecutor
import json

from intent_training.teacher.claims import claim_batch_once, claim_next, finish_family, batch_claim_path
from intent_training.teacher.dispatch import _batch, encoded
from intent_training.teacher.openai_client_transport import compact_payload, compact_prompt, expand_payload
import pytest


def test_lossless_shared_reasoning_preserves_visible_fields():
    reason = "A repeated reasoning block with quotes and unicode \u27e6x\u27e7. " * 100
    payload = {"records": [{"record_id": str(i), "state": "literal state " + str(i),
                "questions": {"M2": {"instructions": "Literal question?"}},
                "teacher_side": {"reasoning": {"1": reason, "2": {"ref": "literal user object"}},
                                 "source_labels": [{"basis": "outcome", "value": i}]}}
                           for i in range(4)]}
    compact = compact_payload(payload)
    assert len(encoded(compact).encode()) < len(encoded(payload).encode())
    assert expand_payload(compact) == payload
    for original, reduced in zip(payload["records"], compact["records"]):
        assert original["state"] == reduced["state"]
        assert original["questions"] == reduced["questions"]
        assert original["teacher_side"]["source_labels"] == reduced["teacher_side"]["source_labels"]


def test_one_claim_owns_both_independent_families(tmp_path):
    batch = _batch("judgment", "main", [{"record_id": "r", "state": "s", "questions": {}}])
    def claim(i):
        return claim_batch_once(tmp_path, batch, str(i), ("sol", "terra"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        winners = [value for value in pool.map(claim, range(4)) if value is not None]
    assert len(winners) == 1
    assert len(list(tmp_path.glob("*.json"))) == 1
    owner = winners[0]["owner"]
    finish_family(tmp_path, batch, owner, "sol", "sol.jsonl")
    assert json.loads(batch_claim_path(tmp_path, batch).read_text())["status"] == "claimed"
    finish_family(tmp_path, batch, owner, "terra", "terra.jsonl")
    result = json.loads(batch_claim_path(tmp_path, batch).read_text())
    assert result["status"] == "completed"
    assert set(result["families"]) == {"sol", "terra"}


def test_auxiliary_terra_keeps_two_slots_and_true_identity(tmp_path):
    batch = _batch("judgment", "requirements", [{"record_id": "r", "state": "s", "questions": {}}])
    batch["model_overrides"] = {"sol": "gpt-6.1-terra"}
    text = compact_prompt(batch, "sol")
    assert "model_family=terra, model=gpt-6.1-terra" in text
    assert "vote_slot=sol, actual_model=gpt-6.1-terra" in text
    claim_batch_once(tmp_path, batch, "worker", ("sol", "terra"))
    first = finish_family(tmp_path, batch, "worker", "sol", "one.jsonl")
    assert first["status"] == "claimed"
    final = finish_family(tmp_path, batch, "worker", "terra", "two.jsonl")
    assert final["status"] == "completed"
    assert final["families"]["sol"]["actual_model"] == "gpt-6.1-terra"
    assert final["families"]["sol"]["vote_slot"] == "sol"
    batch["pass"] = "main"
    assert "model_family=terra, model=gpt-6.1-terra" in compact_prompt(batch, "sol")


def test_rf_assignment_uses_one_terra_slot_without_rewriting_claim(tmp_path):
    row = {"record_id": "rf", "pass": "requirements", "purpose": "requirement_selection",
           "questions": {"RF": {"type": "noul"}}, "state": "s"}
    batch = _batch("judgment", "requirements", [row])
    queue, claims = tmp_path / "queue", tmp_path / "claims"
    queue.write_text(encoded({"batch": batch, "allocation": "paired",
                             "required_families": ["sol", "terra"]}) + "\n", encoding="utf-8")
    item = claim_next(queue, claims, "worker")
    assert item["required_families"] == ["sol"]
    assert item["batch"]["model_overrides"] == {"sol": "gpt-6.1-terra"}
    assert item["claim"]["required_families"] == ["sol", "terra"]
    assert item["batch"]["input_sha256"] == batch["input_sha256"]


def test_luna_assignment_reports_actual_model_and_rejects_unapproved(tmp_path):
    row = {"record_id": "rf", "pass": "requirements", "purpose": "requirement_selection",
           "questions": {"RF": {"type": "noul"}}, "state": "s"}
    batch = _batch("judgment", "requirements", [row])
    queue, claims = tmp_path / "queue", tmp_path / "claims"
    queue.write_text(encoded({"batch": batch, "allocation": "paired", "required_families": ["sol", "terra"]}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        claim_next(queue, claims, "worker", actual_model_override="unapproved")
    item = claim_next(queue, claims, "worker", actual_model_override="gpt-6-luna")
    assert item["required_families"] == ["sol"]
    text = compact_prompt(item["batch"], "sol")
    assert "model_family=luna, model=gpt-6-luna" in text
    receipt = finish_family(claims, item["batch"], "worker", "sol", "out.jsonl", actual_model="gpt-6-luna")
    assert receipt["families"]["sol"]["actual_model"] == "gpt-6-luna"


def test_held_question_does_not_claim_or_block_unrelated_main(tmp_path):
    held = _batch("judgment", "main", [{"record_id": "held", "questions": {"L7#F1": {}}}])
    ready = _batch("judgment", "main", [{"record_id": "ready", "questions": {"M1": {}}}])
    queue = tmp_path / "queue.jsonl"
    queue.write_text("".join(encoded({"batch": batch, "allocation": "paired",
        "required_families": ["sol", "terra"]}) + "\n" for batch in (held, ready)))
    claims = tmp_path / "claims"
    item = claim_next(queue, claims, "worker", excluded_questions=("L7",))
    assert item["batch"]["batch_id"] == ready["batch_id"]
    assert not batch_claim_path(claims, held).exists()
    assert batch_claim_path(claims, ready).exists()
