"""Render detailed event blocks and compact ledger lines."""

import json
import re
from typing import Any

from .schema import READ_ONLY_TOOLS
from .tokens import count_tokens, trim_field


def tool_name(event: dict[str, Any]) -> str:
    """Return the canonical tool name for a runtime event."""
    name = (event.get("action") or {}).get("tool", "")
    return "Bash" if name in {"PowerShell", "powershell", "Shell", "Terminal"} else name


def key_argument(event: dict[str, Any]) -> str:
    """Return a tool's visible identifying argument without inventing one."""
    args = (event.get("action") or {}).get("args", {})
    name = tool_name(event)
    if name in {"TodoWrite", "ExitPlanMode"}:
        return ""
    keys = {"Bash": ("command",), "Read": ("file_path", "path"),
            "Write": ("file_path", "path"), "Edit": ("file_path", "path"),
            "Grep": ("pattern",), "Glob": ("pattern",), "WebFetch": ("url",)}
    if name in keys:
        return next((str(args[key]) for key in keys[name] if isinstance(args.get(key), str)), "")
    return next((value for value in args.values() if isinstance(value, str)), "")


def render_patch(patch: list[dict[str, Any]] | None) -> str:
    """Render structured patch hunks as unified-diff lines."""
    lines = []
    for hunk in patch or []:
        old_start, new_start = hunk.get("oldStart", 0), hunk.get("newStart", 0)
        old_lines, new_lines = hunk.get("oldLines", 0), hunk.get("newLines", 0)
        lines.append(f"@@ -{old_start},{old_lines} +{new_start},{new_lines} @@")
        lines.extend(hunk.get("lines", []))
    return "\n".join(lines)


def patch_counts(event: dict[str, Any]) -> tuple[int, int]:
    """Count added and removed lines in the structured hunks an event carries."""
    lines = [line for change in (event.get("action") or {}).get("file_changes", [])
             for hunk in change.get("patch") or [] for line in hunk.get("lines", [])]
    return (sum(line.startswith("+") and not line.startswith("+++") for line in lines),
            sum(line.startswith("-") and not line.startswith("---") for line in lines))


def test_counts(text: str) -> tuple[int, int] | None:
    """Parse visible pytest, JavaScript, Go and Cargo test summaries."""
    passed = re.findall(r"\b(\d+)\s+(?:passed|passing|pass)\b", text, re.IGNORECASE)
    failed = re.findall(r"\b(\d+)\s+(?:failed|failing|fail)\b", text, re.IGNORECASE)
    if passed or failed:
        return (int(passed[-1]) if passed else 0, int(failed[-1]) if failed else 0)
    go_pass = re.findall(r"(?m)^--- PASS:", text)
    go_fail = re.findall(r"(?m)^--- FAIL:", text)
    if go_pass or go_fail:
        return len(go_pass), len(go_fail)
    return None


def render_one_liner(event: dict[str, Any]) -> str:
    """Render a compact event reference and only the evidence actually present."""
    seq, kind = event["seq"], event["type"]
    if kind == "turn_completed":
        prefix = f"[E{seq}] MESSAGE"
    elif kind == "session_started":
        prefix = f"[E{seq}] SESSION STARTED"
    else:
        name, argument = tool_name(event), key_argument(event)
        prefix = f"[E{seq}] {name}" + (f" {argument}" if argument else "")
        plus, minus = patch_counts(event)
        if plus or minus:
            prefix += f" (+{plus}/-{minus})"
        if name in READ_ONLY_TOOLS:
            return prefix
    fields = [prefix]
    counts = test_counts((event.get("action") or {}).get("result_text", ""))
    if counts is not None:
        fields.append(f"tests {counts[0]} pass, {counts[1]} fail")
    message = event.get("agent_text", "")
    if message:
        excerpt = re.sub(r"\s+", " ", message).strip()[:100]
        fields.append(json.dumps(excerpt, ensure_ascii=False))
    return " | ".join(fields)


