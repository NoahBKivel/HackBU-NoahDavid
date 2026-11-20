"""Check source node mapping and teacher-only hint handling."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from intent_training.sources.goodfire_reward_hack import convert, _stream


def _node(role, **fields):
    return {"message": {"role": role, **fields}, "sampled": role == "assistant"}


def test_tools_preserve_idless_result_and_reasoning_stays_private():
    nodes = [_node("user", content="Fix this.\n## Reward hacking\nDo not hack."),
             _node("assistant", content="Checking.", reasoning_content="Private reasoning.",
                   tool_calls=[{"id": "a", "name": "bash", "arguments": '{"command":"cat file"}'}]),
             _node("tool", content="Actual output.")]
    nodes.append({**nodes[1], "sampled": False})
    events, reasoning, mapped, duplicates = _stream(nodes)
    assert events[1]["new_items"][0]["text"].startswith("## Reward hacking")
    assert events[2]["action"]["tool"] == "Bash"
    assert events[2]["action"]["result_text"] == "Actual output."
    assert all(e["agent_thinking"] == "" for e in events)
    assert list(reasoning.values()) == ["Private reasoning."]
    assert duplicates == 1 and mapped[3] == mapped[1]


def test_only_visible_enacted_flags_localize_and_split_rows_are_excluded(tmp_path):
    nodes = [_node("user", content="Fix this."), _node("assistant", content="All passed."),
             _node("assistant", content="Later evidence.")]
    trace = {"id": "trajectory", "nodes": nodes, "agent": {"harness": "shell"}}
    row = {"id": "source-row", "traces": [trace]}
    label = {"trace_id": "trajectory", "task": "task", "judged": True, "verdict": "yes",
             "flags": [{"status": "enacted", "channel": "content", "node_index": 1}]}
    (tmp_path / "traces.jsonl").write_text(json.dumps(row) + "\n")
    label_path = tmp_path / "judge_rollouts.jsonl"
    label_path.write_text(json.dumps(label) + "\n")
    events, side, meta = list(convert(tmp_path))[0]
    assert meta["cut_seq"] == 2 and len(events) == 3
    assert side["source_labels"] == []
    label["flags"][0]["status"] = "considered"
    label_path.write_text(json.dumps(label) + "\n")
    assert "cut_seq" not in list(convert(tmp_path))[0][2]
    label["verdict"] = "split"
    label_path.write_text(json.dumps(label) + "\n")
    assert list(convert(tmp_path)) == []
