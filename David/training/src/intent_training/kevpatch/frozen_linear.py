"""Reuse the existing autocast representation of immutable linear weights."""

from contextlib import contextmanager
import types
from typing import Any, Iterator


@contextmanager
def cached_frozen_linears(model: Any) -> Iterator[dict[str, int]]:
    """Cache only frozen fp32 Linear weights for CUDA bf16 autocast calls."""
    import torch
    import torch.nn.functional as functional
    originals = []
    manifest = {"modules": 0, "cache_bytes": 0, "cached_calls": 0}
    for module in model.lm.modules():
        if (type(module) is not torch.nn.Linear or module.weight.requires_grad
                or module.weight.dtype != torch.float32
                or (module.bias is not None and module.bias.requires_grad)):
            continue
        original = module.forward
        cache: dict[str, Any] = {}

        def forward(layer: Any, inputs: Any, _original: Any = original,
                    _cache: Any = cache) -> Any:
            if (not torch.is_autocast_enabled("cuda")
                    or torch.get_autocast_dtype("cuda") != torch.bfloat16
                    or inputs.device.type != "cuda"):
                return _original(inputs)
            signature = (layer.weight._version, layer.weight.data_ptr(),
                         None if layer.bias is None else layer.bias._version)
            if _cache.get("signature") != signature:
                old_bytes = _cache.get("bytes", 0)
                weight = layer.weight.detach().to(torch.bfloat16)
                bias = None if layer.bias is None else layer.bias.detach().to(torch.bfloat16)
                size = weight.numel() * weight.element_size()
                if bias is not None:
                    size += bias.numel() * bias.element_size()
                _cache.update(signature=signature, weight=weight, bias=bias, bytes=size)
                manifest["cache_bytes"] += size - old_bytes
            manifest["cached_calls"] += 1
            return functional.linear(inputs, _cache["weight"], _cache["bias"])

        originals.append((module, original))
        module.forward = types.MethodType(forward, module)
        manifest["modules"] += 1
    try:
        yield manifest
    finally:
        for module, original in originals:
            module.forward = original
