"""Render private training inputs on the dedicated CPU volume."""

import json
import os
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[3] if modal.is_local() else Path("/opt/intent-training")
CONFIG = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
app = modal.App(CONFIG["modal_app"])
volume = modal.Volume.from_name(CONFIG["modal_volume"], create_if_missing=True)
image = (
    modal.Image.from_id("im-dfB2QMo1vkk6QHDRHLgbVJ")
    .add_local_dir(ROOT / "src", "/opt/intent-training/src", copy=True,
                   ignore=["**/__pycache__/**", "**/*.pyc"])
    .add_local_file(ROOT / "scripts" / "prepare_records.py",
                    "/opt/intent-training/scripts/prepare_records.py", copy=True)
)


@app.function(image=image, cpu=8, memory=32768, timeout=7200,
              startup_timeout=1200, volumes={"/training": volume})
def prepare(input_path: str, output_root: str, limit: int = 30, state_budget: int = 8191,
            construction_filter: str | None = None) -> dict:
    """Run the trusted formatter with the current input budget and private paths."""
    import subprocess
    import sys
    volume.reload()
    base = CONFIG["base"].replace("/", "--")
    cached = Path("/training/hf/hub") / f"models--{base}" / "snapshots" / CONFIG["base_revision"]
    if not (cached / "tokenizer.json").exists():
        from huggingface_hub import snapshot_download
        cached = Path(snapshot_download(CONFIG["base"], revision=CONFIG["base_revision"],
                    allow_patterns=["tokenizer*", "special_tokens_map.json", "config.json", "vocab*", "merges.txt"], max_workers=1))
    destination = Path(output_root)
    if not destination.is_relative_to(Path("/training")) or not Path(input_path).is_relative_to(Path("/training")):
        raise ValueError("Preparation inputs and outputs must remain on the training volume.")
    destination.mkdir(parents=True, exist_ok=True)
    if construction_filter:
        filtered = destination / "source-input.jsonl"
        selected = 0
        with Path(input_path).open(encoding="utf-8") as source, filtered.open("w", encoding="utf-8") as target:
            for line in source:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("side", {}).get("construction", {}).get("type") == construction_filter:
                    target.write(line.rstrip("\r\n") + "\n")
                    selected += 1
        if not selected:
            raise ValueError("The existing packet contains no requested construction rows.")
        input_path = str(filtered)
    argv = [sys.executable, "-I", "/opt/intent-training/scripts/prepare_records.py",
            "--remote-input", input_path, "--output-root", output_root,
            "--state-budget", str(state_budget), "--limit", str(limit),
            "--tokenizer-dir", str(cached), "--emit-first", "3"]
    with (destination / "formatter.stdout.log").open("a", encoding="utf-8") as stdout, (destination / "formatter.stderr.log").open("a", encoding="utf-8") as stderr:
        process = subprocess.Popen(argv, cwd="/opt/intent-training", stdout=subprocess.PIPE,
                                   stderr=stderr, text=True, bufsize=1)
        for line in process.stdout:
            stdout.write(line)
            stdout.flush()
            print(line, end='', flush=True)
            volume.commit()
        returncode = process.wait()
    result = {"returncode": returncode, "input_path": input_path,
              "output_root": output_root, "b_state": state_budget, "max_state": state_budget + 1,
              "files": [str(path) for path in destination.rglob("*") if path.is_file()]}
    (destination / "remote-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    volume.commit()
    print(json.dumps(result), flush=True)
    return result
