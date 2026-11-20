"""Check pair preservation, preference filtering and hint isolation."""
import json
from pathlib import Path
from intent_training.sources.helpsteer3 import convert
from monitor_format import validate_events


def test_pair_filter_and_hint_isolation(tmp_path: Path):
    context = [{"role": "user", "content": "Keep the API.", "reasoning": "private context"},
               {"role": "assistant", "content": "Prior reply."},
               {"role": "user", "content": "Fix its return value."}]
    row = dict(context=context, response1="Fixed.", response2="Removed it.",
               overall_preference=-2,
               individual_preference=[dict(score=-2, reasoning="The first preserves the API.")])
    weak = dict(row, overall_preference=1)
    (tmp_path / "preference.jsonl").write_text(
        "\n".join(json.dumps(dict(row_idx=i, row=value)) for i, value in enumerate([row, weak])),
        encoding="utf-8")
    result = list(convert(tmp_path))
    assert len(result) == 2
    assert result[0][2]["pair_id"] == result[1][2]["pair_id"]
    assert result[0][2]["source_record_id"] != result[1][2]["source_record_id"]
    for events, side, meta in result:
        validate_events(events)
        assert events[0]["new_items"][0]["text"] == "user:\nKeep the API.\n\nassistant:\nPrior reply.\n\nuser:\nFix its return value."
        assert side["reasoning"] == {"1": "private context"}
        assert all(event["agent_thinking"] == "" for event in events)
        assert "private context" not in json.dumps(events)
        assert "preserves the API" not in json.dumps(events)
        assert side["source_labels"] == []
        assert side["outcomes"]["basis"] == "outcome"
        assert meta["cut_seq"] == 2
        assert meta["objective"] == ["M1", "G1"]
    assert result[0][0][-1]["agent_text"] == row["response1"]
    assert result[1][0][-1]["agent_text"] == row["response2"]
