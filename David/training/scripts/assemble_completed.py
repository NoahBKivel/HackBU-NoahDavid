"""Resolve each existing verified main vote shard independently of source completion."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.assemble.stream import completed_votes, merge_collections, queue_votes, resolve_ready
from intent_training.assemble.receipts import resolve_duplicate_receipts
from intent_training.assemble.instruments import policy_instruments
from intent_training.assemble.relabel import OnceRelabel, apply_main_relabels
from intent_training.assemble.quality import RELABEL_REGISTRY


def rows(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, nargs="+", required=True)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--context", type=Path, nargs="*", default=[])
    parser.add_argument("--queue", type=Path)
    parser.add_argument("--canonical", type=Path, nargs="*", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--instrument-report", type=Path)
    parser.add_argument("--relabel-queue", type=Path)
    parser.add_argument("--relabel-ledger", type=Path, default=ROOT / "data/votes/results/teacher/relabel_ledger.json")
    parser.add_argument("--relabel-cohort", type=Path, default=ROOT / "data/assembly/limit-8191/paired-initial-cohort")
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8")) if args.metadata else {}
    contexts = {row["record_id"]: row for path in args.context for row in rows(path)}
    canonical = {row["record_id"]: row for path in args.canonical for row in rows(path)}
    superseded = {row["_meta"]["supersedes_record_id"] for row in canonical.values()
                  if row.get("_meta", {}).get("supersedes_record_id")}
    for identity, prepared in canonical.items():
        existing = metadata.get(identity, {})
        metadata[identity] = {"_meta": {**existing.get("_meta", existing), **prepared.get("_meta", {})}}
    collected = completed_votes(args.manifest, repository=ROOT.parents[1])
    if args.queue:
        collected = merge_collections(collected, queue_votes(args.queue, passes={"main"}))
    if args.queue and args.canonical:
        collected = resolve_duplicate_receipts(collected, manifests=args.manifest, queue=args.queue,
            canonical=canonical, contexts=contexts, claims_dir=ROOT / "data/votes/claims", repository=ROOT.parents[1])
    inactive = set(collected["prepared"]) - set(canonical) if args.canonical else set()
    for identity in superseded | inactive:
        for key in ("prepared", "votes", "origins"):
            collected[key].pop(identity, None)
        collected["blocked"].discard(identity)
    resolved, report = resolve_ready(collected, metadata=metadata, contexts=contexts)
    final_votes = collected["votes"]
    if args.relabel_queue:
        reader = OnceRelabel(queue=args.relabel_queue, ledger=args.relabel_ledger, cohort=args.relabel_cohort,
            base_pass="main", questions={"G4", "L1", "L2", "L4", "L5", "M4", "M7"})
        RELABEL_REGISTRY.write_bytes((json.dumps({"record_ids": sorted(reader.initial),
            "questions": sorted(reader.entries), "queue": str(args.relabel_queue)}) + "\n").encode("utf-8"))
        final_votes = apply_main_relabels(resolved, collected, reader,
            claims_dir=ROOT / "data/votes/claims", repository=ROOT.parents[1])
        report["main_relabel"] = {"expected_cohort_parents": len(reader.initial), "applied_parents": len(reader.applied),
            "pending_parents": sorted(reader.pending), "stale_current_bodies": sorted(reader.stale),
            "vote_validation_errors": reader.collection["errors"], "complete": len(reader.applied) == len(reader.initial)}
    report["superseded_record_ids"] = sorted(superseded)
    report["inactive_canonical_record_ids"] = sorted(inactive)
    if args.instrument_report:
        joined = {}
        for record in resolved:
            identity = record["_meta"]["record_id"]
            for family, answers in final_votes.get(identity, {}).items():
                for key, value in answers.items():
                    joined.setdefault(identity, {}).setdefault(key, {})[family] = value
        instrument = policy_instruments(resolved, joined)
        args.instrument_report.parent.mkdir(parents=True, exist_ok=True)
        args.instrument_report.write_text(json.dumps(instrument, indent=2) + "\n", encoding="utf-8")
    report.update(observed_at_utc=datetime.now(timezone.utc).isoformat(),
                  resolved_question_rows=sum(len(row["questions"]) for row in resolved),
                  allocation_records=dict(Counter(row["_meta"]["vote_allocation"] for row in resolved)),
                  context_available_records=sum(row["_meta"]["assembly_context_available"] for row in resolved),
                  main_only=True, dependent_questions_complete=False, freeze_ready=False)
    if "receipt_resolution" in collected:
        report["receipt_resolution"] = collected["receipt_resolution"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    for path, content in ((args.output, "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in resolved)),
                          (args.report, json.dumps(report, indent=2, ensure_ascii=False) + "\n")):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(content.encode("utf-8"))
        temporary.replace(path)
    print(json.dumps({key: report[key] for key in ("observed_at_utc", "resolved_records", "resolved_question_rows",
        "allocation_records", "context_available_records", "dependent_questions_complete", "freeze_ready")}))
    print(json.dumps({"errors": len(report["errors"]), "blocked_records": len(report["blocked_record_ids"]),
                      "pending_records": len(report["awaiting_required_families"])}))


if __name__ == "__main__":
    main()
