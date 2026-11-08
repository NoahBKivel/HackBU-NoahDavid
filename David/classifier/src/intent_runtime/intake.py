"""Decide whether a stored Mod event is scored."""

READ_TOOLS = frozenset({"Read", "Grep", "Glob", "WebFetch", "WebSearch", "LS", "NotebookRead", "AskUserQuestion"})


def skipped(event: dict, duplicate: bool = False, stale: bool = False) -> bool:
    """Apply the fixed event table after accepting all new session items."""
    if duplicate or stale or event.get("type") == "session_started":
        return True
    if event.get("type") == "turn_completed":
        return not event.get("agent_text") and (event.get("turn") or {}).get("reason", "answer") != "answer"
    action = event.get("action") or {}
    if action.get("tool") in READ_TOOLS:
        return True
    return not action and not event.get("agent_text")
