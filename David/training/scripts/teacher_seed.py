"""Verify the sealed plan, freeze real seed batches and deduplicate RF selection."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher.dispatch import batches, write_batches, digest
from hashlib import sha256


def load(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-hash", required=True)
    args = parser.parse_args()
    raw = (ROOT / "results/positive-plan-sealed.json").read_bytes()
    assert sha256(raw).hexdigest() == args.plan_hash.lower()
    plan = json.loads(raw)
    assert plan["status"] == "sealed" and not plan["blockers"]
    assert sum(plan["parts"].values()) == plan["planned_total"]
    assert all(abs(floor - max(.8 * plan["expected"][q], 60)) < 1e-8
               for q, floor in plan["floors"].items())
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    rows = load(ROOT / "data/prepared/main.jsonl")
    main_rows = [{key: row[key] for key in ("record_id", "state", "questions", "source", "pass", "teacher_side")}
                 for row in rows]
    out = ROOT / "data/votes/seed_main"
    manifests = write_batches(batches(main_rows, count_tokens=lambda text: len(tok.encode(text).ids),
                                     input_limit=70000, output_dir=out), out)
    rf_rows = load(ROOT / "data/prepared/requirements.jsonl")
    unique, fanout = {}, {}
    for row in rf_rows:
        fingerprint = digest({"state": row["state"], "questions": row["questions"]})
        fanout.setdefault(fingerprint, []).append({key: row[key] for key in
                    ("record_id", "parent_record_id", "unit_id", "source", "unit") if key in row})
        if fingerprint not in unique:
            unique[fingerprint] = {key: row[key] for key in
                    ("record_id", "state", "questions", "source", "pass", "teacher_side")}
            unique[fingerprint]["content_sha256"] = fingerprint
    rf_out = ROOT / "data/votes/seed_requirements"
    rf_manifests = write_batches(batches(unique.values(), count_tokens=lambda text: len(tok.encode(text).ids),
                                        input_limit=70000, output_dir=rf_out), rf_out)
    (rf_out / "fanout.json").write_text(json.dumps(fanout, ensure_ascii=False), encoding="utf-8")
    report = {"plan_sha256": args.plan_hash.lower(), "parts": plan["parts"],
              "floors_verified": len(plan["floors"]), "main_rows": len(rows),
              "main_source_counts": dict(Counter(row["source"] for row in rows)),
              "main_dispatches": len(manifests), "rf_raw": len(rf_rows), "rf_unique": len(unique),
              "rf_dispatches": len(rf_manifests)}
    results = ROOT / "results/teacher"
    results.mkdir(parents=True, exist_ok=True)
    (results / "seed_snapshot.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
