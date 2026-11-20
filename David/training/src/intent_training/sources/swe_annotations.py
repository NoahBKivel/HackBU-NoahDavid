"""Join human issue ratings with separately generated first-action messages.

The input adapter joins the released per-annotator CSV with original issue rows.
No annotation is an action label, and no ensemble rating enters the events.
"""

import csv
import hashlib
import json
from pathlib import Path

from .events import instruction, message

SOURCE = "swe_annotations"
LICENCE = "Annotation licence unverified; SWE-bench issue dataset MIT"


def join_originals(raw_dir: Path, originals_path: Path, limit: int = 200) -> dict:
    """Join inspected annotation columns to issue text in annotation-file order."""
    originals = {}
    with Path(originals_path).open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            originals[row["instance_id"]] = row["problem_statement"]
    grouped = {}
    annotation_count = 0
    with (raw_dir / "samples_with_3_annotations_public.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            annotation_count += 1
            score = float(row["underspecified"]) if row["underspecified"] else None
            if score is not None and (not score.is_integer() or not 0 <= score <= 3):
                raise ValueError("The source underspecified score is outside its ordinal scale.")
            grouped.setdefault(row["instance_id"], []).append({
                "user_id": row["user_id"], "underspecified": int(score) if score is not None else None,
                "underspecified_notes": row["underspecified_notes"]})
    selected = [key for key in grouped if key in originals][:limit]
    with (raw_dir / "joined.jsonl").open("w", encoding="utf-8") as output:
        for key in selected:
            output.write(json.dumps({"instance_id": key, "problem_statement": originals[key],
                                     "annotations": grouped[key]}, ensure_ascii=False) + "\n")
    return {"annotation_rows": annotation_count, "annotation_issues": len(grouped),
            "original_issues": len(originals), "matched_issues": sum(key in originals for key in grouped),
            "selected_issues": len(selected)}


def joined_rows(raw_dir: Path):
    """Read explicitly joined issue records, preserving annotator observations."""
    path = Path(raw_dir) / "joined.jsonl"
    if not path.exists():
        return
    seen = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            instance = row["instance_id"]
            if not isinstance(instance, str) or not instance or instance in seen:
                raise ValueError("Each joined issue needs a unique nonempty instance id.")
            seen.add(instance)
            if not isinstance(row["problem_statement"], str) or not row["problem_statement"].strip():
                raise ValueError("Each joined issue requires its original problem statement.")
            annotations = row["annotations"]
            if not isinstance(annotations, list) or not annotations:
                raise ValueError("Each joined issue requires per-annotator observations.")
            for annotation in annotations:
                score = annotation["underspecified"]
                if score is not None and (type(score) is not int or not 0 <= score <= 3):
                    raise ValueError("An annotator underspecified score must be an integer from zero to three.")
            yield row


def request_for(row: dict) -> dict:
    """Build an action request from the issue alone without annotation leakage."""
    reference = {"instance_id": row["instance_id"], "problem_statement": row["problem_statement"]}
    digest = hashlib.sha256(json.dumps(reference, sort_keys=True).encode()).hexdigest()[:24]
    return {
        "id": f"swe_annotations_{digest}",
        "purpose": "Write an initial coding-assistant message for a real issue.",
        "prompt": (
            "You are a coding assistant beginning work on the following issue. "
            "Write only your first user-visible message: explain the immediate next action "
            "or ask a question if needed. You have not inspected files, run tools or changed code. "
            "Do not claim you have performed any action. Respond naturally to the issue.\n\n"
            + row["problem_statement"]
        ),
        "max_output_tokens": 400,
        "refs": [reference],
    }


def prepare(raw_dir: Path, training_dir: Path) -> int:
    """Persist central-generator requests and exact evaluation exclusions."""
    rows = list(joined_rows(raw_dir))
    requests = training_dir / "data/generation/requests/swe_annotations.jsonl"
    exclusions = training_dir / "data/exclusions/swe_annotations.jsonl"
    requests.parent.mkdir(parents=True, exist_ok=True)
    exclusions.parent.mkdir(parents=True, exist_ok=True)
    with requests.open("w", encoding="utf-8") as req, exclusions.open("w", encoding="utf-8") as exc:
        for row in rows:
            req.write(json.dumps(request_for(row), ensure_ascii=False) + "\n")
            exc.write(json.dumps({"source": SOURCE, "instance_id": row["instance_id"],
                                  "reason": "Issue used for training generation."}) + "\n")
    return len(rows)


def convert(raw_dir: Path):
    """Yield only rows with an actual central-generator response on disk."""
    raw_dir = Path(raw_dir)
    training_dir = raw_dir.resolve().parents[2]
    for row in joined_rows(raw_dir):
        request = request_for(row)
        response_path = training_dir / "data/generation/responses" / (request["id"] + ".json")
        if not response_path.exists():
            continue
        response = json.loads(response_path.read_text(encoding="utf-8"))
        if response.get("id") != request["id"]:
            raise ValueError("A generator response must match its request id.")
        text = response.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("A generator response requires nonempty text.")
        instance = row["instance_id"]
        events = [instruction(row["problem_statement"]), message(text, 2)]
        side = {"reasoning": {}, "licence": LICENCE, "source_labels": [],
                "outcomes": {"annotation_hints": {"basis": "outcome",
                    "origin": "human request annotation", "annotations": row["annotations"]}},
                "generation": {"request_id": request["id"]}}
        meta = {"source": SOURCE, "trajectory_id": request["id"], "task_id": instance,
                "source_record_id": instance, "objective": ["M7"], "licence": LICENCE,
                "harness": "generated_first_action", "cut_seq": 2, "cut_kind": "unspecified"}
        yield events, side, meta

