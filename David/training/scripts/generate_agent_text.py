"""Run the central durable agent-text queue once or watch for new requests."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from intent_training.generation.generator import Generator
from intent_training.generation.request_io import atomic_json


def main() -> int:
    """Persist runner state and print only identifiers, status and billing."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--construction-budget", action="store_true")
    parser.add_argument("--model", choices=["claude-haiku-5-5", "claude-sonnet-5-5"])
    parser.add_argument("--request-id")
    parser.add_argument("--sources", nargs="+")
    parser.add_argument("--expected-prompt-sha256")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=10)
    args = parser.parse_args()
    if args.expected_prompt_sha256 and not args.request_id:
        parser.error("An approved prompt fingerprint requires an exact request identifier.")
    if args.model and not args.request_id:
        parser.error("A pinned retry model requires an exact request identifier.")
    runner = Generator(args.root, retry_failed=args.retry_failed, approved_prompt_sha256=args.expected_prompt_sha256,
                       construction_budget=args.construction_budget, requested_model=args.model)
    while True:
        results = runner.run_once(args.workers, args.limit, args.request_id, args.sources)
        state = {"timestamp": datetime.now(timezone.utc).isoformat(), "mode": "watch" if args.watch else "once",
                 "requests": len(results), "results": results}
        atomic_json(runner.spending.folder / "runner-state.json", state)
        print(json.dumps({"timestamp": state["timestamp"], "mode": state["mode"], "requests": len(results),
                          "statuses": {status: sum(row["status"] == status for row in results) for status in {row["status"] for row in results}}}), flush=True)
        if not args.watch:
            return int(any(row["status"] in ("failed", "incomplete", "refused") for row in results))
        time.sleep(max(1, min(args.interval, 60)))


if __name__ == "__main__":
    raise SystemExit(main())
