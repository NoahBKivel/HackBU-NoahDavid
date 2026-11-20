"""Deduplicate identical RF judgments while preserving every parent unit link."""

from collections import Counter
import json
import os

from .records import stable_id
from .records import load_tokenizer, scan
from monitor_format import fill_question


def deduplicate(root):
    folder = root / "data" / "prepared"
    seen = {}
    counts = Counter()
    names = ("requirements_unique", "requirements_fanout")
    handles = {name: (folder / f"{name}.jsonl.tmp").open("w", encoding="utf-8", newline="\n") for name in names}
    try:
        for line in (folder / "requirements.jsonl").open(encoding="utf-8"):
            record = json.loads(line)
            judgment = {key: record.get(key) for key in ("state", "questions", "teacher_side", "source", "purpose", "pass")}
            digest = stable_id(judgment)
            canonical = seen.get(digest)
            if canonical is None:
                canonical = record["record_id"]
                seen[digest] = canonical
                handles["requirements_unique"].write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                counts["unique"] += 1
            alias = {key: record[key] for key in ("record_id", "parent_record_id", "unit_id")}
            alias["canonical_record_id"] = canonical
            alias["judgment_content_hash"] = digest
            alias["content_sha256"] = stable_id({"state": record["state"], "questions": record["questions"]})
            alias["unit"] = record["unit"]
            handles["requirements_fanout"].write(json.dumps(alias, separators=(",", ":")) + "\n")
            counts["original"] += 1
    finally:
        for handle in handles.values():
            handle.close()
    for name in names:
        os.replace(folder / f"{name}.jsonl.tmp", folder / f"{name}.jsonl")
    report = {"counts": dict(counts), "saved_judgments": counts["original"] - counts["unique"],
              "key_fields": ["state", "questions", "teacher_side", "source", "purpose", "pass"]}
    (root / "results" / "preparation" / "requirements.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)
    return report


def enrich(root, selections=None):
    """Add G2 only for verbatim units whose RF votes resolved yes."""
    selections = selections or root / "data" / "votes" / "results" / "teacher" / "requirements_selected.jsonl"
    approved = {}
    for line in selections.open(encoding="utf-8"):
        item = json.loads(line)
        approved[item["parent_record_id"]] = item["requirements"]
    tokenizer = load_tokenizer(root / "data" / "tokenizer")
    path = root / "data" / "prepared" / "main.jsonl"
    temporary = path.with_suffix(".jsonl.enriched.tmp")
    records = rows = 0
    with path.open(encoding="utf-8") as source, temporary.open("w", encoding="utf-8", newline="\n") as target:
        for line in source:
            record = json.loads(line)
            record["questions"] = {key: value for key, value in record["questions"].items()
                                   if key.split("#")[0] != "G2"}
            record.pop("requirements", None)
            requirements = approved.get(record["record_id"], [])
            if record["_meta"].get("form") != "screen" and requirements:
                candidates = {f"R{index}": unit for index, unit in enumerate(record["requirement_units"], 1)}
                for unit in requirements:
                    candidate = candidates.get(unit["unit_id"])
                    if candidate is None or any(unit[field] != candidate[field] for field in ("source", "position", "text")):
                        raise ValueError("An RF selection must exactly match its original parent unit.")
                    record["questions"][f"G2#{unit['unit_id']}"] = fill_question("G2", requirement_text=unit["text"], tokenizer=tokenizer)
                    rows += 1
                record["requirements"] = requirements
                records += 1
            scan(record)
            target.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(temporary, path)
    report = {"records_with_approved_requirements": records, "g2_rows": rows, "selection_path": str(selections)}
    (root / "results" / "preparation" / "requirements_enriched.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)
    return report
