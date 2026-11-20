"""Measure complete native decision optimizer steps on a fixed admitted payload."""

from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
from pathlib import Path
import random
import time
from types import SimpleNamespace
from typing import Any
import urllib.request


def _arguments(max_state: int, cap: int = 0) -> Any:
    return SimpleNamespace(max_state=max_state, shared_prefix=1, length_sort=1,
                           pass_tokens_max=cap, batch=2, accum=8, seed=1,
                           p_none_pair=0, p_none=0, p_none_distract=0, p_distract=0,
                           row_budget=0, perm_kl=0, perm_frac=0, ord_w=0,
                           label_smoothing=0, brier_w=0, focal_gamma=0, anchor_w=0)


def _largest_record(tokenizer: Any, max_state: int) -> dict[str, Any]:
    from kev.data import materialize
    from kev.model import encode, training_context
    from kev.train import pass_tokens, shape
    from monitor_format import QUESTION_TABLE, fill_question
    from .measure import synthetic_record
    context = training_context(max_state)
    state = synthetic_record(tokenizer, max_state - 1, 1)["state"]
    candidates: list[dict[str, Any]] = []
    current: dict[str, Any] = {"state": state, "questions": {}}
    for question_id in QUESTION_TABLE:
        question = fill_question(question_id, requirement_text=" p" * 1000,
                                 correction="Check the requirement. " + " p" * 1000,
                                 fired_questions=["M2"], event_seq=1, summary="stated requirement at E1",
                                 section_id=1, tokenizer=tokenizer)
        kind = question["type"]
        question["label"] = next(iter(question["criteria"])) if kind == "choice" else 0 if kind == "score" else False
        question["src"] = "synthetic_monitor"
        trial = {"state": state, "questions": {**current["questions"], question_id: question}}
        encoding = encode(tokenizer, materialize(trial), strict=True,
                          max_state=context["max_state"], max_branch=context["max_branch"])
        if len(encoding["ids"]) > context["max_packed"]:
            if current["questions"]:
                candidates.append(current)
            current = {"state": state, "questions": {question_id: question}}
        else:
            current = trial
    if current["questions"]:
        candidates.append(current)
    cost = lambda record: pass_tokens([shape(encode(tokenizer, materialize(record), strict=True,
                            max_state=context["max_state"], max_branch=context["max_branch"]))], True)
    return max(candidates, key=cost)


