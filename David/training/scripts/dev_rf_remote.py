"""Deduplicate private development RF requests while retaining every parent link."""

import json
from pathlib import Path
import modal

ROOT = Path(__file__).resolve().parents[1] if modal.is_local() else Path("/opt/intent-training")
CONFIG = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
volume = modal.Volume.from_name(CONFIG["modal_volume"])
app = modal.App(CONFIG["modal_app"])
image = (modal.Image.from_id("im-dfB2QMo1vkk6QHDRHLgbVJ")
         .add_local_file(ROOT / "environment.json", "/opt/intent-training/environment.json", copy=True)
         .add_local_dir(ROOT / "src", "/opt/intent-training/src", copy=True, ignore=["**/__pycache__/**", "**/*.pyc"])
         .add_local_dir(ROOT / "tests", "/opt/intent-training/tests", copy=True, ignore=["**/__pycache__/**", "**/*.pyc"])
         .add_local_dir(ROOT.parent / "monitor_format", "/opt/monitor_format", copy=True, ignore=["**/__pycache__/**", "**/*.pyc"]))


@app.function(image=image, cpu=2, memory=8192, timeout=3600, volumes={"/training": volume})
def run(folder):
    import hashlib
    import os
    import subprocess
    import sys
    folder = Path(folder)
    if not folder.is_relative_to(Path("/training/prepared")):
        raise ValueError("Development inputs must remain on the training volume.")
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "/opt/intent-training/tests/test_splits_dev.py", "/opt/intent-training/tests/test_splits_grouping.py"],
                           env={**os.environ, "PYTHONPATH": "/opt/intent-training/src:/opt"}, capture_output=True, text=True)
    if tests.returncode:
        raise ValueError(tests.stdout + tests.stderr)
    volume.reload()
    decision_fields = ("state", "questions", "teacher_side", "source", "pass", "purpose", "row_context")
    seen = {}
    count = 0
    unique = folder / "requirements-dev-unique.jsonl"
    fanout = folder / "requirements-dev-fanout.jsonl"
    with (folder / "requirements.jsonl").open(encoding="utf-8") as source, unique.open("w", encoding="utf-8") as output, fanout.open("w", encoding="utf-8") as links:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            content = {key: row[key] for key in decision_fields if key in row}
            if any(key not in content for key in ("state", "questions", "teacher_side", "source", "pass")):
                raise ValueError("An RF request lacks a teacher decision field.")
            key = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            if key not in seen:
                seen[key] = row["record_id"]
                output.write(json.dumps(row, ensure_ascii=False) + "\n")
            links.write(json.dumps({"canonical_record_id": seen[key], "record_id": row["record_id"],
                                    "parent_record_id": row.get("parent_record_id"), "unit_id": row.get("unit_id")}) + "\n")
            count += 1
    result = {"requirements": count, "unique": len(seen), "fanout": count,
              "unique_path": str(unique), "fanout_path": str(fanout),
              "tests": tests.stdout.strip(), "decision_fields": list(decision_fields)}
    (folder / "requirements-dev-dedup-manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    volume.commit()
    return result


if __name__ == "__main__":
    with app.run(detach=True):
        call = run.spawn("/training/prepared/dev-catch-all-cuts-8191")
        print(json.dumps({"app_id": app.app_id, "function_call_id": call.object_id}), flush=True)
