"""Validate real frozen rows, scan their serialized bytes and publish manifests."""

from collections import Counter
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

from intent_training.assemble.balance import question_counts
from intent_training.assemble.labels import record_digest, validate_twins
from intent_training.assemble.native import original_native
from intent_training.assemble.quality import receipt_holds, record_held, relabel_requirements, relabel_pending
from .grouping import assert_split_integrity
from .planning import TRAIN_RECORDS, REPLAY_RECORDS, LONG_RECORDS, SCREEN_RECORDS
from .teacher_fallback import teacher_passed, verify_teacher_fallback
from .reservations import load_reservations, reserved

EVAL_ONLY = frozenset({"mmlu", "emotion", "tweet_offensive", "qnli", "paws", "sciq",
                       "contrastive", "legacy_holdout", "composition_holdout"})
HELDOUT = frozenset({"trace", "llmbar", "rewardbench2", "rewardbench_2", "ifbench_test",
                    "aspi", "userintentbench", "malt", "ifeval", "jevany", "jeva_eval",
                    "patronusai/trace", "patronusai/trace-dataset", "mt-bench", "hi-l-bench", "recap", "mtac-ifbench",
                    "cuad", "schema-guided-dialogue", "contractnli", "facebook/hackbench",
                    "scaleai/mrt", "mjkenney/cot-monitor-robustness", "ameek", "patronusai/trail",
                    "scaleai/aspi", "ifbench", "heldout-intent-probe"})
UNUSED = frozenset({"hewittlab", "oliverdk", "dang-w", "stepguard", "toolprmbench", "funes",
                   "davanstrien", "crispwisp", "rlvr-ifeval", "agentrx", "maud", "swe-gym",
                   "agentglass", "nebius", "agentlogs", "pi_sessions", "devgpt", "skywork-80k",
                   "prism", "uss", "webdev_arena", "jevagentharness", "sengim", "lucabaroni",
                   "rh-bench", "followbench", "complexbench", "handbook", "reqclarifybench",
                   "swe-clarify", "mast", "humanevalcomm", "clarifycodebench", "codeclarqa",
                   "lost_in_conversation", "arena_55k", "arena_100k", "helpsteer2", "ultrafeedback",
                   "specbench", "agent-reward-bench"})
FLOOR_EXEMPT = frozenset({"SCR", "M8", "D1", "D2", "D3", "D5", "L7"})


def _excluded(meta):
    normalize = lambda value: re.sub(r"[^a-z0-9]", "", str(value).split("@", 1)[0].lower())
    forbidden = {normalize(value) for value in EVAL_ONLY | HELDOUT | UNUSED}
    fields = ("source", "dataset", "source_dataset", "origin_dataset", "original_source", "repo")
    identities = [meta[field] for field in fields if meta.get(field)]
    for provenance in meta.get("source_provenance", []):
        if isinstance(provenance, dict):
            identities.extend(provenance[field] for field in fields if provenance.get(field))
    return meta.get("heldout") or meta.get("demo") or any(normalize(value) in forbidden for value in identities)


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _serialized(records):
    return b"".join(_json_bytes(record) + b"\n" for record in records)


def scan_records(splits, *, scanner):
    """Call the actual credential scanner over every serialized record byte."""
    with tempfile.TemporaryDirectory(prefix="intent-record-scan-") as folder:
        paths = []
        for name, records in splits.items():
            path = Path(folder) / (name + ".jsonl")
            path.write_bytes(_serialized(records))
            paths.append(path)
        command = [sys.executable, str(scanner), *map(str, paths)]
        process = subprocess.run(command, capture_output=True, text=True, check=False)
        return {"passed": process.returncode == 0, "returncode": process.returncode,
                "rows_scanned": sum(map(len, splits.values())),
                "scanner_sha256": hashlib.sha256(Path(scanner).read_bytes()).hexdigest(),
                "output": process.stdout.strip(), "error": process.stderr.strip()}


