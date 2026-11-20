"""Preserve InFoBench instructions and centrally sampled responses."""

import hashlib
import json
from pathlib import Path

from monitor_format import split_units, validate_events

from .events import instruction, message
from .reading import rows


def generation_id(row: dict) -> str:
    """Bind each request to the source identifier and verbatim instruction."""
    payload = json.dumps([row["id"], row["instruction"], row.get("input", "")], ensure_ascii=False)
    return "infobench-" + hashlib.sha256(payload.encode()).hexdigest()[:24]


def prompt_text(row: dict) -> str:
    """Retain both the instruction and its separate input verbatim."""
    text = row["instruction"]
    if row.get("input"):
        text += "\n\n" + row["input"]
    return text


def generation_requests(raw_dir: Path):
    """Expose generation work without leaking the decomposed judge hints."""
    for row in rows(raw_dir):
        reference = {"dataset": "kqsong/InFoBench", "source_record_id": row["id"]}
        yield {"id": generation_id(row), "purpose": "instruction_response",
               "prompt": prompt_text(row), "max_output_tokens": 2048,
               "references": [reference], "refs": [reference]}


def _response_text(path: Path) -> str:
    response = json.loads(path.read_text(encoding="utf-8"))
    if response.get("id", path.stem) != path.stem:
        raise ValueError("The central generator response id does not match the request.")
    text = response.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("The central generator response must contain nonempty text.")
    return text


def convert(raw_dir: Path):
    """Yield only source rows with real central generator response artifacts."""
    raw_dir = Path(raw_dir)
    responses = raw_dir.parent.parent / "generation" / "responses"
    for row in rows(raw_dir):
        response_path = responses / (generation_id(row) + ".json")
        if not response_path.exists():
            continue
        text = prompt_text(row)
        events = [instruction(text), message(_response_text(response_path), 2)]
        validate_events(events)
        side = {"reasoning": {}, "outcomes": {}, "source_labels": [], "licence": "MIT",
                "requirement_units": split_units(text, "[I1]"),
                "teacher_hints": [{"basis": "outcome", "origin": "dataset decomposition",
                                   "decomposed_questions": row["decomposed_questions"],
                                   "question_label": row.get("question_label", [])}],
                "generation": {"request_id": generation_id(row),
                               "response_path": str(response_path),
                               "response_sha256": hashlib.sha256(response_path.read_bytes()).hexdigest()}}
        meta = {"source": "infobench", "trajectory_id": row["id"], "task_id": row["id"],
                "source_record_id": row["id"], "objective": ["RF", "M2", "D2", "G2"],
                "licence": "MIT", "harness": "instruction-response", "cut_seq": 2,
                "cut_kind": "unspecified"}
        yield events, side, meta


def materialize(root: Path) -> dict:
    """Write bounded requests, validated conversions and measured source evidence."""
    root = Path(root)
    raw_dir = root / "data/downloads/infobench"
    request_path = root / "data/generation/requests/infobench.jsonl"
    output_path = root / "data/converted/infobench.jsonl"
    report_path = root / "results/sources/infobench.json"
    for path in [request_path, output_path, report_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
    requests = list(generation_requests(raw_dir))
    request_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in requests), encoding="utf-8")
    converted = list(convert(raw_dir))
    output_path.write_text("".join(json.dumps(dict(events=e, side=s, meta=m), ensure_ascii=False) + "\n"
                                   for e, s, m in converted), encoding="utf-8")
    inputs = sorted(raw_dir.glob("*.jsonl"))
    responses = [root / "data/generation/responses" / (request["id"] + ".json")
                 for request in requests]
    inputs += [path for path in responses if path.exists()]
    hashes = [{"path": str(path.relative_to(root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
              for path in inputs + [request_path, output_path]]
    report = {"source": "infobench", "source_rows": len(requests), "generation_requests": len(requests),
              "converted_records": len(converted), "pending_generation": len(requests) - len(converted),
              "filter_counts": {"missing_generated_response": len(requests) - len(converted)},
              "positive_rule_counts": {}, "label_basis": "teacher per requirement",
              "requirement_hints": sum(len(row["decomposed_questions"]) for row in rows(raw_dir)),
              "files": hashes, "errors": []}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(materialize(Path(__file__).resolve().parents[3])))
