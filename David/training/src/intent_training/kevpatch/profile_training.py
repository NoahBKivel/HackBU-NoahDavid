"""Measure actual decision-training passes and their accelerator bottlenecks."""

from copy import deepcopy
import json
import math
from pathlib import Path
import time
from typing import Any


def event_rows(profiler: Any) -> list[dict[str, Any]]:
    """Return the costly measured operators without exporting tensor contents."""
    rows = []
    for event in profiler.key_averages():
        rows.append({"name": event.key, "calls": event.count,
                     "cpu_us": event.self_cpu_time_total,
                     "device_us": getattr(event, "self_device_time_total", 0),
                     "device_total_us": getattr(event, "device_time_total", 0)})
    return sorted(rows, key=lambda row: row["device_us"], reverse=True)[:80]


def training_step(model: Any, variants: list[Any], args: Any, optimizer: Any,
                  scheduler: Any) -> dict[str, Any]:
    """Time a globally normalized native optimizer update on encoded records."""
    import torch
    import kev.train as native
    denominator = sum(variant.share for variant in variants)
    runs = native.row_passes(variants, args.pass_tokens_max, True)
    torch.cuda.synchronize()
    start = time.perf_counter()
    total_loss = torch.zeros((), device="cuda")
    passes = []
    for run in runs:
        with torch.profiler.record_function("decision_forward_and_loss"):
            loss, _ = native.batch_loss(model, args, run, "cuda", {}, None,
                                       torch.autocast("cuda", dtype=torch.bfloat16))
        with torch.profiler.record_function("decision_backward"):
            (loss / denominator).backward()
        total_loss += loss.detach() / denominator
        passes.append({"records": len(run),
                       "useful_tokens": sum(v.tokens for v in run),
                       "padded_tokens": native.pass_tokens([native.shape(v.enc) for v in run], True)})
    with torch.profiler.record_function("decision_optimizer"):
        norm = torch.nn.utils.clip_grad_norm_(model.trainable_parameters(), native.MAX_GRAD_NORM,
                                             error_if_nonfinite=True)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
    torch.cuda.synchronize()
    return {"seconds": time.perf_counter() - start, "loss": float(total_loss),
            "gradient_norm": float(norm), "records": len(variants), "passes": passes,
            "useful_tokens": sum(row["useful_tokens"] for row in passes),
            "padded_tokens": sum(row["padded_tokens"] for row in passes),
            "peak_device_bytes": torch.cuda.max_memory_allocated()}


