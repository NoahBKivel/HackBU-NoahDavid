"""Run decision-model training measurements on the dedicated Modal volume."""

import json
import os
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[3] if modal.is_local() else Path("/opt/intent-training")
CONFIG = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
GPU = os.environ.get("INTENT_TRAINING_GPU", "B200")
app = modal.App(CONFIG["modal_app"])
volume = modal.Volume.from_name(CONFIG["modal_volume"], create_if_missing=True)
pins = CONFIG["gpu_packages"]
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .uv_pip_install(
        f"kev[serve] @ git+{CONFIG['kev_repository']}.git@{CONFIG['kev_commit']}",
        f"torch=={pins['torch']}", f"transformers=={pins['transformers']}", f"peft=={pins['peft']}",
        "pytest", "numpy", "scipy", "scikit-learn",
    )
    .uv_pip_install(f"flash-linear-attention=={pins['flash-linear-attention']}", f"triton=={pins['triton']}")
    .uv_pip_install("pysbd")
    .env({"HF_HOME": "/training/hf", "HF_HUB_DISABLE_PROGRESS_BARS": "1",
          "HF_HUB_DISABLE_XET": "1",
          "INTENT_TRAINING_GPU": GPU,
          "TOKENIZERS_PARALLELISM": "false", "PYTHONUNBUFFERED": "1",
          "PYTHONPATH": "/opt/intent-training/src:/opt/intent-training", "KEV_TEMPERATURE": "1",
          "TRITON_CACHE_DIR": "/training/triton-cache",
          "INTENT_TRAINING_VOLUME": CONFIG["modal_volume"]})
    .add_local_dir(ROOT / "src" / "intent_training" / "kevpatch",
                   "/opt/intent-training/src/intent_training/kevpatch", copy=True)
    .add_local_file(ROOT / "environment.json", "/opt/intent-training/environment.json", copy=True)
    .add_local_dir(ROOT.parent / "monitor_format" if modal.is_local() else ROOT / "monitor_format",
                   "/opt/intent-training/monitor_format", copy=True, ignore=["tests", "__pycache__"])
    .run_commands("python -m intent_training.kevpatch.bootstrap")
)


@app.function(image=image, gpu=GPU, cpu=8, memory=98304, timeout=7200,
              startup_timeout=1800, volumes={"/training": volume})
def smoke(mode: str = "reference") -> dict:
    """Measure kernels, continuation correctness, memory and throughput."""
    from intent_training.kevpatch.batched_measure import run_measurement
    result = run_measurement(Path("/training"), CONFIG, mode=mode)
    volume.commit()
    return result


@app.function(image=image, gpu=GPU, cpu=8, memory=98304, timeout=21600,
              startup_timeout=1800, volumes={"/training": volume})
def train(data: str, out: str, pass_tokens: int, resume: bool = False,
          checkpointing: bool = True, expected_sha256: str = '',
          expected_records: int = 0) -> dict:
    """Continue one frozen training split with persistent adapter snapshots."""
    if resume:
        raise ValueError("Checkpoint resume is disabled after loss-parity failure; restart the run.")
    if not expected_sha256 or expected_records < 1:
        raise ValueError('Training requires the frozen artifact digest and record count.')
    import hashlib
    volume.reload()
    if not Path(data).resolve().is_relative_to('/training'):
        raise ValueError('The frozen training artifact must remain on the private volume.')
    digest = hashlib.sha256()
    count = 0
    with Path(data).open('rb') as source:
        for line in source:
            digest.update(line)
            count += bool(line.strip())
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256.lower() or count != expected_records:
        raise ValueError('The frozen training artifact changed after its admission.')
    print(json.dumps({'data_sha256': actual_sha256, 'records': count}), flush=True)
    from intent_training.kevpatch.smoke import training_command
    import subprocess
    import sys
    command = training_command({**CONFIG, 'checkpointing': int(checkpointing)},
                               Path(data), Path(out), pass_tokens)
    completed = subprocess.run(command, check=False)
    volume.commit()
    return {"returncode": completed.returncode, "data": data, "out": out,
            'data_sha256': actual_sha256, 'records': count}


@app.function(image=image, cpu=16, memory=98304, timeout=3600,
              startup_timeout=1800, volumes={"/training": volume})
def identity() -> dict:
    """Verify serialized alpha-zero weights independently of GPU measurements."""
    from datetime import datetime, timezone
    from huggingface_hub import snapshot_download
    from intent_training.kevpatch.interpolate import export_checkpoint
    volume.reload()
    checkpoint = snapshot_download(CONFIG["checkpoint"], revision=CONFIG["checkpoint_revision"],
                                   allow_patterns=["*.json", "*.safetensors", "*.pt", "*.txt", "*.jinja"], max_workers=1)
    destination = Path("/training/identity") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = export_checkpoint(checkpoint, checkpoint, 0, destination)
    result["status"] = "PASS" if result["alpha_zero_tensor_identity"] and result["written_tensor_identity"] else "FAIL"
    result["path"] = str(destination)
    (destination / "identity-parity.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    volume.commit()
    return result


@app.function(image=image, gpu=GPU, cpu=8, memory=98304, timeout=3600,
              startup_timeout=1800, volumes={"/training": volume})
def resume_check() -> dict:
    """Verify the current adapter persistence and bounded grouped batching."""
    from intent_training.kevpatch.resume_check import run_resume_check
    result = run_resume_check(CONFIG, Path("/training"))
    volume.commit()
    return result


@app.local_entrypoint()
def main(mode: str = "smoke") -> None:
    """Start the detached smoke worker and preserve its remotely resumable call ID."""
    if mode not in {"smoke", "identity", "resume"}:
        raise ValueError("The run mode must be smoke, identity or resume.")
    call = {"smoke": smoke, "identity": identity, "resume": resume_check}[mode].spawn()
    target = ROOT / "results" / "trainer" / f"modal-{mode}-call.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"function_call_id": call.object_id,
                                  "app_id": app.app_id}, indent=2), encoding="utf-8")
    print(f"{mode.capitalize()} function call: {call.object_id}", flush=True)
