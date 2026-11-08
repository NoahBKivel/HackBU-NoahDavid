"""Fill repeated question rows and trim their quoted content consistently."""

from copy import deepcopy
import re
from typing import Any

from .questions import CORRECTION_ORDER, QUESTION_TABLE, SHORT_NAMES
from .tokens import count_tokens, trim_text


def base_question_id(question_id: str) -> str:
    """Return the unsuffixed question id while retaining a negated twin marker."""
    return question_id.split("#", 1)[0]


def row_key(question_id: str, reference: str | int | None = None) -> str:
    """Attach the event, requirement or section suffix used by repeated rows."""
    if reference is None:
        return question_id
    if isinstance(reference, int):
        prefix = "E" if question_id in {"D1", "D3"} else "S" if question_id in {"SCR", "M8"} else "R"
        reference = f"{prefix}{reference}"
    return f"{question_id}#{reference}"


def short_names(question_ids: list[str] | tuple[str, ...]) -> str:
    """List fired-question short names in correction order without duplicates."""
    normalized = {"M2" if base_question_id(qid) == "M8" else base_question_id(qid) for qid in question_ids}
    return ", ".join(SHORT_NAMES[qid] for qid in CORRECTION_ORDER if qid in normalized)


def diagnostic_summary(question_ids: list[str], event_seqs: list[int]) -> str:
    """Summarize fired questions against their localized visible event references."""
    return short_names(question_ids) + " at " + ", ".join(f"E{seq}" for seq in dict.fromkeys(event_seqs))


def question_token_cost(row: dict[str, Any], tokenizer: Any) -> int:
    """Count a question branch exactly as Kev serializes its instructions and options."""
    typ = row["type"]
    criteria = row.get("criteria")
    if typ == "noul":
        criteria = criteria or {}
        choices = [name if criteria.get(key) in {"", None} else f"{name}: {criteria[key]}"
                   for name, key in (("no", "false"), ("yes", "true"))]
    elif typ == "choice":
        choices = [name if value in {"", None} else f"{name}: {value}" for name, value in criteria.items()]
    else:
        choices = criteria
    return 2 + count_tokens(row["instructions"], tokenizer) + sum(
        2 + count_tokens(text, tokenizer) for text in choices)


def fill_question(question_id: str, *, requirement_text: str = "", correction: str = "",
                  fired_questions: list[str] | tuple[str, ...] = (), event_seq: int | None = None,
                  summary: str = "", section_id: str | int | None = None,
                  tokenizer: Any = None, row_budget: int = 640) -> dict[str, Any]:
    """Fill one exact question template and trim quoted content to its branch allowance."""
    base = base_question_id(question_id)
    row = deepcopy(QUESTION_TABLE[base])
    template = row["instructions"]
    if event_seq is not None:
        template = template.replace("event k", f"event E{event_seq}")
    if section_id is not None:
        section = f"S{section_id}" if isinstance(section_id, int) else section_id
        template = template.replace("[Sk]", f"[{section}]")
    template = template.replace("«short names of the questions that fired»", short_names(fired_questions))
    template = template.replace("«summary»", summary)

    def wording(requirement: str, correction_text: str) -> str:
        return template.replace("«R_k text»", requirement).replace("«text»", correction_text)

    row["instructions"] = wording(requirement_text, correction)
    if tokenizer is None or question_token_cost(row, tokenizer) <= row_budget:
        return row
    if base == "L7":
        correction = re.sub(r"(?m)\s*Evidence:.*$", "", correction)
        row["instructions"] = wording(requirement_text, correction)
    quoted = correction if base == "L7" else requirement_text
    if not quoted:
        raise ValueError("The fixed question text exceeds its row allowance.")
    low, high = 0, count_tokens(quoted, tokenizer)
    best = None
    while low <= high:
        allowance = (low + high) // 2
        trimmed = trim_text(quoted, allowance, tokenizer, marker="[cut]")
        row["instructions"] = wording(requirement_text, trimmed) if base == "L7" else wording(trimmed, correction)
        if question_token_cost(row, tokenizer) <= row_budget:
            best, low = row["instructions"], allowance + 1
        else:
            high = allowance - 1
    if best is None:
        raise ValueError("The fixed question and options exceed the row allowance.")
    row["instructions"] = best
    return row
