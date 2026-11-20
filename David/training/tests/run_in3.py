"""Persist measured IN3 conversion artifacts and validation evidence."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

from intent_training.sources.in3 import convert, selected, request_id
from intent_training.sources.reading import rows
from monitor_format import validate_events


def main():
    raw = ROOT / "data/downloads/in3"
    selected_rows = list(selected(raw))
    response_dir = ROOT / "data/generation/responses"
    missing = [request_id(index, row) for index, row, _ in selected_rows
               if not (response_dir / f"{request_id(index, row)}.json").exists()]
    outputs = []
    errors = []
    try:
        for events, side, meta in convert(raw):
            validate_events(events)
            outputs.append({"events": events, "side": side, "meta": meta})
    except (ValueError, KeyError, TypeError) as error:
        errors.append(str(error))
    destination = ROOT / "data/converted/in3.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n"
                                   for record in outputs), encoding="utf-8")
    raw_counts = Counter(str(row["vague"]).lower() for row in rows(raw))
    labels = Counter(str(label["value"]).lower() for record in outputs
                     for label in record["side"]["source_labels"])
    files = list(raw.glob("*.jsonl")) + [destination]
    evidence = {"source": "in3", "dataset": "hbx/IN3", "split": "train",
                "planned_count": 150, "selected_tasks": len(selected_rows),
                "selected_vague": sum(row["vague"] for _, row, _ in selected_rows),
                "selected_clear": sum(not row["vague"] for _, row, _ in selected_rows),
                "raw_rows": sum(raw_counts.values()), "raw_vague_counts": dict(raw_counts),
                "records": len(outputs), "validated_streams": len(outputs),
                "label_counts": dict(labels),
                "unlabelled_records": sum(not record["side"]["source_labels"] for record in outputs),
                "missing_response_ids": missing, "errors": errors,
                "selection_rule": "First 38 eligible rows per vague class, retained in dataset order.",
                "positive_rule": "Exact material source option appears visibly without question, assumption, hedge, or alternative cues.",
                "source_files": [{"path": path.relative_to(ROOT).as_posix(),
                                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                                 for path in files]}
    report = ROOT / "results/sources/in3.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: evidence[key] for key in
                      ("records", "validated_streams", "label_counts", "unlabelled_records", "errors")}))


if __name__ == "__main__":
    main()
