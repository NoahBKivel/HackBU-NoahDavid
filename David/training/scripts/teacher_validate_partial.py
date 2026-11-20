"""Validate completed Codex records without inventing a batch completion time."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT.parent)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    from kev_prepare_upload import available_memory_gib
    memory = available_memory_gib()
    if memory <= 3.5:
        print(json.dumps({"status": "RAM_GATE_CLOSED", "available_gib": memory}))
        return
    from intent_training.teacher import validate_vote
    from intent_training.teacher.claims import claim_path, teacher_input_hash
    output = ROOT / "data/votes/limit-10239"
    index_path = output / "codex_validated_records.jsonl"
    previous = {}
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            previous[(item["record_id"], item["teacher_input_sha256"])] = item
    now = datetime.now(timezone.utc).isoformat()
    errors = []
    count = 0
    allocations = {}
    for entry in json.loads(args.manifest.read_text(encoding="utf-8")):
        if entry["model_family"] != "sol" or not Path(entry["output"]).exists():
            continue
        batch = json.loads(Path(entry["input"]).read_text(encoding="utf-8"))
        path = claim_path(ROOT / "data/votes/claims", batch["batch_id"], "sol", batch["input_sha256"])
        if not path.exists():
            continue
        claim = json.loads(path.read_text(encoding="utf-8"))
        if not claim["owner"].startswith("codex-"):
            continue
        records = {row["record_id"]: row for row in batch["records"]}
        seen = set()
        for line in Path(entry["output"]).read_text(encoding="utf-8").splitlines():
            try:
                vote = validate_vote(json.loads(line), batch, "sol")
                if vote["record_id"] in seen:
                    raise ValueError("A record has duplicate Sol envelopes.")
                seen.add(vote["record_id"])
                row = records[vote["record_id"]]
                key = (vote["record_id"], teacher_input_hash(row))
                previous.setdefault(key, {"record_id": key[0], "teacher_input_sha256": key[1],
                    "validated_at": now, "batch_id": batch["batch_id"], "owner": claim["owner"],
                    "vote_output": entry["output"], "model_family": "sol", "allocation": "single_sol"})
                allocations[key[0]] = {"allocation": "single_sol", "record_kind": "construction",
                                       "provenance": "remote construction-only preparation packet"}
                count += 1
            except (ValueError, KeyError, TypeError) as error:
                errors.append({"output": entry["output"], "error": str(error)})
    temporary = index_path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for item in previous.values():
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    temporary.replace(index_path)
    (output / "allocation_by_record_id.json").write_text(json.dumps(allocations), encoding="utf-8")
    print(json.dumps({"available_gib": memory, "validated_codex_records": count,
                      "first_observed_validation_at": now, "errors": errors, "index": str(index_path)}))


if __name__ == "__main__":
    main()
