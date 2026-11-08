"""Split requirement candidates without paraphrasing their source text."""

import re
import pysbd

_LIST = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+\S")


def split_units(text: str, source: str) -> list[dict[str, str | int]]:
    """Split markdown list items and other prose into verbatim requirement units."""
    segmenter = pysbd.Segmenter(language="en", clean=False)
    chunks: list[str] = []
    prose: list[str] = []
    current: list[str] = []
    list_indent = 0

    def flush_prose() -> None:
        if prose:
            chunks.extend(piece for piece in segmenter.segment("".join(prose)) if piece.strip())
            prose.clear()

    def flush_item() -> None:
        if current:
            chunks.append("".join(current))
            current.clear()

    for line in text.splitlines(keepends=True):
        match = _LIST.match(line)
        if match:
            flush_prose()
            flush_item()
            current.append(line)
            list_indent = len(match.group(1))
        elif current and (not line.strip() or len(line) - len(line.lstrip()) > list_indent):
            current.append(line)
        else:
            flush_item()
            prose.append(line)
    flush_item()
    flush_prose()
    return [{"source": source, "position": index, "text": chunk}
            for index, chunk in enumerate(chunks, 1)]


def rf_window(units: list[dict[str, str | int]], i: int) -> str:
    """Mark one zero-indexed unit with at most two same-source neighbours each side."""
    if not 0 <= i < len(units):
        raise IndexError("The requirement-unit index is outside the source.")
    source = units[i]["source"]
    pieces = []
    for index in range(max(0, i - 2), min(len(units), i + 3)):
        if units[index]["source"] != source:
            continue
        text = str(units[index]["text"])
        pieces.append(f"⟦ {text} ⟧" if index == i else text)
    return "\n".join(pieces)
