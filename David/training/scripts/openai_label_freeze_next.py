"""Freeze the explicitly reserved remainder of the OpenAI cost pilot."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from tokenizers import Tokenizer
from intent_training.teacher.dispatch import batches, write_batches
from teacher_refresh import visible

rows = [visible(json.loads(line)) for line in (
    ROOT / "data/votes/limit-10239/API_next21.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
reserved = set(json.loads((ROOT / "data/votes/limit-10239/api_reserved.json").read_text(
    encoding="utf-8"))["record_ids"])
if not rows or any(row["record_id"] not in reserved for row in rows):
    raise ValueError("The remainder does not match the explicit reserved pilot records.")
tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
output = ROOT / "data/votes/openai_pilot_10k_next21"
items = list(batches(rows, count_tokens=lambda text: len(tokenizer.encode(text).ids),
                     input_limit=200000, batch_size=25, output_dir=output))
manifest = write_batches(items, output)
print(json.dumps({"records": len(rows), "batches": len(items), "family_calls": len(manifest),
                  "manifest": str(output / "manifest.json")}))
