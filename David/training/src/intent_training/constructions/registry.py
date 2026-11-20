"""Resolve independent construction builders from their declarations."""

from importlib import import_module
import json
from pathlib import Path
from typing import Any, Callable


def entries() -> list[dict[str, Any]]:
    """Read all registered construction definitions in stable order."""
    folder = Path(__file__).with_name("entries")
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.json"))]


def builder(slug: str) -> Callable[..., Any]:
    """Resolve a declared construction builder by slug."""
    matches = [entry for entry in entries() if entry["slug"] == slug]
    if len(matches) != 1:
        raise ValueError(f"Expected one construction definition for {slug}, found {len(matches)}.")
    return getattr(import_module(matches[0]["module"]), "build")
