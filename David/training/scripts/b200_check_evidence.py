"""Download smoke evidence and optimizer traces from the dedicated volume."""

import argparse
from pathlib import Path

import modal


def main() -> None:
    """Read a known remote run without creating a worker."""
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--gpu", choices=["h100", "b200"], required=True)
    args = parser.parse_args()
    destination = Path(__file__).resolve().parents[1] / "results" / "b200-check" / args.gpu
    destination.mkdir(parents=True, exist_ok=True)
    volume = modal.Volume.from_name("intent-monitor-training")
    for name in ("summary.json", "reference-a/step-trace.jsonl", "reference-b/step-trace.jsonl", "resume-data.jsonl"):
        try:
            raw = b"".join(volume.read_file(f"/smoke/{args.run_id}/{name}"))
        except Exception as error:
            print(f"{args.gpu} {name}: {type(error).__name__}", flush=True)
            continue
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        print(f"{args.gpu} {name}: {len(raw)} bytes", flush=True)


if __name__ == "__main__":
    main()
