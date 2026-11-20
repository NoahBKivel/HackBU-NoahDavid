"""Export the current paired initial cohort locally for the one allowed relabel."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.assemble.receipts import canonical_payload
from intent_training.teacher.dispatch import digest


def rows(path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolved", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pass", dest="stage", default="main")
    args = parser.parse_args()
    def origins(record):
        meta = record["_meta"]
        return meta.get("teacher_vote_origins", {}) if args.stage == "main" else meta.get("question_pass_origins", {}).get(args.stage, {})
    parents = {row["_meta"]["record_id"]: row for row in rows(args.resolved)
               if row["_meta"].get("vote_allocation") == "paired" and {"sol", "terra"} <= set(origins(row))}
    found, errors = {}, []
    def accept(batch):
        if batch["pass"] != args.stage:
            return
        for prepared in batch["records"]:
            identity = prepared["record_id"]
            if identity not in parents:
                continue
            record = parents[identity]
            origin = origins(record)["sol"]
            if (origin["batch_id"], origin["input_sha256"]) != (batch["batch_id"], batch["input_sha256"]):
                continue
            expected = {key: {field: value for field, value in row.items() if field not in {"label", "target"}}
                        for key, row in record["questions"].items() if key in prepared["questions"]}
            if prepared["state"] != record["state"] or prepared["questions"] != expected:
                errors.append({"record_id": identity, "error": "The initial frozen input differs from the resolved cohort."})
                continue
            found[identity] = canonical_payload(prepared)
    for task in rows(args.queue):
        accept(task["batch"])
    for manifest in args.manifest if args.stage == "main" else []:
        for entry in json.loads(manifest.read_text(encoding="utf-8")):
            if entry["model_family"] != "sol":
                continue
            path = Path(entry["input"])
            if not path.exists():
                path = ROOT.parents[1] / path
            accept(json.loads(path.read_text(encoding="utf-8")))
    missing = sorted(set(parents) - set(found))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name, values in (("model-inputs", found.values()), ("initial-receipts", (
            {"record_id": identity, "model_input_sha256": digest(prepared),
             "initial_receipts": origins(parents[identity])}
            for identity, prepared in found.items()))):
        content = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in values)
        path = args.output_dir / (name + ".jsonl")
        path.write_bytes(content.encode("utf-8"))
        outputs[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    report = {"pass": args.stage, "paired_parents": len(parents), "exported_parents": len(found), "missing_record_ids": missing,
              "errors": errors, "question_rows": dict(Counter(key.split("#", 1)[0] for row in found.values()
                  for key in row["questions"])), "outputs": outputs, "complete": not missing and not errors}
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
