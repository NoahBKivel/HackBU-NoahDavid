"""Render deterministic corrections from visible flagged evidence."""

from typing import Any

from .questions import CORRECTION_ORDER, CORRECTIONS, QUESTION_TABLE, SHORT_NAMES
from .rows import base_question_id


def correction_text(items: list[dict[str, Any]], user_request: str = "", serious: bool = False) -> str:
    """Render ordered correction items with evidence on the first three only."""
    def normalized(item: dict[str, Any]) -> str:
        question = base_question_id(item["question"])
        return "M2" if question == "M8" else question

    ordered = sorted(items, key=lambda item: CORRECTION_ORDER.index(normalized(item)))
    lines = [f"Intent monitor: a check on your recent work flagged {len(ordered)} item(s)."]
    fixes = []
    for index, item in enumerate(ordered, 1):
        question = normalized(item)
        refs = ", ".join(f"E{seq}" for seq in item.get("event_seqs", []))
        requirement = item.get("requirement") or f"the user's request: [I1] {user_request}"
        answer = item.get("answer", "no" if question == "G1" else "yes")
        probability = float(item["probability"])
        if not 0 <= probability <= 1:
            raise ValueError("A correction probability must lie between zero and one.")
        line = (f"{index}. {SHORT_NAMES[question]} at {refs}: asked \"{QUESTION_TABLE[question]['instructions']}\""
                f" against \"{requirement}\", answered {answer} (p = {probability:.2f}).")
        if index <= 3:
            line += " Evidence: " + item.get("evidence", "") + "."
        lines.append(line)
        fix = CORRECTIONS[question]
        if question == "M1":
            fix += f": \"{user_request}\""
        if question == "G2":
            details = []
            for key, label in (("not_done", "not done"), ("broken", "broken")):
                if item.get(key):
                    details.append(f"{label}: " + ", ".join(item[key]))
            if details:
                fix += " (" + "; ".join(details) + ")"
        if fix not in fixes:
            fixes.append(fix)
        serious = serious or item.get("severity") == "serious"
    lines.append("Check whether each item really happened. If one did not, ignore it and continue. "
                 "For each that did: " + "; ".join(fixes) + ".")
    if serious:
        lines.append("Stop and ask the user before continuing.")
    return "\n".join(lines)
