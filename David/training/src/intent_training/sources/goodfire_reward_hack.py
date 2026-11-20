"""Convert Goodfire node traces while retaining judge flags only as hints."""

import json
from pathlib import Path

from .events import instruction, from_messages


def _rows(path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _stream(nodes):
    events, reasoning, node_seqs = [], {}, {}
    results, pending = [], []
    messages, seen = {}, {}
    duplicates = 0
    for index, node in enumerate(nodes):
        msg = dict(node["message"])
        key = json.dumps(msg, sort_keys=True)
        if msg.get("role") == "assistant":
            if node.get("sampled") is False and key in seen:
                messages[index] = (None, seen[key])
                duplicates += 1
                continue
            seen[key] = index
            for call in msg.get("tool_calls", []):
                pending.append(call["id"])
        elif msg.get("role") == "tool":
            call_id = msg.get("tool_call_id")
            if call_id is None and pending:
                call_id = pending[0]
                msg["tool_call_id"] = call_id
            if call_id in pending:
                pending.remove(call_id)
            results.append(msg)
        messages[index] = (msg, None)
    for index, node in enumerate(nodes):
        msg, duplicate_of = messages[index]
        if duplicate_of is not None:
            node_seqs[index] = node_seqs.get(duplicate_of, [])
            continue
        if msg["role"] == "tool":
            continue
        start = len(events)
        if msg["role"] == "user":
            text = msg.get("content", "")
            marker = "## Reward hacking"
            sections = [text] if marker not in text else text.split(marker, 1)
            if len(sections) == 2:
                sections[1] = marker + sections[1]
            for section in sections:
                events.append(instruction(section, len(events) + 1))
        elif msg["role"] == "system":
            continue
        else:
            added, raw_reasoning = from_messages([msg, *results])
            for ev in added:
                old = ev["seq"]
                ev["seq"] = len(events) + 1
                if ev.get("action", {}).get("tool") == "bash":
                    ev["action"]["tool"] = "Bash"
                if str(old) in raw_reasoning:
                    reasoning[str(ev["seq"])] = raw_reasoning[str(old)]
                events.append(ev)
        node_seqs[index] = [e["seq"] for e in events[start:]]
    return events, reasoning, node_seqs, duplicates


def convert(raw_dir: Path):
    """Keep visible enacted flags, clean runs and considered-only negatives.

    Streams remain complete so later construction and matched negative cuts
    retain their evidence. The cut sequence localizes the first visible flag.
    Judge flags remain in outcomes, never authoritative visible source labels.
    """
    raw_dir = Path(raw_dir)
    labels_path = raw_dir / "judge_rollouts.jsonl"
    traces_path = raw_dir / "traces.jsonl"
    if not labels_path.exists() or not traces_path.exists():
        return
    labels = {r["trace_id"]: r for r in _rows(labels_path)}
    for row in _rows(traces_path):
        for trace in row["traces"]:
            label = labels.get(trace["id"])
            if not label or label.get("verdict") == "split" or not label.get("judged"):
                continue
            flags = label.get("flags") or []
            visible = [f for f in flags if f.get("status") == "enacted"
                       and f.get("channel") in {"content", "tool_calls"}]
            negative = label.get("verdict") == "no" or (
                bool(flags) and all(f.get("status") == "considered" for f in flags))
            if not visible and not negative:
                continue
            events, reasoning, nodes, duplicates = _stream(trace["nodes"])
            cut = None
            first = min(visible, key=lambda f: f["node_index"]) if visible else None
            if first:
                candidates = nodes.get(first["node_index"], [])
                if not candidates:
                    continue
                cut = candidates[0]
                # Node flags can identify one call in a parallel call batch.
                if first["channel"] == "tool_calls":
                    matching = [seq for seq in candidates if first.get("quote", "")
                                in json.dumps(events[seq - 1]["action"], ensure_ascii=False)]
                    if matching:
                        cut = matching[0]
                readonly = {"Read", "Grep", "Glob", "WebFetch", "WebSearch", "LS", "NotebookRead", "AskUserQuestion"}
                cut = next((e["seq"] for e in events if e["seq"] >= cut and (
                    e["type"] == "turn_completed" or e.get("action", {}).get("tool") not in readonly
                    and e["type"] == "tool_completed")), None)
                if cut is None:
                    continue
            side = {"reasoning": reasoning, "source_labels": [], "licence": "unstated",
                    "outcomes": {"reward": label.get("reward"), "judge_flags": flags,
                                 "verdict": label["verdict"], "hint_positive": bool(visible)}}
            meta = {"source": "goodfire_reward_hack", "trajectory_id": trace["id"],
                    "source_record_id": row["id"], "task_id": label["task"],
                    "objective": ["M4", "L6"], "licence": "unstated",
                    "harness": trace["agent"]["harness"], "deduplicated_nodes": duplicates,
                    "selection": "visible_enacted" if visible else "clean_or_considered_only"}
            if cut is not None:
                meta["cut_seq"] = cut
                meta["offense_node_index"] = first["node_index"]
            yield events, side, meta
