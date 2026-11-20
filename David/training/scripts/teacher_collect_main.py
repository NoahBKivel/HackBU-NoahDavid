"""Collect a committed main prefix without downloading auxiliary requirements."""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from kev_prepare_upload import available_memory_gib
    memory = available_memory_gib()
    import modal
    config = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
    volume = modal.Volume.from_name(config["modal_volume"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".teacher-download")
    with temporary.open("wb") as handle:
        for chunk in volume.read_file(args.remote.removeprefix("/training/")):
            handle.write(chunk)
    committed = args.output
    try:
        temporary.replace(committed)
    except PermissionError:
        # Windows readers can hold an earlier prefix open. Keep the new complete
        # prefix immutable and usable without touching another process.
        committed = args.output.with_name(args.output.stem + ".pending-" + uuid4().hex + args.output.suffix)
        temporary.replace(committed)
    with committed.open(encoding="utf-8") as handle:
        count = sum(1 for line in handle if line.strip())
    print(json.dumps({"status": "COPIED", "records": count, "output": str(committed),
                      "available_gib": memory}), flush=True)


if __name__ == "__main__":
    main()
