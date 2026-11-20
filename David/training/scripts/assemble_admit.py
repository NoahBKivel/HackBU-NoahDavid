"""Run actual tokenizer and Kev encoder admission for completed candidates."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent), str(ROOT / "vendor/kev")]

from intent_training.assemble.admission import admit_record
from intent_training.assemble.siblings import kev_fit
from intent_training.assemble.quality import receipt_holds, record_held
from intent_training.prepare.records import load_tokenizer


def rows(path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--native", type=Path, nargs="*", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--completed-rows-only", action="store_true")
    args = parser.parse_args()
    contexts = {row["record_id"]: row for row in rows(args.context)}
    requirements = {row["record_id"]: row for row in rows(args.requirements)}
    tokenizer = load_tokenizer(ROOT / "data/tokenizer")
    fits = kev_fit(tokenizer, max_state=8192)
    holds = receipt_holds()
    admitted, errors, parents = [], [], 0
    sources = Counter()
    for path in [args.input, *args.native]:
        for record in rows(path):
            identity = record.get("_meta", {}).get("record_id", record.get("record_id"))
            try:
                if not identity:
                    raise ValueError("A stable prepared record_id is required for encoder admission.")
                record.setdefault("_meta", {}).setdefault("record_id", identity)
                if record_held(record, holds):
                    raise ValueError("A required teacher receipt is held for explicit quality review.")
                siblings = admit_record(record, contexts.get(identity), requirements=requirements.get(identity),
                                        tokenizer=tokenizer, fits=fits, completed_rows_only=args.completed_rows_only)
                admitted.extend(siblings)
                parents += 1
                sources[record["_meta"]["source"]] += 1
            except (ValueError, TypeError, KeyError) as error:
                errors.append({"record_id": identity, "error": str(error)})
            if (parents + len(errors)) % 100 == 0:
                print(json.dumps({"admitted_parents": parents, "errors": len(errors)}), flush=True)
    content = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in admitted)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_bytes(content.encode("utf-8"))
    temporary.replace(args.output)
    report = {"observed_at_utc": datetime.now(timezone.utc).isoformat(), "admitted_parent_records": parents,
              "admitted_sibling_records": len(admitted), "question_rows": sum(len(row["questions"]) for row in admitted),
              "source_counts": dict(sources), "errors": errors,
              "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(), "freeze_ready": False}
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "errors"}), flush=True)


if __name__ == "__main__":
    main()
