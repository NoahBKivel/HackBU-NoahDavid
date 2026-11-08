"""Number user prompts and clarification answers in arrival order."""

from typing import Any


def build_instructions(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return verbatim user instructions and AskUserQuestion answers in event order."""
    instructions = []
    for event in sorted(events, key=lambda item: item["seq"]):
        for item in event.get("new_items", []):
            if item.get("kind") == "user_instruction":
                instructions.append({"id": f"I{len(instructions) + 1}", "text": item.get("text", "")})
        action = event.get("action") or {}
        if action.get("tool") == "AskUserQuestion":
            instructions.append({"id": f"I{len(instructions) + 1}", "text": action.get("result_text", "")})
    return instructions


def instruction_text(instructions: list[dict[str, str]]) -> str:
    """Render numbered instructions without altering their text."""
    return "\n".join(f"[{item['id']}] {item['text']}" for item in instructions)


def collect_documents(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return the latest visible version of each project document in arrival order."""
    documents = {}
    for event in sorted(events, key=lambda item: item["seq"]):
        for item in event.get("new_items", []):
            if item.get("kind") == "project_doc":
                documents[item["path"]] = {"path": item["path"], "text": item.get("text", "")}
    return list(documents.values())
