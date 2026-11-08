"""Validate and copy model handoffs without replacing checkpoint files in place."""

import json
import math
import os
import re
import shutil
from pathlib import Path

from David.monitor_format import QUESTION_TABLE


def read_json(path: Path) -> dict:
    """Read one JSON object while rejecting duplicate keys and nonfinite constants."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}.")
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f"Nonfinite JSON value: {value}.")
    result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(result, dict):
        raise ValueError("The handoff JSON root must be an object.")
    return result


def validate_calibration(parameters: dict) -> None:
    """Require exact serving question identities and finite calibration parameters."""
    if not isinstance(parameters, dict):
        raise ValueError("Calibration must be an object keyed by base question id.")
    for key, config in parameters.items():
        if key not in QUESTION_TABLE or "#" in key or "~" in key:
            raise ValueError(f"Unknown serving calibration question: {key}.")
        if not isinstance(config, dict) or set(config) != {"T", "b"}:
            raise ValueError(f"Calibration for {key} must contain exactly T and b.")
        temperature, offset = config["T"], config["b"]
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not math.isfinite(temperature) or temperature <= 0:
            raise ValueError(f"Calibration temperature for {key} must be positive and finite.")
        question = QUESTION_TABLE[key]
        if question["type"] == "noul":
            if temperature < 1 or isinstance(offset, bool) or not isinstance(offset, (int, float)) or not math.isfinite(offset):
                raise ValueError(f"Yes/no calibration for {key} requires T at least one and a finite scalar b.")
        else:
            options = set(question["criteria"]) if question["type"] == "choice" else {str(i) for i in range(len(question["criteria"]))}
            if not isinstance(offset, dict) or set(offset) != options:
                raise ValueError(f"Calibration offsets for {key} must match its serving option keys.")
            if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in offset.values()):
                raise ValueError(f"Calibration offsets for {key} must be finite numbers.")


def validated_length(record: dict) -> int:
    """Resolve an unambiguous positive L or validated_length from handoff metadata."""
    if not isinstance(record, dict):
        raise ValueError("Long-context metadata must be an object.")
    values = [record[key] for key in ("L", "validated_length") if key in record]
    if not values or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values):
        raise ValueError("Long-context metadata needs a positive integer L or validated_length.")
    if len(set(values)) != 1:
        raise ValueError("Long-context metadata contains conflicting validated lengths.")
    return values[0]


def source_identity(metadata: dict, explicit: str | None = None) -> str:
    """Resolve source from supplied metadata or an explicit value without guessing."""
    if not isinstance(metadata, dict):
        raise ValueError("Selection metadata must be an object.")
    values = [value for value in (metadata.get("source"), explicit) if value is not None]
    if not values or any(not isinstance(value, str) or value not in {"stock-kev", "kev-tuned"} for value in values):
        raise ValueError("A stock-kev or kev-tuned source must be supplied explicitly or in selection metadata.")
    if len(set(values)) != 1:
        raise ValueError("Explicit source conflicts with the selected checkpoint metadata.")
    return values[0]


def copy_handoff(source: Path, target: Path, version: str, explicit_source: str | None = None) -> dict:
    """Validate every handoff input before copying a fresh checkpoint and switching its pointer."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", version):
        raise ValueError("The checkpoint version must be one safe path component.")
    checkpoint = source / "selected"
    calibration_path, length_path = source / "calibration.json", source / "long_context.json"
    if not checkpoint.is_dir() or not (checkpoint / "head.pt").is_file() or not calibration_path.is_file() or not length_path.is_file():
        raise FileNotFoundError("The handoff requires selected/head.pt, calibration.json and long_context.json.")
    calibration = read_json(calibration_path)
    validate_calibration(calibration)
    length = validated_length(read_json(length_path))
    metadata_path = checkpoint / "selected.json"
    source_name = source_identity(read_json(metadata_path) if metadata_path.exists() else {}, explicit_source)
    files = list(checkpoint.rglob("*"))
    if any(path.is_symlink() for path in [checkpoint, calibration_path, length_path, *files]):
        raise ValueError("A handoff must contain regular files and directories, without symlinks.")
    destination = target / "selected" / version
    if destination.exists():
        raise FileExistsError("The checkpoint version already exists and will not be overwritten.")
    destination.mkdir(parents=True)
    shutil.copytree(checkpoint, destination / "checkpoint")
    shutil.copyfile(calibration_path, destination / "calibration.json")
    shutil.copyfile(length_path, destination / "long_context.json")
    pointer = {"checkpoint": str(destination / "checkpoint"),
               "calibration": str(destination / "calibration.json"), "source": source_name}
    temporary = target / f".selected-{version}.json.tmp"
    temporary.write_text(json.dumps(pointer), encoding="utf-8")
    os.replace(temporary, target / "selected.json")
    return {"selected": pointer, "validated_length": length,
            "long_context": str(destination / "long_context.json"),
            "checkpoint_files": sum(path.is_file() for path in files),
            "checkpoint_bytes": sum(path.stat().st_size for path in files if path.is_file())}
