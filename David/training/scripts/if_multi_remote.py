"""Run and collect one immutable official IF verifier cohort in private Modal."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Launch an isolated verifier cohort or collect its completed JSON evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--collect", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "scripts"))
    import modal
    config = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
    volume = modal.Volume.from_name(config["modal_volume"])
    if args.collect:
        manifest = json.loads(args.collect.read_text(encoding="utf-8"))
        result = modal.FunctionCall.from_id(manifest["function_call_id"]).get(timeout=1)
        destination = ROOT / "data/downloads/if_multi/checks"
        destination.mkdir(parents=True, exist_ok=True)
        for name in result["files"]:
            payload = b"".join(volume.read_file(result["output"].removeprefix("/training/") + "/" + name))
            value = json.loads(payload)
            if name != value["id"] + ".json":
                raise ValueError("A verifier evidence identity disagrees with its filename.")
            temporary = destination / (name + ".tmp")
            temporary.write_bytes(payload)
            temporary.replace(destination / name)
        print(json.dumps(result), flush=True)
        return
    source = args.input.resolve()
    if not source.is_relative_to(ROOT / "data"):
        raise ValueError("Verifier inputs must stay inside the build data directory.")
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != args.sha256:
        raise ValueError("The verifier input differs from the immutable requested cohort.")
    from scan_secrets import PATTERNS
    patterns = [re.compile(pattern) for pattern in PATTERNS]
    decoded = [json.loads(line) for line in payload.decode("utf-8-sig").splitlines() if line.strip()]
    if any(pattern.search(payload.decode("utf-8-sig")) or
           pattern.search(json.dumps(decoded, ensure_ascii=False)) for pattern in patterns):
        raise ValueError("The verifier cohort matched a credential pattern.")
    checker = ROOT / "data/downloads/if_multi/checkers"
    for path in checker.rglob("*.py"):
        if any(pattern.search(path.read_text(encoding="utf-8")) for pattern in patterns):
            raise ValueError("The official verifier code matched a credential pattern.")
    app = modal.App(config["modal_app"])
    expected_count = len(decoded)
    image = (modal.Image.debian_slim(python_version=f"{sys.version_info.major}.{sys.version_info.minor}")
        .pip_install("nltk", "langdetect", "absl-py", "immutabledict")
        .run_commands("python -m nltk.downloader -d /usr/local/share/nltk_data punkt punkt_tab")
        .add_local_dir(checker, "/opt/checkers", copy=True, ignore=["Dockerfile", "**/__pycache__/**"])
        .add_local_file(ROOT / "scripts/if_multi_check.py", "/opt/if_multi_check.py", copy=True)
        .add_local_file(source, "/opt/if_multi_input.jsonl", copy=True))

    @app.function(image=image, cpu=2, memory=4096, timeout=1800, serialized=True,
                  block_network=True, volumes={"/training": volume})
    def check():
        import subprocess
        output = Path("/training/source-checks/if-multi") / digest
        output.mkdir(parents=True, exist_ok=True)
        process = subprocess.run([sys.executable, "-I", "/opt/if_multi_check.py",
            "--checkers", "/opt/checkers", "--input", "/opt/if_multi_input.jsonl",
            "--isolation", "modal"], capture_output=True, text=True, timeout=1500, check=True)
        files = []
        for line in process.stdout.splitlines():
            row = json.loads(line)
            ident = row["id"]
            if not re.fullmatch(r"[A-Za-z0-9_-]+", ident):
                raise ValueError("Unsafe verifier evidence identifier.")
            name = ident + ".json"
            temporary = output / (name + ".tmp")
            temporary.write_text(line + "\n", encoding="utf-8")
            os.replace(temporary, output / name)
            files.append(name)
        if len(files) != expected_count or len(set(files)) != len(files):
            raise ValueError("The verifier cohort did not produce exactly one result per input.")
        volume.commit()
        return {"output": str(output), "sha256": digest, "records": len(files), "files": files}

    with app.run(detach=True):
        call = check.spawn()
        manifest = {"app_id": app.app_id, "function_call_id": call.object_id,
                    "input_sha256": digest, "records": len(decoded), "isolation": "modal"}
        destination = ROOT / "results/remote-preparation/if-multi-checker-manifest.json"
        destination.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
