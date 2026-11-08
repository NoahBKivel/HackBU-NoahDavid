"""Validate runtime events and labelled decision records."""

import math
from typing import Any

READ_ONLY_TOOLS = frozenset({"Read", "Grep", "Glob", "WebFetch", "WebSearch", "LS", "NotebookRead"})
_EVENT_TYPES = {"session_started", "tool_completed", "turn_completed"}
_EVAL_ONLY = {"mmlu", "emotion", "tweet_offensive", "qnli", "paws", "sciq", "contrastive",
              "legacy_holdout", "composition_holdout"}


def validate_event(event: dict[str, Any]) -> None:
    """Raise ValueError when an event violates the runtime interchange contract."""
    if not isinstance(event, dict):
        raise ValueError("An event must be an object.")
    if not isinstance(event.get("seq"), int) or isinstance(event.get("seq"), bool):
        raise ValueError("An event requires an integer seq.")
    if event.get("type") not in _EVENT_TYPES:
        raise ValueError("The event type is unsupported.")
    for key in ("ts", "agent_text", "agent_thinking"):
        if not isinstance(event.get(key), str):
            raise ValueError(f"The event requires a string {key}.")
    if not isinstance(event.get("new_items"), list) or not isinstance(event.get("todos"), list):
        raise ValueError("The event requires new_items and todos lists.")
    for item in event["new_items"]:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            raise ValueError("Each new item requires verbatim text.")
        if item.get("kind") == "project_doc" and not isinstance(item.get("path"), str):
            raise ValueError("A project document requires its path.")
        if item.get("kind") == "user_instruction" and not isinstance(item.get("id"), str):
            raise ValueError("A user instruction requires its source id.")
    action = event.get("action")
    if not isinstance(action, dict):
        raise ValueError("The event requires an action object, empty when absent.")
    if event["type"] == "tool_completed":
        if not isinstance(action.get("tool"), str) or not isinstance(action.get("args"), dict):
            raise ValueError("A tool event requires its name and argument object.")
        if not isinstance(action.get("result_text"), str) or not isinstance(action.get("is_error"), bool):
            raise ValueError("A tool event requires result_text and is_error.")
    changes = action.get("file_changes", [])
    if not isinstance(changes, list):
        raise ValueError("File changes must be a list.")
    if changes and action.get("tool") not in {"Edit", "Write"}:
        raise ValueError("Only Edit and Write events may carry file changes.")
    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get("path"), str):
            raise ValueError("A file change requires a path.")
        if change.get("op") not in {"edit", "write"}:
            raise ValueError("A file change must be an edit or write.")
        patch = change.get("patch")
        if patch is not None:
            if not isinstance(patch, list):
                raise ValueError("A patch must be structured hunks or null.")
            for hunk in patch:
                if not isinstance(hunk, dict) or not isinstance(hunk.get("lines"), list):
                    raise ValueError("A patch hunk requires a lines list.")
                if any(not isinstance(line, str) for line in hunk["lines"]):
                    raise ValueError("Patch hunk lines must be strings.")
    if not isinstance(event.get("turn"), dict):
        raise ValueError("The event requires a turn object, empty when absent.")
    if event["type"] == "turn_completed" and event["turn"].get("reason") not in {
        "answer", "aborted", "refusal", "error"
    }:
        raise ValueError("A completed turn requires its end reason.")


def validate_events(events: list[dict[str, Any]]) -> None:
    """Validate an event stream with strictly increasing sequence numbers."""
    previous = None
    for event in events:
        validate_event(event)
        if previous is not None and event["seq"] <= previous:
            raise ValueError("Event sequence numbers must increase strictly.")
        previous = event["seq"]


def is_cut_point(event: dict[str, Any]) -> bool:
    """Return whether an event is classified rather than a read or clarification."""
    return event["type"] == "turn_completed" or (
        event["type"] == "tool_completed"
        and (event.get("action") or {}).get("tool") not in READ_ONLY_TOOLS | {"AskUserQuestion"}
    )


def validate_record(record: dict[str, Any]) -> None:
    """Validate the external labelled record shape before tokenizer admission."""
    if not isinstance(record.get("state"), str) or not isinstance(record.get("questions"), dict):
        raise ValueError("A record requires a text state and a question object.")
    if not record["questions"]:
        raise ValueError("A record must contain at least one question.")
    if record.get("_meta", {}).get("source") in _EVAL_ONLY:
        raise ValueError("An evaluation-only source cannot enter training.")
    for key, row in record["questions"].items():
        if row.get("type") not in {"noul", "choice", "score"} or "label" not in row:
            raise ValueError(f"Question {key} requires a supported type and label.")
        if not isinstance(row.get("instructions"), str):
            raise ValueError(f"Question {key} requires its wording.")
        if row["type"] == "noul":
            if not isinstance(row["label"], bool):
                raise ValueError(f"Question {key} requires a boolean label.")
            options = {"false", "true"}
        elif row["type"] == "choice":
            criteria = row.get("criteria")
            if not isinstance(criteria, dict) or not criteria or row["label"] not in criteria:
                raise ValueError(f"Question {key} requires choice criteria and a matching label.")
            options = set(criteria)
        else:
            criteria = row.get("criteria")
            label = row["label"]
            if (not isinstance(criteria, list) or not criteria or not isinstance(label, int)
                    or isinstance(label, bool) or not 0 <= label < len(criteria)):
                raise ValueError(f"Question {key} requires score criteria and a valid integer label.")
            options = {str(index) for index in range(len(criteria))}
        if "target" in row:
            target = row["target"]
            if (not isinstance(target, dict) or not target or not set(target) <= options
                    or any(not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
                           for value in target.values())):
                raise ValueError(f"Question {key} has an invalid target distribution.")
            if abs(sum(target.values()) - 1) > 1e-7:
                raise ValueError(f"Question {key} target probabilities must sum to one.")
