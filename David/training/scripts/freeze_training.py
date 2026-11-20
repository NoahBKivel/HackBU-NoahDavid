"""Prepare a gated training candidate and publish it only on explicit root activation."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent), str(ROOT / "vendor/kev")]

from intent_training.assemble.freeze import file_reference, prepare_freeze, publish_freeze, read_rows
from intent_training.assemble.quality import REGISTRY
from intent_training.assemble.siblings import kev_fit
from intent_training.prepare.records import load_tokenizer
from intent_training.splits.freeze import _serialized


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--positive-plan", type=Path, required=True)
    parser.add_argument("--source-plan", type=Path, required=True)
    parser.add_argument("--composition", type=Path, required=True)
    parser.add_argument("--base-dev", type=Path)
    parser.add_argument("--dev-topup", type=Path)
    parser.add_argument("--teacher-fallbacks", type=Path)
    parser.add_argument("--data-report", type=Path, nargs="+", required=True)
    parser.add_argument("--tokenizer", type=Path, default=ROOT / "data/tokenizer")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--authorize-freeze", action="store_true")
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args()
    if args.authorize_freeze and args.directory is None:
        parser.error("Explicit root activation requires a private destination directory.")
    inputs = [*args.input, args.positive_plan, args.source_plan, args.composition, *args.data_report,
              Path(__file__), ROOT / "src/intent_training/assemble/freeze.py",
              ROOT / "src/intent_training/assemble/freeze_groups.py"]
    inputs.extend(path for path in [args.base_dev, args.dev_topup, args.teacher_fallbacks, REGISTRY] if path)
    inputs.extend((ROOT / "data/exclusions").glob("*reservations*.jsonl"))
    before = {str(path): file_reference(path)["sha256"] for path in inputs}
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    fits = kev_fit(load_tokenizer(args.tokenizer), max_state=8192)
    splits, report = prepare_freeze(
        [row for path in args.input for row in read_rows(path)],
        preregistration=load(args.positive_plan), source_plan=load(args.source_plan),
        composition=load(args.composition), fits=fits, scanner=ROOT / "scripts/scan_secrets.py",
        input_paths=inputs, seed=args.seed,
        base_dev=read_rows(args.base_dev) if args.base_dev else (),
        dev_topup=read_rows(args.dev_topup) if args.dev_topup else (),
        teacher_fallbacks=load(args.teacher_fallbacks) if args.teacher_fallbacks else None)
    if any(reference["sha256"] != before[path] for path, reference in report["inputs"].items()):
        report["failures"].append("input_changed_during_gates")
        report["passed"] = False
    args.candidate.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.candidate.write_bytes(_serialized(splits["train"]))
    args.report.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
    result = {"passed": report["passed"], "failures": report["failures"],
              "training_lines": len(splits["train"]), "report": str(args.report),
              "candidate": str(args.candidate), "sha256": report["outputs"]["train"]["sha256"]}
    if args.authorize_freeze:
        result["root_launch_request"] = publish_freeze(splits, report, args.directory, authorized=True)
    print(json.dumps(result), flush=True)
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
