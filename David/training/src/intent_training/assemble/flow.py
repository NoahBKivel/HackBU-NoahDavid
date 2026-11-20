"""Prepare each dependent question pass only after its evidence is resolved."""

from copy import deepcopy

from monitor_format import EVERY_EVENT, fill_question
from intent_training.teacher import diagnostic_record, prepare_record, requirement_records

from .labels import base_question, positive, resolve_record
from .native import original_native


def assembly_context(context, *, event_required=True):
    """Retain cut evidence needed for subsequent passes without raw source payloads."""
    meta = context["_meta"]
    cut = meta["cut_seq"]
    event = next((event for event in context["events"] if event["seq"] == cut), None)
    if event is None and event_required:
        raise ValueError("The recovered context does not contain its actual cut event.")
    side = context.get("side", {})
    labels = [deepcopy(label) for label in side.get("source_labels", [])
              if label.get("basis") in {"outcome", "O"} or label.get("event_seq", cut) <= cut]
    construction = side.get("construction")
    return {"record_id": context["record_id"], "_meta": deepcopy(meta),
            "events": ([{"seq": event["seq"], "type": event["type"], "turn": deepcopy(event.get("turn", {}))}] if event else []),
            "side": {"reasoning": {str(seq): text for seq, text in side.get("reasoning", {}).items() if int(seq) <= cut},
                     "source_labels": labels, "construction": deepcopy(construction)},
            "detailed_event_seqs": deepcopy(context["detailed_event_seqs"]),
            "requirement_units": deepcopy(context.get("requirement_units", []))}


def route(record):
    """Separate native, RF windows, screens and ordinary event records."""
    if original_native(record):
        return "native"
    bases = {base_question(key) for key in record["questions"]}
    meta = record.get("_meta", {})
    if (meta.get("form") == "screen" or meta.get("record_kind") == "screen"
            or meta.get("construction") == "overflow_screen" or bases & {"SCR", "M8"}):
        if not bases <= {"SCR", "M8"}:
            raise ValueError("A screen record may contain only SCR and M8 rows.")
        sections = {}
        for key in record["questions"]:
            base, separator, section = key.partition("#")
            if not separator or not section:
                raise ValueError("Every screen row must identify its actual section.")
            sections.setdefault(section, set()).add(base)
        if any(pair != {"SCR", "M8"} for pair in sections.values()):
            raise ValueError("Every screen section requires both SCR and M8.")
        return "screen"
    if bases == {"RF"}:
        return "rf"
    return "event"


def answer_cut(record, context):
    cut = record["_meta"]["cut_seq"]
    event = next((event for event in context["events"] if event["seq"] == cut), None)
    if event is None:
        raise ValueError("The event context does not contain the actual cut.")
    return event["type"] == "turn_completed" and event.get("turn", {}).get("reason") == "answer"


def flagged(record):
    return any(positive(key, row["label"]) for key, row in record["questions"].items()
               if "~neg" not in key and base_question(key) in {*EVERY_EVENT, "G2", "G5"})


def _private(prepared, record, *, purpose=None):
    prepared = deepcopy(prepared)
    prepared["_meta"] = deepcopy(record["_meta"])
    prepared["_meta"]["record_id"] = prepared["record_id"]
    prepared["parent_meta"] = deepcopy(record["_meta"])
    if purpose:
        prepared["purpose"] = purpose
    return prepared


def selection_inputs(record, context):
    """Return auxiliary RF windows without creating quota RF training rows."""
    if route(record) != "event":
        return []
    identity = record["_meta"]["record_id"]
    return [_private(item, record, purpose="requirement_selection") for item in
            requirement_records(identity, record["_meta"]["source"], context.get("requirement_units", []))]


def resolve_requirements(record, context, votes, *, receipt_provenance=None):
    """Resolve every unit before assigning contiguous requirement identifiers."""
    accepted, audits = [], []
    for prepared in selection_inputs(record, context):
        unit_record = {"state": prepared["state"], "questions": prepared["questions"],
                       "pass": prepared["pass"], "purpose": prepared["purpose"],
                       "_meta": prepared["_meta"]}
        # Parent labels describe event questions, not an auxiliary RF window.
        unit_record["_meta"].pop("merged_cut_source_labels", None)
        resolved, audit = resolve_record(unit_record, votes.get(prepared["record_id"], {}), allocation_mode="rf_single")
        proof = (receipt_provenance or {}).get(prepared["record_id"])
        audits.append({"record_id": prepared["record_id"], **audit,
                       **({"rf_reuse": deepcopy(proof)} if proof else {})})
        if resolved["questions"]["RF"]["label"]:
            accepted.append({**deepcopy(prepared["unit"]), "id": f"R{len(accepted) + 1}",
                             "rf_record_id": prepared["record_id"], "rf_unit_id": prepared["unit_id"],
                             **({"rf_reuse": deepcopy(proof)} if proof else {})})
    return {"complete": True, "accepted": accepted, "unit_count": len(audits), "audits": audits}


def _has_all(record, keys):
    return all(key in record["questions"] and "label" in record["questions"][key] for key in keys)


