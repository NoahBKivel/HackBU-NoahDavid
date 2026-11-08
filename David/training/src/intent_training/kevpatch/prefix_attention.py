"""Run shared-prefix causal attention without padding-dependent dense masks."""

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass
class PrefixMask:
    """Describe valid state lengths without materializing a per-layer attention bias."""

    state: bool
    prefix_width: int
    groups: list[tuple[int, Any]]


def length_groups(lengths: list[int]) -> list[tuple[int, list[int]]]:
    """Group equal lengths while preserving their first encounter order."""
    groups: dict[int, list[int]] = defaultdict(list)
    for index, length in enumerate(lengths):
        if length < 1:
            raise ValueError("A shared-prefix state must contain a real token.")
        groups[length].append(index)
    return list(groups.items())


def prefix_mask(allow: Any, dtype: Any, attention: str) -> Any:
    """Convert the exact shared-prefix mask into independent causal sequences."""
    import torch
    if attention != 'sdpa':
        raise ValueError("The padding-free prefix path requires SDPA.")
    query, key = allow.shape[-2:]
    state = query == key
    prefix = key if state else key - query
    lengths = (allow[:, -1, :].sum(-1) if state else allow[:, 0, :prefix].sum(-1)).tolist()
    groups = [(length, torch.tensor(indices, device=allow.device))
              for length, indices in length_groups(lengths)]
    return PrefixMask(state, prefix, groups)


def prefix_sdpa(module: Any, query: Any, key: Any, value: Any, attention_mask: Any,
                dropout: float = 0.0, scaling: float | None = None,
                **kwargs: Any) -> tuple[Any, None]:
    """Apply SDPA to real causal tokens and scatter results into the original layout."""
    import torch
    import torch.nn.functional as functional
    from torch.nn.attention.bias import causal_lower_right
    if not isinstance(attention_mask, PrefixMask):
        raise TypeError("The specialized attention path requires a shared-prefix mask.")
    mask = attention_mask
    result = torch.zeros_like(query)
    for length, indices in mask.groups:
        q = query.index_select(0, indices)
        k = key.index_select(0, indices)
        v = value.index_select(0, indices)
        left = mask.prefix_width - length
        if mask.state:
            q, k, v = q[:, :, left:], k[:, :, left:], v[:, :, left:]
            bias, causal = None, True
        else:
            k, v = k[:, :, left:], v[:, :, left:]
            bias, causal = causal_lower_right(q.shape[-2], k.shape[-2]), False
        answer = functional.scaled_dot_product_attention(
            q, k, v, attn_mask=bias, is_causal=causal,
            dropout_p=dropout, scale=scaling,
            enable_gqa=q.shape[1] != k.shape[1])
        if mask.state:
            answer = functional.pad(answer, (0, 0, left, 0))
        result.index_copy_(0, indices, answer)
    return result.transpose(1, 2).contiguous(), None


@contextmanager
def padding_free_attention() -> Iterator[None]:
    """Temporarily specialize only Kev's functional shared-prefix SDPA calls."""
    import kev.shared_prefix as shared
    from transformers.modeling_utils import ALL_ATTENTION_FUNCTIONS
    original_mask = shared._masks
    original_attention = ALL_ATTENTION_FUNCTIONS['sdpa']

    def attention(module: Any, query: Any, key: Any, value: Any, mask: Any,
                  **kwargs: Any) -> Any:
        if isinstance(mask, PrefixMask):
            return prefix_sdpa(module, query, key, value, mask, **kwargs)
        return original_attention(module, query, key, value, mask, **kwargs)

    shared._masks = prefix_mask
    ALL_ATTENTION_FUNCTIONS.register('sdpa', attention)
    try:
        yield
    finally:
        shared._masks = original_mask
        ALL_ATTENTION_FUNCTIONS.register('sdpa', original_attention)
