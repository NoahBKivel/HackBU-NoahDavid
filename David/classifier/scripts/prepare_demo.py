"""Prepare identical fresh project copies for a two-session refund demonstration."""

import argparse
import hashlib
import json
import shutil
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(destination: Path) -> dict:
    """Copy the same fixture into both arms and verify their starting file identities."""
    if destination.exists():
        raise FileExistsError("Use a new destination so previous sessions remain preserved.")
    scene = json.loads((ROOT / "demos/refund-scene.json").read_text(encoding="utf-8"))
    template = ROOT / "demos" / scene["fixture"]
    arms = {}
    for name in ("without-monitor", "with-monitor"):
        folder = destination / name
        shutil.copytree(template, folder, ignore=shutil.ignore_patterns("PROMPT.md", "__pycache__"))
        subprocess.run(["git", "-c", f"safe.directory={folder}", "init", "--quiet"], cwd=folder, check=True)
        settings = folder / ".claude/settings.json"
        settings.parent.mkdir()
        excludes = [str(parent / "CLAUDE.md").replace("\\", "/") for parent in folder.parents]
        excludes += [str(Path.home() / ".claude/CLAUDE.md").replace("\\", "/")]
        settings.write_text(json.dumps({"claudeMdExcludes": excludes, "autoMemoryEnabled": False}), encoding="utf-8")
        hashes = {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in folder.rglob("*") if p.is_file() and ".git" not in p.relative_to(folder).parts}
        arms[name] = {"path": str(folder), "files": hashes}
    assert arms["without-monitor"]["files"] == arms["with-monitor"]["files"]
    receipt = {"model": scene["model"], "required_classifier_source": scene["required_classifier_source"],
               "prompt": (ROOT / "demos" / scene["prompt_file"]).read_text(encoding="utf-8").strip(), "arms": arms}
    (destination / "pair.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or ROOT / "results" / "scenes" / uuid.uuid4().hex
    print(json.dumps(prepare(output.resolve()), indent=2))
