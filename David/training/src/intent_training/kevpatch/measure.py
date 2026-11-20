"""Measure required training kernels and padded-pass memory."""

import gc
import math
from pathlib import Path
import time
from typing import Any


def training_model(config: dict[str, Any]) -> tuple[Any, Any]:
    """Load the pinned stock adapter into the trainable architecture used by Kev."""
    import torch
    from kev.checkpoint import Checkpoint, Meta
    from kev.model import DecisionModel, load_tokenizer
    tokenizer = load_tokenizer(config["base"], revision=config["base_revision"])
    model = DecisionModel(config["base"], tokenizer, "cuda", lora=16,
                          revision=config["base_revision"], head_dim=256,
                          lora_targets="all", dtype=torch.float32, attn="sdpa")
    meta = Meta(base=config["base"], base_revision=config["base_revision"], lora=16,
                head_dim=256, weights_dtype="fp32", weights="lora")
    checkpoint = config.get("checkpoint_path", f"{config['checkpoint']}@{config['checkpoint_revision']}")
    Checkpoint(checkpoint).warm_start(model, meta)
    model.lm.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.lm.config.use_cache = False
    model.train()
    return tokenizer, model


def synthetic_record(tokenizer: Any, state_tokens: int, question_count: int,
                     long_instruction: bool = False) -> dict[str, Any]:
    """Create a bounded native decision record at an explicitly measured shape."""
    from kev.model import user_tokens
    text = " a" * state_tokens
    while len(user_tokens(tokenizer, text)) > state_tokens:
        text = text[:-2]
    questions = [{"instr": " p" * 600 if long_instruction and i == 0 else "Allowed?",
                  "options": ["no", "yes"], "label": i % 2, "qtype": "noul"}
                 for i in range(question_count)]
    return {"state": text, "questions": questions}


def largest_monitor_record(tokenizer: Any) -> dict[str, Any]:
    """Pack exact monitor templates at the maximum state and quoted-row allowance."""
    from copy import deepcopy
    from kev.data import materialize
    from kev.model import encode, training_context
    from kev.train import pass_tokens, shape
    from monitor_format import QUESTION_TABLE, fill_question
    state = synthetic_record(tokenizer, 32767, 1)["state"]
    candidates = []
    current = {"state": state, "questions": {}}
    for question_id in QUESTION_TABLE:
        question = fill_question(question_id, requirement_text=" p" * 1000,
                                 correction="Check the requirement. " + " p" * 1000,
                                 fired_questions=["M2"], event_seq=1, summary="stated requirement at E1",
                                 section_id=1, tokenizer=tokenizer)
        kind = question["type"]
        question["label"] = next(iter(question["criteria"])) if kind == "choice" else 0 if kind == "score" else False
        question["src"] = "synthetic_monitor"
        trial = {"state": state, "questions": {**current["questions"], question_id: question}}
        encoded = encode(tokenizer, materialize(trial), strict=True, **{key: value for key, value in training_context(32768).items() if key != "max_packed"})
        if len(encoded["ids"]) > training_context(32768)["max_packed"]:
            candidates.append(materialize(current))
            current = {"state": state, "questions": {question_id: question}}
        else:
            current = trial
    if current["questions"]:
        candidates.append(materialize(current))
    context = training_context(32768)
    return max(candidates, key=lambda record: pass_tokens([shape(encode(tokenizer, record, strict=True, max_state=context["max_state"], max_branch=context["max_branch"]))], True))


