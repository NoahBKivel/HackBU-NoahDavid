"""Run batched candidate scoring, selection and calibration on prepared artifacts."""

import argparse
import json
from pathlib import Path
from typing import Any, Iterator

from .calibration import fit_calibration
from .scoring import load_and_score, target_rows
from .selection import select_candidate


def _rows(path: str) -> Iterator[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _write(path: str, value: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(output)


def main() -> None:
    """Execute one artifact operation without touching held-out evaluation inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    scoring = commands.add_parser("score")
    scoring.add_argument("--checkpoint", required=True)
    scoring.add_argument("--records", required=True)
    scoring.add_argument("--out", required=True)
    scoring.add_argument("--device", default="cuda")
    scoring.add_argument("--max-state", type=int, required=True)
    scoring.add_argument("--pass-tokens-max", type=int, required=True)
    scoring.add_argument("--base-dev", action="store_true")
    scoring.add_argument("--intent-ids", help="JSON array of intent-slice record IDs.")
    picking = commands.add_parser("pick")
    picking.add_argument("--candidate", action="append", required=True, help="Candidate name=score JSONL path.")
    picking.add_argument("--stock", required=True)
    picking.add_argument("--seed", type=int, default=1)
    picking.add_argument("--out", required=True)
    calibrating = commands.add_parser("calibrate")
    calibrating.add_argument("--dev-scores", required=True)
    calibrating.add_argument("--train-records")
    calibrating.add_argument("--stock", action="store_true")
    calibrating.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.command == "score":
        intent_ids = set(json.loads(Path(args.intent_ids).read_text(encoding="utf-8"))) if args.intent_ids else set()
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        count = 0
        with temporary.open("w", encoding="utf-8") as handle:
            for row in load_and_score(args.checkpoint, _rows(args.records), device=args.device,
                                      max_state=args.max_state, pass_tokens_max=args.pass_tokens_max,
                                      is_base_dev=args.base_dev, intent_ids=intent_ids):
                handle.write(json.dumps(row, allow_nan=False) + "\n")
                count += 1
        if count == 0:
            raise ValueError("Candidate scoring produced no question rows.")
        temporary.replace(output)
    elif args.command == "pick":
        candidates = {}
        for value in args.candidate:
            name, path = value.split("=", 1)
            if name in candidates:
                raise ValueError("Candidate names must be unique.")
            candidates[name] = list(_rows(path))
        _write(args.out, select_candidate(candidates, stock=args.stock, seed=args.seed))
    else:
        if not args.stock and not args.train_records:
            parser.error("Tuned calibration requires --train-records.")
        training = target_rows(_rows(args.train_records)) if args.train_records else []
        _write(args.out, fit_calibration(_rows(args.dev_scores), training, stock=args.stock))


if __name__ == "__main__":
    main()
