"""Reserve independent HelpSteer preference groups on the private volume."""

import hashlib
import json
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1] if modal.is_local() else Path("/opt/intent-training")
CONFIG = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
volume = modal.Volume.from_name(CONFIG["modal_volume"])
app = modal.App(CONFIG["modal_app"])
image = (modal.Image.from_id("im-dfB2QMo1vkk6QHDRHLgbVJ")
         .add_local_file(ROOT / "environment.json", "/opt/intent-training/environment.json", copy=True)
         .add_local_file(ROOT / "scripts/scan_secrets.py", "/opt/intent-training/scripts/scan_secrets.py", copy=True)
         .add_local_dir(ROOT / "src", "/opt/intent-training/src", copy=True, ignore=["**/__pycache__/**", "**/*.pyc"])
         .add_local_dir(ROOT.parent / "monitor_format", "/opt/monitor_format", copy=True, ignore=["**/__pycache__/**", "**/*.pyc"]))


@app.function(image=image, cpu=2, memory=8192, timeout=1800, volumes={"/training": volume})
def reserve(prefix, offset, target):
    import re
    import sys
    import urllib.parse
    import urllib.request
    sys.path[:0] = ["/opt/intent-training/src", "/opt/intent-training/scripts", "/opt"]
    from scan_secrets import PATTERNS
    from intent_training.sources.helpsteer3 import convert
    volume.reload()
    root = Path(prefix)
    training = [json.loads(line) for line in (root / "train.jsonl").read_text(encoding="utf-8").splitlines() if line]
    reserved = {row["meta"]["task_id"] for row in training}
    rawdir = root / "raw"
    rawdir.mkdir(parents=True, exist_ok=True)
    raw = rawdir / "preference.jsonl"
    fetched = []
    for start in range(offset, offset + 2000, 100):
        params = urllib.parse.urlencode(dict(dataset="nvidia/HelpSteer3", config="preference", split="train", offset=start, length=100))
        with urllib.request.urlopen("https://datasets-server.huggingface.co/rows?" + params, timeout=45) as response:
            batch = json.load(response).get("rows", [])
        if not batch:
            break
        fetched.extend(batch)
        if sum(abs(row["row"]["overall_preference"]) >= 2 for row in fetched) >= target * 2:
            break
    raw.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in fetched), encoding="utf-8")
    groups = {}
    for events, side, meta in convert(rawdir):
        if meta["task_id"] not in reserved:
            groups.setdefault(meta["task_id"], []).append({"events": events, "side": side, "meta": {**meta, "split": "dev"}})
    selected = list(groups.items())[:target]
    output = root / "candidates.jsonl"
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for _, rows in selected for row in rows)
    if any(re.search(pattern, payload) for pattern in PATTERNS):
        raise ValueError("A credential pattern was found in the reserved source records.")
    output.write_text(payload, encoding="utf-8")
    result = {"source": "helpsteer3", "start_offset": offset, "fetched_source_rows": len(fetched),
              "reserved_groups": len(selected), "records": sum(len(rows) for _, rows in selected),
              "train_group_overlap": len(set(dict(selected)) & reserved), "output_path": str(output),
              "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
              "train_sha256": hashlib.sha256((root / "train.jsonl").read_bytes()).hexdigest(),
              "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(), "credential_scan": "PASS"}
    (root / "manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    volume.commit()
    return result


def main():
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from scan_secrets import PATTERNS
    import re
    path = ROOT / "data/converted/helpsteer3.jsonl"
    raw_prefix = ROOT / "data/downloads/helpsteer3/preference.jsonl"
    with raw_prefix.open(encoding="utf-8") as stream:
        offset = max(json.loads(line)["row_idx"] for line in stream if line.strip()) + 1
    payload = path.read_bytes()
    if any(re.search(pattern, payload.decode("utf-8")) for pattern in PATTERNS):
        raise ValueError("A credential pattern was found in the training source file.")
    prefix = "/source-conversion/helpsteer-dev/" + hashlib.sha256(payload).hexdigest()
    with volume.batch_upload(force=True) as upload:
        upload.put_file(path, prefix + "/train.jsonl")
    with app.run(detach=True):
        call = reserve.spawn("/training" + prefix, offset, 200)
        print(json.dumps({"app_id": app.app_id, "function_call_id": call.object_id, "output_root": "/training" + prefix}), flush=True)


if __name__ == "__main__":
    main()
