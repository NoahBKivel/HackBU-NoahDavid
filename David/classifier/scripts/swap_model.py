"""Copy a read-only training handoff into a runtime volume and recreate its service."""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import modal

FOLDER = Path(__file__).resolve().parents[1]


def swap(target: str, source: str | None, receipt_path: Path) -> dict:
    """Copy a validated remote handoff and deploy its model with the validated length."""
    app_name = "intent-monitor-dev" if target == "dev" else "intent-monitor"
    volume_name = "intent-monitor-model-dev" if target == "dev" else "intent-monitor-model"
    helper = modal.App(app_name)
    origin = modal.Volume.from_name("intent-monitor-training").with_mount_options(read_only=True)
    destination = modal.Volume.from_name(volume_name, create_if_missing=True)
    image = (modal.Image.debian_slim(python_version="3.13").pip_install("pysbd")
             .add_local_dir(FOLDER / "src" / "intent_runtime", "/root/intent_runtime")
             .add_local_dir(FOLDER.parents[0] / "monitor_format", "/root/David/monitor_format"))

    @helper.function(image=image, volumes={"/handoff": origin, "/model": destination}, cpu=2, timeout=1800)
    def copy_selected(version: str, explicit_source: str | None) -> dict:
        from intent_runtime.handoff import copy_handoff
        result = copy_handoff(Path("/handoff"), Path("/model"), version, explicit_source)
        destination.commit()
        return result

    version = uuid.uuid4().hex
    receipt = {"target": target, "app": app_name, "volume": volume_name, "version": version,
               "started_at": datetime.now(timezone.utc).isoformat(), "deployed": False}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with helper.run():
            receipt.update(copy_selected.remote(version, source))
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        environment = {**os.environ, "PYTHONUTF8": "1", "INTENT_MONITOR_TARGET": target,
                       "INTENT_MONITOR_LENGTH": str(receipt["validated_length"])}
        deploy = [sys.executable, "-m", "modal", "deploy", str(FOLDER / "app.py"), "--strategy", "recreate"]
        subprocess.run(deploy, env=environment, check=True)
        subprocess.run([sys.executable, "-m", "modal", "app", "rollover", app_name, "--strategy", "recreate"],
                       env=environment, check=True)
        receipt["deployed"] = True
        receipt["completed_at"] = datetime.now(timezone.utc).isoformat()
        return receipt
    except Exception as error:
        receipt["error_type"] = type(error).__name__
        raise
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")


def main() -> int:
    """Swap the selected model into dev or live and save a local copy receipt."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("dev", "live"), required=True)
    parser.add_argument("--source", choices=("stock-kev", "kev-tuned"))
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    receipt_path = args.receipt or FOLDER / "results" / "model-swap" / f"{args.target}-{uuid.uuid4().hex}.json"
    receipt = swap(args.target, args.source, receipt_path)
    print(json.dumps(receipt), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