def next_pass(record, context, *, requirements=None, tokenizer):
    """Return the next required pass, or a completed event-question assessment."""
    if any("label" not in row for row in record["questions"].values()):
        raise ValueError("Main labels must be resolved before preparing dependent questions.")
    kind = route(record)
    if kind != "event":
        if record.get("_meta", {}).get("main_relabel_complete") is False:
            return {"stage": "main_relabel_pending", "records": [], "route": kind}
        return {"stage": "complete", "records": [], "route": kind}
    if context is None:
        return {"stage": "context_pending", "records": [], "route": kind}
    if not set(EVERY_EVENT) <= set(record["questions"]):
        raise ValueError("An ordinary event record is missing every-event labels.")
    is_answer = answer_cut(record, context)
    if is_answer and "G5" not in record["questions"]:
        raise ValueError("An answer cut requires its resolved G5 label.")
    if not is_answer and any(base_question(key) in {"G2", "G5"} for key in record["questions"]):
        raise ValueError("G2 and G5 may be asked only at an actual answer cut.")
    needs_requirements = is_answer or any(base_question(key) == "M2" and positive(key, row["label"])
                                         for key, row in record["questions"].items())
    if needs_requirements and not context.get("requirement_units"):
        requirements = {"complete": True, "accepted": []}
    requirements_pending = needs_requirements and not (requirements and requirements.get("complete"))
    if is_answer and requirements_pending:
        return {"stage": "requirements", "records": selection_inputs(record, context), "route": kind}
    if record.get("_meta", {}).get("main_relabel_complete") is False:
        return {"stage": "main_relabel_pending", "records": [], "route": kind,
                "requirements_records": selection_inputs(record, context) if requirements_pending else []}
    accepted = requirements.get("accepted", []) if requirements else []
    side = context.get("side", {})
    if is_answer:
        expected = [f"G2#R{i}" for i in range(1, len(accepted) + 1)]
        if not _has_all(record, expected):
            rows = {key: fill_question("G2", requirement_text=unit["text"], tokenizer=tokenizer)
                    for key, unit in zip(expected, accepted) if key not in record["questions"]}
            prepared = prepare_record(dict(record, questions=rows), side, stage="main_completion")
            prepared = _private(prepared, record)
            prepared["_meta"]["requirement_bindings"] = dict(zip(expected, (unit["text"] for unit in accepted)))
            return {"stage": "main_completion", "records": [prepared], "route": kind}
    if not flagged(record):
        return {"stage": "complete", "records": [], "route": kind}
    detailed = sorted(set(context["detailed_event_seqs"]) | {record["_meta"]["cut_seq"]})
    if any(seq > record["_meta"]["cut_seq"] for seq in detailed):
        raise ValueError("A localization candidate points beyond the visible cut.")
    expected = [f"D1#E{seq}" for seq in detailed] + ["D5"]
    if not _has_all(record, expected):
        prepared = diagnostic_record(record, side, stage="localization", detailed_event_seqs=detailed,
                                     requirements=accepted, tokenizer=tokenizer)
        prepared["questions"] = {key: row for key, row in prepared["questions"].items() if key not in record["questions"]}
        return {"stage": "localization", "records": [_private(prepared, record)], "route": kind,
                "requirements_records": selection_inputs(record, context) if requirements_pending else []}
    needs_d2 = any(base_question(key) in {"M2", "G2"} and positive(key, row["label"])
                   for key, row in record["questions"].items())
    expected = [f"D2#R{i}" for i in range(1, len(accepted) + 1)] if needs_d2 else []
    if needs_d2 and requirements_pending:
        return {"stage": "requirements", "records": selection_inputs(record, context), "route": kind}
    if not _has_all(record, expected):
        localized = [int(key.split("#E", 1)[1]) for key, row in record["questions"].items()
                     if key.startswith("D1#E") and row["label"]]
        prepared = diagnostic_record(record, side, stage="requirements_diagnostic", detailed_event_seqs=detailed,
            requirements=accepted, localized_event_seqs=localized, tokenizer=tokenizer)
        prepared["questions"] = {key: row for key, row in prepared["questions"].items() if key not in record["questions"]}
        prepared = _private(prepared, record)
        prepared["_meta"]["requirement_bindings"] = dict(zip(expected, (unit["text"] for unit in accepted)))
        return {"stage": "requirements_diagnostic", "records": [prepared], "route": kind}
    return {"stage": "complete", "records": [], "route": kind}


def merge_pass(record, prepared, votes, *, context):
    """Merge a resolved dependent pass without changing the state or prior labels."""
    identity = record["_meta"]["record_id"]
    if prepared["record_id"] != identity or prepared["state"] != record["state"]:
        raise ValueError("A dependent pass differs from its parent identity or state.")
    stage_record = {"state": prepared["state"], "questions": prepared["questions"],
                    "_meta": deepcopy(record["_meta"])}
    stage_record["_meta"]["requirement_bindings"] = deepcopy(prepared.get("_meta", {}).get("requirement_bindings", {}))
    result, audit = resolve_record(stage_record, votes, source_labels=prepared.get("teacher_side", {}).get("source_labels", []),
                                   construction=context.get("side", {}).get("construction"))
    merged = deepcopy(record)
    for key, row in result["questions"].items():
        if key in merged["questions"] and merged["questions"][key] != row:
            raise ValueError("A dependent pass attempts to replace an already resolved question.")
        merged["questions"][key] = row
    merged["_meta"].setdefault("teacher_vote_families", {}).update(result["_meta"].get("teacher_vote_families", {}))
    merged["_meta"].setdefault("completed_question_passes", []).append(prepared["pass"])
    return merged, audit
