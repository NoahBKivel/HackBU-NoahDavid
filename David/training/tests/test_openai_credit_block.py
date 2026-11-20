"""Ensure exhausted provider credit stops admissions without repeating rejected calls."""

from io import BytesIO
import json
from urllib.error import HTTPError

import pytest

from intent_training.teacher.dispatch import _batch, MODELS
from intent_training.teacher.openai_client_live import PairedLiveClient
from intent_training.teacher.claims import claim_batch_once, delegate_family, finish_family


def test_credit_exhaustion_rejects_once_and_settles_zero(tmp_path, monkeypatch):
    calls = []

    def reject(request, **kwargs):
        calls.append(request)
        payload = {"error": {"code": "credit_balance_exhausted", "type": "insufficient_quota"}}
        raise HTTPError(request.full_url, 429, "Rejected", {}, BytesIO(json.dumps(payload).encode()))

    monkeypatch.setattr("intent_training.teacher.openai_client_live.urlopen", reject)
    client = PairedLiveClient(key="placeholder", pricing={"models": {MODELS["sol"]:
        {"long": {"input": 1, "cache_write_30m": 1, "output": 1}}}},
        ledger=tmp_path / "ledger.jsonl", claims=tmp_path / "claims",
        stop_file=tmp_path / "stop", max_concurrency=1)
    batch = _batch("judgment", "main", [{"record_id": "r", "state": "literal",
        "source": "judgment", "pass": "main", "teacher_side": {}, "questions": {}}])
    with pytest.raises(RuntimeError, match="credit_balance_exhausted"):
        client.vote({"batch": batch}, "sol", "owner")
    assert len(calls) == 1
    assert client.stopped()
    rows = client.budget._rows()
    assert [row["status"] for row in rows] == ["reserved", "settled"]
    assert rows[-1]["http_status"] == 429
    assert rows[-1]["cost_usd"] == 0
    assert client.budget.exposure() == 0


def test_resumed_api_does_not_repeat_delegated_slot(tmp_path, monkeypatch):
    client = PairedLiveClient(key="placeholder", pricing={}, ledger=tmp_path / "ledger.jsonl",
        claims=tmp_path / "claims", stop_file=tmp_path / "stop", max_concurrency=1)
    batch = _batch("judgment", "main", [{"record_id": "r", "questions": {}, "pass": "main"}])
    owner = "openai-continuous"
    claim_batch_once(client.claims, batch, owner, ["sol", "terra"])
    slot = delegate_family(client.claims, batch, owner, "sol", "codex_worker", quiescent=True)
    assert slot["delegated_to"] == "codex_worker"
    assert delegate_family(client.claims, batch, owner, "sol", "other_worker", quiescent=True) is None
    finish_family(client.claims, batch, owner, "terra", tmp_path / "terra.jsonl")
    queue = tmp_path / "queue.jsonl"
    queue.write_text(json.dumps({"batch": batch, "allocation": "paired",
        "required_families": ["sol", "terra"], "outputs": {}}) + "\n")
    calls = []
    monkeypatch.setattr(client, "vote", lambda *args: calls.append(args))
    assert client.run(queue, idle_timeout=.01) == 0
    assert calls == []
