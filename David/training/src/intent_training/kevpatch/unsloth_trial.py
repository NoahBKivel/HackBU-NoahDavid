"""Bound an official Unsloth LoRA trial without changing shared-prefix attention."""

import ast
from contextlib import contextmanager
import hashlib
import linecache
import math
from pathlib import Path
import types
from typing import Any, Iterator, Sequence


def _source_functions(path: Path, expected_blob_sha: str, names: set[str],
                      namespace: dict[str, Any]) -> dict[str, Any]:
    source = path.read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    if actual != expected_blob_sha:
        raise ValueError("The official accelerator source differs from its pinned Git blob.")
    tree = ast.parse(source, filename=str(path))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in functions} != names:
        raise ValueError("The official accelerator source lacks the selected helper definitions.")
    text = source.decode("utf-8")
    linecache.cache[str(path)] = (len(source), None, text.splitlines(keepends=True), str(path))
    selected = ast.Module(body=functions, type_ignores=[])
    exec(compile(selected, str(path), "exec"), namespace)
    return namespace


def _decoder_signature(model: Any) -> dict[str, Any]:
    base = model.lm.get_base_model() if hasattr(model.lm, "get_base_model") else model.lm
    return {
        "attention": base.config._attn_implementation,
        "layers": [(id(layer.forward.__func__),
                    id(layer.self_attn.forward.__func__) if hasattr(layer, "self_attn") else None)
                   for layer in base.layers],
    }


@contextmanager
def lean_lora_trial(model: Any, source_path: Path, source_blob_sha: str) -> Iterator[dict[str, Any]]:
    """Apply only verified official LoRA helpers and restore every touched instance attribute."""
    from peft.tuners.lora.layer import Linear
    import torch
    helpers = _source_functions(source_path, source_blob_sha,
                                {"_lean_lora_forward", "_lean_lora"},
                                {"torch": torch, "types": types})
    before = _decoder_signature(model)
    if before["attention"] != "sdpa":
        raise ValueError("The accelerator trial requires the native SDPA mask path.")
    names = ("forward", "_unsloth_adapter", "_unsloth_peft_forward")
    originals = [(module, {name: (name in module.__dict__, module.__dict__.get(name)) for name in names})
                 for module in model.lm.modules() if type(module) is Linear]
    manifest: dict[str, Any] = {
        "variant": "unsloth_lean_lora", "source_blob_sha": source_blob_sha,
        "eligible_modules": len(originals), "patched_modules": 0, "forward_calls": 0,
        "attention": before["attention"], "decoder_forwards_unchanged": False,
        "scope": "Official decision-model LoRA helpers only; no FastModel, attention or loss patch.",
    }
    try:
        helpers["_lean_lora"](model.lm)
        for module, original in originals:
            if getattr(module.forward, "__func__", None) is not helpers["_lean_lora_forward"]:
                continue
            official = module.forward

            def counted(self: Any, *args: Any, _official: Any = official, **kwargs: Any) -> Any:
                manifest["forward_calls"] += 1
                return _official(*args, **kwargs)

            module.forward = types.MethodType(counted, module)
            manifest["patched_modules"] += 1
        manifest["decoder_forwards_unchanged"] = _decoder_signature(model) == before
        if not manifest["patched_modules"]:
            raise RuntimeError("The official LoRA helpers patched no eligible native adapter modules.")
        if not manifest["decoder_forwards_unchanged"]:
            raise RuntimeError("The accelerator modified the decoder attention or layer path.")
        yield manifest
        if _decoder_signature(model) != before:
            raise RuntimeError("The decoder path changed during the accelerator trial.")
    finally:
        for module, original in originals:
            for name, (present, value) in original.items():
                if present:
                    setattr(module, name, value)
                else:
                    module.__dict__.pop(name, None)


