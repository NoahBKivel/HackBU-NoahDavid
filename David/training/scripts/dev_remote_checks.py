"""Run bounded development checks and CATCH reservation on the private volume."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import modal

ROOT = Path(__file__).resolve().parents[1] if modal.is_local() else Path("/opt/intent-training")
sys.path.insert(0, str(ROOT / "scripts"))
from scan_secrets import PATTERNS

config = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
volume = modal.Volume.from_name(config["modal_volume"])
app = modal.App(config["modal_app"])
image = (modal.Image.from_id("im-dfB2QMo1vkk6QHDRHLgbVJ")
         .add_local_file(ROOT / "environment.json", "/opt/intent-training/environment.json", copy=True)
         .add_local_file(ROOT / "scripts/scan_secrets.py", "/opt/intent-training/scripts/scan_secrets.py", copy=True)
         .add_local_dir(ROOT / "src", "/opt/intent-training/src", copy=True, ignore=["**/__pycache__/**", "**/*.pyc"])
         .add_local_dir(ROOT.parent / "monitor_format", "/opt/monitor_format", copy=True, ignore=["**/__pycache__/**", "**/*.pyc"])
         .add_local_dir(ROOT / "tests", "/opt/intent-training/tests", copy=True, ignore=["**/__pycache__/**", "**/*.pyc"]))


@app.function(image=image, cpu=2, memory=8192, timeout=1800, volumes={"/training": volume})
def run(work):
    import runpy
    volume.reload()
    work = Path(work)
    os.chdir(work)
    sys.path[:0] = ["/opt/intent-training/src", "/opt"]
    sys.argv = ["catch_hacking", "--limit", "237", "--dev-positive-groups", "60", "--dev-negative-groups", "60"]
    runpy.run_module("intent_training.sources.catch_hacking", run_name="__main__")
    output = work / "data/converted/catch_hacking.jsonl"
    def rows(path):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if rows(output) != rows(work / "train-baseline.jsonl"):
        raise ValueError("CATCH conversion changed the reserved training records.")
    test = subprocess.run([sys.executable, "-m", "pytest", "-q", "/opt/intent-training/tests/test_splits_dev.py",
                           "/opt/intent-training/tests/test_splits_grouping.py", "/opt/intent-training/tests/test_catch_hacking.py",
                           "/opt/intent-training/tests/test_source_aria_reward_hacking.py"],
                          env={**os.environ, "PYTHONPATH": "/opt/intent-training/src:/opt"}, capture_output=True, text=True)
    dev = work / "data/dev_candidates/catch_hacking.jsonl"
    result = {"tests_returncode": test.returncode, "tests_stdout": test.stdout, "tests_stderr": test.stderr,
              "dev_sha256": hashlib.sha256(dev.read_bytes()).hexdigest(), "dev_path": str(dev),
              "report_path": str(work / "results/sources/catch_hacking.json")}
    volume.commit()
    return result


def main():
    print("Scanning private source inputs.", flush=True)
    inputs = [ROOT / "data/downloads/catch_hacking" / name for name in
              ("hacking.json", "hacking_100.json", "nonhacking.json", "nonhacking_100.json")]
    baseline = ROOT / "data/converted/catch_hacking.jsonl"
    patterns = [re.compile(pattern) for pattern in PATTERNS]
    digest = hashlib.sha256()
    for path in inputs + [baseline]:
        payload = path.read_bytes()
        if any(pattern.search(payload.decode("utf-8-sig")) for pattern in patterns):
            raise ValueError("Credential pattern found in the source transfer.")
        digest.update(payload)
    remote = "/source-conversion/catch-dev/" + digest.hexdigest()
    print("Uploading private source inputs.", flush=True)
    with volume.batch_upload(force=True) as upload:
        for path in inputs:
            upload.put_file(path, remote + "/data/downloads/catch_hacking/" + path.name)
        upload.put_file(baseline, remote + "/train-baseline.jsonl")
    print("Launching private CPU conversion and tests.", flush=True)
    with app.run():
        result = run.remote("/training" + remote)
    print(json.dumps(result), flush=True)
    if result["tests_returncode"]:
        raise SystemExit(result["tests_returncode"])
    payload = b"".join(volume.read_file(result["dev_path"].removeprefix("/training/")))
    if hashlib.sha256(payload).hexdigest() != result["dev_sha256"]:
        raise ValueError("The collected development output failed its hash check.")
    destination = ROOT / "data/dev_candidates/catch_hacking.jsonl"
    temp = destination.with_suffix(".tmp")
    temp.write_bytes(payload)
    os.replace(temp, destination)
    report = json.loads(b"".join(volume.read_file(result["report_path"].removeprefix("/training/"))))
    report["regenerated_output_sha256"] = report["output_sha256"]
    report["output_sha256"] = hashlib.sha256(baseline.read_bytes()).hexdigest()
    (ROOT / "results/sources/catch_hacking.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
