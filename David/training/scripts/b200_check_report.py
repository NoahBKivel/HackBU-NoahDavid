"""Derive comparison measurements exclusively from recorded evidence."""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else None


def main() -> None:
    """Write derived throughput, cost and paired optimizer-loss evidence."""
    project = Path(__file__).resolve().parents[1]
    root = project / "results" / "b200-check"
    price = read(root / "pricing.json")
    report = {"observed_at": datetime.now(timezone.utc).isoformat(),
              "historical_only": True,
              "projection_records": 12200,
              "projection_records_status": "Planning estimate, not an actual frozen corpus count.",
              "available": read(root / "availability.json"),
              "price_evidence": price, "decision": "PENDING",
              "spec_edits_committed": "none", "gpus": {}}
    for gpu in ("h100", "b200"):
        summary = read(root / gpu / "summary.json")
        if summary is None:
            continue
        if gpu == "b200" and summary.get("started"):
            availability = {"available": True, "run_id": summary["run_id"],
                            "started": summary["started"], "evidence": "Remote summary.json"}
            report["available"] = availability
            (root / "availability.json").write_text(json.dumps(availability, indent=2), encoding="utf-8")
        row = {"packages": summary.get("packages"),
               "kernel_check": summary.get("kernel-check"),
               "run_id": summary.get("run_id"), "started": summary.get("started"),
               "error": summary.get("error"), "finished": summary.get("finished")}
        throughput = summary.get("pass-cap-throughput")
        if throughput:
            seconds = throughput["projected_training_seconds"]
            gpu_rate = price["gpu_usd_per_second"]["H100_SXM5" if gpu == "h100" else "B200"]
            total_rate = gpu_rate + 8 * price["physical_cpu_core_usd_per_second"] + 96 * price["memory_gib_usd_per_second"]
            short_tokens = sum(item["padded_tokens"] for item in throughput["timings"][:-1]) / len(throughput["timings"][:-1])
            long_tokens = throughput["timings"][-1]["padded_tokens"]
            weighted_tokens = throughput["projection_short_share"] * short_tokens + throughput["projection_long_share"] * long_tokens
            row.update(pass_tokens_max=throughput["pass_tokens_max"],
                       throughput_records_hour=throughput["throughput_records_per_hour"],
                       throughput_padded_tokens_s=weighted_tokens * throughput["throughput_records_per_hour"] / 3600,
                       estimated_training_hours=seconds / 3600,
                       estimated_training_gpu_cost_usd=seconds * gpu_rate,
                       estimated_training_requested_resource_cost_usd=seconds * total_rate,
                       requested_resource_hourly_usd=total_rate * 3600,
                       measured_at_pass_cap=False,
                       throughput_limitation="Same one-record synthetic timing mix; maximum-cap batching and full optimizer overhead are unmeasured.")
        traces = root / gpu / "reference-a" / "step-trace.jsonl"
        if traces.exists():
            steps = [json.loads(line) for line in traces.read_text().splitlines()]
            row["step_trace"] = steps
            row["finite_losses"] = all(math.isfinite(item["loss"]) for item in steps)
            row["first_loss"] = steps[0]["loss"]
            row["last_loss"] = steps[-1]["loss"]
        data = root / gpu / "resume-data.jsonl"
        if data.exists():
            row["batch_file_sha256"] = hashlib.sha256(data.read_bytes()).hexdigest()
        report["gpus"][gpu] = row
    h, b = (report["gpus"].get(gpu, {}) for gpu in ("h100", "b200"))
    if "throughput_records_hour" in h and "throughput_records_hour" in b:
        report["throughput_ratio"] = b["throughput_records_hour"] / h["throughput_records_hour"]
        report["requested_resource_cost_ratio"] = b["estimated_training_requested_resource_cost_usd"] / h["estimated_training_requested_resource_cost_usd"]
    if "step_trace" in h and "step_trace" in b:
        pairs = list(zip(h["step_trace"], b["step_trace"]))
        report["loss_behaviour_vs_h100"] = {
            "same_batch_file": h.get("batch_file_sha256") == b.get("batch_file_sha256"),
            "same_step_count": len(h["step_trace"]) == len(b["step_trace"]),
            "same_record_order": all(x["records"] == y["records"] for x, y in pairs),
            "both_finite": h["finite_losses"] and b["finite_losses"],
            "h100_first_last": [h["first_loss"], h["last_loss"]],
            "b200_first_last": [b["first_loss"], b["last_loss"]],
            "max_absolute_gap": max(abs(x["loss"] - y["loss"]) for x, y in pairs)}
    (root / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "gpus"}, indent=2))


if __name__ == "__main__":
    main()
