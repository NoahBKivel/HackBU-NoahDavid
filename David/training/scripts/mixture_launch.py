"""Submit the sole shared real-record benchmark sampler."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys


def main() -> None:
    """Send the canonical source weights and candidate namespaces to one CPU job."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared-dir", action="append", required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    from kev_prepare_upload import available_memory_gib
    memory = available_memory_gib()
    sys.path.insert(0, str(root / "src"))
    from intent_training.modal_app import mixture as module
    plan = json.loads((args.plan or root / "results/positive-plan.json").read_text())
    seed = args.seed if args.seed is not None else random.SystemRandom().getrandbits(63)
    with module.app.run(detach=True):
        call = module.seal.spawn(args.prepared_dir, plan, seed)
        result = {"function_call_id": call.object_id, "app_id": module.app.app_id,
                  "image_id": module.image.object_id, "prepared_directories": args.prepared_dir,
                  "submitted_at": datetime.now(timezone.utc).isoformat(), "seed": seed,
                  "available_memory_gib": memory}
        directory = root / "results/benchmark-mixture"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "launch.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