def build_manifest(splits, *, preregistration, instruments, balance_metrics, scanner,
                   input_paths=(), composition=None, teacher_fallbacks=None):
    """Collect measured counts and gates without writing frozen split artifacts."""
    failures = []
    owner_resolved_scope = bool(composition and composition.get("owner_resolved_main_scope"))
    holds = receipt_holds()
    retry_requirements = relabel_requirements()
    reservations = load_reservations()
    integrity = assert_split_integrity(splits)
    train = splits.get("train", [])
    if any(reserved(record, reservations) for record in train):
        raise ValueError("A dev-reserved task or trajectory entered the training split.")
    admission = {"records": 0, "admitted": 0, "pending": []}
    for records in splits.values():
        for record in records:
            meta = record.get("_meta", {})
            if record_held(record, holds):
                failures.append("receipt_hold:" + str(meta.get("record_id", record.get("record_id"))))
            if relabel_pending(record, retry_requirements) and not owner_resolved_scope:
                failures.append("main_relabel:" + str(meta.get("record_id", record.get("record_id"))))
            admission["records"] += 1
            if meta.get("dependent_questions_complete") and meta.get("encoder_admitted"):
                admission["admitted"] += 1
            else:
                identity = meta.get("record_id", record.get("record_id", record_digest(record)))
                admission["pending"].append(identity)
                failures.append("admission:" + str(identity))
            if meta.get("source_label_conflicts") or meta.get("blocked_for_source_label_conflict"):
                raise ValueError("Conflicting visible source labels block the data freeze.")
            if _excluded(meta):
                raise ValueError("An evaluation-only or held-out source entered the training pool.")
            if not record.get("questions"):
                raise ValueError("A frozen record has no question rows.")
            if not original_native(record):
                validate_twins(record)
            if any("label" not in row for row in record["questions"].values()):
                raise ValueError("A frozen question row has no resolved label.")
    counts = {name: question_counts(records) for name, records in splits.items()}
    floors = {}
    for key, floor in preregistration["floors"].items():
        if key in FLOOR_EXEMPT or "~neg" in key:
            continue
        observed = counts.get("train", {}).get(key, {}).get("positives", 0)
        floors[key] = {"required": floor, "observed": observed, "passed": observed >= floor}
        if observed < floor:
            failures.append("positive_floor:" + key)
    required_questions = {key.split("#", 1)[0] for record in train
                          if not original_native(record)
                          for key in record["questions"] if "~neg" not in key}
    for key in sorted(required_questions - FLOOR_EXEMPT - set(preregistration["floors"])):
        failures.append("missing_preregistered_floor:" + key)
    agreement = {}
    verified_fallbacks = {}
    for key in sorted(required_questions):
        item = instruments.get(key)
        if not item or item.get("total_rows", item.get("rows", 0)) <= 0:
            failures.append("missing_teacher_instrument:" + key)
            continue
        passed = teacher_passed(key, item)
        agreement[key] = {**item, "passed": passed}
        if not passed:
            evidence = (teacher_fallbacks or {}).get(key)
            if evidence:
                verified_fallbacks[key] = verify_teacher_fallback(key, evidence, item)
                agreement[key]["fallback_verified"] = True
            elif owner_resolved_scope:
                agreement[key]["owner_accepted_original_resolved_labels"] = True
            else:
                failures.append("teacher_agreement:" + key)
    expected = {"train": TRAIN_RECORDS, "replay": REPLAY_RECORDS,
                "long": LONG_RECORDS, "screen": SCREEN_RECORDS}
    if composition is not None:
        # Explicit caller-supplied amendments must carry their concrete fallback evidence.
        if not composition.get("fallback_evidence"):
            raise ValueError("Amended composition needs its specified fallback evidence.")
        expected = composition["expected"]
    measured = Counter(record.get("_meta", {}).get("record_kind", "task") for record in train)
    measured["train"] = len(train)
    for kind, count in expected.items():
        if measured[kind] != count:
            failures.append("composition:" + kind)
    secrets = scan_records(splits, scanner=scanner)
    if not secrets["passed"]:
        failures.append("secrets_scan")
    files = {}
    for path in input_paths:
        path = Path(path)
        files[str(path)] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
    serialized = {name: _serialized(records) for name, records in splits.items()}
    return {"passed": not failures, "failures": failures, "counts": counts,
            "record_counts": {name: len(records) for name, records in splits.items()},
            "source_counts": {name: dict(Counter(r.get("_meta", {}).get("source") for r in records))
                              for name, records in splits.items()},
            "composition": {"expected": expected, "measured": dict(measured)},
            "pair_integrity": integrity, "positive_floors": floors,
            "admission": admission,
            "teacher_instruments": agreement, "secrets_scan": secrets,
            "reported_teacher_failures": verified_fallbacks,
            "balance": balance_metrics, "preregistration_sha256": record_digest(preregistration),
            "inputs": files, "outputs": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                                           for name, data in serialized.items()},
            "base_dev_prevalence": counts.get("base_dev", {})}


def freeze(splits, *, manifest, directory, authorized=False):
    """Write approved bytes once, only after every measured gate passes."""
    if not authorized:
        raise PermissionError("The root orchestrator must authorize the data freeze after the gates.")
    if not manifest.get("passed"):
        raise ValueError("The data gates have not passed.")
    holds = receipt_holds()
    retry_requirements = relabel_requirements()
    if any(relabel_pending(record, retry_requirements) for records in splits.values() for record in records):
        raise ValueError("A selected initial-cohort parent still needs its authorized main relabel.")
    reservations = load_reservations()
    if any(reserved(record, reservations) for record in splits.get("train", [])):
        raise ValueError("A dev-reserved task or trajectory entered the training split.")
    if any(record_held(record, holds) for records in splits.values() for record in records):
        raise ValueError("A required teacher receipt is held for explicit quality review.")
    payloads = {name + ".jsonl": _serialized(records) for name, records in splits.items()}
    for name, records in splits.items():
        actual = hashlib.sha256(payloads[name + ".jsonl"]).hexdigest()
        if actual != manifest["outputs"][name]["sha256"]:
            raise ValueError("The rows changed after the data gates ran.")
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    payloads["manifest.json"] = _json_bytes(manifest) + b"\n"
    if any((destination / name).exists() for name in payloads):
        raise FileExistsError("A frozen artifact already exists; frozen splits cannot be overwritten.")
    for name, data in payloads.items():
        with (destination / name).open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    return {name: str(destination / name) for name in payloads}
