"""Submit isolated four-GPU Accelerate work to the training app."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


def main() -> None:
    """Launch the requested measured configuration and preserve its remote handle."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", required=True)
    parser.add_argument("--mode", choices=("parity", "benchmark", "train"), default="parity")
    parser.add_argument("--pass-tokens", type=int, default=115200)
    parser.add_argument("--fixed-records", type=int, default=16)
    args = parser.parse_args()
    from kev_prepare_upload import available_memory_gib
    memory = available_memory_gib()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from intent_training.modal_app import accelerate_training as module
    with module.app.run(detach=True):
        call = module.run_accelerate.spawn(args.records, args.mode, args.pass_tokens, args.fixed_records)
        result = {"function_call_id": call.object_id, "app_id": module.app.app_id,
                  "image_id": module.image.object_id, "submitted_at": datetime.now(timezone.utc).isoformat(),
                  "records_path": args.records, "mode": args.mode, "available_memory_gib": memory}
        destination = root / "results/accelerate"
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / f"{args.mode}-launch.json"
        path.write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
