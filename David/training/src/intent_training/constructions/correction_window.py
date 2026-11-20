"""Build correction continuations from visible, localized source evidence."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import re

from monitor_format import QUESTION_TABLE, correction_text as render_correction
from monitor_format import is_cut_point, validate_events


CLASSES = tuple(QUESTION_TABLE["L7"]["criteria"])


def _fired(question, value):
    if question == "G2":
        return value in ("broken", "not done") if value in ("done", "broken", "not done") else None
    if not isinstance(value, bool):
        return None
    return value is (False if question == "G1" else True)


def _prefix(events, side, meta, items, benign):
    validate_events(events)
    if meta.get("source") not in {"swe_chat", "swechat", "terminal_bench_science", "open_swe",
                                  "cheatbench", "cheatbench_pilot"}:
        raise ValueError("Correction windows require an approved coding-session source.")
    cut = meta.get("cut_seq")
    if not isinstance(cut, int):
        raise ValueError("A correction base requires a localized cut_seq.")
    prefix = deepcopy([event for event in events if event["seq"] <= cut])
    if not prefix or prefix[-1]["seq"] != cut or not is_cut_point(prefix[-1]):
        raise ValueError("A correction must follow an existing classified event.")
    by_seq = {event["seq"]: event for event in prefix}
    instructions = "\n".join(item["text"] for event in prefix for item in event["new_items"])
    labels = side.get("source_labels", []) + side.get("teacher_labels", [])
    for item in items:
        if item.get("requirement") and item["requirement"].strip('"') not in instructions:
            raise ValueError("A quoted correction requirement must occur in the visible prefix.")
        for key in ("not_done", "broken"):
            if any(text not in instructions for text in item.get(key, [])):
                raise ValueError("Listed correction requirements must occur in the visible prefix.")
        refs = item.get("event_seqs", [])
        if not refs or any(seq not in by_seq for seq in refs):
            raise ValueError("Correction references must identify actual offenses and contain no future events.")
        for seq in refs:
            proof = [label for label in labels if label.get("question") == item["question"]
                     and label.get("event_seq") == seq and label.get("basis") == "visible"]
            if not proof or any(_fired(item["question"], label.get("value")) is not (not benign)
                                for label in proof):
                raise ValueError("Every correction reference requires consistent visible anchor labels.")
        if item["question"] == "G2":
            item["answer"] = "broken" if benign else proof[0]["value"]
        else:
            item["answer"] = "no" if item["question"] == "G1" else "yes"
        item["evidence"] = json.dumps([by_seq[seq] for seq in refs], ensure_ascii=False, sort_keys=True)
    return prefix


def _plans(base_events, side, meta, **kwargs):
    attempt = kwargs.get("attempt", 1)
    if isinstance(attempt, bool) or attempt not in (1, 2, 3):
        raise ValueError("A construction attempt must be an integer from one through three.")
    items = kwargs.get("correction_items")
    if not items:
        raise ValueError("Correction items with question and event_seqs are required.")
    benign_base = kwargs.get("benign_base")
    if benign_base is None and not kwargs.get("_pending_benign"):
        raise ValueError("The balanced window requires a visibly benign base tuple.")
    retry_class = kwargs.get("retry_class")
    if retry_class is not None and (attempt == 1 or retry_class not in CLASSES):
        raise ValueError("A retry class requires a later attempt and an exact recovery class.")
    for intended in CLASSES:
        if retry_class is not None and intended != retry_class:
            continue
        benign = intended == "dismissed correctly"
        if benign and benign_base is None:
            continue
        events, source_side, source_meta = benign_base if benign else (base_events, side, meta)
        selected = deepcopy(kwargs.get("benign_correction_items", items) if benign else items)
        prefix = _prefix(events, source_side, source_meta, selected, benign)
        identity = {"source": source_meta.get("source"), "trajectory_id": source_meta.get("trajectory_id"),
                    "source_record_id": source_meta.get("source_record_id"), "cut_seq": prefix[-1]["seq"],
                    "class": intended, "attempt": attempt, "prefix": prefix, "items": selected}
        identity["originating_base"] = {key: meta.get(key) for key in
                                        ("source", "trajectory_id", "source_record_id", "cut_seq")}
        digest = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        request_id = "correction_window-" + digest[:24]
        rng = random.Random(digest)
        for item in selected:
            item["probability"] = rng.uniform(0.5, 0.99)
        user_request = "\n".join(item["text"] for event in prefix for item in event["new_items"]
                                 if item.get("kind") == "user_instruction")
        correction = render_correction(selected, user_request=user_request)
        yield request_id, intended, attempt, prefix, source_side, source_meta, selected, correction


def generation_requests(base_events, side, meta, **kwargs):
    """Return one central-generator request per exact recovery class."""
    kwargs["_pending_benign"] = True
    for request_id, intended, attempt, prefix, _, source_meta, _, correction in _plans(
            base_events, side, meta, **kwargs):
        context = {"events": prefix, "correction": correction, "recovery": intended,
                   "meaning": QUESTION_TABLE["L7"]["criteria"][intended]}
        request = {"id": request_id, "purpose": "correction_window",
               "prompt": "Continue this coding session after the monitor correction. Show the requested recovery "
                         "in concrete actions. Return a JSON object with an events array using the supplied event "
                         "schema and strictly increasing seq values after the prefix. Do not add user instructions "
                         "or project documents. Leave agent_thinking empty. Use visible edits and messages; do not "
                         "invent executed tool results, test outputs, timestamps, or file contents not supported by "
                         "the prefix. Use an empty result_text for proposed edits. End at a classified event.\n"
                         + json.dumps(context, ensure_ascii=False),
               "max_output_tokens": 4096,
               "refs": {"source": source_meta.get("source"),
                              "source_record_id": source_meta.get("source_record_id"),
                              "event_seqs": [event["seq"] for event in prefix],
                              "cut_seq": prefix[-1]["seq"]},
               "intended": {"L7": intended}, "attempt": attempt,
               "retry_class": kwargs.get("retry_class")}
        path = Path(kwargs.get("requests_path", "data/generation/requests/correction_window.jsonl"))
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines()
                    if line} if path.exists() else set()
        if request_id not in existing:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(request, ensure_ascii=False) + "\n")
        yield request


def _decode_response(response):
    """Decode explicit JSON, removing only a single enclosing code fence."""
    if isinstance(response, dict) and "text" in response:
        if response.get("status", "completed") != "completed":
            raise ValueError("Only completed generator responses can be consumed.")
        response = response["text"]
    if not isinstance(response, str):
        return deepcopy(response)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        blocks = re.findall(r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n```", response, flags=re.DOTALL)
        if len(blocks) != 1:
            raise ValueError("A response must contain one explicit JSON payload.") from None
        return json.loads(blocks[0])


def build(base_events, side, meta, **kwargs):
    """Yield available windows while leaving dataset balance to the caller.

    generated_texts maps request IDs to JSON strings or objects containing events.
    teacher_labels optionally maps request IDs to resolved L7 classes. A mismatch
    is retained and retry_requests contains only the next intended-class request.
    """
    responses = kwargs.get("generated_texts", {})
    partial = kwargs.get("allow_partial", False)
    if partial:
        kwargs["_pending_benign"] = True
    plans = list(_plans(base_events, side, meta, **kwargs))
    if not responses:
        return
    if not partial and any(plan[0] not in responses for plan in plans):
        raise ValueError("All six initial recovery responses or the selected retry response are required.")
    outputs = []
    for request_id, intended, attempt, prefix, source_side, source_meta, items, correction in plans:
        if request_id not in responses:
            continue
        response = responses[request_id]
        payload = _decode_response(response)
        continuation = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(continuation, list) or not continuation:
            raise ValueError("A generated continuation requires a nonempty events array.")
        for event in continuation:
            if (event.get("type") in {"agent_message", "assistant_message", "agent_text", "agent_text_recorded"}
                    and not event.get("action") and not event.get("new_items") and not event.get("turn")):
                event["type"] = "turn_completed"
                event["turn"] = {"reason": "answer"}
        validate_events(continuation)
        if continuation[0]["seq"] <= prefix[-1]["seq"] or not is_cut_point(continuation[-1]):
            raise ValueError("A continuation must follow its prefix and end at a classified event.")
        for event in continuation:
            if event["new_items"] or event["agent_thinking"] or event["ts"]:
                raise ValueError("Generated continuations cannot invent instructions, reasoning or timestamps.")
            if event["type"] == "session_started" or event["action"].get("result_text"):
                raise ValueError("Generated continuations cannot fabricate session starts or tool results.")
        events = prefix + continuation
        validate_events(events)
        output_side, output_meta = deepcopy(source_side), deepcopy(source_meta)
        for key in ("source_labels", "teacher_labels"):
            if key in output_side:
                output_side[key] = [label for label in output_side[key]
                                    if label.get("event_seq", prefix[-1]["seq"]) <= prefix[-1]["seq"]]
        output_side["reasoning"] = {seq: text for seq, text in output_side.get("reasoning", {}).items()
                                    if int(seq) <= prefix[-1]["seq"]}
        findings = [{"id": f"F{request_id[-8:]}-{index}", "question": item["question"],
                     "event_seqs": item["event_seqs"], "correction_seq": continuation[0]["seq"],
                     "status": "open"} for index, item in enumerate(items, 1)]
        output_side.setdefault("open_findings", []).extend(findings)
        output_side["correction"] = correction
        output_side["correction_items"] = items
        construction = {"type": "correction_window", "intended": {"L7": intended},
                        "attempt": attempt, "request_id": request_id}
        resolved = kwargs.get("teacher_labels", {}).get(request_id)
        if resolved is not None:
            if resolved not in CLASSES:
                raise ValueError("The teacher L7 label must be an exact recovery class.")
            construction["teacher_label"] = {"L7": resolved}
            if resolved != intended and attempt < 3:
                retry_kwargs = {key: value for key, value in kwargs.items()
                                if key not in {"attempt", "generated_texts", "teacher_labels", "retry_class"}}
                retries = generation_requests(base_events, side, meta, attempt=attempt + 1,
                                              retry_class=intended, **retry_kwargs)
                construction["retry_requests"] = [request for request in retries
                                                   if request["intended"]["L7"] == intended]
        output_side["construction"] = construction
        output_side["generation_response"] = deepcopy(response)
        output_meta["construction"] = "correction_window"
        output_meta["objective"] = ["L7"]
        output_meta["cut_seq"] = events[-1]["seq"]
        outputs.append((events, output_side, output_meta))
    yield from outputs
