"""Compose ordered notices and link a shared correction to its findings."""

from collections.abc import Callable

from .findings import close_minor_actions


def compose(changed: list[dict], short_names: Callable[[list[str]], str], correction: Callable[[list[dict]], str],
            header: dict, event_id: str) -> list[dict]:
    """Return the notices and shared correction for new or upgraded issues."""
    if not changed:
        return []
    severity = changed[0]["severity"]
    names = short_names([finding["question"] for finding in changed])
    cited = sorted({seq for f in changed for seq in f["cited"]})
    references = ", ".join(f"E{seq}" for seq in cited)
    if severity == "minor":
        close_minor_actions(changed)
        return [{"type": "notify_user", "level": "potential", "text": f"Possible issue: {names} at {references}."}]
    text = correction(changed)
    message_id = f"M{len(header['messages']) + 1}"
    header["messages"][message_id] = {"text": text, "event_id": event_id}
    for finding in changed:
        finding["message"] = message_id
        finding["reached_at"] = None
    detected = f"Detected: {names} at {references}."
    if severity == "serious":
        detected += " The agent was told to stop and ask you before continuing."
    return [{"type": "notify_user", "level": "detected", "text": detected},
            {"type": "inject_agent", "text": text},
            {"type": "notify_user", "level": "intervened", "text": "A correction was sent to the agent."}]
