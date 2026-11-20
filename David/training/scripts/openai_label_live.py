"""Run the continuous standard paired-only labelling queue."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher.openai_client_live import PairedLiveClient
from openai_label import load_key

parser = argparse.ArgumentParser()
parser.add_argument("--queue", type=Path, required=True)
parser.add_argument("--env-file", type=Path, required=True)
parser.add_argument("--stop-file", type=Path, default=ROOT / "results/openai-labelling/STOP_ADMISSIONS")
parser.add_argument("--concurrency", type=int, default=64)
parser.add_argument("--hold-question", action="append", default=[])
args = parser.parse_args()
client = PairedLiveClient(key=load_key(args.env_file),
    pricing=json.loads((ROOT / "openai-label-pricing.json").read_text(encoding="utf-8")),
    ledger=ROOT / "results/openai-spend.jsonl", claims=ROOT / "data/votes/claims",
    stop_file=args.stop_file, max_concurrency=args.concurrency)
client.run(args.queue, excluded_questions=tuple(args.hold_question))
