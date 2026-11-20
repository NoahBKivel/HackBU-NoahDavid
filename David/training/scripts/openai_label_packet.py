"""Label an exclusively assigned current-budget packet with its private family allocation."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from tokenizers import Tokenizer
from intent_training.prepare.priority import teacher_payload
from intent_training.teacher.dispatch import _batch, write_batches, encoded
from intent_training.teacher.openai_client import OpenAILabeller, request_body
from intent_training.teacher.openai_client_state import utc_now
from openai_label import load_key

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--controls", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--env-file", type=Path, required=True)
args = parser.parse_args()
controls = json.loads(args.controls.read_text(encoding="utf-8"))
groups = defaultdict(list)
for line in args.input.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    row = json.loads(line)
    control = controls[row["record_id"]]
    if control["_meta"]["validated_length"] != 8191:
        raise ValueError("The assigned input is not certified at the current state budget.")
    families = ("sol", "terra") if control["allocation"] == "paired" else ("sol",)
    payload = teacher_payload(row)
    groups[(payload["source"], payload["pass"], families)].append(payload)
tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
items = []
allocations = {}
oversized = []
def cost(batch):
    return len(tokenizer.encode(encoded(request_body(batch, "sol", 16000))).ids)
for (source, stage, families), rows in groups.items():
    current = []
    for row in rows:
        candidate = _batch(source, stage, current + [row])
        if current and (len(current) >= 25 or cost(candidate) > 200000):
            batch = _batch(source, stage, current)
            items.append(batch)
            allocations[batch["batch_id"]] = families
            current = []
        single = _batch(source, stage, [row])
        if cost(single) > 720000:
            oversized.append(row["record_id"])
            continue
        current.append(row)
    if current:
        batch = _batch(source, stage, current)
        items.append(batch)
        allocations[batch["batch_id"]] = families
manifest = write_batches(items, args.output)
entries = [entry for entry in manifest if entry["model_family"] in allocations[entry["batch_id"]]]
(args.output / "manifest.json").write_text(encoded(entries) + "\n", encoding="utf-8")
print(json.dumps({"started_at": utc_now(), "assigned_records": sum(len(batch["records"]) for batch in items),
                  "family_calls": len(entries), "oversized_hard_context_excluded": oversized}), flush=True)
rates = json.loads((ROOT / "openai-label-pricing.json").read_text(encoding="utf-8"))
client = OpenAILabeller(api_key=load_key(args.env_file), rates=rates,
                        ledger=ROOT / "results/openai-spend.jsonl", claims=ROOT / "data/votes/claims",
                        evidence=args.evidence, max_concurrency=64)
client.capacity.limit = min(len(entries), 3)
results = client.run(entries)
completed = defaultdict(set)
for result in results:
    if "error" not in result:
        completed[result["batch_id"]].add(result["family"])
labelled = sum(len(batch["records"]) for batch in items
               if set(allocations[batch["batch_id"]]) <= completed[batch["batch_id"]])
print(json.dumps({"completed_at": utc_now(), "allocation_complete_records": labelled,
                  "family_results": results, "openai_exposure_usd": client.budget.exposure()}), flush=True)
