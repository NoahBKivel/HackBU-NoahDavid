"""Bound each historical comparison observation without creating a GPU worker."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path

import modal


async def main() -> None:
    """Distinguish failed observation from a failed or unfinished remote call."""
    root = Path(__file__).resolve().parents[1] / "results" / "b200-check"
    record = json.loads((root / "modal-call.json").read_text(encoding="utf-8"))
    run = json.loads((root / "availability.json").read_text(encoding="utf-8"))
    evidence = {"started": datetime.now(timezone.utc).isoformat(), "call": record,
                "run_id": run["run_id"], "historical_only": True, "observations": {}}

    def save() -> None:
        (root / "historical-diagnostic.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    async def observe(name, operation):
        evidence["observations"][name] = {"started": datetime.now(timezone.utc).isoformat()}
        save()
        try:
            value = await asyncio.wait_for(operation(), timeout=30)
            evidence["observations"][name].update(status="retrieved", value=value)
        except Exception as error:
            evidence["observations"][name].update(status="observer_error", error_type=type(error).__name__, error=str(error))
        evidence["observations"][name]["finished"] = datetime.now(timezone.utc).isoformat()
        save()
        print(json.dumps({name: evidence["observations"][name]}), flush=True)

    call = modal.FunctionCall.from_id(record["function_call_id"])

    async def graph():
        values = await call.get_call_graph.aio()
        return [{"input_id": item.input_id, "task_id": item.task_id, "status": item.status.name} for item in values]

    async def result():
        value = await call.get.aio(timeout=1)
        (root / "historical-smoke-results.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
        return {"finished": value.get("finished"), "error": value.get("error"), "run_id": value.get("run_id")}

    await observe("call_graph", graph)
    await observe("call_result", result)
    volume = modal.Volume.from_name("intent-monitor-training")
    for name in ("summary.json", "reference-a/step-trace.jsonl", "reference-b/step-trace.jsonl", "resume-data.jsonl"):
        async def fetch(name=name):
            raw = b"".join([chunk async for chunk in volume.read_file.aio(f"/smoke/{run['run_id']}/{name}")])
            target = root / "b200" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            return {"bytes": len(raw)}
        await observe(name, fetch)
    evidence["finished"] = datetime.now(timezone.utc).isoformat()
    save()


if __name__ == "__main__":
    asyncio.run(main())
