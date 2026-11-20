"""Freeze newly prepared real records without overlapping previous frozen main rows."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher.dispatch import batches, write_batches
from intent_training.teacher.claims import teacher_input_hash


def visible(row):
    """Keep exactly the fields dispatched to both teacher families."""
    payload = {key: row[key] for key in ("record_id", "state", "questions", "source", "pass", "teacher_side")}
    for key in ("purpose", "row_context"):
        if key in row:
            payload[key] = row[key]
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-source", type=int, default=30)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--input-limit", type=int, required=True)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    existing = set()
    for path in (ROOT / "data/votes").glob("*/*-main-*.json"):
        try:
            batch = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        existing.update(teacher_input_hash(row) for row in batch.get("records", []))
    counts = defaultdict(int)
    rows = []
    with args.input.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            payload = visible(row)
            if teacher_input_hash(payload) in existing or counts[row["source"]] >= args.per_source:
                continue
            counts[row["source"]] += 1
            rows.append(payload)
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    manifest = write_batches(batches(rows, count_tokens=lambda text: len(tokenizer.encode(text).ids),
                                    input_limit=args.input_limit, output_dir=args.output), args.output)
    print(json.dumps({"new_records": len(rows), "source_counts": dict(counts), "dispatches": len(manifest)}))


if __name__ == "__main__":
    main()
