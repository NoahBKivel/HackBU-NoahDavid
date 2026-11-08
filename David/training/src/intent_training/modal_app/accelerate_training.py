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
                   fixed_records: int = 16) -> dict[str, Any]:
    """Execute isolated reference and distributed workers with the same pinned inputs."""
    volume.reload()
    source = Path(records_path)
    if not source.is_relative_to("/training") or not source.is_file():
        raise ValueError("The records must exist on the training volume.")
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
        if mode == "parity":
            config["fixed_records"] = fixed_records
            config["partition_world"] = 4
        path = root / f"{name}-config.json"
        path.write_text(json.dumps(config))
        module = "intent_training.kevpatch.distributed_accelerate"
        command = [sys.executable, "-m", module, str(path)] if world == 1 else [
            sys.executable, "-m", "accelerate.commands.launch", "--multi_gpu",
            "--num_processes", str(world), "--num_machines", "1", "--mixed_precision", "no",
            "--dynamo_backend", "no", "--module", module, str(path)]
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "TOKENIZERS_PARALLELISM": "false"}
        with (root / f"{name}.stdout.log").open("w") as stdout, (root / f"{name}.stderr.log").open("w") as stderr:
            process = subprocess.run(command, env=env, stdout=stdout, stderr=stderr,
                                     timeout=9600, check=False)
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
