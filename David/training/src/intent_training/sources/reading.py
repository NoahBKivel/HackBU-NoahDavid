"""Stream data rows from inert local source files."""

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def _json_records(path: Path) -> Iterator[Any]:
    decoder = json.JSONDecoder()
    with path.open(encoding="utf-8-sig") as handle:
        buffer = ""
        ended = False

        def fill() -> bool:
            nonlocal buffer, ended
            chunk = handle.read(65536)
            buffer += chunk
            ended = not chunk
            return bool(chunk)

        while not buffer.strip() and fill():
            pass
        buffer = buffer.lstrip()
        if not buffer:
            raise ValueError(f"Empty JSON source: {path.name}.")
        array = buffer.startswith("[")
        if array:
            buffer = buffer[1:]
        first = True
        while True:
            buffer = buffer.lstrip()
            while not buffer and not ended:
                fill()
                buffer = buffer.lstrip()
            if array and buffer.startswith("]"):
                buffer = buffer[1:]
                break
            if not first and array:
                if not buffer.startswith(","):
                    raise ValueError(f"Expected a JSON array separator: {path.name}.")
                buffer = buffer[1:].lstrip()
            while True:
                try:
                    value, offset = decoder.raw_decode(buffer)
                    break
                except json.JSONDecodeError:
                    if ended:
                        raise
                    fill()
                    buffer = buffer.lstrip()
            buffer = buffer[offset:]
            yield value
            first = False
            if not array:
                break
        if buffer.strip() or handle.read().strip():
            raise ValueError(f"Unexpected trailing JSON content: {path.name}.")


def _files(path: Path) -> Iterator[Path]:
    if path.is_file():
        yield path
        return
    for directory, folders, files in os.walk(path):
        folders[:] = sorted(folder for folder in folders if not (
            folder.startswith((".", "datasets--", "models--"))
            or folder in {"__pycache__", "huggingface", "hf_cache"}))
        for name in sorted(files):
            candidate = Path(directory) / name
            if not name.startswith(".") and candidate.suffix.lower() in {".json", ".jsonl", ".parquet"}:
                yield candidate


def rows(raw_dir: Path) -> Iterator[dict[str, Any]]:
    """Yield JSON, JSONL or parquet records without executing dataset code."""
    for path in _files(Path(raw_dir)):
        suffix = path.suffix.lower()
        if suffix == ".jsonl":
            with path.open(encoding="utf-8-sig") as handle:
                for line in handle:
                    if line.strip():
                        value = json.loads(line)
                        if not isinstance(value, dict):
                            raise ValueError(f"A source row must be an object: {path.name}.")
                        yield value
        elif suffix == ".parquet":
            import pyarrow.parquet as parquet

            with parquet.ParquetFile(path) as source:
                for batch in source.iter_batches(batch_size=64):
                    yield from batch.to_pylist()
        elif suffix == ".json":
            for record in _json_records(path):
                if not isinstance(record, dict):
                    raise ValueError(f"A source row must be an object: {path.name}.")
                yield record
        else:
            raise ValueError(f"Unsupported source file format: {path.suffix}.")
