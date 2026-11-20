"""Load declarative source converters without changing the assembly pipeline."""

from importlib import import_module
import json
from pathlib import Path
from typing import Any, Callable, Iterator

Converted = tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]


def entries() -> list[dict[str, Any]]:
    """Return source definitions in stable slug order."""
    folder = Path(__file__).with_name("entries")
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.json"))]


def converter(slug: str) -> Callable[[Path], Iterator[Converted]]:
    """Resolve one declared converter by its unique slug."""
    matches = [entry for entry in entries() if entry["slug"] == slug]
    if len(matches) != 1:
        raise ValueError(f"Expected one source definition for {slug}, found {len(matches)}.")
    return getattr(import_module(matches[0]["module"]), "convert")
