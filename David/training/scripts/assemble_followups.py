"""Advance verified parent records through their completed dependent label passes."""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.assemble.flow import assembly_context, merge_pass, next_pass, resolve_requirements, selection_inputs
from intent_training.assemble.flow import route
from intent_training.assemble.labels import positive
from intent_training.assemble.instruments import policy_instruments, combine_instruments
from intent_training.assemble.rf_reuse import load_fanout, reuse
from intent_training.assemble.relabel import OnceRelabel
from intent_training.assemble.stream import queue_votes, queue_tasks
from intent_training.assemble.receipts import canonical_payload, _receipt
from intent_training.teacher.dispatch import digest
from intent_training.teacher.claims import batch_claim_path, validated_rf_slots
from intent_training.prepare.records import load_tokenizer
from intent_training.teacher.vote_allocation import required_families, rf_quorum_slots


def rows(path):
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def atomic_rows(path, values):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def joined(collection, identity):
    result = {}
    for family, answers in collection["votes"].get(identity, {}).items():
        for key, value in answers.items():
            result.setdefault(key, {})[family] = value
    return result


def ready(collection, prepared, *, claims_dir=None, repository=None):
    claims_dir = Path(claims_dir or ROOT / "data/votes/claims")
    repository = Path(repository or ROOT.parents[1])
    identity = prepared["record_id"]
    expected_hash = digest(canonical_payload(prepared))
    variant = collection.get("variants", {}).get(identity, {}).get(expected_hash)
    if variant and not variant["blocked"]:
        for key in ("prepared", "votes", "origins"):
            collection[key][identity] = variant[key]
        collection["blocked"].discard(identity)
    if prepared.get("purpose") == "requirement_selection" and reuse(collection, prepared,
            claims_dir=claims_dir, repository=repository):
        return True
    if prepared.get("purpose") == "requirement_selection":
        if identity in collection["blocked"] or variant is None or variant["blocked"]:
            return False
        valid, origins = {}, {}
        for slot in rf_quorum_slots(canonical_payload(prepared), variant["votes"]):
            origin = variant["origins"][slot]
            batch = collection["batches"][(origin["batch_id"], origin["input_sha256"])]
            output = Path(origin["output"])
            cache = collection.setdefault("validated_rf_claim_cache", {})
            cache_key = (batch["batch_id"], batch["input_sha256"], slot, str(output))
            if cache_key not in cache:
                try:
                    claim = json.loads(batch_claim_path(claims_dir, batch).read_text(encoding="utf-8"))
                    proof = _receipt(batch, slot, output, claims_dir, repository)
                    cache[cache_key] = proof[1] if proof and slot in validated_rf_slots(claims_dir, batch, claim) else None
                except (OSError, ValueError, KeyError, TypeError):
                    cache[cache_key] = None
            if cache[cache_key] is not None:
                valid[slot] = variant["votes"][slot]
                origins[slot] = {**origin, **cache[cache_key]}
        if not valid:
            return False
        collection["votes"][identity] = valid
        collection["origins"][identity] = origins
        collection.setdefault("reuse_provenance", {})[identity] = {
            "kind": "direct", "canonical_record_id": identity,
            "canonical_record_sha256": expected_hash, "receipts": deepcopy(origins)}
        return True
    if identity in collection["blocked"] or not set(required_families(prepared)) <= set(collection["votes"].get(identity, {})):
        return False
    actual = collection["prepared"].get(identity)
    if actual is None:
        return False
    if digest(canonical_payload(actual)) != expected_hash:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolved", type=Path, required=True)
    parser.add_argument("--context", type=Path, nargs="+", required=True)
    parser.add_argument("--context-proof", type=Path, nargs="*", default=[])
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--main-instruments", type=Path)
    parser.add_argument("--rf-fanout", type=Path, nargs="*", default=[])
    parser.add_argument("--d2-relabel-queue", type=Path)
    parser.add_argument("--d2-relabel-ledger", type=Path, default=ROOT / "data/votes/results/teacher/relabel_ledger.json")
    parser.add_argument("--d2-relabel-cohort", type=Path, default=ROOT / "data/assembly/limit-8191/paired-d2-initial-cohort")
    args = parser.parse_args()
    d2_relabel = (OnceRelabel(queue=args.d2_relabel_queue, ledger=args.d2_relabel_ledger,
        cohort=args.d2_relabel_cohort, base_pass="requirements_diagnostic", questions={"D2"})
        if args.d2_relabel_queue else None)
    records = list(rows(args.resolved))
    by_id = {record["_meta"]["record_id"]: record for record in records}
    proof = {row["record_id"]: row for path in args.context_proof for row in rows(path)}
    contexts, errors = {}, []
    for path in args.context:
        for context in rows(path):
            identity = context["record_id"]
            if identity not in proof and identity not in by_id:
                continue
            reference = by_id.get(identity, proof.get(identity))
            is_rf = {key.split("#", 1)[0] for key in reference["questions"]} == {"RF"}
            try:
                candidate = assembly_context(context, event_required=not is_rf)
            except (ValueError, KeyError, TypeError) as error:
                errors.append({"record_id": identity, "error": str(error)})
                continue
            if identity in proof and identity in by_id and proof[identity]["state"] != by_id[identity]["state"]:
                errors.append({"record_id": identity, "error": "Recovered context has a different frozen parent state."})
                continue
            construction = candidate["side"].get("construction")
            if construction and construction.get("type"):
                candidate["_meta"]["construction"] = construction["type"]
            contexts[identity] = candidate
    stages = ("requirements", "main_completion", "localization", "requirements_diagnostic")
    collections = {stage: queue_votes(args.queue, passes={stage}) for stage in stages}
    collections["requirements"]["rf_aliases"] = load_fanout(args.rf_fanout)
    known = {stage: set() for stage in (*stages, "main")}
    known_payloads = {stage: set() for stage in (*stages, "main")}
    for task in queue_tasks(args.queue):
        stage = task["batch"]["pass"]
        if stage in known:
            known[stage].update(row["record_id"] for row in task["batch"]["records"])
            known_payloads[stage].update(digest(canonical_payload(row)) for row in task["batch"]["records"])
    tokenizer = load_tokenizer(ROOT / "data/tokenizer")
    pending, status, accepted, audits, complete, updated = defaultdict(list), Counter(), {}, [], [], []
    measured_records, measured_votes = {}, defaultdict(dict)
    rf_priority_parents = {}
    def observed_ready(stage, prepared):
        if not ready(collections[stage], prepared):
            return False
        identity = prepared["record_id"]
        measured_identity = collections[stage].get("reuse_provenance", {}).get(identity, {}).get("canonical_record_id", identity)
        measured_records[(measured_identity, stage)] = {"record_id": measured_identity, "questions": prepared["questions"],
            "_meta": prepared["_meta"], **{key: prepared[key] for key in ("pass", "purpose") if key in prepared}}
        measured_votes[measured_identity].update(joined(collections[stage], identity))
        return True
    def rf_ready(units, record):
        present = [observed_ready("requirements", unit) for unit in units]
        missing = [unit for unit, found in zip(units, present) if not found]
        identity = record["_meta"]["record_id"]
        if missing:
            aliases = collections["requirements"]["rf_aliases"]
            canonicals = sorted({aliases.get(unit["record_id"], {}).get("canonical_record_id", unit["record_id"])
                                 for unit in missing})
            rf_priority_parents[identity] = {"record_id": identity, "source": record["_meta"]["source"],
                "reason": "actual_answer_or_M2_positive", "unit_count": len(units),
                "missing_unit_rows": len(missing), "missing_canonical_decisions": len(canonicals),
                "canonical_record_ids": canonicals, "objective": record["_meta"].get("objective", [])}
        return not missing
    for original in records:
        record = deepcopy(original)
        identity = record["_meta"]["record_id"]
        context = contexts.get(identity)
        requirements = None
        try:
            # Frozen main envelopes already contain the exact RF units and neighbouring text.
            # Their RF selection can progress while event-detail context is still in transit.
            if context is None and identity in proof and "requirement_units" in proof[identity]:
                needs_rf = "G5" in record["questions"] or any(
                    key.split("#", 1)[0] == "M2" and positive(key, row["label"])
                    for key, row in record["questions"].items())
                if needs_rf:
                    frozen_units = {"requirement_units": proof[identity]["requirement_units"]}
                    units = selection_inputs(record, frozen_units)
                    if rf_ready(units, record):
                        unit_votes = {unit["record_id"]: joined(collections["requirements"], unit["record_id"]) for unit in units}
                        requirements = resolve_requirements(record, frozen_units, unit_votes,
                            receipt_provenance=collections["requirements"].get("reuse_provenance"))
                        accepted[identity] = {"record_id": identity, **requirements}
                    else:
                        for unit in units:
                            if digest(canonical_payload(unit)) not in known_payloads["requirements"]:
                                pending["requirements"].append(unit)
            if context:
                record["_meta"].update(context["_meta"])
                record["_meta"]["record_id"] = identity
                record["_meta"]["assembly_context_available"] = True
            first = next_pass(record, context, tokenizer=tokenizer)
            units = first["records"] if first["stage"] == "requirements" else first.get("requirements_records", [])
            if units:
                if rf_ready(units, record):
                    unit_votes = {unit["record_id"]: joined(collections["requirements"], unit["record_id"]) for unit in units}
                    requirements = resolve_requirements(record, context, unit_votes,
                        receipt_provenance=collections["requirements"].get("reuse_provenance"))
                    accepted[identity] = {"record_id": identity, **requirements}
            for _ in range(4):
                step = next_pass(record, context, requirements=requirements, tokenizer=tokenizer)
                stage = step["stage"]
                for unit in step.get("requirements_records", []):
                    if digest(canonical_payload(unit)) not in known_payloads["requirements"]:
                        pending["requirements"].append(unit)
                if stage in {"main_completion", "localization", "requirements_diagnostic"} and observed_ready(stage, step["records"][0]):
                    prepared = step["records"][0]
                    answers = joined(collections[stage], identity)
                    relabel_origins = {}
                    if stage == "requirements_diagnostic" and d2_relabel:
                        answers, relabel_status, relabel_origins = d2_relabel.votes_for(prepared, answers,
                            claims_dir=ROOT / "data/votes/claims", repository=ROOT.parents[1])
                        if relabel_status in {"pending", "stale_body"}:
                            status["requirements_diagnostic_relabel_pending"] += 1
                            break
                        if relabel_status == "applied":
                            measured_votes[identity].update(answers)
                    record, audit = merge_pass(record, prepared, answers, context=context)
                    audits.append({"record_id": identity, "pass": stage, **audit})
                    record["_meta"].setdefault("question_pass_origins", {})[stage] = collections[stage]["origins"].get(identity, {})
                    if relabel_origins:
                        record["_meta"]["question_pass_origins"][stage] = relabel_origins
                    continue
                status[stage] += 1
                if stage == "complete":
                    complete.append(record)
                for prepared in step["records"]:
                    if digest(canonical_payload(prepared)) not in known_payloads.get(stage, set()):
                        pending[stage].append(prepared)
                break
            updated.append(record)
        except (ValueError, KeyError, TypeError) as error:
            errors.append({"record_id": identity, "error": str(error)})
            updated.append(record)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_rows(args.output_dir / "rf-priority-parents.jsonl", sorted(rf_priority_parents.values(),
        key=lambda row: (row["missing_canonical_decisions"], row["unit_count"], row["record_id"])))
    auxiliary_instruments = policy_instruments(measured_records.values(), measured_votes)
    (args.output_dir / "policy-instruments-auxiliary.json").write_text(json.dumps(auxiliary_instruments, indent=2) + "\n", encoding="utf-8")
    if args.main_instruments:
        main_instruments = json.loads(args.main_instruments.read_text(encoding="utf-8"))
        combined = combine_instruments(main_instruments, auxiliary_instruments)
        (args.output_dir / "policy-instruments-all-passes.json").write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
    atomic_rows(args.output_dir / "context-ready.jsonl", contexts.values())
    atomic_rows(args.output_dir / "main-with-followups.jsonl", updated)
    atomic_rows(args.output_dir / "requirements-accepted.jsonl", accepted.values())
    atomic_rows(args.output_dir / "complete-before-admission.jsonl", complete)
    for stage in stages:
        atomic_rows(args.output_dir / (stage + "-additional-pending.jsonl"), pending.get(stage, []))
    # Publish eligible ordinary main inputs only after actual construction context is joined.
    unlabelled, held = [], Counter()
    if args.context_proof:
        for identity, prepared in proof.items():
            if identity in by_id or identity in known["main"]:
                continue
            context = contexts.get(identity)
            if not context:
                held["context_pending"] += 1
                continue
            prepared = deepcopy(prepared)
            prepared["_meta"] = deepcopy(context["_meta"])
            try:
                route(prepared)
            except ValueError:
                held["invalid_screen_route"] += 1
                continue
            unlabelled.append(prepared)
        atomic_rows(args.output_dir / "main-additional-pending.jsonl", unlabelled)
    report = {"observed_at_utc": datetime.now(timezone.utc).isoformat(), "resolved_parent_records": len(records),
              "resolved_question_rows": sum(len(record["questions"]) for record in updated),
              "context_available_records": sum(identity in contexts for identity in by_id),
              "accepted_requirement_parent_records": len(accepted), "accepted_requirement_units": sum(len(value["accepted"]) for value in accepted.values()),
              "completed_dependent_passes_merged": len(audits), "status_records": dict(status),
              "additional_pending_model_records": {stage: len(pending.get(stage, [])) for stage in stages},
              "additional_main_model_records": len(unlabelled), "held_unlabelled_main": dict(held),
              "complete_before_actual_encoder_admission": len(complete), "errors": errors,
              "vote_validation_errors": {stage: value["errors"] for stage, value in collections.items()},
              "freeze_ready": False}
    (args.output_dir / "followup-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    atomic_rows(args.output_dir / "followup-resolution-audit.jsonl", audits)
    print(json.dumps({key: value for key, value in report.items() if key not in {"errors", "vote_validation_errors"}}))
    print(json.dumps({"errors": len(errors), "vote_validation_errors": {key: len(value) for key, value in report["vote_validation_errors"].items()}}))


if __name__ == "__main__":
    main()
