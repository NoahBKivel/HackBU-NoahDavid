"""Persist bounded source preparation and measured conversion evidence."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.sources.if_multi import (
    convert, generation_requests, parse_row, requirement_units, source_rows,
)
from monitor_format import validate_events


def write_lines(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values), encoding="utf-8")


def main() -> None:
    raw = ROOT / "data/downloads/if_multi"
    records = list(source_rows(raw))
    requests = list(generation_requests(raw))
    write_lines(ROOT / "data/generation/requests/if_multi.jsonl", requests)
    rf = []
    for index, row in records[:200]:
        base, constraints, ids, kwargs = parse_row(row)
        context = {"instruction": "\n\n".join(constraints) + "\n\n" + base,
                   "document": None, "constraints": constraints}
        rf.append({"source_record_id": row["key"], "row_idx": index,
                   "units": requirement_units(context, constraints, base),
                   "original_constraints": constraints, "instruction_ids": ids, "kwargs": kwargs})
    write_lines(raw / "rf_units.jsonl", rf)
    converted = []
    for events, side, meta in convert(raw):
        validate_events(events)
        converted.append({"events": events, "side": side, "meta": meta})
    output = ROOT / "data/converted/if_multi.jsonl"
    write_lines(output, converted)
    files = [raw / "rows.jsonl", raw / "rf_units.jsonl", output,
             ROOT / "data/generation/requests/if_multi.jsonl"]
    files += sorted((raw / "checkers/open_instruct/IFEvalG").glob("*.py"))
    smoke_path = ROOT / "results/sources/if_multi-checker-smoke.jsonl"
    smoke = [json.loads(line) for line in smoke_path.read_text(encoding="utf-8").splitlines()] if smoke_path.is_file() else []
    if smoke_path.is_file():
        files.append(smoke_path)
    evidence = {
        "source": "if_multi", "dataset": "allenai/IF_multi_constraints_upto5",
        "status": "partial_generation_blocked", "planned_count": 400,
        "planned_slices": {"RF": 200, "M2_D2_G2": 200},
        "actual_rows_inspected": 3, "actual_rows_extracted": len(records),
        "rows_with_aligned_constraints": sum(bool(parse_row(row)) for _, row in records),
        "records_written": len(converted),
        "records_by_objective": {"RF": sum(x["meta"]["objective"] == ["RF"] for x in converted),
                                 "M2_D2_G2": sum(x["meta"]["objective"] == ["M2", "D2", "G2"] for x in converted)},
        "native_rf_source_records": len(rf),
        "native_rf_positive_units": sum(unit["value"] for record in rf for unit in record["units"]),
        "native_rf_negative_units": sum(not unit["value"] for record in rf for unit in record["units"]),
        "output_rf_positive_units": sum(unit["value"] for x in converted for unit in x["side"]["requirement_units"]),
        "output_rf_negative_units": sum(not unit["value"] for x in converted for unit in x["side"]["requirement_units"]),
        "generation_requests": len(requests),
        "generation_responses": sum((ROOT / f"data/generation/responses/{r['id']}.json").is_file() for r in requests),
        "verified_generated_responses": sum(x["meta"]["objective"] != ["RF"] for x in converted),
        "checker_smoke": {"source_instruction_groups": len(smoke),
                          "boolean_results": sum(type(value) is bool for record in smoke for value in record["passed"]),
                          "errors": sum(len(record["errors"]) for record in smoke),
                          "input_kind": "nonempty test fixture; not agent generation"},
        "converted_event_streams_validated": len(converted),
        "files": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "bytes": path.stat().st_size} for path in files],
        "errors": [{"stage": "central_generation", "reason": "Parent reported provider DNS failure and automatic approval review rejection of outbound payload and credential authorization. No independent generation was attempted."}],
        "notes": "All remaining RF rewrites and agent answers await central generation. Native units are preparation evidence, not additional training records. Only verifier done/broken states are native; no synthetic not-done or cannot-tell labels are supplied.",
    }
    destination = ROOT / "results/sources/if_multi.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: evidence[key] for key in ("records_by_objective", "native_rf_positive_units", "native_rf_negative_units", "generation_requests", "generation_responses")}))


if __name__ == "__main__":
    main()
