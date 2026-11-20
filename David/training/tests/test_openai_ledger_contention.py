"""Ensure transient ledger sharing violations do not repeat settlement writes."""

from pathlib import Path

from intent_training.teacher.openai_client_state import OpenAIBudget


def test_permission_denied_before_open_retries_without_duplicate_rows(tmp_path, monkeypatch):
    budget = OpenAIBudget(tmp_path / "ledger.jsonl")
    original = Path.open
    denied = 0

    def open_with_contention(path, mode="r", *args, **kwargs):
        nonlocal denied
        if path == budget.ledger and denied < 2:
            denied += 1
            raise PermissionError("Simulated Windows sharing violation before open")
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_with_contention)
    monkeypatch.setattr("intent_training.teacher.openai_client_state.time.sleep", lambda _: None)
    call = budget.reserve(1)
    budget.settle(call, .1)
    rows = budget._rows()
    assert denied == 2
    assert [row["status"] for row in rows] == ["reserved", "settled"]
    assert budget.exposure() == .1
