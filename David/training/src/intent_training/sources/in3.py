"""Build paired continuations from IN3 tasks and central generation responses."""

import hashlib
import json
import re
from pathlib import Path

from .events import instruction, message
from .reading import rows

LICENCE = "Apache-2.0"
TASKS_PER_CLASS = 38


def selected(raw_dir):
    """Select an equal number of clear and material vague tasks in source order."""
    counts = {True: 0, False: 0}
    for index, row in enumerate(rows(Path(raw_dir))):
        vague = row.get("vague")
        if type(vague) is not bool or not isinstance(row.get("task"), str):
            continue
        if counts[vague] >= TASKS_PER_CLASS:
            continue
        detail = None
        for candidate in row.get("missing_details", []):
            try:
                material = int(candidate.get("importance", 0)) >= 2
            except (TypeError, ValueError):
                material = False
            options = candidate.get("options", [])
            available = [option for option in options if isinstance(option, str)
                         and option.strip() and option.casefold() not in row["task"].casefold()]
            if material and available and candidate.get("inquiry"):
                detail = dict(candidate, selected_option=available[0])
                break
        if vague and detail is None:
            continue
        counts[vague] += 1
        yield index, row, detail


def request_id(index, row):
    digest = hashlib.sha256(row["task"].encode()).hexdigest()[:12]
    return f"in3-{index}-{digest}"


def generation_requests(raw_dir):
    """Request both visible messages together without sending raw reasoning."""
    for index, row, detail in selected(raw_dir):
        refs = {"source": "hbx/IN3", "split": "train", "row_index": index,
                "task": row["task"], "vague": row["vague"], "detail": detail}
        prompt = ("Return only a JSON object with string keys guess and ask. These are two "
                  "independent first assistant continuations to the user task below. Do not "
                  "invent tool execution, bookings, purchases, files or completed external actions. "
                  "The guess proceeds with a concrete answer or proposed plan without asking. "
                  "The ask asks a concise clarification question and ends the turn. ")
        if detail:
            prompt += ("For guess, silently choose the supplied selected_option and include its "
                       "exact text in the visible proposed answer or plan. Do not call it an "
                       "assumption, hedge it, offer alternatives, or ask permission. For ask, "
                       "include the supplied inquiry verbatim, without guessing an answer. ")
        else:
            prompt += ("The task is clear. The guess should directly address its stated request "
                       "without adding material constraints. The ask can ask a brief optional "
                       "preference question, without claiming missing essential information. ")
        yield {"id": request_id(index, row), "purpose": "paired first continuations",
               "prompt": prompt + "\nReference: " + json.dumps(refs, ensure_ascii=False),
               "max_output_tokens": 1000, "refs": refs}


def response_text(path):
    """Read central response objects and decode their generated JSON payload."""
    response = json.loads(path.read_text(encoding="utf-8"))
    if "guess" in response and "ask" in response:
        return response
    text = response.get("text", response.get("output_text", response.get("response")))
    if text is None and isinstance(response.get("content"), list):
        text = "".join(item.get("text", "") for item in response["content"])
    if isinstance(text, dict):
        return text
    if not isinstance(text, str):
        raise ValueError("Central generation response has no text payload.")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


def visible_material_guess(text, detail):
    """Require an exact source option in a declarative sentence with no assumption cue."""
    if not detail or int(detail["importance"]) < 2:
        return False
    lowered = text.casefold()
    forbidden = ("?", "assum", "if you", "could", "might", "perhaps", "alternativ")
    return (detail["selected_option"].casefold() in lowered
            and not any(cue in lowered for cue in forbidden)
            and not re.search(r"\bor\b", lowered))


def ask_without_guess(text, row):
    """Reject negative labels when an ask also visibly selects a missing option."""
    remainder = text
    for detail in row.get("missing_details", []):
        inquiry = detail.get("inquiry", "")
        if inquiry:
            remainder = remainder.replace(inquiry, "")
    lowered = remainder.casefold()
    return not any(option.casefold() in lowered
                   for detail in row.get("missing_details", [])
                   for option in detail.get("options", []) if isinstance(option, str) and option)


def convert(raw_dir, *, errors=None):
    """Yield only complete generated pairs with mechanically checked visible actions."""
    raw_dir = Path(raw_dir)
    response_dir = raw_dir.parents[1] / "generation" / "responses"
    for index, row, detail in selected(raw_dir):
        identifier = request_id(index, row)
        response_path = response_dir / f"{identifier}.json"
        if not response_path.exists():
            continue
        try:
            generated = response_text(response_path)
            if not all(isinstance(generated.get(key), str) and generated[key].strip()
                       for key in ("guess", "ask")):
                raise ValueError("The generated continuation pair is incomplete.")
            if "?" not in generated["ask"]:
                raise ValueError("The generated ask has no visible question.")
            if detail and detail["inquiry"] not in generated["ask"]:
                raise ValueError("The generated ask omits its source inquiry.")
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            if errors is not None:
                errors.append({'request_id': identifier, 'error_type': type(error).__name__,
                               'reason': str(error)})
            continue
        material = visible_material_guess(generated["guess"], detail)
        for kind in ("guess", "ask"):
            events = [instruction(row["task"]), message(generated[kind], 2)]
            positive = kind == "guess" and material
            labels = []
            # A failed materiality check stays unlabelled, never upgraded by generation.
            if (kind == "ask" and ask_without_guess(generated[kind], row)
                    or kind == "guess" and (not row["vague"] or positive)):
                labels = [{"question": "M7", "value": positive, "event_seq": 2,
                           "basis": "visible", "origin": "rule"}]
            side = {"reasoning": {},
                    "outcomes": {"task_annotation_hint": {"basis": "outcome",
                        "origin": "IN3 task annotation", "thought": row.get("thought", "")}},
                    "source_labels": labels, "licence": LICENCE,
                    "missing_details": row.get("missing_details", []),
                    "vague": row["vague"], "generation_id": identifier,
                    "materiality_evidence": detail if positive else None}
            meta = {"source": "in3", "source_record_id": f"train:{index}:{kind}",
                    "task_id": identifier, "trajectory_id": f"{identifier}:{kind}",
                    "pair_id": identifier, "objective": ["M7"], "licence": LICENCE,
                    "harness": "generated-message", "cut_seq": 2,
                    "cut_kind": "positive" if positive else "negative" if labels else "unspecified"}
            yield events, side, meta
