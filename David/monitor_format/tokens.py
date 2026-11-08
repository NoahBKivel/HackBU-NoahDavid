"""Pure token accounting and lossless boundary-aware trimming."""

import re
from typing import Any

_SPECIAL = re.compile(r"<\|([A-Za-z0-9_]+)\|>")


def token_ids(text: str, tokenizer: Any) -> list[int]:
    """Encode user text with Kev's special-token escaping."""
    escaped = _SPECIAL.sub(r"<¦\1¦>", text)
    encoded = tokenizer(escaped, add_special_tokens=False)
    return list(encoded.input_ids if hasattr(encoded, "input_ids") else encoded["input_ids"])


def count_tokens(text: str, tokenizer: Any) -> int:
    """Count user-text tokens under an explicitly supplied tokenizer."""
    return len(token_ids(text, tokenizer))


def trim_text(text: str, budget: int, tokenizer: Any, marker: str = "[cut]") -> str:
    """Keep a balanced character head and tail within an exact token budget."""
    if budget < 0:
        raise ValueError("The token budget must be nonnegative.")
    if count_tokens(text, tokenizer) <= budget:
        return text
    if count_tokens(marker, tokenizer) > budget:
        return ""
    low, high = 0, len(text)
    best = marker
    while low <= high:
        keep = (low + high) // 2
        head, tail = (keep + 1) // 2, keep // 2
        candidate = text[:head] + marker + (text[-tail:] if tail else "")
        if count_tokens(candidate, tokenizer) <= budget:
            best, low = candidate, keep + 1
        else:
            high = keep - 1
    return best


def trim_field(text: str, budget: int, tokenizer: Any) -> str:
    """Trim an event field and report the number of removed source tokens."""
    original = count_tokens(text, tokenizer)
    if original <= budget:
        return text
    if budget <= 0:
        return ""
    low, high = 0, len(text)
    best = ""
    while low <= high:
        keep = (low + high) // 2
        head, tail = (keep + 1) // 2, keep // 2
        prefix, suffix = text[:head], text[-tail:] if tail else ""
        removed = original - count_tokens(prefix, tokenizer) - count_tokens(suffix, tokenizer)
        candidate = prefix + f"[cut {max(0, removed)} tokens]" + suffix
        if count_tokens(candidate, tokenizer) <= budget:
            best, low = candidate, keep + 1
        else:
            high = keep - 1
    return best
