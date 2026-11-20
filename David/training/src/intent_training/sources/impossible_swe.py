"""Fail closed for an inaccessible source whose row schema remains unverified.

The authenticated data-file request was denied. No actual rows were inspected,
so a message mapping and visible test-edit rule cannot yet be validated.
"""

from pathlib import Path
from typing import Iterator


class UninspectedSourceError(ValueError):
    """Source data arrived but its actual row schema still needs inspection."""


def convert(raw_dir: Path) -> Iterator[tuple[list[dict], dict, dict]]:
    """Yield zero records without source data and reject unverified source rows.

    Repository file listings and access reports are metadata, not trajectories.
    New raw files require inspection of three actual rows before conversion can
    be implemented. No source label becomes visible evidence in this adapter.
    """
    raw_dir = Path(raw_dir)
    if not raw_dir.is_dir():
        raise FileNotFoundError("The raw source directory does not exist.")
    metadata = {"repository-files.json", "access.json"}
    unexpected = sorted(
        path for path in raw_dir.rglob("*")
        if path.is_file() and path.name not in metadata
    )
    if unexpected:
        raise UninspectedSourceError(
            "Source files require three actual row inspections and a verified "
            "message mapping before conversion."
        )
    yield from ()
