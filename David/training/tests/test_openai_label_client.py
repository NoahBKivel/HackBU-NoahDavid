"""Exercise ownership races, billing categories and rejected incomplete votes."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading
import time

import pytest

from intent_training.teacher.claims import claim_batch, complete_claim
from intent_training.teacher.dispatch import _batch, INSTRUCTIONS
from intent_training.teacher.openai_client import (AdaptiveConcurrency, OpenAILabeller,
                                                  request_body, validate_response)
from intent_training.teacher.openai_client_state import BudgetExhausted, OpenAIBudget, usage_cost
from intent_training.prepare.records import scan


@pytest.fixture
def batch():
    return _batch("construction", "main", [{"record_id": "record", "source": "construction",
                   "pass": "main", "state": "visible evidence", "teacher_side": {},
                   "questions": {"M2": {"type": "noul", "instructions": "Question?"}}}])


def test_claim_is_exclusive_under_parallel_dispatch(tmp_path, batch):
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims = list(pool.map(lambda i: claim_batch(tmp_path, batch, "sol", str(i)), range(8)))
    assert sum(claim is not None for claim in claims) == 1
    winner = next(claim for claim in claims if claim is not None)
    with pytest.raises(ValueError):
        complete_claim(tmp_path, batch, "sol", "other", "votes.jsonl")
    complete_claim(tmp_path, batch, "sol", winner["owner"], "votes.jsonl")
    assert claim_batch(tmp_path, batch, "sol", "duplicate") is None
    assert claim_batch(tmp_path, batch, "terra", "independent") is not None


def test_budget_serializes_reservations_and_retains_unknown_calls(tmp_path):
    budget = OpenAIBudget(tmp_path / "openai.jsonl", cap_usd=10)
    def reserve(_):
        try:
            return budget.reserve(3)
        except RuntimeError:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        reservations = list(pool.map(reserve, range(8)))
    assert sum(value is not None for value in reservations) == 3
    assert budget.exposure() == 9
    settled = next(value for value in reservations if value)
    budget.settle(settled, 1)
    assert budget.exposure() == 7
    with pytest.raises(ValueError):
        budget.settle(settled, 1)
    with pytest.raises(RuntimeError):
        budget.reserve(4)


def test_usage_prices_cache_writes_once_and_long_context():
    rates = {"long_threshold_tokens": 100,
             "short": {"input": 2, "cached_input": .1, "cache_write_30m": 2.5, "output": 10},
             "long": {"input": 4, "cached_input": .2, "cache_write_30m": 5, "output": 15}}
    usage = {"input_tokens": 100, "output_tokens": 10,
             "input_tokens_details": {"cached_tokens": 20, "cache_write_tokens": 30}}
    assert usage_cost(usage, rates) == pytest.approx((50 * 2 + 20 * .1 + 30 * 2.5 + 10 * 10) / 1e6)
    usage["input_tokens"] = 101
    assert usage_cost(usage, rates) == pytest.approx((51 * 4 + 20 * .2 + 30 * 5 + 10 * 15) / 1e6)
    usage["input_tokens"] = 1
    with pytest.raises(ValueError):
        usage_cost(usage, rates)


def test_prompt_keeps_exact_rules_and_cache_prefix(batch):
    body = request_body(batch, "sol", 1000)
    assert INSTRUCTIONS in body["input"][0]["content"][0]["text"]
    assert body["reasoning"] == {"effort": "low"}
    assert body["service_tier"] == "default"
    assert body["prompt_cache_options"] == {"mode": "explicit", "ttl": "30m"}
    assert body["input"][0]["content"][0]["prompt_cache_breakpoint"] == {"mode": "explicit"}
    assert batch["records"] == json.loads(body["input"][1]["content"])["records"]


def test_outbound_payload_secret_scan_rejects_without_echoing_secret(batch):
    batch["records"][0]["state"] = "sk-ant-" + "a" * 25
    with pytest.raises(ValueError, match="Credential pattern") as caught:
        scan(request_body(batch, "sol", 1000))
    assert "a" * 25 not in str(caught.value)


def test_incomplete_or_missing_votes_never_validate(batch):
    vote = {"record_id": "record", "batch_id": batch["batch_id"], "input_sha256": batch["input_sha256"],
            "model_family": "sol", "model": "gpt-6.1-sol", "pass": "main",
            "votes": {"M2": True}, "evidence": {"M2": "visible evidence"}}
    def response(votes, status="completed"):
        return {"status": status, "output": [{"type": "message", "content": [{
            "type": "output_text", "text": json.dumps({"records": votes})}]}]}
    assert validate_response(response([vote]), batch, "sol") == [vote]
    for invalid in (response([vote], "incomplete"), response([]), response([vote, vote])):
        with pytest.raises(ValueError):
            validate_response(invalid, batch, "sol")
    vote["input_sha256"] = "different"
    with pytest.raises(ValueError):
        validate_response(response([vote]), batch, "sol")


def test_scheduler_admits_only_current_capacity_before_loading_batches(tmp_path, batch, monkeypatch):
    client = OpenAILabeller(api_key="unused", rates={}, ledger=tmp_path / "ledger.jsonl",
                           claims=tmp_path / "claims", evidence=tmp_path / "evidence", max_concurrency=8)
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    lock = threading.Lock()
    active = 0
    maximum = 0
    def fake_vote(*args):
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
        time.sleep(.01)
        with lock:
            active -= 1
        return {"records": 1}
    monkeypatch.setattr(client, "vote", fake_vote)
    entries = [{"batch_id": str(i), "model_family": "sol", "input": str(batch_path),
                "output": str(tmp_path / f"votes{i}.jsonl")} for i in range(8)]
    assert len(client.run(entries)) == 8
    assert maximum == 2


def test_token_limit_headers_suspend_admission_until_reported_reset():
    capacity = AdaptiveConcurrency(8)
    capacity.enter()
    before = time.monotonic()
    capacity.leave({"x-ratelimit-remaining-tokens": "0", "x-ratelimit-reset-tokens": "1m2s"})
    assert capacity.blocked_until >= before + 62
    assert capacity.remaining_tokens == 0


def test_budget_preflight_failure_has_explicit_no_request_claim(tmp_path, batch):
    rate = {"input": 1, "output": 1, "cached_input": .1, "cache_write_30m": 1.25}
    client = OpenAILabeller(api_key="unused", rates={"models": {"gpt-6.1-sol": {
                               "long_threshold_tokens": 100, "short": rate, "long": rate}}},
                           ledger=tmp_path / "ledger.jsonl", claims=tmp_path / "claims",
                           evidence=tmp_path / "evidence")
    client.budget.cap = 0
    with pytest.raises(RuntimeError, match="spend cap"):
        client.vote(batch, "sol", tmp_path / "votes.jsonl")
    from intent_training.teacher.claims import claim_path
    claim = json.loads(claim_path(tmp_path / "claims", batch["batch_id"], "sol",
                                  batch["input_sha256"]).read_text(encoding="utf-8"))
    assert claim["status"] == "failed_preflight"
    assert claim["no_request_sent"] is True
    assert not (tmp_path / "votes.jsonl").exists()


def test_budget_exhaustion_stops_admission_of_unstarted_queue(tmp_path, batch, monkeypatch):
    client = OpenAILabeller(api_key="unused", rates={}, ledger=tmp_path / "ledger.jsonl",
                           claims=tmp_path / "claims", evidence=tmp_path / "evidence", max_concurrency=8)
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    def exhausted(*args):
        raise BudgetExhausted("No budget remains.")
    monkeypatch.setattr(client, "vote", exhausted)
    entries = [{"batch_id": str(i), "model_family": "sol", "input": str(batch_path),
                "output": str(tmp_path / f"votes{i}.jsonl")} for i in range(20)]
    results = client.run(entries)
    assert len(results) <= 2
    progress = json.loads((tmp_path / "evidence/progress.json").read_text(encoding="utf-8"))
    assert progress["admission_stopped"] == "budget_exhausted"
    assert progress["remaining_calls"] >= 18
