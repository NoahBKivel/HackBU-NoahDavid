"""Stream credential-free construction inputs to private remote preparation."""

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys


def available_memory_gib() -> float:
    """Read the owner-required memory start gate without inspecting any process."""
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                    ("total_physical", ctypes.c_ulonglong), ("available_physical", ctypes.c_ulonglong),
                    ("total_page", ctypes.c_ulonglong), ("available_page", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
                    ("available_extended", ctypes.c_ulonglong)]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("The physical-memory start gate could not be read.")
    return status.available_physical / (1024 ** 3)


def main() -> None:
    """Use one leased process for bounded extraction, private upload and CPU launch."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument('--inputs', nargs='+', type=Path)
    parser.add_argument('--name')
    parser.add_argument('--output-root', default='/training/prepared/limit-8191')
    parser.add_argument('--state-budget', type=int, default=8191)
    parser.add_argument('--existing-manifest', type=Path)
    parser.add_argument('--construction-filter')
    args = parser.parse_args()
    memory = available_memory_gib()
    root = Path(__file__).resolve().parents[1]
    work = root / "results" / "remote-preparation"
    work.mkdir(parents=True, exist_ok=True)
    if args.existing_manifest:
        manifest_path = args.existing_manifest.resolve()
        if not manifest_path.is_relative_to(work.resolve()):
            raise ValueError('The existing manifest must be inside the preparation results directory.')
        previous = json.loads(manifest_path.read_text(encoding='utf-8'))
        remote_input = previous['remote_input']
        if previous.get('status') != 'SPAWNED' or not remote_input.startswith('/training/prepare-inputs/'):
            raise ValueError('Only a previously launched private input may be reused.')
        if not args.output_root.startswith('/training/prepared/') or '..' in args.output_root.split('/'):
            raise ValueError('The output must remain inside the existing private prepared directory.')
        sys.path.insert(0, str(root / 'src'))
        from intent_training.modal_app import prepare_remote as module
        with module.app.run(detach=True):
            call = module.prepare.spawn(remote_input, args.output_root, 0, args.state_budget, args.construction_filter)
            result = {'status': 'SPAWNED', 'app_id': module.app.app_id,
                      'function_call_id': call.object_id, 'remote_input': remote_input,
                      'remote_output': args.output_root, 'state_budget': args.state_budget,
                      'existing_payload_sha256': previous['payload_sha256'],
                      'dataset_bytes_uploaded': 0, 'available_gib_at_start': memory}
            result['construction_filter'] = args.construction_filter
            (work / f"{args.name or 'existing'}-manifest.json").write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result), flush=True)
        return
    sys.path.insert(0, str(root / "scripts"))
    from scan_secrets import PATTERNS
    patterns = [re.compile(pattern) for pattern in PATTERNS]
    name = args.name or ("constructions" if args.all else "priority30")
    if not re.fullmatch('[a-z0-9-]+', name):
        raise ValueError('The upload name must contain lowercase letters, digits or hyphens.')
    payload = work / f"{name}.jsonl"
    paths = args.inputs or [root / "data" / "constructions" / f"{slug}.jsonl"
                            for slug in ("priority", "constraint", "overflow_screen")]
    paths = [(path if path.is_absolute() else root / path).resolve() for path in paths]
    if any(not path.is_relative_to((root / 'data').resolve()) or path.suffix != '.jsonl' for path in paths):
        raise ValueError('Only JSONL inputs inside the training data directory may be uploaded.')
    rows = 0
    excluded = []
    provenance = []
    with payload.open("w", encoding="utf-8", newline="\n") as destination:
        for path in paths:
            accepted = 0
            with path.open(encoding="utf-8-sig") as source:
                for index, raw in enumerate(source, 1):
                    if not raw.strip():
                        continue
                    if any(pattern.search(raw) for pattern in patterns):
                        excluded.append({"file": path.name, "line": index})
                        continue
                    decoded = json.loads(raw)
                    if any(pattern.search(json.dumps(decoded, ensure_ascii=False)) for pattern in patterns):
                        excluded.append({"file": path.name, "line": index})
                        continue
                    destination.write(raw.rstrip("\r\n") + "\n")
                    provenance.append({"file": path.name, "line": index,
                                       "sha256": hashlib.sha256(raw.encode()).hexdigest()})
                    accepted += 1
                    rows += 1
                    if not args.all and accepted == 10:
                        break
    with payload.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    remote_input = f"/prepare-inputs/limit-10239/{name}-{digest[:12]}.jsonl"
    remote_output = args.output_root
    if not remote_output.startswith('/training/prepared/') or '..' in remote_output.split('/'):
        raise ValueError('The remote output must remain inside the private prepared directory.')
    manifest = {"status": "launching", "time": datetime.now(timezone.utc).isoformat(),
                "rows": rows, "payload_sha256": digest, "available_gib_at_start": memory,
                "excluded_secret_rows": excluded, "provenance": provenance,
                "remote_input": "/training" + remote_input, "remote_output": remote_output}
    (work / f"{name}-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if not rows:
        raise ValueError("No credential-free preparation rows were selected.")
    import modal
    configuration = json.loads((root / "environment.json").read_text(encoding="utf-8-sig"))
    volume = modal.Volume.from_name(configuration["modal_volume"])
    with volume.batch_upload(force=True) as upload:
        upload.put_file(payload, remote_input)
    sys.path.insert(0, str(root / 'src'))
    from intent_training.modal_app import prepare_remote as module
    with module.app.run(detach=True):
        call = module.prepare.spawn("/training" + remote_input, remote_output, 0 if args.all else rows, args.state_budget)
        manifest.update(status="SPAWNED", app_id=module.app.app_id, function_call_id=call.object_id)
        (work / f"{name}-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps({key: value for key, value in manifest.items() if key != "provenance"}), flush=True)


if __name__ == "__main__":
    main()
