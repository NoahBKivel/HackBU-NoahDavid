"""Require the installed Triton DeltaNet path during training."""

from typing import Any

_calls = 0
_conv_calls = 0


def install_required_kernels() -> dict[str, Any]:
    """Bind the training DeltaNet chunk rule directly to FLA without a torch fallback."""
    import inspect
    from fla.ops.gated_delta_rule import chunk_gated_delta_rule
    from fla.modules.conv import causal_conv1d
    from transformers.models.qwen3_5 import modeling_qwen3_5
    if not inspect.getmodule(chunk_gated_delta_rule).__name__.startswith("fla."):
        raise RuntimeError("The required FLA DeltaNet kernel is unavailable.")

    def required_chunk(*args: Any, **kwargs: Any) -> Any:
        global _calls
        _calls += 1
        return chunk_gated_delta_rule(*args, **kwargs)

    def required_conv(hidden_states: Any, weight: Any, bias: Any = None,
                      activation: str | None = None, **kwargs: Any) -> Any:
        global _conv_calls
        _conv_calls += 1
        output, _ = causal_conv1d(hidden_states.transpose(1, 2), weight, bias,
                                 activation=activation, backend="triton")
        return output.transpose(1, 2)

    modeling_qwen3_5.torch_chunk_gated_delta_rule = required_chunk
    modeling_qwen3_5.causal_conv1d_fn = required_conv
    return {"chunk_rule_module": inspect.getmodule(chunk_gated_delta_rule).__name__,
            "convolution_module": inspect.getmodule(causal_conv1d).__name__,
            "torch_fallback_allowed": False}


def kernel_calls() -> int:
    """Return the observed number of required DeltaNet chunk-rule calls."""
    return _calls


def convolution_calls() -> int:
    """Return the observed number of required Triton convolution calls."""
    return _conv_calls
