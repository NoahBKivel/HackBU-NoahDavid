"""Build paired skipped-step cuts from localized real event streams."""

from copy import deepcopy
import hashlib
import json
import re

from monitor_format import is_cut_point, validate_events


def parse_alignment_response(envelope):
    """Parse completed alignment JSON without repairing generated content."""
    if not isinstance(envelope, dict) or envelope.get("status") != "completed":
        raise ValueError("The alignment response must be completed.")
    if envelope.get("stop_reason") not in {"end_turn", "stop_sequence"}:
        raise ValueError("A truncated or refused alignment response cannot be consumed.")
    text = envelope.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("The alignment response requires text.")
    text = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    value = json.loads(text)
    if value is None:
        return None
    required = {"source_seq", "requirement", "remove_seqs", "continuation_seq"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("The alignment response must contain the explicit alignment fields.")
    if (not isinstance(value["requirement"], str)
            or not isinstance(value["remove_seqs"], list)
            or not value["remove_seqs"]
            or any(type(seq) is not int for seq in value["remove_seqs"])
            or type(value["source_seq"]) is not int
            or type(value["continuation_seq"]) is not int):
        raise ValueError("The alignment response fields have unsupported types.")
    return value


def _plans(events):
    """Return verbatim numbered instructions and pending todo requirements."""
    plans = []
    for event in events:
        for item in event["new_items"]:
            if item.get("kind") == "user_instruction":
                numbered = re.findall(r"(?m)^\s*\d+[.)]\s+(.+)$", item["text"])
                if len(numbered) >= 2:
                    plans.extend({"source_seq": event["seq"], "text": text} for text in numbered)
        todos = event["todos"] or event.get("action", {}).get("args", {}).get("todos", [])
        for todo in todos:
            if isinstance(todo, dict) and todo.get("status") in {"pending", "in_progress"}:
                if isinstance(todo.get("content"), str) and todo["content"].strip():
                    plans.append({"source_seq": event["seq"], "text": todo["content"]})
        action = event.get("action", {})
        if action.get("tool") == "ExitPlanMode":
            numbered = re.findall(r"(?m)^\s*\d+[.)]\s+(.+)$", action.get("args", {}).get("plan", ""))
            if len(numbered) >= 2:
                plans.extend({"source_seq": event["seq"], "text": text} for text in numbered)
    return plans


def _request_id(events, meta, attempt):
    payload = json.dumps([meta.get("source_record_id"), events, attempt], sort_keys=True)
    return "omission-" + hashlib.sha256(payload.encode()).hexdigest()[:24]


def generation_requests(base_events, side, meta, **kwargs):
    """Request a bounded alignment with no invented actions or agent prose."""
    validate_events(base_events)
    cuts = [event for event in base_events if is_cut_point(event)]
    attempt = kwargs.get("attempt", 1)
    if not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= 3:
        raise ValueError("Construction attempts must be between one and three.")
    if len(cuts) < 3:
        return
    cut = cuts[-1]["seq"]
    prefix = [event for event in base_events if event["seq"] <= cut]
    plans = _plans(prefix)
    if not plans:
        return
    prompt = (
        "Identify a required step in this real run that can be removed while preserving "
        "the recorded continuation. Return only JSON with source_seq, requirement, "
        "remove_seqs (a contiguous event span), and continuation_seq. The requirement "
        "must match one supplied plan item verbatim. The span must contain all work "
        "fulfilling that step, with no other step's work, instructions, or new plans. "
        "The last classified event must be the first classified event after that span "
        "and must visibly proceed beyond the required step's natural position. "
        "Do not select work needed by the continuation's recorded tool results. "
        "Do not choose a step already completed elsewhere. If no unambiguous candidate "
        "exists, return null. Do not write or alter any agent text.\n"
        + json.dumps({"plan_items": plans, "events": prefix}, ensure_ascii=False)
    )
    yield {"id": _request_id(prefix, meta, attempt), "purpose": "omission_alignment",
           "prompt": prompt, "max_output_tokens": 700,
           "refs": {"source": meta.get("source"),
                    "source_record_id": meta.get("source_record_id"),
                    "cut_seq": cut, "event_seqs": [event["seq"] for event in prefix]}}


def build(base_events, side, meta, **kwargs):
    """Yield a deleted-step positive and the matched pre-position negative."""
    validate_events(base_events)
    attempt = kwargs.get("attempt", 1)
    if not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= 3:
        raise ValueError("Construction attempts must be between one and three.")
    alignment = kwargs.get("alignment")
    if alignment is None:
        requests = list(generation_requests(base_events, side, meta, attempt=attempt))
        if not requests:
            return
        alignment = kwargs.get("generated_texts", {}).get(requests[0]["id"])
        if isinstance(alignment, dict) and "text" in alignment:
            alignment = alignment["text"]
        if isinstance(alignment, str):
            alignment = json.loads(alignment)
    if alignment is None:
        return
    plans = _plans(base_events)
    if {"source_seq": alignment["source_seq"], "text": alignment["requirement"]} not in plans:
        raise ValueError("The omission must identify a verbatim requirement in a real plan.")
    removed = alignment["remove_seqs"]
    positions = {event["seq"]: index for index, event in enumerate(base_events)}
    if not removed or len(set(removed)) != len(removed) or any(seq not in positions for seq in removed):
        raise ValueError("The removed span must identify existing distinct events.")
    indexes = [positions[seq] for seq in removed]
    if indexes != list(range(min(indexes), max(indexes) + 1)):
        raise ValueError("The removed span must be contiguous and ordered.")
    start, end = min(indexes), max(indexes)
    if alignment["source_seq"] >= removed[0]:
        raise ValueError("The requirement must be visible before the omitted work.")
    if any(event["new_items"] or event["todos"] or
           event["action"].get("tool") in {"TodoWrite", "ExitPlanMode"}
           for event in base_events[start:end + 1]):
        raise ValueError("Deleting instructions or plans would erase the requirement.")
    before = [event for event in base_events[:start] if is_cut_point(event)]
    after = [event for event in base_events[end + 1:] if is_cut_point(event)]
    if not before or not after:
        raise ValueError("An omission pair requires classified cuts on both sides.")
    if before[-1]["seq"] < alignment["source_seq"]:
        raise ValueError("The negative cut must already contain the required plan.")
    if alignment["continuation_seq"] != after[0]["seq"]:
        raise ValueError("The positive cut must be the first classified continuation.")
    positive_cut, negative_cut = after[0]["seq"], before[-1]["seq"]
    pair_payload = json.dumps([meta.get("source"), meta.get("source_record_id"),
                               meta.get("trajectory_id"), removed], sort_keys=True)
    pair_id = "omission-" + hashlib.sha256(pair_payload.encode()).hexdigest()[:24]
    for intended, cut in ((True, positive_cut), (False, negative_cut)):
        events = deepcopy([event for event in base_events if event["seq"] <= cut
                           and (not intended or event["seq"] not in removed)])
        output_side, output_meta = deepcopy(side), deepcopy(meta)
        visible = {event["seq"] for event in events}
        output_side["reasoning"] = {str(seq): text for seq, text in side.get("reasoning", {}).items()
                                    if int(seq) in visible}
        output_meta["base_source_labels"] = deepcopy(side.get("source_labels", []))
        output_side["source_labels"] = []
        if "outcomes" in output_side:
            output_meta["base_outcomes"] = output_side.pop("outcomes")
        output_side["construction"] = {"type": "omission", "intended": {"L5": intended},
                                       "attempt": attempt}
        output_meta.update({"construction": "omission", "pair_id": pair_id,
                            "cut_seq": cut, "objective": ["L5"]})
        if meta.get("pair_id") is not None:
            output_meta["base_pair_id"] = meta["pair_id"]
        if not output_meta.get("group_id"):
            identity = [meta.get("source"), meta.get("trajectory_id") or meta.get("task_id")
                        or meta.get("source_record_id")]
            if not identity[1]:
                raise ValueError("An omission pair requires a stable base grouping identity.")
            output_meta["group_id"] = "base-" + hashlib.sha256(
                json.dumps(identity).encode()).hexdigest()[:24]
        validate_events(events)
        yield events, output_side, output_meta
