"""Split documents at their own structure while preserving every source character."""

import re
from typing import Any

import pysbd

from .tokens import count_tokens

_STRUCTURE = re.compile(r"(?m)^(?:#{1,6}\s+[^\n]+|\d+(?:\.\d+)*[.)]?\s+[^\n]+)")


def _pack_parts(parts: list[str], cap: int, tokenizer: Any) -> list[str]:
    packed: list[str] = []
    current = ""
    for part in parts:
        if current and count_tokens(current + part, tokenizer) > cap:
            packed.append(current)
            current = ""
        current += part
    if current:
        packed.append(current)
    return packed


def _split_large(text: str, cap: int, tokenizer: Any) -> list[str]:
    paragraphs = re.split(r"(?<=\n)(?=\s*\n)", text)
    parts = []
    segmenter = pysbd.Segmenter(language="en", clean=False)
    for paragraph in paragraphs:
        if count_tokens(paragraph, tokenizer) > cap:
            sentences = segmenter.segment(paragraph)
            for sentence in sentences:
                if count_tokens(sentence, tokenizer) > cap:
                    raise ValueError("A single sentence exceeds the section cap and cannot be split losslessly.")
            parts.extend(sentences)
        else:
            parts.append(paragraph)
    return _pack_parts(parts, cap, tokenizer)


def split_sections(document: dict[str, str] | str, *, tokenizer: Any = None,
                   cap: int | None = None, floor: int | None = None) -> list[dict[str, str]]:
    """Split a document at headings or paragraphs with optional exact token bounds."""
    text = document if isinstance(document, str) else document.get("text", "")
    path = "" if isinstance(document, str) else document.get("path", "")
    if not text:
        return []
    matches = list(_STRUCTURE.finditer(text))
    sections = []
    if matches:
        if matches[0].start():
            sections.append({"path": path, "heading": "", "text": text[:matches[0].start()]})
        for index, match in enumerate(matches):
            stop = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            heading = re.sub(r"^#{1,6}\s+", "", match.group(0)).strip()
            sections.append({"path": path, "heading": heading, "text": text[match.start():stop]})
    else:
        paragraphs = re.split(r"(?<=\n)(?=\s*\n)", text)
        sections = [{"path": path, "heading": "", "text": part} for part in paragraphs if part]
    if cap is not None:
        if tokenizer is None or cap <= 0:
            raise ValueError("A positive section cap requires an explicit tokenizer.")
        bounded = []
        for section in sections:
            pieces = (_split_large(section["text"], cap, tokenizer)
                      if count_tokens(section["text"], tokenizer) > cap else [section["text"]])
            bounded.extend({**section, "text": piece} for piece in pieces)
        sections = bounded
        minimum = cap // 4 if floor is None else floor
        merged = []
        for section in sections:
            if merged and count_tokens(section["text"], tokenizer) < minimum and (
                count_tokens(merged[-1]["text"] + section["text"], tokenizer) <= cap
            ):
                merged[-1]["text"] += section["text"]
            elif merged and count_tokens(merged[-1]["text"], tokenizer) < minimum and (
                count_tokens(merged[-1]["text"] + section["text"], tokenizer) <= cap
            ):
                previous = merged.pop()
                merged.append({**previous, "text": previous["text"] + section["text"]})
            else:
                merged.append(dict(section))
        sections = merged
    return [{"id": f"S{index}", **section} for index, section in enumerate(sections, 1)]
