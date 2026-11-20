"""Run Accelerate decision training and fixed-batch parity on four B200s."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import modal

ROOT = Path(__file__).resolve().parents[3] if modal.is_local() else Path("/opt/intent-training")
CONFIG = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
app = modal.App(CONFIG["modal_app"])
volume = modal.Volume.from_name(CONFIG["modal_volume"])
image = (modal.Image.from_id(os.environ["INTENT_MEASUREMENT_IMAGE_ID"])
         .add_local_dir(ROOT / "src/intent_training/kevpatch",
                        "/opt/intent-training/src/intent_training/kevpatch", copy=True)
         if modal.is_local() else modal.Image.debian_slim())


from intent_training.kevpatch.distributed_accelerate import compare_losses


@app.function(image=image, gpu="B200:4", cpu=16, memory=196608,
              timeout=10800, startup_timeout=600, volumes={"/training": volume})
def run_accelerate(records_path: str, mode: str = "parity", pass_tokens: int = 115200,
                   fixed_records: int = 16, expected_sha256: str | None = None,
                   expected_records: int | None = None, resume_from: str | None = None,
                   original_config: str | None = None, absolute_deadline_utc: str | None = None,
                   continuation_release: str | None = None, original_call_id: str | None = None) -> dict[str, Any]:
    """Execute isolated reference and distributed workers with the same pinned inputs."""
    volume.reload()
    source = Path(records_path)
    if not source.is_relative_to("/training") or not source.is_file():
        raise ValueError("The records must exist on the training volume.")
    if mode == "train":
        from intent_training.kevpatch.distributed_accelerate import verify_frozen_input
        verification = verify_frozen_input(source, expected_sha256 or "", expected_records or 0)
        print(json.dumps({"frozen_input_verified": verification}), flush=True)
    if resume_from:
        if mode != "train" or not original_config or not absolute_deadline_utc:
            raise ValueError("Continuation requires training, original config, and absolute deadline.")
        original_path = Path(original_config)
        if not original_path.is_relative_to("/training/accelerate") or Path(resume_from) != original_path.parent / "train" / "resume":
            raise ValueError("Continuation must point to the original training resume directory.")
        if continuation_release and (not original_call_id or not Path(continuation_release).is_relative_to("/training/accelerate")):
            raise ValueError("Warm continuation requires an original call ID and volume release path.")
        original = json.loads(original_path.read_text())
        if (original["records_path"] != records_path or original["pass_tokens_max"] != pass_tokens
                or original["mode"] != "train"):
            raise ValueError("Continuation inputs differ from the original configuration.")
    root = Path("/training/accelerate") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    root.mkdir(parents=True)
    import importlib.metadata
    packages = {name: importlib.metadata.version(name) for name in CONFIG["gpu_packages"]}
    for name, expected in CONFIG["gpu_packages"].items():
        if packages[name].split("+")[0] != expected:
            raise RuntimeError(f"The environment differs from its pinned package: {name}.")
    accelerate_version = importlib.metadata.version("accelerate")
    configs = []
    if mode == "parity":
        configs = [("reference", 1), ("distributed", 4)]
    elif mode in {"benchmark", "train"}:
        configs = [(mode, 4)]
    else:
        raise ValueError("Unknown execution mode.")
    results = {}
    for name, world in configs:
        destination = root / name
        config = {**CONFIG, "records_path": records_path, "output": str(destination),
                  "mode": mode, "max_state": 8192, "seed": 1,
                  "pass_tokens_max": pass_tokens, "steps": 3,
                  "projection_records": 12200}
        if resume_from:
            config = {**original, "output": str(destination), "resume_from": resume_from,
                      "expected_sha256": expected_sha256, "expected_records": expected_records,
                      "absolute_deadline_utc": absolute_deadline_utc,
                      "continuation_release": continuation_release, "original_call_id": original_call_id}
        if mode == "parity":
            config["fixed_records"] = fixed_records
            config["partition_world"] = 4
        path = root / f"{name}-config.json"
        path.write_text(json.dumps(config))
        if resume_from:
            volume.commit()
        module = "intent_training.kevpatch.distributed_accelerate"
        command = [sys.executable, "-m", module, str(path)] if world == 1 else [
            sys.executable, "-m", "accelerate.commands.launch", "--multi_gpu",
            "--num_processes", str(world), "--num_machines", "1", "--mixed_precision", "no",
            "--dynamo_backend", "no", "--module", module, str(path)]
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "TOKENIZERS_PARALLELISM": "false"}
        stdout_path = Path(f"/tmp/continuation-{name}.stdout.log") if resume_from else root / f"{name}.stdout.log"
        stderr_path = Path(f"/tmp/continuation-{name}.stderr.log") if resume_from else root / f"{name}.stderr.log"
        with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
            process = subprocess.run(command, env=env, stdout=stdout, stderr=stderr,
                                     timeout=9600, check=False)
        if resume_from:
            (root / f"{name}.stdout.log").write_text(stdout_path.read_text())
            (root / f"{name}.stderr.log").write_text(stderr_path.read_text())
        volume.commit()
        if process.returncode:
            result = {"status": "ERROR", "path": str(root), "failed_worker": name,
                      "returncode": process.returncode,
                      "stderr_tail": (root / f"{name}.stderr.log").read_text()[-12000:]}
            (root / "result.json").write_text(json.dumps(result, indent=2))
            volume.commit()
            return result
        results[name] = json.loads((destination / "result.json").read_text())
    gate = compare_losses(results["reference"], results["reference"], results["distributed"]) if mode == "parity" else {"status": "MEASURED"}
    if mode == "parity":
        gate["same_seed_noise_floor_measured"] = False
    result = {"path": str(root), "mode": mode, "packages": packages,
              "accelerate_version": accelerate_version, "gate": gate,
              "workers": results, "status": gate["status"]}
    (root / "result.json").write_text(json.dumps(result, indent=2))
    volume.commit()
    return result


@app.function(image=image, gpu="B200", cpu=8, memory=98304,
              timeout=1800, startup_timeout=600, volumes={"/training": volume})
def repeat_reference(previous_root: str) -> dict[str, Any]:
    """Measure same-seed reference noise only after a distributed comparison needs it."""
    volume.reload()
    previous = Path(previous_root)
    if not previous.is_relative_to("/training/accelerate"):
        raise ValueError("The prior comparison must belong to this trainer.")
    config = json.loads((previous / "reference-config.json").read_text())
    destination = previous / "repeat"
    config["output"] = str(destination)
    path = previous / "repeat-config.json"
    path.write_text(json.dumps(config))
    command = [sys.executable, "-m", "intent_training.kevpatch.distributed_accelerate", str(path)]
    with (previous / "repeat.stdout.log").open("w") as stdout, (previous / "repeat.stderr.log").open("w") as stderr:
        process = subprocess.run(command, stdout=stdout, stderr=stderr,
                                 env={**os.environ, "PYTHONUNBUFFERED": "1"}, timeout=1500)
    if process.returncode:
        result = {"status": "ERROR", "returncode": process.returncode,
                  "stderr_tail": (previous / "repeat.stderr.log").read_text()[-12000:]}
    else:
        reference = json.loads((previous / "reference/result.json").read_text())
        repeat = json.loads((destination / "result.json").read_text())
        distributed = json.loads((previous / "distributed/result.json").read_text())
        result = compare_losses(reference, repeat, distributed)
        result["same_seed_noise_floor_measured"] = True
        result["reference_path"] = str(previous)
    (previous / "noise-result.json").write_text(json.dumps(result, indent=2))
    volume.commit()
    return result
