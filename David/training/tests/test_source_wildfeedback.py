"""Check feedback isolation and conversation grouping."""

import json

from monitor_format import validate_events
from intent_training.sources.wildfeedback import convert


def test_feedback_stays_out_of_reply_prefix(tmp_path):
    rows = []
    for i, (role, text) in enumerate([
        ("User", "Explain this code."), ("Agent", "The loop counts items."),
        ("User", "That explanation missed the return value."), ("Agent", "It returns the count."),
    ]):
        rows.append({"row_idx": i, "row": {"TurnId": i // 2 + 1, "UtterranceId": i,
                    "Role": role, "Content": text, "Disatisfaction": True, "State": "FEEDBACK"}})
    (tmp_path / "rows-0000.json").write_text(json.dumps({"rows": rows}))
    first, second = list(convert(tmp_path))
    events, side, meta = first
    validate_events(events)
    assert len(events) == 2
    assert "return value" not in json.dumps(events)
    assert side["outcomes"]["feedback"]["next_user_text"] == rows[2]["row"]["Content"]
    assert side["source_labels"] == []
    assert events[-1]["turn"]["reason"] == "answer"
    assert second[2]["trajectory_id"] == meta["trajectory_id"]
    assert len(second[0]) == 4
    assert "outcomes" not in second[1]
    assert all(e["agent_thinking"] == "" for e in second[0])
