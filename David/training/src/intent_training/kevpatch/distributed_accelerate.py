"""Train grouped decision records through Accelerate's synchronized forward path."""

from contextlib import nullcontext
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any


def verify_frozen_input(path: Path, expected_sha256: str, expected_records: int) -> dict:
    """Reject a changed frozen artifact before allocating model state."""
    import re
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256 or "") or expected_records < 1:
        raise ValueError("Training requires its frozen SHA256 and positive record count.")
    digest, count = hashlib.sha256(), 0
    with path.open("rb") as source:
        for line in source:
            digest.update(line)
            count += bool(line.strip())
    if digest.hexdigest() != expected_sha256.lower() or count != expected_records:
        raise ValueError("The frozen training artifact changed after admission.")
    return {"records_sha256": digest.hexdigest(), "records": count}


def compare_losses(reference: dict, repeat: dict, distributed: dict) -> dict:
    """Require matched work and loss gaps bounded by measured noise or relative tolerance."""
    for other in (repeat, distributed):
        for field in ("records_sha256", "fixed_records", "max_state", "pass_tokens_max", "global_batch"):
            if other[field] != reference[field]:
                raise ValueError(f"The parity inputs differ: {field}.")
        if len(other["steps"]) != len(reference["steps"]):
            raise ValueError("The parity trajectories have different step counts.")
    import math
    baseline = [row["loss"] for row in reference["steps"]]
    duplicated = [row["loss"] for row in repeat["steps"]]
    candidate = [row["loss"] for row in distributed["steps"]]
    noise = max(abs(a - b) for a, b in zip(baseline, duplicated))
    differences = [abs(a - b) for a, b in zip(baseline, candidate)]
    allowed = [max(2 * noise, abs(value) * 1e-3) for value in baseline]
    passed = all(math.isfinite(value) for value in baseline + duplicated + candidate)
    passed = passed and all(gap <= limit for gap, limit in zip(differences, allowed))
    return {"status": "PASS" if passed else "FAIL", "reference_losses": baseline,
            "repeat_losses": duplicated, "distributed_losses": candidate,
            "same_seed_noise_floor": noise, "allowed_absolute_per_step": allowed,
            "max_absolute_gap": max(differences),
            "max_relative_gap": max(gap / max(abs(value), 1e-12) for gap, value in zip(differences, baseline))}


def rank_records(records: list[dict], world: int, rank: int) -> list[dict]:
    """Assign linked units once while retaining their global optimizer step."""
    from .grouping import linked_units
    if world < 1 or not 0 <= rank < world:
        raise ValueError("The distributed rank must belong to the process group.")
    assignments: list[list[dict]] = [[] for _ in range(world)]
    for unit in sorted(linked_units(records), key=len, reverse=True):
        owner = min(range(world), key=lambda index: (len(assignments[index]), index))
        assignments[owner].extend(unit)
    return assignments[rank]


def local_passes(native: Any, records: list[dict], shapes: dict,
                 cap: int, shared: bool) -> list[list[dict]]:
    """Pack a rank's complete records under the measured padded-token cap."""
    if not records:
        return [[]]
    def cost(items: list[dict]) -> int:
        return native.pass_tokens([shape for record in items for shape in shapes[id(record)]], shared)
    if any(cost([record]) > cap for record in records):
        raise ValueError("A record exceeds the measured per-device pass cap.")
    ordered = sorted(records, key=lambda record: cost([record]), reverse=True)
    count = 1
    while True:
        runs = native.balanced_runs(ordered, count, cost)
        if max(map(cost, runs)) <= cap:
            return runs
        count += 1


