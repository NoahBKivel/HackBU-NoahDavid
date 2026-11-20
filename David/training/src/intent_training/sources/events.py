"""Normalize source conversations into runtime events without inventing evidence."""

import json
from collections.abc import Iterable, Mapping
from typing import Any


def event(seq: int, kind: str, **fields: Any) -> dict[str, Any]:
    """Build an event with every required field present."""
    result = dict(seq=seq, type=kind, ts="", new_items=[], action={},
                  agent_text="", agent_thinking="", todos=[], turn={})
    result.update(fields)
    return result


def instruction(text: str, seq: int = 1, documents: Any = None) -> dict[str, Any]:
    """Preserve a user instruction and any supplied project documents."""
    items = [{"kind": "user_instruction", "id": f"I{seq}", "text": text}]
    if isinstance(documents, Mapping):
        documents = [{"path": path, "text": value} for path, value in documents.items()]
    for document in documents or []:
        items.append({"kind": "project_doc", "path": document["path"], "text": document["text"]})
    return event(seq, "session_started", new_items=items)


def message(text: str, seq: int, reason: str = "answer") -> dict[str, Any]:
    """Build a visible assistant answer ending a turn."""
    return event(seq, "turn_completed", agent_text=text, turn={"reason": reason})


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_text(block.get("text")) for block in value
                         if isinstance(block, dict) and block.get("type") in {"text", "output_text"})
    return json.dumps(value, ensure_ascii=False)


def _args(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return {"raw": value}
        return parsed if isinstance(parsed, dict) else {"raw": value}
    return {}


def tool(name: str, args: Any, result: Any, seq: int, is_error: bool = False,
         agent_text: str = "", file_changes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build a tool event while retaining only supplied execution evidence."""
    action = {"tool": name, "args": _args(args), "result_text": _text(result), "is_error": is_error}
    if file_changes is not None:
        if name not in {"Edit", "Write"} and file_changes:
            raise ValueError("Only Edit and Write may carry file changes.")
        action["file_changes"] = file_changes
    return event(seq, "tool_completed", action=action, agent_text=agent_text)


def from_messages(messages: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Convert Anthropic or OpenAI messages while keeping reasoning in a side map."""
    messages = list(messages)
    results: dict[str, list[tuple[Any, bool]]] = {}
    for item in messages:
        if item.get("role") in {"tool", "function"}:
            key = item.get("tool_call_id", item.get("name", ""))
            results.setdefault(key, []).append((item.get("content"), item.get("is_error", False)))
        content = item.get("content")
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                results.setdefault(block.get("tool_use_id", ""), []).append(
                    (block.get("content"), block.get("is_error", False)))
    events: list[dict[str, Any]] = []
    reasoning: dict[str, str] = {}
    pending_reasoning: list[str] = []

    def append(value: dict[str, Any]) -> None:
        events.append(value)
        if pending_reasoning:
            reasoning[str(value["seq"])] = "\n".join(pending_reasoning)
            pending_reasoning.clear()

    def call(block: dict[str, Any], visible: str) -> None:
        function = block.get("function") or block
        name = function.get("name", "")
        key = block.get("id", name)
        matches = results.get(key, [])
        result, error = matches.pop(0) if matches else ("", False)
        append(tool(name, function.get("arguments", function.get("input", {})), result,
                    len(events) + 1, is_error=error, agent_text=visible))

    for item in messages:
        role = item.get("role")
        content = item.get("content")
        if role in {"system", "developer", "user", "human"}:
            # Tool results are associated with their calls, never new user instructions.
            text = _text(content)
            if text:
                append(instruction(text, len(events) + 1))
            continue
        if role not in {"assistant", "gpt"}:
            continue
        raw_reasoning = item.get("reasoning_content", item.get("reasoning", ""))
        if isinstance(raw_reasoning, str) and raw_reasoning:
            pending_reasoning.append(raw_reasoning)
        visible: list[str] = []
        had_call = False
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                kind = block.get("type")
                if kind in {"thinking", "reasoning"}:
                    raw = block.get("thinking", block.get("text", ""))
                    if isinstance(raw, str) and raw:
                        pending_reasoning.append(raw)
                elif kind in {"text", "output_text"}:
                    visible.append(block.get("text", ""))
                elif kind == "tool_use":
                    call(block, "\n".join(visible))
                    visible.clear()
                    had_call = True
        elif isinstance(content, str):
            visible.append(content)
        calls = item.get("tool_calls") or []
        if item.get("function_call"):
            calls = [item["function_call"]]
        for block in calls:
            call(block, "\n".join(visible))
            visible.clear()
            had_call = True
        if visible or not had_call:
            append(message("\n".join(visible), len(events) + 1))
    return events, reasoning