def run_profile(records_path: str, output: str, config: dict[str, Any],
                pass_tokens: int, projection_records: int, volume: Any) -> dict[str, Any]:
    """Profile the reference, then compare checkpointing and padding on identical data."""
    import torch
    import kev.train as native
    from .batched_measure import _arguments, _optimizer, _seed
    from .grouping import optimizer_groups
    from .kernels import install_required_kernels, kernel_calls, convolution_calls
    from .measure import training_model
    destination = Path(output)
    destination.mkdir(parents=True)

    def save(name: str, value: Any) -> None:
        (destination / f"{name}.json").write_text(json.dumps(value, indent=2))
        volume.commit()
        print(json.dumps({"event": name, "output": output}), flush=True)

    records = [json.loads(line) for line in Path(records_path).read_text().splitlines() if line.strip()]
    if not records:
        raise ValueError("The profiling records are empty.")
    _seed(1)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    binding = install_required_kernels()
    started = time.perf_counter()
    tokenizer, model = training_model(config)
    load_seconds = time.perf_counter() - started
    args = _arguments(8192, pass_tokens)
    args.batch, args.accum = 16, 1
    groups = optimizer_groups(records, 16)
    encoding_start = time.perf_counter()
    encoded = [native.encode_batch(model, tokenizer, args, group, 0, set()) for group in groups]
    encode_seconds = time.perf_counter() - encoding_start
    snapshot = {name: value.detach().cpu().clone() for name, value in model.named_parameters()
                if value.requires_grad}
    memory = torch.cuda.get_device_properties(0).total_memory
    save("input", {"records": len(records), "groups": len(groups), "encoding_seconds": encode_seconds,
                   "model_load_seconds": load_seconds, "gpu": torch.cuda.get_device_name(),
                   "gpu_memory_bytes": memory, "weight_dtype": model.dtype,
                   "kernel_binding": binding, "pass_cap": pass_tokens,
                   "source_counts": dict(__import__("collections").Counter(
                       r.get("_meta", {}).get("source", "unknown") for r in records))})

    def reset(checkpointing: bool) -> tuple[Any, Any]:
        model.zero_grad(set_to_none=True)
        with torch.no_grad():
            for name, value in model.named_parameters():
                if name in snapshot:
                    value.copy_(snapshot[name])
        if checkpointing:
            model.lm.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        else:
            model.lm.gradient_checkpointing_disable()
        _seed(1)
        torch.cuda.empty_cache()
        return _optimizer(model, math.ceil(projection_records / 16))

    optimizer, scheduler = reset(True)
    training_step(model, encoded[0], args, optimizer, scheduler)
    optimizer, scheduler = reset(True)
    torch.cuda.reset_peak_memory_stats()
    with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,
                                           torch.profiler.ProfilerActivity.CUDA],
                                record_shapes=True, profile_memory=True) as profiler:
        profiled = training_step(model, encoded[0], args, optimizer, scheduler)
    operators = event_rows(profiler)
    kernels = {}
    for event in profiler.events():
        if "CUDA" in str(getattr(event, "device_type", "")):
            row = kernels.setdefault(event.name, {"calls": 0, "device_us": 0})
            row["calls"] += 1
            row["device_us"] += getattr(event, "device_time_total", 0)
    save("profile", {"step": profiled, "operators": operators,
                     "cuda_kernel_events": kernels,
                     "fla_calls": kernel_calls(), "convolution_calls": convolution_calls(),
                     "attention_events": [r for r in operators if any(
                         name in r["name"].lower() for name in ("attention", "flash", "sdpa"))]})
    results = []
    for checkpointing in (True, False):
        del optimizer, scheduler
        optimizer, scheduler = reset(checkpointing)
        torch.cuda.reset_peak_memory_stats()
        try:
            warm = training_step(model, encoded[0], args, optimizer, scheduler)
            if warm["peak_device_bytes"] > 0.9 * memory:
                results.append({"checkpointing": checkpointing, "status": "OVER_MEMORY_LIMIT", "warmup": warm})
                continue
            del optimizer, scheduler
            optimizer, scheduler = reset(checkpointing)
            rows = []
            torch.cuda.reset_peak_memory_stats()
            for _ in range(2):
                for group in encoded:
                    rows.append(training_step(model, group, args, optimizer, scheduler))
            seconds = sum(row["seconds"] for row in rows)
            count = sum(row["records"] for row in rows)
            peak = max(row["peak_device_bytes"] for row in rows)
            result = {"checkpointing": checkpointing,
                      "status": "PASS" if peak <= 0.9 * memory else "OVER_MEMORY_LIMIT",
                      "steps": rows, "seconds": seconds, "records": count,
                      "records_per_hour": count / seconds * 3600,
                      "useful_tokens_per_second": sum(row["useful_tokens"] for row in rows) / seconds,
                      "padded_tokens_per_second": sum(row["padded_tokens"] for row in rows) / seconds,
                      "peak_device_bytes": peak,
                      "projected_full_run_hours": projection_records / count * seconds / 3600}
            results.append(result)
        except torch.cuda.OutOfMemoryError:
            results.append({"checkpointing": checkpointing, "status": "OOM"})
            model.zero_grad(set_to_none=True)
            torch.cuda.empty_cache()
        save("measurements", results)
    result = {"status": "MEASURED", "path": output, "measurements": results,
              "profile": {"step": profiled, "operators": operators},
              "cuda_kernel_events": kernels,
              "fla_calls": kernel_calls(), "convolution_calls": convolution_calls(),
              "max_state": args.max_state, "pass_cap": args.pass_tokens_max,
              "geometry_only": True, "training_labels_created": 0}
    save("result", result)
    return result