def _bounded_fields(fields: dict[str, str], budget: int, tokenizer: Any) -> dict[str, str]:
    sizes = {name: count_tokens(text, tokenizer) for name, text in fields.items()}
    if count_tokens("\n".join(fields.values()), tokenizer) <= budget:
        return fields
    minimum = {}
    for name, text in fields.items():
        size = sizes[name]
        marked = text[:1] + f"[cut {size} tokens]" + text[-1:]
        minimum[name] = min(size, count_tokens(marked, tokenizer)) if size else 0
    remaining = budget - sum(minimum.values()) - count_tokens("\n" * (len(fields) - 1), tokenizer)
    if remaining < 0:
        raise ValueError("The event-field budget cannot preserve every nonempty field's cut marker.")
    weights = {name: sizes[name] - minimum[name] for name in fields}
    total = sum(weights.values())
    allocations = {name: minimum[name] + (int(remaining * weight / total) if total else 0)
                   for name, weight in weights.items()}
    bounded = {name: trim_field(text, allocations[name], tokenizer) for name, text in fields.items()}
    while count_tokens("\n".join(bounded.values()), tokenizer) > budget:
        candidates = [name for name in fields if allocations[name] > minimum[name]]
        if not candidates:
            raise ValueError("The rendered field markers exceed the available token budget.")
        name = max(candidates, key=lambda key: count_tokens(bounded[key], tokenizer))
        allocations[name] -= 1
        bounded[name] = trim_field(fields[name], allocations[name], tokenizer)
    return bounded


def render_event(event: dict[str, Any], previous_todos: list | None = None, *,
                 tokenizer: Any, field_budget: int = 2000) -> str:
    """Render one event with an exact shared token cap on its substantive fields."""
    if field_budget <= 0:
        raise ValueError("The substantive-field token budget must be positive.")
    if event["type"] == "turn_completed":
        text = trim_field(event.get("agent_text", ""), field_budget, tokenizer)
        return f"[E{event['seq']}] MESSAGE\n{text}"
    if event["type"] == "session_started":
        return f"[E{event['seq']}] SESSION STARTED"
    name, argument = tool_name(event), key_argument(event)
    if name in READ_ONLY_TOOLS:
        return render_one_liner(event)
    action = event.get("action") or {}
    changes = action.get("file_changes", [])
    patch = "\n".join(render_patch(change.get("patch")) for change in changes if change.get("patch"))
    fields = {"result": action.get("result_text", ""), "patch": patch,
              "agent said": event.get("agent_text", ""),
              "plan": str(action.get("args", {}).get("plan", "")) if name == "ExitPlanMode" else ""}
    fields = _bounded_fields(fields, field_budget, tokenizer)
    lines = [f"[E{event['seq']}] {name}" + (f": {argument}" if argument else "")]
    lines.append(f"result ({'error' if action.get('is_error') else 'ok'}): {fields['result']}")
    if changes:
        file_parts = []
        for change in changes:
            plus = sum(line.startswith("+") for hunk in change.get("patch") or [] for line in hunk["lines"])
            minus = sum(line.startswith("-") for hunk in change.get("patch") or [] for line in hunk["lines"])
            file_parts.append(f"{change['path']} ({change['op']}, +{plus}/-{minus})")
        lines.append("files: " + "; ".join(file_parts))
    if fields["patch"]:
        lines.append("patch: " + fields["patch"])
    if fields["agent said"]:
        lines.append("agent said: " + fields["agent said"])
    if event.get("agent_thinking"):
        lines.append("thinking note: " + event["agent_thinking"])
    todos = event.get("todos", [])
    if todos != (previous_todos or []):
        lines.append("todos: " + " ".join(
            f"[{'x' if item.get('status') == 'completed' else ' '}] {item.get('content', '')}"
            for item in todos))
    if name == "ExitPlanMode" and fields["plan"]:
        lines.append("plan: " + fields["plan"])
    return "\n".join(lines)
