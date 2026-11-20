"""Atomically prepare converted streams using the actual cached tokenizer."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))

from intent_training.prepare.records import load_tokenizer, prepare_native, prepare_stream, stable_id


def write_line(handle, record):
    handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--sources", nargs="*")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--remote-input", nargs="+")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--tokenizer-dir", type=Path, default=ROOT / "data" / "tokenizer")
    parser.add_argument("--state-budget", type=int, default=8191)
    parser.add_argument("--screen-budget", type=int, default=8192)
    parser.add_argument("--emit-first", type=int, default=3)
    parser.add_argument("--build-sample", type=Path)
    parser.add_argument("--reconcile-manifests", nargs="+", type=Path)
    parser.add_argument("--extra-calls", nargs="*", default=[])
    parser.add_argument("--frozen-manifest", type=Path)
    parser.add_argument("--audit-export", nargs="+")
    parser.add_argument("--export-manifest", type=Path)
    parser.add_argument("--measure", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--deduplicate-requirements", action="store_true")
    parser.add_argument("--enrich-requirements", action="store_true")
    parser.add_argument("--publish-partial", action="store_true")
    args = parser.parse_args()
    if args.audit_export:
        from intent_training.prepare.sample import available_ram_gib
        if available_ram_gib() <= 3.5:
            raise SystemExit("The owner RAM gate is closed.")
        from intent_training.prepare.export_manifest import build
        build(ROOT, args.audit_export, args.export_manifest)
        return
    if args.reconcile_manifests:
        from intent_training.prepare.reconcile import run
        run(ROOT, args.output_root, args.reconcile_manifests, args.extra_calls, args.frozen_manifest)
        return
    if args.build_sample:
        from intent_training.prepare.sample import build, available_ram_gib
        available = available_ram_gib()
        if available < float(os.environ.get("INTENT_LOCAL_RAM_MIN_GIB", "3.5")):
            raise SystemExit(f"The owner RAM gate is closed: {available:.3f} GiB.")
        build(ROOT, args.build_sample)
        return
    if args.remote_input:
        from intent_training.prepare.priority import run
        run(args.remote_input, args.output_root or ROOT / "data" / "prepared" / f"limit-{args.state_budget}",
            args.tokenizer_dir, budget=args.state_budget, screen_budget=args.screen_budget,
            limit=30 if args.limit is None else args.limit, emit_first=args.emit_first)
        return
    if args.measure:
        from intent_training.prepare.measure import measure
        measure(ROOT)
        return
    if args.finalize:
        from intent_training.prepare.provenance import finalize
        finalize(ROOT)
        return
    if args.deduplicate_requirements:
        from intent_training.prepare.requirements import deduplicate
        deduplicate(ROOT)
        return
    if args.enrich_requirements:
        from intent_training.prepare.requirements import enrich
        enrich(ROOT)
        return
    if args.publish_partial:
        from intent_training.prepare.snapshot import publish
        publish(ROOT)
        return
    started = time.time()
    registry = ROOT / "src" / "intent_training" / "sources" / "entries"
    declared = {json.loads(path.read_text(encoding="utf-8-sig"))["slug"]
                for path in registry.glob("*.json")}
    rows, provenance, errors = [], [], []
    for path in sorted((ROOT / "data" / "converted").glob("*.jsonl")):
        if args.sources and path.stem not in args.sources:
            continue
        if path.stem.endswith("_bases"):
            continue
        count = 0
        with path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, 1):
                if args.limit and count >= args.limit:
                    break
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    if row["meta"]["source"] not in declared:
                        raise ValueError("Source is absent from the canonical registry.")
                    rows.append(row)
                    provenance.append((path.name, line_number))
                    count += 1
                except Exception as error:
                    errors.append({"file": path.name, "line": line_number, "error": str(error)})
    from intent_training.prepare.cuts import plan_cuts
    cuts = plan_cuts(rows)
    tokenizer = load_tokenizer(ROOT / "data" / "tokenizer")
    output = args.output_root or ROOT / "data" / "prepared" / f"limit-{args.state_budget}"
    results = ROOT / "results" / "preparation" / f"limit-{args.state_budget}"
    output.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    names = ("main", "native", "requirements", "context")
    handles = {name: (output / f"{name}.jsonl.tmp").open("w", encoding="utf-8", newline="\n") for name in names}
    counts, by_source, seen = Counter(), {}, set()
    rendered_parents = set()
    try:
        for index, row in enumerate(rows):
            source = row["meta"]["source"]
            source_counts = by_source.setdefault(source, Counter())
            source_counts["converted"] += 1
            try:
                if not row["events"] and "native_record" in row["side"]:
                    native = prepare_native(row)
                    if native["record_id"] not in seen:
                        write_line(handles["native"], native)
                        seen.add(native["record_id"])
                        counts["native"] += 1
                        source_counts["native"] += 1
                    continue
                if not cuts[index]:
                    source_counts["deferred_cut"] += 1
                for cut in cuts[index]:
                    parent_identity = stable_id({"source": source,
                        "trajectory": row["meta"].get("trajectory_id"),
                        "pair": row["meta"].get("pair_id"), "cut": cut["cut_seq"],
                        "events": [event for event in row["events"] if event["seq"] <= cut["cut_seq"]]})
                    if parent_identity in rendered_parents:
                        source_counts["duplicate_cut"] += 1
                        continue
                    main_rows, rf_rows, contexts = prepare_stream(row, cut, tokenizer, args.state_budget, args.screen_budget)
                    rendered_parents.add(parent_identity)
                    fresh = {record["record_id"] for record in main_rows} - seen
                    for name, values in (("main", main_rows), ("requirements", rf_rows), ("context", contexts)):
                        for record in values:
                            parent = record.get("parent_record_id", record["record_id"])
                            if parent not in fresh:
                                continue
                            write_line(handles[name], record)
                            counts[name] += 1
                            source_counts[name] += 1
                    seen.update(fresh)
            except Exception as error:
                errors.append({"file": provenance[index][0], "line": provenance[index][1],
                               "error_type": type(error).__name__, "error": str(error)[:300]})
                source_counts["rejected"] += 1
            if (index + 1) % 100 == 0:
                print(json.dumps({"processed": index + 1, "counts": counts}), flush=True)
    finally:
        for handle in handles.values():
            handle.close()
    for name in names:
        os.replace(output / f"{name}.jsonl.tmp", output / f"{name}.jsonl")
    manifest = {"converted_rows": len(rows), "counts": counts, "by_source": by_source,
                "errors": errors, "elapsed_seconds": round(time.time() - started, 3),
                "label_authorization": "pending_root_confirmation",
                "complete": False, "input_files": sorted({name for name, _ in provenance})}
    path = results / "manifest.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)
    print(json.dumps({"manifest": str(path), "counts": counts, "errors": len(errors)}), flush=True)


if __name__ == "__main__":
    main()