@contextmanager
def patch_context(model: Any, contract: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Trial official zero-centered RMSNorm kernels while preserving the native decoder path."""
    import torch
    import triton
    import triton.language as tl
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5RMSNorm
    names = {"_gemma_rms_layernorm_forward", "_rms_backward_row", "_rms_layernorm_backward"}
    kernels = _source_functions(Path(contract["source_path"]), contract["source_blob_sha"],
                               names, {"torch": torch, "triton": triton, "tl": tl,
                                       "__name__": "intent_official_unsloth_rmsnorm"})
    kernels["_rms_layernorm_backward"] = triton.jit(kernels["_rms_layernorm_backward"])
    before = _decoder_signature(model)
    if before["attention"] != "sdpa":
        raise ValueError("The RMSNorm trial requires the native SDPA mask path.")
    norms = [module for module in model.lm.modules() if type(module) is Qwen3_5RMSNorm]
    if not norms or any(module.weight.requires_grad for module in norms):
        raise ValueError("The RMSNorm trial requires frozen native zero-centered norm weights.")
    originals = [(module, "forward" in module.__dict__, module.__dict__.get("forward")) for module in norms]
    manifest: dict[str, Any] = {
        "variant": "unsloth_zero_centered_rmsnorm", "source_blob_sha": contract["source_blob_sha"],
        "patched_modules": len(norms), "forward_calls": 0, "backward_calls": 0,
        "attention": before["attention"], "decoder_forwards_unchanged": True,
        "scope": "Official Unsloth frozen-weight RMSNorm kernels; native masks and dropout retained.",
    }

    class FrozenRMSNorm(torch.autograd.Function):
        @staticmethod
        def forward(ctx: Any, values: Any, weight: Any, eps: float) -> Any:
            manifest["forward_calls"] += 1
            shape = values.shape
            columns = shape[-1]
            inputs = values.reshape(-1, columns).contiguous()
            weights = weight.contiguous()
            output = torch.empty_like(inputs)
            inverse = torch.empty((inputs.shape[0],), dtype=torch.float32, device=inputs.device)
            block = triton.next_power_of_2(columns)
            warps = min(32, max(4, block // 2048))
            with torch.cuda.device(inputs.device):
                kernels["_gemma_rms_layernorm_forward"][(inputs.shape[0],)](
                    output, inputs, weights, inverse, output.stride(0), inputs.stride(0), 1, 1,
                    columns, eps, LONG_INDEXING=inputs.numel() >= 2**31,
                    BLOCK_SIZE=block, num_warps=warps)
            ctx.save_for_backward(inputs, weights, inverse)
            ctx.eps, ctx.block, ctx.warps = eps, block, warps
            return output.reshape(shape)

        @staticmethod
        def backward(ctx: Any, gradient: Any) -> tuple[Any, None, None]:
            manifest["backward_calls"] += 1
            shape = gradient.shape
            inputs, weights, inverse = ctx.saved_tensors
            incoming = gradient.reshape_as(inputs).contiguous()
            outgoing = torch.empty_like(inputs)
            rows, columns = inputs.shape
            with torch.cuda.device(inputs.device):
                kernels["_rms_layernorm_backward"][(rows,)](
                    incoming, outgoing, inputs, weights, inverse, None, rows, 1,
                    incoming.stride(0), outgoing.stride(0), inputs.stride(0), 1, 1,
                    columns, ctx.eps, GEMMA=True, LONG_INDEXING=inputs.numel() >= 2**31,
                    BLOCK_SIZE=ctx.block, TRAIN_W=False, FROM_Y=False, num_warps=ctx.warps)
            return outgoing.reshape(shape), None, None

    def accelerated(self: Any, values: Any) -> Any:
        return FrozenRMSNorm.apply(values, self.weight, self.eps)

    try:
        for module in norms:
            module.forward = types.MethodType(accelerated, module)
        if _decoder_signature(model) != before:
            raise RuntimeError("The RMSNorm patch changed the decoder layer or attention forward.")
        yield manifest
        if _decoder_signature(model) != before:
            raise RuntimeError("The decoder layer or attention forward changed during the RMSNorm trial.")
    finally:
        for module, present, value in originals:
            if present:
                module.forward = value
            else:
                module.__dict__.pop("forward", None)


def evaluate_gate(reference_losses: Sequence[float], repeat_losses: Sequence[float],
                  accelerated_losses: Sequence[float], reference_seconds: Sequence[float],
                  accelerated_seconds: Sequence[float]) -> dict[str, Any]:
    """Compare measured fixed-batch loss noise and nonoverlapping timing spreads."""
    if not reference_losses or not reference_seconds or not accelerated_seconds:
        raise ValueError("The accelerator comparison requires measured losses and timings.")
    if len({len(reference_losses), len(repeat_losses), len(accelerated_losses)}) != 1:
        raise ValueError("The accelerator comparison requires the same fixed loss sequence.")
    values = [*reference_losses, *repeat_losses, *accelerated_losses,
              *reference_seconds, *accelerated_seconds]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Every comparison value must be finite.")
    if min(*reference_seconds, *accelerated_seconds) <= 0:
        raise ValueError("Step durations must be positive.")
    relative = lambda left, right: abs(left - right) / max(abs(left), abs(right), 1e-12)
    noise = max(relative(a, b) for a, b in zip(reference_losses, repeat_losses))
    difference = max(relative(a, b) for a, b in zip(reference_losses, accelerated_losses))
    threshold = max(noise, 1e-3)
    loss_pass = difference <= threshold
    time_pass = max(accelerated_seconds) < min(reference_seconds)
    return {
        "status": "PASS" if loss_pass and time_pass else "REFERENCE_FALLBACK",
        "loss_pass": loss_pass, "timing_pass": time_pass,
        "same_seed_relative_noise": noise, "maximum_relative_loss_difference": difference,
        "relative_loss_threshold": threshold,
        "reference_seconds_range": [min(reference_seconds), max(reference_seconds)],
        "accelerated_seconds_range": [min(accelerated_seconds), max(accelerated_seconds)],
        "timing_rule": "The slowest accelerated step is faster than the fastest reference step.",
    }
