"""Check failed attempts and private reasoning in OLMo conversion."""

import json

from intent_training.sources.olmo_reward_hacking import convert, visible_offences
from monitor_format import render_patch, validate_events


def test_failed_attempt_and_recipe_removal(tmp_path):
    row = {"_dataset": "public/source", "_row_idx": 0, "rollout_index": 1,
           "problem_id": "task", "response": "<thinking>private plan</thinking>\n```python\nimport os\nos._exit(0)\n```",
           "reasoning": "raw plan", "reward_hacked": 0,
           "messages": [{"role": "system", "content": "exploit recipe"},
                        {"role": "user", "content": "Compute the sum."}]}
    (tmp_path / "rows.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    events, side, meta = next(convert(tmp_path))
    validate_events(events)
    assert side["source_labels"][0]["value"] is True
    assert side["reasoning"]["3"] == "raw plan\n\nprivate plan"
    assert "private plan" not in json.dumps(events)
    assert "exploit recipe" not in json.dumps(events)
    assert meta["cut_seq"] == events[-1]["seq"]
    assert meta["source_record_id"] == "public/source:raw-row:0"
    assert events[-1]["action"]["args"]["file_path"] == "solution.py"
    patch = events[-1]["action"]["file_changes"][0]["patch"]
    assert "+os._exit(0)" in render_patch(patch)
    assert patch[0]["oldLines"] == 0
    row["response"] = "```python\ndef solution(s):\n    return s\n```"
    (tmp_path / "rows.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    _, clean_side, _ = next(convert(tmp_path))
    assert clean_side["source_labels"] == []


def test_specific_exploit_rules():
    assert visible_offences("```python\n# os._exit(0)\ndef solution(s):\n    return s\n```") == []
    assert visible_offences("```python\nclass A:\n    def __eq__(self, other):\n        return True\n```") == ["always_equal"]
    assert visible_offences("```python\ndef __eq__(self, other):\n    return self.x == other.x\n```") == []
