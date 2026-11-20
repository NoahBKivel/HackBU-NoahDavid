"""Check shared budget exposure and evidence-based Batch reconciliation."""

import json
from pathlib import Path

import pytest

from intent_training.teacher.claims import claim_path
from intent_training.teacher.dispatch import digest
from intent_training.teacher.openai_client_batch import BatchLabeller, batch_rates
from intent_training.teacher.openai_client_state import BudgetExhausted, OpenAIBudget, usage_cost


@pytest.fixture
def setup(tmp_path, monkeypatch):
    import intent_training.teacher.openai_client_batch as module
    monkeypatch.setattr(module, "scan", lambda body: None)
    monkeypatch.setattr(module, "request_body", lambda batch, family, maximum:
                        {"model": family, "input": batch["records"], "max_output_tokens": maximum})
    rate = {"input": 2.0, "output": 10.0, "cached_input": 0.1, "cache_write_30m": 2.5}
    pricing = {"source": "official", "models": {"gpt-6.1-sol": {
        "long_threshold_tokens": 10000, "short": rate, "long": rate}}}
    client = BatchLabeller(pricing=pricing, ledger=tmp_path / "spend.jsonl", claims=tmp_path / "claims")
    entries, control = [], {}
    for number in range(2):
        record = {"record_id": str(number), "questions": {"M1": "Question?"}}
        batch = {"batch_id": "batch" + str(number), "records": [record],
                 "input_sha256": digest([record]), "pass": "base"}
        entries.append({"batch": batch, "output": str(tmp_path / (str(number) + ".jsonl"))})
        control[str(number)] = {"allocation": "single_sol", "_meta": {"validated_length": 8191}}
    return client, entries, control, tmp_path / "batch", module


def prepared(setup):
    client, entries, control, directory, module = setup
    plan = client.prepare(entries, control, directory, family="sol", lower_priority=True)
    plan["batch_id"] = "remote"
    (directory / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    return client, entries, directory, module, plan


def output_line(item, *, valid=True):
    return {"custom_id": item["custom_id"], "error": None, "response": {
        "status_code": 200, "body": {"status": "completed",
        "usage": {"input_tokens": 10, "output_tokens": 5}, "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "[]"}]}],
        "test_valid": valid}}}


def test_standard_reservation_blocks_batch_budget(setup):
    client, entries, control, directory, _ = setup
    standard = OpenAIBudget(client.budget.ledger)
    standard.reserve(200)
    with pytest.raises(BudgetExhausted):
        client.prepare(entries, control, directory, family="sol", lower_priority=True)
    assert standard.exposure() == 200


def test_batch_reservations_block_standard_budget(setup):
    client, _, _, _, plan = prepared(setup)
    standard = OpenAIBudget(client.budget.ledger)
    with pytest.raises(BudgetExhausted):
        standard.reserve(200)
    assert standard.exposure() == plan["reserved_usd"]


def test_cancelled_completed_usage_is_paid_and_unknown_stays_reserved(setup, monkeypatch):
    client, _, directory, module, plan = prepared(setup)
    monkeypatch.setattr(module, "validate_response", lambda body, batch, family: [{"ok": True}])
    result = client.collect(directory, {"id": "remote", "status": "cancelled", "output_file_id": "out"},
                            {"out": json.dumps(output_line(plan["items"][0]))})
    expected = usage_cost({"input_tokens": 10, "output_tokens": 5}, batch_rates(client.pricing, "sol"))
    assert client.budget.exposure() == pytest.approx(expected + plan["items"][1]["reserved_usd"])
    assert result["outstanding"] == 1
    assert result["completed"] == 1


def test_terminal_expired_artifact_proves_unexecuted(setup):
    client, _, directory, _, plan = prepared(setup)
    line = {"custom_id": plan["items"][0]["custom_id"], "response": None,
            "error": {"code": "batch_expired"}}
    status = {"id": "remote", "status": "expired", "error_file_id": "errors"}
    with pytest.raises(ValueError):
        client.collect(directory, status, {})
    result = client.collect(directory, status, {"errors": json.dumps(line)})
    assert result["outstanding"] == 1
    assert client.budget.exposure() == pytest.approx(plan["items"][1]["reserved_usd"])


def test_out_of_order_identity_mapping_and_idempotent_charges(setup, monkeypatch):
    client, entries, directory, module, plan = prepared(setup)
    monkeypatch.setattr(module, "validate_response", lambda body, batch, family:
                        [{"record_id": batch["records"][0]["record_id"]}])
    artifacts = {"out": "\n".join(json.dumps(output_line(item)) for item in reversed(plan["items"]))}
    status = {"id": "remote", "status": "completed", "output_file_id": "out"}
    assert client.collect(directory, status, artifacts)["completed"] == 2
    charged = client.budget.exposure()
    assert client.collect(directory, status, artifacts)["completed"] == 2
    assert client.budget.exposure() == charged
    for entry in entries:
        value = json.loads(Path(entry["output"]).read_text(encoding="utf-8"))
        assert value["record_id"] == entry["batch"]["records"][0]["record_id"]


def test_invalid_vote_is_charged_without_completing_claim(setup):
    client, _, directory, _, plan = prepared(setup)
    item = plan["items"][0]
    result = client.collect(directory, {"id": "remote", "status": "completed", "output_file_id": "out"},
                            {"out": json.dumps(output_line(item))})
    assert result["invalid"] == 1
    claim = json.loads(claim_path(client.claims, item["batch_id"], item["family"],
                                  item["input_sha256"]).read_text(encoding="utf-8"))
    assert claim["status"] == "claimed"
    assert not Path(item["output"]).exists()


def test_priority_and_missing_explicit_eligibility_are_rejected(setup):
    client, entries, control, directory, _ = setup
    with pytest.raises(ValueError):
        client.prepare(entries, control, directory, family="sol")
    control["0"]["_meta"]["priority"] = "C"
    with pytest.raises(ValueError):
        client.prepare(entries, control, directory, family="sol", lower_priority=True)


def test_explicit_construction_is_rejected_with_lower_priority_flag(setup):
    client, entries, control, directory, _ = setup
    for index, metadata in enumerate(({"construction": True},
                                      {"construction_type": "transformation"},
                                      {"record_kind": "construction"})):
        policy = {key: dict(value, _meta=dict(value["_meta"])) for key, value in control.items()}
        policy["0"]["_meta"].update(metadata)
        with pytest.raises(ValueError, match="explicitly eligible"):
            client.prepare(entries, policy, directory.with_name("construction" + str(index)),
                           family="sol", lower_priority=True)
