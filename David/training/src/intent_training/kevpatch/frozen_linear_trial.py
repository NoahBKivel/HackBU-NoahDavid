"""Run a bounded frozen-weight cast-cache comparison on admitted records."""

from contextlib import nullcontext
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def compare(records_path: str, output: str, config: dict[str, Any], cap: int,
            volume: Any) -> dict[str, Any]:
    import torch
    from .batched_measure import _arguments, _optimizer, _seed, _step
    from .frozen_linear import cached_frozen_linears
    from .grouping import optimizer_groups
    from .kernels import install_required_kernels
    from .measure import training_model
    destination = Path(output)
    destination.mkdir(parents=True)
    payload = Path(records_path).read_bytes()
    records = [json.loads(line) for line in payload.splitlines() if line.strip()]
    groups = optimizer_groups(records, 16)
    _seed(1)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    install_required_kernels()
    tokenizer, model = training_model(config)
    snapshot = {name: p.detach().cpu().clone() for name, p in model.named_parameters() if p.requires_grad}
    args = _arguments(8192, cap)
    args.batch, args.accum = 16, 1
    memory = torch.cuda.get_device_properties(0).total_memory
    result: dict[str, Any] = {"records_sha256": hashlib.sha256(payload).hexdigest(),
                              "records": len(records), "cap": cap, "gpu_memory_bytes": memory,
                              "arms": [], "status": "IN_PROGRESS"}

    def save() -> None:
        (destination / "result.json").write_text(json.dumps(result, indent=2))
        volume.commit()
        print(json.dumps({"event": "cast-cache-progress", "path": output,
                          "arms": len(result["arms"]), "status": result["status"]}), flush=True)

    def reset() -> tuple[Any, Any]:
        model.zero_grad(set_to_none=True)
        with torch.no_grad():
            for name, parameter in model.named_parameters():
                if name in snapshot:
                    parameter.copy_(snapshot[name])
        _seed(1)
        torch.cuda.empty_cache()
        return _optimizer(model, math.ceil(12200 / 16))

    for name in ("reference", "repeat", "cached"):
        with cached_frozen_linears(model) if name == "cached" else nullcontext({}) as manifest:
            optimizer, scheduler = reset()
            try:
                warm_groups = groups if name != "repeat" else groups[:1]
                for group in warm_groups:
                    _step(model, tokenizer, group, args, optimizer, scheduler, 0)
                del optimizer, scheduler
                optimizer, scheduler = reset()
                torch.cuda.reset_peak_memory_stats()
                parity = [_step(model, tokenizer, groups[0], args, optimizer, scheduler, 0) for _ in range(2)]
                rows = []
                if name != "repeat":
                    for _ in range(2):
                        rows.extend(_step(model, tokenizer, group, args, optimizer, scheduler, 0) for group in groups)
                peak = torch.cuda.max_memory_allocated()
                seconds = sum(row["seconds"] for row in rows)
                result["arms"].append({"name": name, "parity": parity, "steps": rows,
                    "peak_device_bytes": peak, "manifest": manifest.copy(),
                    "useful_tokens_per_second": sum(r["forward_tokens"] for r in rows) / seconds if seconds else None,
                    "records_per_hour": sum(r["records"] for r in rows) / seconds * 3600 if seconds else None,
                    "status": "PASS" if peak <= memory * 0.9 else "OVER_MEMORY_LIMIT"})
            except torch.cuda.OutOfMemoryError:
                result["arms"].append({"name": name, "status": "OOM"})
                model.zero_grad(set_to_none=True)
            finally:
                del optimizer, scheduler
                torch.cuda.empty_cache()
            save()
    if all(arm["status"] == "PASS" for arm in result["arms"]):
        reference, repeat, candidate = (arm["parity"] for arm in result["arms"])
        relative = lambda a, b: abs(a - b) / max(abs(a), 1e-12)
        noise = max(relative(a["loss"], b["loss"]) for a, b in zip(reference, repeat))
        gap = max(relative(a["loss"], b["loss"]) for a, b in zip(reference, candidate))
        result.update(status="PASS" if gap <= max(noise, 1e-3) else "PARITY_FAIL",
                      same_seed_relative_noise=noise, max_relative_loss_difference=gap)
    else:
        result["status"] = "MEMORY_FAIL"
    save()
    return result
