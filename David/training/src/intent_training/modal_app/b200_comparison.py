"""Run the immutable training smoke image on a comparison GPU."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import modal

app = modal.App("intent-monitor-training")
volume = modal.Volume.from_name("intent-monitor-training")
image = (modal.Image.from_id(os.environ["B200_COMPARISON_IMAGE_ID"])
         if modal.is_local() else modal.Image.debian_slim())


@app.function(image=image, gpu="B200", cpu=8, memory=98304,
              timeout=7200, startup_timeout=600, volumes={"/training": volume})
def smoke() -> dict:
    """Execute the same smoke callable preserved in the H100 image."""
    from intent_training.kevpatch.smoke import run_smoke
    result = run_smoke(Path("/training"), Path("/opt/intent-training/environment.json"))
    volume.commit()
    return result


@app.function(image=image, gpu="B200", cpu=8, memory=98304,
              timeout=7200, startup_timeout=600, volumes={"/training": volume})
def batched_smoke(mode: str = "reference") -> dict:
    """Measure the matched native optimizer contract in the immutable image."""
    from intent_training.kevpatch.batched_measure import run_measurement
    config = json.loads(Path("/opt/intent-training/environment.json").read_text(encoding="utf-8-sig"))
    result = run_measurement(Path("/training/b200-check"), config, mode=mode)
    volume.commit()
    return result


@app.local_entrypoint()
def main(benchmark: str = "batched", mode: str = "reference") -> None:
    """Persist the submitted call identity before returning from deployment."""
    root = Path(__file__).resolve().parents[3] / "results" / "b200-check"
    if benchmark not in {"historical", "batched"}:
        raise ValueError("The benchmark must be historical or batched.")
    if benchmark == "batched":
        root = root / "batched" / mode
        previous = root / "modal-call.json"
        if previous.exists():
            record = json.loads(previous.read_text(encoding="utf-8"))
            if record["image_id"] != os.environ["B200_COMPARISON_IMAGE_ID"]:
                root = root / os.environ["B200_COMPARISON_IMAGE_ID"]
    root.mkdir(parents=True, exist_ok=True)
    target = root / "modal-call.json"
    if target.exists():
        raise RuntimeError("A comparison call is already recorded. Retrieve it before launching another.")
    started = datetime.now(timezone.utc).isoformat()
    call = smoke.spawn() if benchmark == "historical" else batched_smoke.spawn(mode)
    target.write_text(json.dumps({"app_id": app.app_id,
        "function_call_id": call.object_id,
        "submitted_at": started,
        "image_id": os.environ["B200_COMPARISON_IMAGE_ID"],
        "gpu": "B200", "benchmark": benchmark, "mode": mode}, indent=2), encoding="utf-8")
    print(target.read_text(encoding="utf-8"), flush=True)
