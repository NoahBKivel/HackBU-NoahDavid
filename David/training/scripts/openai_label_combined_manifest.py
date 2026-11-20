"""Index current 10K teacher batches from both execution paths for rate measurement."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher.openai_client_state import atomic_json

paths = [ROOT / "data/votes/openai_pilot_10k/manifest.json",
         ROOT / "data/votes/openai_pilot_10k_next21/manifest.json"]
paths.extend(sorted((ROOT / "data/votes/limit-10239/codex-waves").glob("*/manifest.json")))
entries = {}
for path in paths:
    if not path.exists():
        continue
    for entry in json.loads(path.read_text(encoding="utf-8")):
        entries[(entry["batch_id"], entry["model_family"], entry["input_sha256"])] = entry
output = ROOT / "results/openai-labelling/combined-manifest.json"
atomic_json(output, list(entries.values()))
print(json.dumps({"manifests": len(paths), "family_entries": len(entries), "output": str(output)}))
