"""Supervise prepared container jobs across an editor restart."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main() -> None:
    """Wait briefly for existing preparation jobs, then launch the bounded batch."""
    root = Path(__file__).resolve().parents[1]
    output = root / "results/agent-runs"
    output.mkdir(parents=True, exist_ok=True)
    state = {"pid": os.getpid(), "started_at": datetime.now(timezone.utc).isoformat(),
             "status": "waiting_for_existing_preparation", "preparation_limit_seconds": 300}
    deadline = time.monotonic() + state["preparation_limit_seconds"]
    while time.monotonic() < deadline:
        completed = root / "data/downloads/duc-anh-2002--SWE-Misbehavior/extraction.json"
        image = subprocess.run(["docker", "image", "inspect", "intent-agent-run"],
                               capture_output=True, timeout=30)
        state["source_ready"] = completed.exists()
        state["image_ready"] = image.returncode == 0
        state["checked_at"] = datetime.now(timezone.utc).isoformat()
        (output / "supervisor.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        if state["source_ready"] and state["image_ready"]:
            break
        time.sleep(15)
    else:
        state["status"] = "blocked_preparation"
        state["reason"] = "Required task source or Claude container image did not become available within the bounded wait."
        (output / "supervisor.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        return
    subprocess.run([sys.executable, "-I", str(root / "scripts/agent_run_manifest.py")], check=True, timeout=120)
    state["status"] = "running_batch"
    (output / "supervisor.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    process = subprocess.Popen([sys.executable, "-I", str(root / "scripts/agent_run_batch.py"),
                                str(output / "swe-manifest.jsonl"), "--workers", "20"])
    state["batch_pid"] = process.pid
    (output / "supervisor.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    process.wait()
    state["status"] = "finished" if process.returncode == 0 else "batch_failed"
    state["returncode"] = process.returncode
    (output / "supervisor.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
