"""Seal a shared real-record benchmark mixture on the training volume."""

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
         .add_local_file(ROOT / "src/intent_training/kevpatch/mixture.py",
                         "/opt/intent-training/src/intent_training/kevpatch/mixture.py", copy=True)
         .add_local_dir(ROOT / "src/intent_training/assemble",
                        "/opt/intent-training/src/intent_training/assemble", copy=True)
         .add_local_dir(ROOT / "src/intent_training/prepare",
                        "/opt/intent-training/src/intent_training/prepare", copy=True)
         if modal.is_local() else modal.Image.debian_slim())


@app.function(image=image, cpu=8, memory=32768, timeout=1800,
              startup_timeout=600, volumes={"/training": volume})
def seal(directories: list[str], plan: dict, seed: int) -> dict:
    """Sample completed record prefixes without relabelling or changing their states."""
    volume.reload()
    if any(not Path(path).is_relative_to("/training/prepared") for path in directories):
        raise ValueError("Benchmark candidates must belong to the private prepared namespace.")
    from transformers import AutoTokenizer
    from intent_training.kevpatch.mixture import build_payload
    cached = (Path("/training/hf/hub") / ("models--" + CONFIG["base"].replace("/", "--")) /
              "snapshots" / CONFIG["base_revision"])
    tokenizer = AutoTokenizer.from_pretrained(cached, local_files_only=True)
    target = (Path("/training/benchmarks") /
              datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") / "records.jsonl")
    try:
        result = build_payload(directories, plan, str(target), tokenizer, seed)
    except ValueError as error:
        return {"status": "WAITING_INPUT", "reason": str(error), "seed": seed}
    volume.commit()
    return result
