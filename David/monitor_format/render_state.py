"""Render a bounded monitor state from visible runtime events."""

from typing import Any

from .effort import render_effort
from .instructions import instruction_text
from .render_event import render_event, render_one_liner, tool_name
from .schema import READ_ONLY_TOOLS
from .tokens import count_tokens


def open_findings_line(finding: dict[str, Any]) -> str:
    """Render the only state-visible representation of a monitor correction."""
    refs = ", ".join(f"E{seq}" for seq in finding.get("event_seqs", []))
    correction = finding.get("correction_seq")
    sent = f"E{correction}" if correction is not None else "not sent"
    return (f"[{finding['id']}] {finding['question']} at {refs} · correction sent at {sent}"
            f" · L7 status: {finding.get('status', 'open')}")


def document_text(documents: list[dict[str, str]] | dict[str, str]) -> str:
    """Render verbatim documents with their visible path headings."""
    items = ([{"path": path, "text": text} for path, text in documents.items()]
             if isinstance(documents, dict) else documents)
    return "\n\n".join(f"=== {item['path']} ===\n{item['text']}" for item in items)


def count_line(events: list[dict[str, Any]]) -> str:
    """Represent an oldest contiguous run of collapsed ledger events."""
    if not events:
        return ""
    return f"[E{events[0]['seq']}–E{events[-1]['seq']}: {len(events)} earlier events]"


def render_state(instructions: list[dict[str, str]], documents: list[dict[str, str]] | dict[str, str],
                 events: list[dict[str, Any]], k: int, findings: list[dict[str, Any]],
                 b_state: int, *, tokenizer: Any) -> tuple[str, list[int], bool]:
    """Render a newest-detail state and indicate when document overflow requires screening."""
    if b_state <= 0:
        raise ValueError("The state budget must be positive.")
    visible = sorted((event for event in events if event["seq"] <= k), key=lambda item: item["seq"])
    if not visible or visible[-1]["seq"] != k:
        raise ValueError("The cut event is absent from the visible event stream.")
    old, latest = visible[:-1], visible[-1]
    prefix = ("USER INSTRUCTIONS\n" + instruction_text(instructions)
              + "\n\nPROJECT DOCUMENTS\n" + document_text(documents))
    previous = old[-1].get("todos", []) if old else []
    latest_block = render_event(latest, previous, tokenizer=tokenizer)
    active = [finding for finding in findings if finding.get("correction_seq", k) is None
              or finding.get("correction_seq", k) <= k]
    finding_lines = "\n".join(open_findings_line(finding) for finding in active) or "(none)"
    tail = ("OPEN FINDINGS\n" + finding_lines + "\nEFFORT\n" + render_effort(visible)
            + "\n\nLATEST EVENT\n" + latest_block)

    def assemble(ledger: list[str]) -> str:
        return prefix + "\n\nRUN LEDGER\n" + "\n".join(ledger) + "\n" + tail

    collapsed = count_line(old)
    headings_and_required = "\n\nRUN LEDGER\n" + collapsed + "\n" + tail
    available_for_documents = b_state - 0.15 * b_state - count_tokens(headings_and_required, tokenizer)
    fits = count_tokens(prefix, tokenizer) <= available_for_documents
    if not fits:
        return assemble([collapsed] if collapsed else []), [k], False
    detail_budget = max(0.40 * b_state - count_tokens(prefix, tokenizer), 0.15 * b_state)
    detail_blocks: dict[int, str] = {}
    detail_tokens = 0
    for index in range(len(old) - 1, -1, -1):
        event = old[index]
        prior = old[index - 1].get("todos", []) if index else []
        block = render_event(event, prior, tokenizer=tokenizer)
        size = count_tokens(block + "\n", tokenizer)
        proposed = [count_line(old[:index])] if index else []
        proposed += [block] + [detail_blocks[item["seq"]] for item in old[index + 1:]]
        if detail_tokens + size > detail_budget or count_tokens(assemble(proposed), tokenizer) > b_state:
            break
        detail_blocks[event["seq"]] = block
        detail_tokens += size
    boundary = len(old) - len(detail_blocks)
    lines = [render_one_liner(event) for event in old[:boundary]]
    detailed = [detail_blocks[event["seq"]] for event in old[boundary:]]
    collapsed_count = 0
    while True:
        ledger = ([count_line(old[:collapsed_count])] if collapsed_count else []) + lines[collapsed_count:] + detailed
        text = assemble(ledger)
        if count_tokens(text, tokenizer) <= b_state:
            break
        if collapsed_count >= boundary:
            raise ValueError("Required state content exceeds the requested budget.")
        collapsed_count += 1
    detailed_seqs = [event["seq"] for event in old[boundary:]
                     if tool_name(event) not in READ_ONLY_TOOLS and event["type"] != "session_started"]
    detailed_seqs.append(k)
    return text, detailed_seqs, True
