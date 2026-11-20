"""Run approved auxiliary Sonnet votes without changing other teacher streams."""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher.anthropic_client import AnthropicAuxiliaryClient


def main() -> int:
    """Admit only owner-reviewed candidate batch identities with fresh ownership."""
    manifest = json.loads((ROOT / "results/anthropic-label-assessment/offline-manifest.json").read_text())
    allowed = {item["batch_id"] for item in manifest}
    client = AnthropicAuxiliaryClient(ROOT, maximum=32)
    print(json.dumps({"started": True, "model": "claude-sonnet-5-5", "candidate_batches": len(allowed),
                      "max_concurrency": 32, "label_cap_usd": 80, "construction_headroom_usd": 25}), flush=True)
    result = client.run(ROOT / "data/votes/limit-8191/continuous-queue.jsonl", allowed)
    print(json.dumps({"finished": True, "batches": len(result["results"])}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
