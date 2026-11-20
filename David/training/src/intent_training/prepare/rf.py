"""Turn genuine RF source annotations into window-only teacher training inputs."""

from copy import deepcopy

from monitor_format import (build_instructions, collect_documents, fill_question,
    rf_window, count_tokens, validate_record, validate_events)
from intent_training.teacher.prepare import prepare_record
from .records import metadata, prepare_native, stable_id, scan, _units


def _window_record(state, questions, meta, labels, provenance, tokenizer, budget):
    if count_tokens(state, tokenizer) > budget:
        raise ValueError("The RF window exceeds the validated state budget.")
    meta = metadata(meta)
    meta.update(cut_seq=0, record_kind="task", native_record=False,
                state_budget=budget, validated_length=budget,
                state_tokens=count_tokens(state, tokenizer), source_annotations=provenance,
                merged_cut_source_labels=labels)
    identity = {"source": meta["source"], "source_record_id": meta.get("source_record_id"),
                "state": state, "questions": questions, "annotations": labels}
    record = {"record_id": stable_id(identity), "state": state, "questions": questions, "_meta": meta}
    result = prepare_record(record, {"reasoning": {}, "source_labels": labels})
    result.update(_meta=meta, purpose="rf_training", requirement_units=[])
    scan(result)
    return result


def annotated_windows(row, tokenizer, budget=8191):
    """Use real localized annotations, without labeling unannotated units no."""
    validate_events(row["events"])
    scan(row["side"])
    seen = set()
    for annotation in row["side"].get("source_labels", []):
        if annotation.get("question", "").split("#")[0] != "RF" or annotation.get("basis") not in {"V", "visible"}:
            continue
        seq = int(annotation["event_seq"])
        visible = [event for event in row["events"] if event["seq"] <= seq]
        units = _units(build_instructions(visible), collect_documents(visible))
        annotated_unit = annotation.get("unit", {})
        text = annotation.get("requirement_text", annotated_unit.get("text"))
        position = annotation.get("unit_position", annotated_unit.get("position"))
        matches = [index for index, unit in enumerate(units)
                   if unit["text"] == text and (position is None or unit["position"] == position)
                   and (not annotated_unit.get("source") or unit["source"] == annotated_unit["source"])]
        if len(matches) != 1:
            raise ValueError("The RF annotation must identify one exact visible unit.")
        index = matches[0]
        state = rf_window(units, index)
        value = annotation["value"]
        if type(value) is not bool:
            raise ValueError("An RF source annotation requires its actual boolean value.")
        label = {"question": "RF", "value": value, "event_seq": 0,
                 "basis": "visible", "origin": annotation.get("origin", "source annotation")}
        output = _window_record(state, {"RF": fill_question("RF", tokenizer=tokenizer)},
                               row["meta"], [label], [deepcopy(annotation)], tokenizer, budget)
        if output["record_id"] not in seen:
            seen.add(output["record_id"])
            yield output


def native_task(row, tokenizer, budget=8191):
    """Require actual teacher votes for monitor tasks carried in native envelopes."""
    original = deepcopy(row["side"]["native_record"])
    validate_record(original)
    scan(row["side"])
    questions, labels = {}, []
    for key, question in original["questions"].items():
        if key.split("#")[0] != "RF" or type(question["label"]) is not bool:
            raise ValueError("Only annotated RF monitor tasks use the native task envelope.")
        questions[key] = {name: deepcopy(value) for name, value in question.items() if name not in {"label", "target"}}
        labels.append({"question": key, "value": question["label"], "event_seq": 0,
                       "basis": "visible", "origin": "original source RF annotation"})
    preserved = prepare_native(row)["_meta"]
    return _window_record(original["state"], questions, preserved, labels,
                          deepcopy(original.get("_meta", {})), tokenizer, budget)