def _payload(tokenizer: Any, config: dict[str, Any], maximum: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    if config.get("measurement_records"):
        records = [json.loads(line) for line in Path(config["measurement_records"]).read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(records) != 16:
            raise ValueError("The matched measurement payload must contain exactly sixteen records.")
        basis = "fixed admitted real records"
    else:
        records = [deepcopy(maximum) for _ in range(16)]
        basis = "synthetic largest admitted monitor shape, conservative worst-shape projection"
    for index, record in enumerate(records):
        record.setdefault("_meta", {}).setdefault("id", f"measurement-{index}")
        record["_meta"].setdefault("source", "measurement")
    return records, basis


def _seed(seed: int) -> None:
    import numpy as np
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def _optimizer(model: Any, steps: int) -> tuple[Any, Any]:
    import torch
    head = list(model.head.parameters())
    ids = {id(parameter) for parameter in head}
    groups = [{"params": [p for p in model.trainable_parameters() if id(p) not in ids], "lr": 2e-5},
              {"params": head, "lr": 2e-5}]
    optimizer = torch.optim.AdamW(groups, lr=2e-5, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=[2e-5, 2e-5],
                                                  total_steps=steps, pct_start=0.1)
    return optimizer, scheduler


def _step(model: Any, tokenizer: Any, records: list[dict[str, Any]], args: Any,
          optimizer: Any, scheduler: Any, epoch: int) -> dict[str, Any]:
    import torch
    import kev.train as native
    from .grouping import microbatch_plan
    counts = native.state_token_counts(tokenizer, records)
    shapes = native.plan_shapes(model, tokenizer, args, records, epoch, set(), counts)
    plan = microbatch_plan(native, records, args, 1, 0, set(), shapes)
    if sum(ending for _, _, ending in plan) != 1:
        raise RuntimeError("The fixed payload does not form one grouped optimizer step.")
    torch.cuda.synchronize()
    started = time.perf_counter()
    total_loss = tokens = padded = 0
    passes: list[dict[str, Any]] = []
    for chunk, count, ending in plan:
        variants = native.encode_batch(model, tokenizer, args, chunk, epoch, set())
        denominator = count * sum(v.share for v in variants) / len(chunk)
        loss, terms = native.batch_loss(model, args, variants, "cuda", {}, None,
                                       torch.autocast("cuda", dtype=torch.bfloat16))
        (loss / denominator).backward()
        total_loss += float(loss.detach()) / denominator
        tokens += sum(v.tokens for v in variants)
        cost = native.pass_tokens([native.shape(v.enc) for v in variants], True)
        padded += cost
        passes.append({"records": len(chunk), "padded_tokens": cost})
        if ending:
            gradient_norm = float(torch.nn.utils.clip_grad_norm_(model.trainable_parameters(),
                                  native.MAX_GRAD_NORM, error_if_nonfinite=True))
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
    torch.cuda.synchronize()
    return {"loss": total_loss, "seconds": time.perf_counter() - started,
            "records": len(records), "forward_tokens": tokens, "padded_tokens": padded,
            "gradient_norm": gradient_norm, "passes": passes,
            "peak_device_bytes": torch.cuda.max_memory_allocated()}


def run_measurement(root: Path, config: dict[str, Any], mode: str = "reference") -> dict[str, Any]:
    """Measure full grouped optimizer steps and optionally compare official RMSNorm kernels."""
    import importlib.metadata
    import torch
    import kev.train as native
    from .kernels import install_required_kernels, kernel_calls, convolution_calls
    from .measure import training_model
    from .unsloth_trial import evaluate_gate, patch_context
    if mode not in {"reference", "unsloth"}:
        raise ValueError("The measurement mode must be reference or unsloth.")
    max_state = int(config.get("max_state", 10240))
    if max_state != 10240:
        raise ValueError("This measurement contract requires the owner-selected context limit.")
    packages = {name: importlib.metadata.version(name) for name in config["gpu_packages"]}
    mismatches = {name: {"expected": expected, "actual": packages[name]}
                  for name, expected in config["gpu_packages"].items()
                  if packages[name].partition("+")[0] != expected}
    if mismatches and not config.get("allow_environment_difference", False):
        raise RuntimeError(f"The measured stack differs from the pinned environment: {mismatches}")
    root.mkdir(parents=True, exist_ok=True)
    destination = root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination.mkdir()

    def save(name: str, value: Any) -> None:
        (destination / f"{name}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
        print(json.dumps({"measurement": name, "path": str(destination), "status": value.get("status")}), flush=True)
        if config.get("modal_volume"):
            import modal
            modal.Volume.from_name(config["modal_volume"]).commit()

    _seed(1)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    kernels = install_required_kernels()
    tokenizer, model = training_model(config)
    maximum = _largest_record(tokenizer, max_state)
    records, basis = _payload(tokenizer, config, maximum)
    serialized = "".join(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" for record in records).encode()
    (destination / "fixed-records.jsonl").write_bytes(serialized)
    snapshot = {name: value.detach().cpu().clone() for name, value in model.named_parameters() if value.requires_grad}
    total_memory = torch.cuda.get_device_properties(0).total_memory
    schedule_steps = math.ceil(int(config.get("projection_records", 12200)) / 16)

    def reset() -> tuple[Any, Any]:
        model.zero_grad(set_to_none=True)
        with torch.no_grad():
            for name, parameter in model.named_parameters():
                if name in snapshot:
                    parameter.copy_(snapshot[name])
        _seed(1)
        return _optimizer(model, schedule_steps)

    probes: list[dict[str, Any]] = []
    accepted: list[int] = []
    # Probe full forward/backward with resident AdamW moments, not inference-only memory.
    optimizer, scheduler = reset()
    warm = deepcopy(maximum)
    warm["state"] = "Short warmup state."
    warm["_meta"] = {"id": "warm", "source": "measurement"}
    _step(model, tokenizer, [deepcopy(warm) for _ in range(16)], _arguments(max_state), optimizer, scheduler, 0)
    # Later accumulated forwards coexist with every trainable parameter's gradient buffer.
    for parameter in model.trainable_parameters():
        parameter.grad = torch.zeros_like(parameter)
    low, high, copies = 0, 17, 1
    while copies < high:
        batch = [deepcopy(maximum) for _ in range(copies)]
        for index, record in enumerate(batch):
            record["_meta"] = {"id": str(index), "source": "measurement"}
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        try:
            variants = native.encode_batch(model, tokenizer, _arguments(max_state), batch, 0, set())
            cost = native.pass_tokens([native.shape(v.enc) for v in variants], True)
            loss, _ = native.batch_loss(model, _arguments(max_state), variants, "cuda", {}, None,
                                        torch.autocast("cuda", dtype=torch.bfloat16))
            (loss / copies).backward()
            torch.cuda.synchronize()
            peak = torch.cuda.max_memory_allocated()
            probe = {"copies": copies, "padded_tokens": cost, "peak_device_bytes": peak,
                     "status": "PASS" if peak <= 0.9 * total_memory else "OVER_MEMORY_LIMIT"}
            if probe["status"] == "PASS":
                accepted.append(cost)
        except torch.cuda.OutOfMemoryError:
            probe = {"copies": copies, "status": "OOM"}
        finally:
            model.zero_grad(set_to_none=False)
            if "variants" in locals():
                del variants
            if "loss" in locals():
                del loss
            gc.collect()
            torch.cuda.empty_cache()
        probes.append(probe)
        save("pass-cap-progress", {"probes": probes})
        if probe["status"] == "PASS":
            low = max(low, copies)
        else:
            high = min(high, copies)
        if high - low <= 1:
            break
        copies = min(16, copies * 2) if high == 17 and copies < 16 else (low + high) // 2
        if copies == low:
            break
    if not accepted:
        raise RuntimeError("The largest admitted record exceeds the GPU memory bound.")
    validations: list[dict[str, Any]] = []
    cap = 0
    for candidate in sorted(set(accepted), reverse=True):
        torch.cuda.reset_peak_memory_stats()
        try:
            validation = _step(model, tokenizer, records, _arguments(max_state, candidate),
                               optimizer, scheduler, 0)
            validation["status"] = ("PASS" if validation["peak_device_bytes"] <= 0.9 * total_memory
                                    else "OVER_MEMORY_LIMIT")
        except torch.cuda.OutOfMemoryError as error:
            validation = {"status": "OOM", "error": str(error),
                          "peak_device_bytes": torch.cuda.max_memory_allocated()}
        finally:
            model.zero_grad(set_to_none=False)
            gc.collect()
            torch.cuda.empty_cache()
        validation["pass_tokens_max"] = candidate
        validations.append(validation)
        save("full-step-cap-validation", {"attempts": validations})
        if validation["status"] == "PASS":
            cap = candidate
            break
    del optimizer, scheduler
    if not cap:
        raise RuntimeError("No measured pass cap completes the full optimizer step within the GPU memory bound.")
    args = _arguments(max_state, cap)
    arms: dict[str, Any] = {}
    source_contract = config.get("accelerator_source")
    for arm in (["reference", "repeat", "unsloth"] if mode == "unsloth" else ["reference"]):
        optimizer, scheduler = reset()
        try:
            if arm == "unsloth":
                if not source_contract:
                    raise ValueError("The accelerator comparison requires an official-source pin.")
                source_path = destination / "official-rms-layernorm.py"
                with urllib.request.urlopen(source_contract["url"], timeout=60) as response:
                    source_path.write_bytes(response.read())
                patch_contract = {"source_path": str(source_path), "source_blob_sha": source_contract["blob_sha"]}
            context = patch_context(model, patch_contract) if arm == "unsloth" else nullcontext({})
            with context as manifest:
                _step(model, tokenizer, records, args, optimizer, scheduler, 0)
                del optimizer, scheduler
                optimizer, scheduler = reset()
                torch.cuda.reset_peak_memory_stats()
                timings = [_step(model, tokenizer, records, args, optimizer, scheduler, step) for step in range(3)]
                seconds = sum(row["seconds"] for row in timings)
                count = sum(row["records"] for row in timings)
                arms[arm] = {"steps": timings, "manifest": dict(manifest),
                             "records_per_hour": count / seconds * 3600,
                             "tokens_per_second": sum(row["forward_tokens"] for row in timings) / seconds,
                             "projected_training_seconds": int(config.get("projection_records", 12200)) * seconds / count}
        except Exception as error:
            if arm != "unsloth":
                raise
            arms[arm] = {"status": "REFERENCE_FALLBACK", "error_type": type(error).__name__, "error": str(error)}
            model.zero_grad(set_to_none=True)
        del optimizer, scheduler
        save(arm, arms[arm])
    result = {"status": "PASS", "mode": mode, "path": str(destination), "arms": arms,
              "payload_sha256": hashlib.sha256(serialized).hexdigest(), "payload_records": len(records),
              "projection_basis": basis, "max_state": max_state, "b_state": max_state - 1,
              "pass_tokens_max": cap, "memory_probes": probes, "gpu_memory_bytes": total_memory,
              "full_step_cap_validations": validations,
              "gpu": torch.cuda.get_device_name(0), "seed": 1,
              "packages": packages, "environment_differences": mismatches,
              "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in Path(__file__).parent.glob("*.py")},
              "kernel_calls": kernel_calls(), "convolution_calls": convolution_calls(), "kernel_binding": kernels}
    if not result["kernel_calls"] or not result["convolution_calls"]:
        raise RuntimeError("Required FLA kernels did not execute.")
    if mode == "unsloth" and "steps" in arms["unsloth"]:
        result["accelerator_gate"] = evaluate_gate(*[[row["loss"] for row in arms[arm]["steps"]] for arm in ("reference", "repeat", "unsloth")],
                     [row["seconds"] for row in arms["reference"]["steps"] + arms["repeat"]["steps"]],
                     [row["seconds"] for row in arms["unsloth"]["steps"]])
        if not arms["unsloth"]["manifest"]["backward_calls"]:
            result["accelerator_gate"]["status"] = "REFERENCE_FALLBACK"
    elif mode == "unsloth":
        result["accelerator_gate"] = arms["unsloth"]
    save("result", result)
    return result
