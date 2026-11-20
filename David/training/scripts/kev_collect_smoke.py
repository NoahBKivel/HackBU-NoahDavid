"""Collect a detached smoke call across local session restarts."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


def main() -> None:
    """Persist call status and collect completed measurements without relaunching work."""
    from kev_prepare_upload import available_memory_gib
    memory = available_memory_gib()
    if memory <= 3.5:
        print(json.dumps({'status': 'RAM_GATE_CLOSED', 'available_gib': memory}), flush=True)
        return
    import modal
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", type=float, default=0)
    parser.add_argument("--mode", choices=["smoke", "identity", "resume", "batched"], default="smoke")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    directory = root / "results" / "trainer"
    record = json.loads((directory / f"modal-{args.mode}-call.json").read_text(encoding="utf-8-sig"))
    call = modal.FunctionCall.from_id(record["function_call_id"])
    graph = call.get_call_graph()
    status = {**record, "time": datetime.now(timezone.utc).isoformat(),
              "inputs": [{"input_id": item.input_id, "task_id": item.task_id,
                          "status": item.status.name} for item in graph]}
    (directory / f"modal-{args.mode}-status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status), flush=True)
    if any(item.status.name in ('FAILURE', 'TERMINATED', 'TIMEOUT') for item in graph):
        print('Remote call is terminal; inspect app logs without deserializing its exception.', flush=True)
        return
    if args.wait or all(item.status.name == "SUCCESS" for item in graph):
        try:
            result = call.get(timeout=args.wait or 0)
        except Exception as error:
            if type(error).__name__ in ("TimeoutError", "FunctionTimeoutError"):
                print("The detached smoke call is still running.")
                return
            raise
        (directory / f"modal-{args.mode}-results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("Collected completed smoke measurements.", flush=True)


if __name__ == "__main__":
    main()
