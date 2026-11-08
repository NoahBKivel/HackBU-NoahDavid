"""Select row identities without formatting their question text."""

from .firing import EVERY_EVENT


def initial(event: dict, header: dict) -> list[str]:
    """Select action, correction-followup and answer-turn rows."""
    keys = list(EVERY_EVENT) if event.get("type") != "turn_completed" or event.get("agent_text") else []
    seq = event.get("seq")
    for finding in header["findings"]:
        reached = finding.get("reached_at")
        if finding["status"] == "open" and finding.get("message") and reached is not None and seq is not None and seq > reached:
            key = f"L7#{finding['message']}"
            if key not in keys:
                keys.append(key)
    if event.get("type") == "turn_completed" and (event.get("turn") or {}).get("reason", "answer") == "answer":
        keys.extend(f"G2#R{unit['k']}" for unit in header["units"] if unit["accepted"])
        keys.append("G5")
    return keys
