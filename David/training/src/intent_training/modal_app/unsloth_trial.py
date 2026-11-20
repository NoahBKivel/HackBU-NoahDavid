"""Run the matched decision benchmark in an immutable remote GPU image."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[3] if modal.is_local() else Path("/opt/intent-training")
CONFIG = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
app = modal.App(CONFIG["modal_app"])
volume = modal.Volume.from_name(CONFIG["modal_volume"])
image = (modal.Image.from_id(os.environ["INTENT_MEASUREMENT_IMAGE_ID"])
         if modal.is_local() else modal.Image.debian_slim())
GPU = os.environ.get("INTENT_MEASUREMENT_GPU", "H100")


@app.function(image=image, gpu=GPU, cpu=8, memory=98304,
              timeout=7200, startup_timeout=600, volumes={"/training": volume})
def measurement(mode: str, source_contract: dict, measurement_records: str = "") -> dict:
    """Run complete native optimizer-step measurements without altering the source image."""
    from intent_training.kevpatch.batched_measure import run_measurement
    config = dict(CONFIG)
    config["accelerator_source"] = source_contract
    if measurement_records:
        config["measurement_records"] = measurement_records
    result = run_measurement(Path("/training/measurements"), config, mode)
    volume.commit()
    return result


@app.local_entrypoint()
def main(mode: str = "unsloth", measurement_records: str = "") -> None:
    """Record the detached call identity for later retrieval without duplicate launches."""
    if mode not in {"reference", "unsloth"}:
        raise ValueError("The measurement mode must be reference or unsloth.")
    target = ROOT / "results" / "unsloth"
    target.mkdir(parents=True, exist_ok=True)
    source = json.loads((target / "source-contract.json").read_text(encoding="utf-8"))
    destination = target / f"modal-{mode}-call.json"
    if destination.exists():
        raise RuntimeError("A measurement call is already recorded. Retrieve it before another launch.")
    call = measurement.spawn(mode, source, measurement_records)
    destination.write_text(json.dumps({"app_id": app.app_id, "function_call_id": call.object_id,
        "image_id": os.environ["INTENT_MEASUREMENT_IMAGE_ID"], "gpu": GPU, "mode": mode,
        "submitted_at": datetime.now(timezone.utc).isoformat()}, indent=2), encoding="utf-8")
    print(destination.read_text(encoding="utf-8"), flush=True)
