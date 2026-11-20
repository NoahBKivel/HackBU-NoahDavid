"""Restrict teacher evidence to the rendered cut and build ordered diagnostics."""

from copy import deepcopy
from monitor_format import fill_question, rf_window, diagnostic_summary, EVERY_EVENT


def prepare_record(record, side=None, *, stage="main"):
    """Remove labels, construction intentions and all future side information."""
    meta = record["_meta"]
    record_id = record.get("record_id", meta.get("record_id"))
    if not record_id:
        raise ValueError("A stable record_id is required before teacher dispatch.")
    cut = int(meta["cut_seq"])
    questions = {}
    for key, row in record["questions"].items():
        if "~neg" in key:
            continue
        base = key.split("#")[0]
        diagnostic = base in {"D1", "D2", "D3", "D5"}
        if stage == "main" and diagnostic:
            continue
        questions[key] = {k: deepcopy(v) for k, v in row.items() if k not in {"label", "target"}}
    side = side or {}
    labels = []
    for label in side.get("source_labels", []):
        if label.get("basis") == "outcome" or int(label["event_seq"]) <= cut:
            labels.append({k: deepcopy(label[k]) for k in
                           ("question", "value", "event_seq", "basis", "origin", "requirement_text") if k in label})
    return {"record_id": str(record_id), "state": record["state"], "questions": questions,
            "source": meta["source"], "pass": stage,
            "teacher_side": {"reasoning": {str(seq): text for seq, text in side.get("reasoning", {}).items()
                                            if int(seq) <= cut}, "source_labels": labels}}


def requirement_records(record_id, source, units):
    """Create RF selection votes whose answers define requirements without adding training rows."""
    return [{"record_id": f"{record_id}:unit:{i + 1}", "parent_record_id": record_id,
             "unit_id": f"R{i + 1}", "purpose": "requirement_selection",
             "unit": deepcopy(unit), "source": source, "pass": "requirements",
             "state": rf_window(units, i), "questions": {"RF": fill_question("RF")},
             "teacher_side": {"reasoning": {}, "source_labels": []}}
            for i, unit in enumerate(units)]


def positive(key, label):
    """Identify the positive class from resolved labels, including whole-run polarity."""
    base = key.split("#")[0]
    if base == "G1":
        return label is False
    if base == "G2":
        return label in {"broken", "not done"}
    return label is True


def diagnostic_record(record, side, *, stage, detailed_event_seqs, requirements=(),
                      localized_event_seqs=(), tokenizer=None, localization_question="D1"):
    """Build diagnostics only after their prerequisite labels have been resolved."""
    questions = record["questions"]
    fired = [key for key, row in questions.items()
             if key.split("#")[0] in {*EVERY_EVENT, "G2", "G5"}
             and "~neg" not in key and positive(key, row["label"])]
    if not fired:
        return None
    rows = {}
    if stage == "localization":
        if localization_question not in {"D1", "D3"}:
            raise ValueError("Localization questions must use D1 or D3.")
        for seq in detailed_event_seqs:
            rows[f"{localization_question}#E{seq}"] = fill_question(
                localization_question, fired_questions=fired, event_seq=seq, tokenizer=tokenizer)
        rows["D5"] = fill_question("D5", tokenizer=tokenizer)
    elif stage == "requirements_diagnostic":
        if not any(key.split("#")[0] in {"M2", "G2"} for key in fired):
            return None
        seqs = list(localized_event_seqs) or [int(record["_meta"]["cut_seq"])]
        summary = diagnostic_summary(fired, seqs)
        for i, requirement in enumerate(requirements, 1):
            rows[f"D2#R{i}"] = fill_question("D2", requirement_text=requirement["text"],
                                             summary=summary, tokenizer=tokenizer)
    else:
        raise ValueError("The diagnostic stage is unsupported.")
    if not rows:
        return None
    enriched = dict(record, questions=rows)
    return prepare_record(enriched, side, stage=stage)
