"""Launch prepared task manifests with persistent job state."""

import argparse
import json
import os
from pathlib import Path
import sys


def main() -> None:
    """Run a manifest of isolated coding tasks under the configured limits."""
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from intent_training.generation.agent_runs import run_tasks
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args()
    tasks = [json.loads(line) for line in args.manifest.read_text(encoding="utf-8").splitlines() if line]
    output = root / "results/agent-runs"
    output.mkdir(parents=True, exist_ok=True)
    (output / "batch.json").write_text(json.dumps({"pid": os.getpid(), "manifest": str(args.manifest),
                                                   "workers": args.workers, "task_count": len(tasks)}), encoding="utf-8")
    results = run_tasks(root, tasks, args.workers)
    (output / "batch-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
