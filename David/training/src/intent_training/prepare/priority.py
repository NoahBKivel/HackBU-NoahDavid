"""Render a bounded real-input packet and publish each admitted teacher record."""

from copy import deepcopy
import json
import os
from pathlib import Path

from monitor_format import count_tokens
from intent_training.teacher.claims import teacher_input_hash
from intent_training.teacher.vote_allocation import allocation, required_families
from .cuts import plan_cuts
from .records import load_tokenizer, prepare_stream, prepare_native, scan
from .rf import annotated_windows, native_task


def teacher_payload(record):
    """Return exactly the fields authorized for the frozen model-visible payload."""
    visible = {key: deepcopy(record[key]) for key in
               ("record_id", "state", "questions", "source", "pass", "teacher_side", "purpose", "row_context")
               if key in record}
    visible["questions"] = {key: {name: value for name, value in row.items()
                                  if name not in {"label", "target"}}
                            for key, row in visible["questions"].items()}
    return visible


def run(inputs, output, tokenizer_dir, *, budget=8191, limit=30, screen_budget=8192, emit_first=3):
    """Rerender actual streams at the supplied budget, without reading old states."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    provenance = []
    errors = []
    registry = Path(__file__).resolve().parents[1] / "sources" / "entries"
    declared = {json.loads(path.read_text(encoding="utf-8-sig"))["slug"] for path in registry.glob("*.json")}
    for path in map(Path, inputs):
        with path.open(encoding="utf-8-sig") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    if row["meta"]["source"] in {"quality_long", "policy_long"}:
                        continue
                    if row["meta"]["source"] not in declared:
                        raise ValueError("The source is absent from the canonical source registry.")
                    rows.append(row)
                    provenance.append({"input": path.name, "line": number})
                except Exception as error:
                    errors.append({"input": path.name, "line": number, "error": str(error)[:200]})
    cuts = plan_cuts(rows)
    tokenizer = load_tokenizer(Path(tokenizer_dir))
    collected = {name: [] for name in ("main", "native", "requirements", "context")}
    seen = set()
    for name in collected:
        existing = output / f"{name}.jsonl"
        if existing.exists():
            with existing.open(encoding="utf-8") as handle:
                collected[name] = [json.loads(line) for line in handle if line.strip()]
    seen.update(record["record_id"] for record in collected["main"])
    native_seen = {record["record_id"] for record in collected["native"]}

    def publish(final=False):
        for name, records in collected.items():
            if not final and name not in {"main", "native", "context"}:
                continue
            destination = output / f"{name}.jsonl"
            temporary = destination.with_suffix(".jsonl.tmp")
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                for record in records:
                    handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            os.replace(temporary, destination)
        report = {"counts": {key: len(value) for key, value in collected.items()},
                  "input_rows": len(rows), "state_budget": budget, "screen_budget": screen_budget,
                  "validated_length": budget, "errors": errors, "complete": False,
                  "source_snapshot": provenance, "historical_states_reused": 0,
                  "label_authorization": "root_confirmed", "freeze_allowed": False}
        temporary = output / "manifest.json.tmp"
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, output / "manifest.json")
        controls = {}
        for context in collected["context"]:
            try:
                controls[context["record_id"]] = {"allocation": allocation(context),
                    "required_families": list(required_families(context))}
            except ValueError as error:
                controls[context["record_id"]] = {"blocked": str(error)}
        temporary = output / "allocation_by_record_id.json.tmp"
        temporary.write_text(json.dumps(controls, sort_keys=True), encoding="utf-8")
        os.replace(temporary, output / "allocation_by_record_id.json")
        return report

    def admit(record, context):
        if record["record_id"] in seen:
            return
        if count_tokens(record["state"], tokenizer) > budget:
            raise ValueError("The prepared state exceeds its actual BPE budget.")
        scan(record)
        record["_meta"]["validated_length"] = budget
        record["_meta"]["teacher_input_sha256"] = teacher_input_hash(teacher_payload(record))
        for directory, value in (("records", record), ("contexts", context)):
            destination = output / directory
            destination.mkdir(exist_ok=True)
            temporary = destination / f"{record['record_id']}.json.tmp"
            temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            os.replace(temporary, destination / f"{record['record_id']}.json")
        collected["main"].append(record)
        collected["context"].append(context)
        seen.add(record["record_id"])
        if len(collected["main"]) <= 16 or len(collected["main"]) % 25 == 0:
            publish()
        if len(collected["main"]) <= emit_first:
            print(json.dumps({"kind": "prepared_teacher_input", "payload": teacher_payload(record),
                              "input_sha256": record["_meta"]["teacher_input_sha256"]}, ensure_ascii=False), flush=True)
        print(json.dumps({"prepared": len(collected["main"]), "record_id": record["record_id"],
                          "source": record["source"], "state_tokens": record["_meta"].get("state_tokens"),
                          "questions": list(record["questions"])}), flush=True)

    for index, row in enumerate(rows):
        if limit and len(collected["main"]) >= limit:
            break
        try:
            if row["meta"].get("objective") == ["RF"] and "native_record" not in row["side"]:
                for record in annotated_windows(row, tokenizer, budget):
                    if limit and len(collected["main"]) >= limit:
                        break
                    admit(record, {"record_id": record["record_id"], "_meta": record["_meta"],
                                   "events": row["events"], "side": row["side"],
                                   "detailed_event_seqs": [], "requirement_units": []})
                continue
            if not row["events"] and "native_record" in row["side"]:
                if row["meta"].get("objective"):
                    record = native_task(row, tokenizer, budget)
                    admit(record, {"record_id": record["record_id"], "_meta": record["_meta"],
                                   "events": [], "side": row["side"], "detailed_event_seqs": [], "requirement_units": []})
                else:
                    native = prepare_native(row)
                    if native["record_id"] in native_seen:
                        continue
                    if count_tokens(native["state"], tokenizer) > budget:
                        raise ValueError("An original replay state exceeds the native state budget.")
                    native["_meta"].update(state_budget=budget, validated_length=budget)
                    collected["native"].append(native)
                    native_seen.add(native["record_id"])
                    publish()
                    print(json.dumps({"native_prepared": len(collected["native"]),
                                      "record_id": native["record_id"]}), flush=True)
                continue
            selected = cuts[index][:1] if limit or row["side"].get("construction") else cuts[index]
            for cut in selected:
                records, requirements, contexts = prepare_stream(row, cut, tokenizer, budget, screen_budget)
                for record, context in zip(records, contexts):
                    if limit and len(collected["main"]) >= limit:
                        break
                    if record["record_id"] in seen:
                        continue
                    collected["requirements"].extend(item for item in requirements
                                                     if item["parent_record_id"] == record["record_id"])
                    admit(record, context)
        except Exception as error:
            errors.append(dict(provenance[index], error_type=type(error).__name__, error=str(error)[:200]))
            print(json.dumps({"rejected": provenance[index], "error_type": type(error).__name__, "error": str(error)[:200]}), flush=True)
    report = publish(final=True)
    print(json.dumps({"kind": "preparation_manifest", "manifest": report}, ensure_ascii=False), flush=True)
    return report
