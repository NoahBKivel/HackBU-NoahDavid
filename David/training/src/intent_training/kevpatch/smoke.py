"""Coordinate persistent correctness and throughput measurements."""

from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import sys
import time
import traceback
from typing import Any


def training_command(config: dict[str, Any], data: Path, out: Path,
                     pass_tokens: int) -> list[str]:
    """Build the agreed continuation recipe with one frozen data file."""
    return [sys.executable, "-m", "kev.train", "--init_from",
            config.get("checkpoint_path", f"{config['checkpoint']}@{config['checkpoint_revision']}"), "--base", config["base"],
            "--base_revision", config["base_revision"], "--lora", "16", "--lora_targets", "all",
            "--head_dim", "256", "--data", str(data), "--max_state", "8192",
            "--shared_prefix", "1", "--length_sort", "1", "--pass_tokens_max", str(pass_tokens),
            "--p_none_pair", "0", "--p_none", "0", "--p_none_distract", "0", "--p_distract", "0",
            "--epochs", "1", "--lr", "2e-5", "--batch", "2", "--accum", "8",
            "--dtype", "bf16", "--checkpointing", str(int(config.get('checkpointing', 1))), "--device", "cuda", "--seed", "1", "--out", str(out)]


def run_smoke(volume_root: Path, config_path: Path) -> dict[str, Any]:
    """Persist every measurement before moving to the next correctness check."""
    import modal
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = volume_root / "smoke" / run_id
    root.mkdir(parents=True, exist_ok=False)
    results = {"run_id": run_id, "started": datetime.now(timezone.utc).isoformat(),
               "packages": {name: importlib.metadata.version(name) for name in config["gpu_packages"]}}

    def save(name: str, value: Any) -> None:
        results[name] = value
        (root / f"{name}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
        (root / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        modal.Volume.from_name(config["modal_volume"]).commit()
        print(json.dumps({"measurement": name, "path": str(root / f"{name}.json"), "status": value.get("status") if isinstance(value, dict) else None}), flush=True)

    try:
        from huggingface_hub import snapshot_download
        for attempt in range(1, 4):
            try:
                config["checkpoint_path"] = snapshot_download(
                    config["checkpoint"], revision=config["checkpoint_revision"],
                    allow_patterns=["*.json", "*.safetensors", "*.pt", "*.txt", "*.jinja"],
                    max_workers=1,
                )
                save("checkpoint-download", {"status": "PASS", "attempt": attempt})
                break
            except Exception as error:
                save("checkpoint-download", {"status": "retry", "attempt": attempt,
                                              "error_type": type(error).__name__})
                if attempt == 3:
                    raise
                time.sleep(2)
        from .measure import kernel_and_memory
        kernel_and_memory(config, save)
        from .resume_probe import check_resume
        resume = check_resume(config, root, training_command, save)
        if resume["status"] != "PASS":
            save("resume-fallback", {"status": "reference-rerun", "reason": "Continuation losses or order failed parity."})
        from .interpolate import export_checkpoint
        stock = config["checkpoint_path"]
        identity = export_checkpoint(stock, stock, 0, root / "stock-full")
        identity["status"] = "PASS" if identity["alpha_zero_tensor_identity"] else "FAIL"
        save("identity-parity", identity)
        save("accelerated-kernel-parity", {"status": "reference-fallback", "accelerated_kernels_adopted": False})
        save("finished", {"status": "PASS", "time": datetime.now(timezone.utc).isoformat()})
    except BaseException as error:
        save("error", {"status": "FAIL", "type": type(error).__name__, "message": str(error)})
        traceback.print_exc()
        raise
    return results
