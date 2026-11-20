"""Run official per-instruction verifiers inside the dedicated Docker runtime.

This script belongs inside the container. Mount only the checker folder and a
bounded input file. Its output is captured by the caller into source evidence.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkers", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--isolation", choices=["docker", "modal"], default="docker")
    args = parser.parse_args()
    sys.path.insert(0, str(args.checkers.resolve()))
    from langdetect import DetectorFactory
    from open_instruct.IFEvalG.instructions_registry import INSTRUCTION_DICT

    DetectorFactory.seed = 0
    for line in args.input.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        passed, errors = [], []
        for ident, kwargs in zip(row["instruction_ids"], row["kwargs"], strict=True):
            try:
                checker = INSTRUCTION_DICT[ident](ident)
                checker.build_description(**(kwargs or {}))
                passed.append(bool(checker.check_following(row["response"])))
            except Exception as exc:
                passed.append(None)
                errors.append({"instruction_id": ident, "error_type": type(exc).__name__})
        print(json.dumps({"id": row["id"], "isolation": args.isolation, "instruction_ids": row["instruction_ids"],
                          "response_sha256": hashlib.sha256(row["response"].encode("utf-8")).hexdigest(),
                          "passed": passed, "errors": errors}))


if __name__ == "__main__":
    main()
