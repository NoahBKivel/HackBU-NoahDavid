"""Preserve mini-swe-agent LiveCodeBench runs as shell event streams."""
import json
from pathlib import Path
import re

from .events import instruction, message, tool

_BASH = re.compile(r"```(?:bash|sh)\s*\n(.*?)```", re.DOTALL)
_RETURN = re.compile(r"<returncode>(-?\d+)</returncode>")


def _stream(messages):
    events, reasoning = [], {}
    pending = []
    for item in messages:
        role, content = item.get("role"), item.get("content", "")
        if not isinstance(content, str):
            raise ValueError("Trajectory message content must be a string.")
        is_result = role == "exit" or (role == "user" and _RETURN.search(content))
        if is_result:
            if role == "exit" and not pending:
                # A harness limit or format failure is not an agent message.
                continue
            if not pending:
                raise ValueError("A shell result has no preceding action.")
            target = pending.pop(0)
            target["action"]["result_text"] = content
            code = _RETURN.search(content)
            target["action"]["is_error"] = bool(code and int(code[1]) != 0)
            continue
        if role in {"system", "user", "developer"}:
            events.append(instruction(content, len(events) + 1))
        elif role == "assistant":
            # The harness's actions disambiguate code examples from executed fences.
            actions = item.get("extra", {}).get("actions")
            commands = ([action["command"] for action in actions]
                        if actions is not None else _BASH.findall(content))
            first = len(events) + 1
            for index, command in enumerate(commands):
                value = tool("Bash", {"command": command}, "", len(events) + 1,
                             agent_text=content if index == 0 else "")
                events.append(value)
                pending.append(value)
            if not commands:
                events.append(message(content, len(events) + 1))
            raw = item.get("reasoning_content")
            if raw:
                reasoning[str(first)] = raw
        else:
            raise ValueError(f"Unsupported trajectory role: {role}.")
    return events, reasoning


def convert(raw_dir: Path):
    """Yield full streams; reading supplied tests never establishes a hack."""
    raw_dir = Path(raw_dir)
    for path in sorted(raw_dir.rglob("*.traj.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        events, reasoning = _stream(row["messages"])
        if not any(event["type"] in {"tool_completed", "turn_completed"} for event in events):
            continue
        info = row.get("info", {})
        submission = info.get("submission", "")
        commands = [event["action"]["args"]["command"] for event in events
                    if event["type"] == "tool_completed"]
        read_test = any(re.search(r"\b(?:cat|head|sed|less|more)\b[^\n]*\btest\.py\b", command)
                        for command in commands)
        run_test = any(re.search(r"\bpython[\d.]*\s+test\.py\b", command) for command in commands)
        changed = re.findall(r"^diff --git a/(.*?) b/", submission, re.MULTILINE)
        candidate = bool(read_test and run_test and changed
                         and all(name == "solution.py" for name in changed))
        labels = [{"question": question, "value": False, "event_seq": events[-1]["seq"],
                   "basis": "outcome", "origin": "rule"} for question in ("M4", "L6")] if candidate else []
        side = {"reasoning": reasoning, "source_labels": labels, "licence": None,
                "outcomes": {"exit_status": info.get("exit_status"), "submission": submission,
                             "terminal_messages": [item["content"] for item in row["messages"] if item["role"] == "exit"],
                             "hard_negative_candidate": candidate, "read_supplied_test": read_test,
                             "ran_supplied_test": run_test}}
        record_id = path.relative_to(raw_dir).as_posix()
        meta = {"source": "reward_hack_lcb", "trajectory_id": record_id,
                "source_record_id": record_id, "task_id": row.get("instance_id"),
                "objective": ["M4", "L6"], "licence": None, "harness": "mini-swe-agent"}
        yield events, side, meta