def measure_pass(model: Any, tokenizer: Any, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Run a complete shared-prefix forward and backward and measure its peak."""
    import torch
    import torch.nn.functional as functional
    from kev.model import rows_of, training_context
    context = training_context(32768)
    encodings = [model.encode(tokenizer, record, max_state=context["max_state"],
                              max_branch=context["max_branch"], strict=True) for record in records]
    if any(len(encoding["ids"]) > context["max_packed"] for encoding in encodings):
        raise ValueError("The synthetic record exceeds Kev's packed allowance.")
    shapes = [(len(rows_of(encoding)[0]), [len(row["ids"]) for row in rows_of(encoding)[2]])
              for encoding in encodings]
    padded = len(shapes) * max(state for state, _ in shapes) + sum(len(branches) for _, branches in shapes) * max(branch for _, branches in shapes for branch in branches)
    model.zero_grad(set_to_none=True)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    started = time.monotonic()
    try:
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model.forward_batch(encodings, True)
        loss = sum(functional.cross_entropy(values.float()[None], torch.tensor([question["label"]], device="cuda"))
                   for record, answers in zip(records, logits) for question, values in zip(record["questions"], answers))
        loss.backward()
        torch.cuda.synchronize()
        return {"status": "PASS", "padded_tokens": padded, "records": len(records),
                "shapes": shapes, "seconds": time.monotonic() - started,
                "peak_device_bytes": torch.cuda.max_memory_allocated(), "loss": loss.item()}
    except torch.cuda.OutOfMemoryError:
        return {"status": "OOM", "padded_tokens": padded, "records": len(records),
                "shapes": shapes, "seconds": time.monotonic() - started,
                "peak_device_bytes": torch.cuda.max_memory_allocated()}
    finally:
        model.zero_grad(set_to_none=True)
        gc.collect()
        torch.cuda.empty_cache()


def kernel_and_memory(config: dict[str, Any], save: Any) -> dict[str, Any]:
    """Measure the required kernel path, bounded pass cap and runtime projection."""
    import torch
    from .kernels import install_required_kernels, kernel_calls, convolution_calls
    torch.manual_seed(1)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    kernel = install_required_kernels()
    tokenizer, model = training_model(config)
    total = torch.cuda.get_device_properties(0).total_memory
    warm = measure_pass(model, tokenizer, [synthetic_record(tokenizer, 256, 4)])
    kernel.update(status="PASS" if warm["status"] == "PASS" and kernel_calls() > 0 and convolution_calls() > 0
                  and model.lm.config._attn_implementation == "sdpa" else "FAIL",
                  calls=kernel_calls(), convolution_calls=convolution_calls(), attention=model.lm.config._attn_implementation,
                  gpu=torch.cuda.get_device_name(0), total_memory_bytes=total,
                  warmup=warm)
    save("kernel-check", kernel)
    if kernel["status"] != "PASS":
        raise RuntimeError("The required training kernel check failed.")
    largest = largest_monitor_record(tokenizer)
    probes = []
    accepted = []
    for copies in (1, 2, 3, 4):
        measurement = measure_pass(model, tokenizer, [largest] * copies)
        probes.append(measurement)
        save("pass-cap-progress", {"probes": probes, "memory_fraction_limit": 0.9})
        if measurement["status"] == "PASS" and measurement["peak_device_bytes"] <= 0.9 * total:
            accepted.append(measurement)
        else:
            break
    if not accepted:
        raise RuntimeError("The largest synthetic record does not fit within the GPU memory bound.")
    ceiling = max(measurement["padded_tokens"] for measurement in accepted)
    measure_pass(model, tokenizer, [synthetic_record(tokenizer, 4096, 16)])
    measure_pass(model, tokenizer, [synthetic_record(tokenizer, 24576, 16)])
    timings = []
    for state_tokens in (4096, 4096, 4096, 4096, 24576):
        measurement = measure_pass(model, tokenizer, [synthetic_record(tokenizer, state_tokens, 16)])
        timings.append(measurement)
    short = [row["seconds"] for row in timings[:-1]]
    long = timings[-1]["seconds"]
    seconds_per_record = 0.9 * (sum(short) / len(short)) + 0.1 * long
    result = {"status": "PASS", "pass_tokens_max": ceiling, "probes": probes,
              "gpu_memory_bytes": total, "memory_fraction_limit": 0.9,
              "largest_synthetic_question_count": len(largest["questions"]), "actual_corpus_shape_check_pending": True,
              "throughput_records_per_hour": 3600 / seconds_per_record,
              "projected_training_seconds": 12200 * seconds_per_record,
              "timings": timings, "projection_short_share": 0.9, "projection_long_share": 0.1}
    save("pass-cap-throughput", result)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return result
