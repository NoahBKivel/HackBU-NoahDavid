"""Upload scanned bounded source files and launch their trusted CPU conversion."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Launch one assigned source expansion or atomically collect its result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["aria_reward_hacking", "olmo_reward_hacking"])
    parser.add_argument("--target", type=int, default=158)
    parser.add_argument("--collect", type=Path)
    args = parser.parse_args()
    import modal
    config = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
    volume = modal.Volume.from_name(config["modal_volume"])
    if args.collect:
        manifest = json.loads(args.collect.read_text(encoding="utf-8"))
        report = modal.FunctionCall.from_id(manifest["function_call_id"]).get(timeout=1)
        destination = ROOT / "data/converted" / (report["source"] + ".jsonl")
        payload = b"".join(volume.read_file(report["output"].removeprefix("/training/")))
        if hashlib.sha256(payload).hexdigest() != report["output_sha256"]:
            raise ValueError("The collected conversion hash differs from its report.")
        previous = destination.read_bytes()
        if not payload.startswith(previous):
            raise ValueError("The collected conversion does not preserve the current source prefix.")
        temporary = destination.with_suffix(".jsonl.tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, destination)
        (ROOT / "results/sources" / (report["source"] + ".json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report), flush=True)
        return
    sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
    from scan_secrets import PATTERNS
    patterns = [re.compile(pattern) for pattern in PATTERNS]
    names = ["rows.jsonl"] if args.source == "aria_reward_hacking" else [
        "kl0.0.jsonl", "kl0.02.jsonl", "kl0.0-additional.jsonl", "kl0.02-additional.jsonl"]
    paths = [ROOT / "data/downloads" / args.source / name for name in names]
    paths.append(ROOT / "data/converted" / (args.source + ".jsonl"))
    digest = hashlib.sha256()
    evidence = []
    for path in paths:
        payload = path.read_bytes()
        for line in payload.decode("utf-8-sig").splitlines():
            if not line.strip():
                continue
            decoded = json.dumps(json.loads(line), ensure_ascii=False)
            if any(pattern.search(line) or pattern.search(decoded) for pattern in patterns):
                raise ValueError("Credential pattern in a proposed source transfer.")
        digest.update(payload)
        evidence.append({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)})
    work = "/source-conversion/" + args.source + "/" + digest.hexdigest()
    with volume.batch_upload(force=True) as upload:
        for path in paths:
            upload.put_file(path, work + "/" + path.relative_to(ROOT).as_posix())
    from intent_training.modal_app import gaming_convert_remote as module
    with module.app.run(detach=True):
        call = module.convert_expansion.spawn(args.source, "/training" + work, args.target)
        report = {"source": args.source, "app_id": module.app.app_id,
            "function_call_id": call.object_id, "work_root": "/training" + work,
            "files": evidence, "target": args.target, "credential_patterns": len(patterns)}
        destination = ROOT / "results/remote-preparation" / (args.source + "-conversion-manifest.json")
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
