"""Freeze existing rendered teacher records into independent model batch files."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher import batches, write_batches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tokenizer", type=Path, default=ROOT / "data/tokenizer/tokenizer.json")
    parser.add_argument("--input-limit", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(args.tokenizer))
    with args.input.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    manifest = write_batches(batches(records, count_tokens=lambda value: len(tokenizer.encode(value).ids),
                                    input_limit=args.input_limit, batch_size=args.batch_size,
                                    output_dir=args.output), args.output)
    print(json.dumps({"records": len(records), "dispatches": len(manifest), "output": str(args.output)}))


if __name__ == "__main__":
    main()
