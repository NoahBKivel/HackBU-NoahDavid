"""Preserve ambiguous issue prompts and oracle originals for teacher judgments."""

import csv
import json
from pathlib import Path
import xml.etree.ElementTree as xml
import zipfile

from .events import from_messages, instruction, message
from .reading import rows


def originals(raw_dir: Path) -> dict[str, str]:
    """Join actual SWE-bench originals, never a summary or outcome table."""
    directory = raw_dir / "originals"
    if not directory.exists():
        workbook = raw_dir / "full_summaries_verified.xlsx"
        return _workbook_originals(workbook) if workbook.exists() else {}
    return {row["instance_id"]: row["problem_statement"] for row in rows(directory)
            if row.get("instance_id") and row.get("problem_statement")}


def _workbook_originals(path: Path) -> dict[str, str]:
    """Read sparse XLSX cells by their column references, without executing code."""
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        strings = ["".join(part.text or "" for part in item.findall(".//s:t", namespace))
                   for item in xml.fromstring(archive.read("xl/sharedStrings.xml")).findall("s:si", namespace)]
        sheet = xml.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    records = []
    for row in sheet.findall("s:sheetData/s:row", namespace):
        record = {}
        for cell in row:
            column = "".join(char for char in cell.attrib["r"] if char.isalpha())
            value = cell.find("s:v", namespace)
            record[column] = (strings[int(value.text)] if cell.get("t") == "s"
                              else value.text or "") if value is not None else ""
        records.append(record)
    header = records[0]
    output = {}
    for row in records[1:]:
        named = {header[column]: value for column, value in row.items()}
        if named.get("instance_id") and named.get("original_issue"):
            output[named["instance_id"]] = named["original_issue"]
    return output


def seeds(raw_dir: Path):
    """Read the released underspecified issue table in its source order."""
    path = raw_dir / "underspecified.csv"
    if not path.exists():
        return
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def generation_requests(raw_dir: Path, limit: int = 200):
    """Request first decisions only when the complete original is available."""
    full = originals(raw_dir)
    emitted = 0
    for row in seeds(raw_dir):
        key = row["instance_id"]
        if key not in full:
            continue
        if emitted >= limit:
            break
        mode = "asked" if emitted % 2 == 0 else "silently_assumed"
        direction = (
            "Ask one targeted clarification question about a material missing detail."
            if mode == "asked" else
            "Write a concrete first implementation decision that commits to one material "
            "reading of a missing detail without asking or acknowledging the ambiguity."
        )
        yield {"id": f"ambig_swe-{key}", "purpose": "first_action",
               "prompt": "Act as a coding assistant receiving this issue:\n" + row["problem_statement"]
               + "\n\n" + direction + " Do not claim to have read files, run tools or changed code. "
               "Output only the visible assistant message. Hidden oracle context for the missing "
               "detail follows; do not quote it as something the user supplied:\n" + full[key],
               "max_output_tokens": 600,
               "refs": {"source": "ambig_swe", "instance_id": key,
                        "underspecified_issue": row["problem_statement"],
                        "full_original_issue": full[key], "intended_first_action": mode}}
        emitted += 1


def convert(raw_dir: Path):
    """Yield grounded first decisions or actual conversations without source verdicts."""
    raw_dir = Path(raw_dir)
    full = originals(raw_dir)
    trajectories = raw_dir / "trajectories"
    actual = {}
    if trajectories.exists():
        actual = {row["instance_id"]: row for row in rows(trajectories)
                  if row.get("instance_id") and row.get("messages")}
    responses = raw_dir.parents[1] / "generation" / "responses"
    for row in seeds(raw_dir):
        key = row["instance_id"]
        if key not in full:
            continue
        reasoning = {}
        if key in actual:
            continuation = [item for item in actual[key]["messages"]
                            if item.get("role") != "system"]
            events, reasoning = from_messages(
                [{"role": "user", "content": row["problem_statement"]}] + continuation)
            harness = "OpenHands"
            trajectory_id = actual[key].get("trajectory_id", key)
        else:
            path = responses / f"ambig_swe-{key}.json"
            if not path.exists():
                continue
            response = json.loads(path.read_text(encoding="utf-8"))
            text = response.get("text")
            if response.get("id") != f"ambig_swe-{key}" or not isinstance(text, str) or not text.strip():
                raise ValueError("A generated first action requires its matching id and nonempty text.")
            events = [instruction(row["problem_statement"]), message(text, 2)]
            harness = "generated_first_action"
            trajectory_id = response["id"]
        if len(events) < 2:
            continue
        side = {"reasoning": reasoning, "full_original_issue": full[key],
                "source_labels": [], "licence": "MIT",
                "outcomes": {"published_model_outcomes": {
                    name: value for name, value in row.items()
                    if name not in {"instance_id", "problem_statement"}}}}
        meta = {"source": "ambig_swe", "source_record_id": key, "task_id": key,
                "trajectory_id": trajectory_id, "objective": ["M7"], "licence": "MIT",
                "harness": harness, "cut_kind": "unspecified"}
        yield events, side, meta
