"""Retrieve the recorded comparison call without submitting another GPU job."""

from datetime import datetime, timezone
import json
from pathlib import Path

import modal


def main() -> None:
    """Save remote call state and completed measurements."""
    root = Path(__file__).resolve().parents[1] / "results" / "b200-check"
    record = json.loads((root / "modal-call.json").read_text(encoding="utf-8-sig"))
    call = modal.FunctionCall.from_id(record["function_call_id"])
    graph = call.get_call_graph()
    status = {**record, "observed_at": datetime.now(timezone.utc).isoformat(),
              "inputs": [{"input_id": item.input_id, "task_id": item.task_id,
                          "status": item.status.name} for item in graph]}
    (root / "modal-status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status), flush=True)
    first_path = root / "first-attempt-call.json"
    first = json.loads(first_path.read_text(encoding="utf-8")) if first_path.exists() else record
    queued_seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(first["submitted_at"])).total_seconds()
    if not (root / "availability.json").exists() and graph and all(item.status.name == "PENDING" and not item.task_id for item in graph) and queued_seconds > 600:
        call.cancel(terminate_containers=True)
        status["decision"] = "KEEP_H100"
        status["reason"] = "The comparison exceeded the owner-authorized ten-minute queue bound."
        status["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        (root / "modal-status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status), flush=True)
        return
    try:
        result = call.get(timeout=1)
    except Exception as error:
        status["retrieval"] = {"type": type(error).__name__, "message": str(error)}
        (root / "modal-status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status["retrieval"]), flush=True)
        return
    (root / "smoke-results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
