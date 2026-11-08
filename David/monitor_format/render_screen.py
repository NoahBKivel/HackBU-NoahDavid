"""Render the document-overflow screen with a bounded recent-event ledger."""

from typing import Any

from .instructions import instruction_text
from .render_event import render_event
from .tokens import count_tokens


def screen_section_cap(instructions: list[dict[str, str]], events: list[dict[str, Any]],
                       k: int, budget: int, *, tokenizer: Any, target_sections: int = 10) -> int:
    """Compute the section cap after the exact instruction and recent-ledger cost."""
    empty, _ = render_screen(instructions, [], events, k, budget, tokenizer=tokenizer)
    return max(1, (budget - count_tokens(empty, tokenizer)) // target_sections)


def render_screen(instructions: list[dict[str, str]], sections: list[dict[str, str]],
                  events: list[dict[str, Any]], k: int, budget: int, *,
                  tokenizer: Any) -> tuple[str, bool]:
    """Fill one overflow screen without truncating instructions or section text."""
    visible = sorted((event for event in events if event["seq"] <= k), key=lambda item: item["seq"])
    if not visible or visible[-1]["seq"] != k:
        raise ValueError("The cut event is absent from the visible event stream.")
    latest = render_event(visible[-1], visible[-2].get("todos", []) if len(visible) > 1 else [],
                          tokenizer=tokenizer)
    recent: list[str] = []
    for index in range(len(visible) - 2, -1, -1):
        block = render_event(visible[index], visible[index - 1].get("todos", []) if index else [],
                             tokenizer=tokenizer)
        ledger = "RUN LEDGER\n" + "\n".join([block] + recent) + "\n\nLATEST EVENT\n" + latest
        if count_tokens(ledger, tokenizer) > 0.15 * budget:
            break
        recent.insert(0, block)
    prefix = "USER INSTRUCTIONS\n" + instruction_text(instructions) + "\n\nDOCUMENT SECTIONS\n"
    suffix = "\n\nRUN LEDGER\n" + "\n".join(recent) + "\n\nLATEST EVENT\n" + latest
    included: list[str] = []
    fits = count_tokens(prefix + suffix, tokenizer) <= budget
    for index, section in enumerate(sections, 1):
        heading = section.get("heading", "")
        label = section.get("path", "") + (f" › {heading}" if heading else "")
        block = f"[{section.get('id', f'S{index}')}] {label}\n{section['text']}"
        candidate = prefix + "\n".join(included + [block]) + suffix
        if count_tokens(candidate, tokenizer) > budget:
            fits = False
            break
        included.append(block)
    return prefix + "\n".join(included) + suffix, fits