def loss_module(model: Any, args: Any) -> Any:
    """Wrap custom decision forwards inside Accelerate's actual DDP entry point."""
    import torch
    import kev.train as native
    class DecisionLoss(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.decision = model

        def forward(self, variants: list[Any]) -> Any:
            if variants:
                loss, _ = native.batch_loss(self.decision, args, variants, "cuda", {}, None,
                    torch.autocast("cuda", dtype=torch.bfloat16))
            else:
                loss = torch.zeros((), device="cuda")
            # An empty rank and conditionally unused parameters still join the same reduction.
            return loss + sum(parameter.reshape(-1)[0] * 0
                              for parameter in self.decision.trainable_parameters())
    return DecisionLoss()


def run(config_path: str) -> None:
    """Execute a fixed-batch comparison, throughput measurement or complete training run."""
    import torch
    from accelerate import Accelerator
    from accelerate.utils import DistributedDataParallelKwargs
    import kev.train as native
    from kev.checkpoint import Meta
    from .batched_measure import _arguments, _optimizer, _seed
    from .grouping import optimizer_groups
    from .kernels import install_required_kernels, kernel_calls, convolution_calls
    from .measure import training_model
    from .persistence import save_checkpoint, LoRAResumeWriter

    config = json.loads(Path(config_path).read_text())
    accelerator = Accelerator(mixed_precision="no", gradient_accumulation_steps=1,
        kwargs_handlers=[DistributedDataParallelKwargs(broadcast_buffers=False,
                                                       find_unused_parameters=False)])
    torch.cuda.set_device(accelerator.local_process_index)
    _seed(int(config.get("seed", 1)))
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    binding = install_required_kernels()
    startup = time.perf_counter()
    tokenizer, model = training_model(config)
    args = _arguments(int(config.get("max_state", 8192)), int(config["pass_tokens_max"]))
    args.batch, args.accum = 16, 1
    records_bytes = Path(config["records_path"]).read_bytes()
    records = [json.loads(line) for line in records_bytes.splitlines() if line.strip()]
    if config.get("fixed_records"):
        records = records[:int(config["fixed_records"])]
    for index, record in enumerate(records):
        meta = record.setdefault("_meta", {})
        meta.setdefault("id", record.get("record_id", f"record-{index}"))
        meta.setdefault("source", record.get("source", "measurement"))
    groups = optimizer_groups(records, 16)
    cycle_group_count = len(groups)
    mode = config.get("mode", "parity")
    if mode == "train":
        ordered = list(records)
        import random
        random.Random(int(config.get("seed", 1))).shuffle(ordered)
        groups = optimizer_groups(ordered, 16)
    elif mode == "parity":
        if len(groups) != 1:
            raise ValueError("The parity fixture must form exactly one global batch.")
        groups = groups * int(config.get("steps", 3))
    elif mode == "benchmark":
        groups = groups * (int(config.get("cycles", 2)) + 1)
    else:
        raise ValueError("Unknown distributed execution mode.")
    optimizer, scheduler = _optimizer(model, math.ceil(int(config.get("projection_records", 12200)) / 16))
    wrapper, optimizer = accelerator.prepare(loss_module(model, args), optimizer)
    destination = Path(config["output"])
    if accelerator.is_main_process:
        destination.mkdir(parents=True, exist_ok=True)
    accelerator.wait_for_everyone()
    startup_seconds = time.perf_counter() - startup
    counts = native.state_token_counts(tokenizer, records)
    shapes = native.plan_shapes(model, tokenizer, args, records, 0, set(), counts)
    timings = []
    save_interval = max(1, math.ceil(len(groups) / 10))
    for index, group in enumerate(groups):
        partition_world = int(config.get("partition_world", accelerator.num_processes))
        shard_ids = (range(partition_world) if accelerator.num_processes == 1
                     else [accelerator.process_index])
        passes = []
        for shard in shard_ids:
            local = rank_records(group, partition_world, shard)
            passes.extend((shard, offset == 0, chunk) for offset, chunk in enumerate(
                local_passes(native, local, shapes, args.pass_tokens_max, True)))
        accelerator.wait_for_everyone()
        torch.cuda.synchronize()
        started = time.perf_counter()
        loss_sum = torch.zeros((), device=accelerator.device, dtype=torch.float64)
        tokens = 0
        for offset, (shard, first, chunk) in enumerate(passes):
            if first:
                _seed(int(config.get("seed", 1)) + index * partition_world + shard)
            variants = native.encode_batch(model, tokenizer, args, chunk, 0, set()) if chunk else []
            context = accelerator.no_sync(wrapper) if offset + 1 < len(passes) else nullcontext()
            with context:
                loss = wrapper(variants)
                loss_sum += loss.detach().double()
                # DDP averages across ranks; this restores the global record-mean objective.
                accelerator.backward(loss * accelerator.num_processes / len(group))
            tokens += sum(variant.tokens for variant in variants)
        norm = accelerator.clip_grad_norm_(wrapper.parameters(), native.MAX_GRAD_NORM)
        if not torch.isfinite(norm):
            raise ValueError("The distributed gradient norm is non-finite.")
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        seconds = torch.tensor(time.perf_counter() - started, device=accelerator.device)
        global_loss = float(accelerator.reduce(loss_sum, reduction="sum")) / len(group)
        seconds = float(accelerator.reduce(seconds, reduction="max"))
        global_tokens = int(accelerator.reduce(torch.tensor(tokens, device=accelerator.device), reduction="sum"))
        peak = int(accelerator.reduce(torch.tensor(torch.cuda.max_memory_allocated(), device=accelerator.device), reduction="max"))
        memory = torch.cuda.get_device_properties(accelerator.device).total_memory
        if peak > .9 * memory:
            raise RuntimeError("The distributed configuration exceeds ninety percent device memory.")
        row = {"step": index + 1, "loss": global_loss, "seconds": seconds,
               "records": len(group), "forward_tokens": global_tokens,
               "gradient_norm": float(norm), "peak_device_bytes": peak}
        timings.append(row)
        if accelerator.is_main_process:
            (destination / "progress.json").write_text(json.dumps({"steps": timings}))
            print(json.dumps(row), flush=True)
        if mode == "train" and ((index + 1) % save_interval == 0 or index + 1 == len(groups)):
            if accelerator.is_main_process:
                unwrapped = accelerator.unwrap_model(wrapper).decision
                meta = Meta(base=config["base"], base_revision=config["base_revision"],
                            lora=16, head_dim=256, weights_dtype="fp32", weights="lora")
                save_checkpoint(destination / f"step-{index + 1}" / "checkpoint", unwrapped,
                                tokenizer, meta, {"step": index + 1, "steps": len(groups)})
                LoRAResumeWriter(destination / "resume", unwrapped, tokenizer, meta).save(
                    index + 1, optimizer, scheduler,
                    {"epoch": 0, "next_global_step": index + 1, "resume_allowed": False})
                import modal
                modal.Volume.from_name(config["modal_volume"]).commit()
            accelerator.wait_for_everyone()
    if accelerator.is_main_process:
        timed = timings[cycle_group_count:] if mode == "benchmark" else timings
        result = {"status": "MEASURED", "backend": "accelerate", "mode": mode,
                  "world_size": accelerator.num_processes, "steps": timings,
                  "records_sha256": hashlib.sha256(records_bytes).hexdigest(),
                  "fixed_records": config.get("fixed_records"), "startup_seconds": startup_seconds,
                  "records_per_hour": sum(row["records"] for row in timed) / sum(row["seconds"] for row in timed) * 3600,
                  "tokens_per_second": sum(row["forward_tokens"] for row in timed) / sum(row["seconds"] for row in timed),
                  "kernel_binding": binding, "kernel_calls_rank0": kernel_calls(),
                  "convolution_calls_rank0": convolution_calls(), "max_state": args.max_state,
                  "pass_tokens_max": args.pass_tokens_max, "global_batch": 16}
        result["gpu_memory_bytes_per_device"] = memory
        (destination / "result.json").write_text(json.dumps(result, indent=2))
    accelerator.wait_for_everyone()


if __name__ == "__main__":
    import sys
    run(sys.argv[1])
