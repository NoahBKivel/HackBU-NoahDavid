"""Verify the current grouped trainer after implementation amendments."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def run_resume_check(config: dict[str, Any], volume_root: Path) -> dict[str, Any]:
    """Run real continuation parity and retain the exact tested source hashes."""
    import modal
    from huggingface_hub import snapshot_download
    from .resume_probe import check_resume
    from .smoke import training_command
    config = dict(config)
    config["checkpoint_path"] = snapshot_download(
        config["checkpoint"], revision=config["checkpoint_revision"],
        allow_patterns=["*.json", "*.safetensors", "*.pt", "*.txt", "*.jinja"], max_workers=1)
    root = volume_root / "resume-check" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root.mkdir(parents=True, exist_ok=False)

    def save(name: str, value: Any) -> None:
        (root / f"{name}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
        modal.Volume.from_name(config["modal_volume"]).commit()
        print(json.dumps({"measurement": name, "status": value.get("status"), "path": str(root)}), flush=True)

    result = check_resume(config, root, training_command, save)
    result["source_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in Path(__file__).parent.glob("*.py")}
    result["path"] = str(root)
    save("verified-resume", result)
    return result
