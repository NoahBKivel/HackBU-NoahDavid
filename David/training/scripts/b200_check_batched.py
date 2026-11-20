"""Retrieve one recorded batched benchmark and derive a matched GPU comparison."""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re

import modal


async def collect(record_path: Path, result_path: Path, remote_root: str | None = None,
                  extra_call_id: str | None = None) -> None:
    record = json.loads(record_path.read_text(encoding="utf-8-sig"))
    call = modal.FunctionCall.from_id(record["function_call_id"])
    status = {**record, "observed_at": datetime.now(timezone.utc).isoformat()}
    try:
        graph = await asyncio.wait_for(call.get_call_graph.aio(), timeout=30)
        status["inputs"] = [{"input_id": item.input_id, "task_id": item.task_id,
                             "status": item.status.name} for item in graph]
        if any(item.status.name == "FAILURE" for item in graph):
            status.update(retrieved=False, terminal_failure=True,
                          failure_detail="Remote exception deserialization was skipped to keep this collector free of Torch imports.")
        elif graph and all(item.status.name == "SUCCESS" for item in graph):
            result = await asyncio.wait_for(call.get.aio(timeout=1), timeout=30)
            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            status["retrieved"] = True
        else:
            status.update(retrieved=False, awaiting_completion=True)
    except Exception as error:
        status.update(retrieved=False, error_type=type(error).__name__, error=str(error))
    record_path.with_name("modal-status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status), flush=True)
    if extra_call_id:
        extra = {"function_call_id": extra_call_id, "observed_at": datetime.now(timezone.utc).isoformat()}
        try:
            other = modal.FunctionCall.from_id(extra_call_id)
            graph = await asyncio.wait_for(other.get_call_graph.aio(), timeout=30)
            extra["inputs"] = [{"input_id": item.input_id, "task_id": item.task_id,
                                 "status": item.status.name} for item in graph]
            if graph and all(item.status.name == "SUCCESS" for item in graph):
                other_result = await asyncio.wait_for(other.get.aio(timeout=1), timeout=30)
                result_path.with_name("extra-call-result.json").write_text(json.dumps(other_result, indent=2), encoding="utf-8")
                extra["result_saved"] = True
        except Exception as error:
            extra.update(error_type=type(error).__name__, error=str(error))
        result_path.with_name("extra-call-status.json").write_text(json.dumps(extra, indent=2), encoding="utf-8")
        print(json.dumps({"extra_call": extra}), flush=True)
    if remote_root:
        volume = modal.Volume.from_name("intent-monitor-training")
        async def fetch(path):
            return b"".join([chunk async for chunk in volume.read_file.aio(path)])
        try:
            entries = await asyncio.wait_for(volume.listdir.aio(remote_root), timeout=30)
            runs = sorted(entry.path.rstrip("/").rsplit("/", 1)[-1] for entry in entries
                          if re.fullmatch(r"\d{8}T\d{12}Z", entry.path.rstrip("/").rsplit("/", 1)[-1]))
            if not runs:
                print(json.dumps({"remote_root": remote_root, "observed_runs": []}), flush=True)
                return
            run = runs[-1]
            for name in ("pass-cap-progress.json", "reference.json", "result.json"):
                try:
                    raw = await asyncio.wait_for(fetch(f"{remote_root.rstrip('/')}/{run}/{name}"), timeout=30)
                    result_path.with_name(name).write_bytes(raw)
                    print(json.dumps({"remote_run": run, "artifact": name, "value": json.loads(raw)}), flush=True)
                except Exception as error:
                    print(json.dumps({"remote_run": run, "artifact": name, "error_type": type(error).__name__}), flush=True)
        except Exception as error:
            print(json.dumps({"remote_root": remote_root, "observer_error": type(error).__name__, "error": str(error)}), flush=True)


def compare(h100_path: Path, b200_path: Path, target: Path) -> None:
    project = Path(__file__).resolve().parents[1]
    price = json.loads((project / "results/b200-check/pricing.json").read_text(encoding="utf-8"))
    h100 = json.loads(h100_path.read_text(encoding="utf-8-sig"))
    b200 = json.loads(b200_path.read_text(encoding="utf-8-sig"))
    report = {"observed_at": datetime.now(timezone.utc).isoformat(),
              "historical_only": False, "projection_records_status": "Planning estimate; actual frozen N remains owner-controlled.",
              "price_evidence": price, "decision": "PENDING", "spec_edits_committed": "none",
              "matched_state_budget": h100["max_state"] == b200["max_state"],
              "matched_payload": h100["payload_sha256"] == b200["payload_sha256"],
              "matched_source": h100.get("source_sha256") == b200.get("source_sha256"), "gpus": {}}
    for name, evidence in (("h100", h100), ("b200", b200)):
        arm = evidence["arms"]["reference"]
        seconds = arm["projected_training_seconds"]
        gpu_rate = price["gpu_usd_per_second"]["H100_SXM5" if name == "h100" else "B200"]
        total_rate = gpu_rate + 8 * price["physical_cpu_core_usd_per_second"] + 96 * price["memory_gib_usd_per_second"]
        losses = [step["loss"] for step in arm["steps"]]
        report["gpus"][name] = {"records_per_hour": arm["records_per_hour"],
            "tokens_per_second": arm["tokens_per_second"], "pass_tokens_max": evidence["pass_tokens_max"],
            "estimated_training_hours": seconds / 3600, "estimated_gpu_cost_usd": seconds * gpu_rate,
            "estimated_requested_resource_cost_usd": seconds * total_rate,
            "packages": evidence["packages"], "projection_basis": evidence["projection_basis"],
            "max_state": evidence["max_state"], "b_state": evidence["b_state"],
            "payload_sha256": evidence["payload_sha256"], "source_sha256": evidence.get("source_sha256"),
            "gpu_memory_bytes": evidence["gpu_memory_bytes"],
            "full_step_cap_validations": evidence.get("full_step_cap_validations"),
            "payload_records": evidence["payload_records"],
            "losses": losses, "all_losses_finite": all(math.isfinite(loss) for loss in losses),
            "steps": arm["steps"], "memory_probes": evidence["memory_probes"]}
    h, b = (report["gpus"][name] for name in ("h100", "b200"))
    report["throughput_ratio"] = b["records_per_hour"] / h["records_per_hour"]
    report["requested_resource_cost_ratio"] = b["estimated_requested_resource_cost_usd"] / h["estimated_requested_resource_cost_usd"]
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "gpus"}), flush=True)
    for name, values in report["gpus"].items():
        print(json.dumps({"gpu": name, **{key: values[key] for key in
              ("records_per_hour", "tokens_per_second", "pass_tokens_max", "estimated_training_hours",
               "estimated_gpu_cost_usd", "estimated_requested_resource_cost_usd", "projection_basis", "losses")}}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--call-json", type=Path)
    parser.add_argument("--result-json", type=Path)
    parser.add_argument("--h100-json", type=Path)
    parser.add_argument("--comparison-json", type=Path)
    parser.add_argument("--remote-root")
    parser.add_argument("--extra-call-id")
    args = parser.parse_args()
    if args.call_json:
        asyncio.run(collect(args.call_json, args.result_json, args.remote_root, args.extra_call_id))
    if args.h100_json and args.result_json.exists():
        compare(args.h100_json, args.result_json, args.comparison_json)


if __name__ == "__main__":
    main()
