"""Verify every public generation payload and append its source index mapping."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
raw_path = ROOT / "data/downloads/in3/train.jsonl"
raw = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
requests = [json.loads(line) for line in (ROOT / "data/generation/requests/in3.jsonl")
            .read_text(encoding="utf-8").splitlines()]
table = ["", "| Request id | Source row index | JSONL line | Vague | Missing-detail index | Selected-option index |",
         "|---|---:|---:|---|---:|---:|"]
for request in requests:
    ref = request["refs"]
    index = ref["row_index"]
    row = raw[index]
    assert ref["task"] == row["task"] and ref["vague"] == row["vague"]
    digest = hashlib.sha256(row["task"].encode()).hexdigest()[:12]
    assert request["id"] == f"in3-{index}-{digest}"
    detail = ref["detail"]
    detail_index = option_index = None
    if detail:
        public = {key: value for key, value in detail.items() if key != "selected_option"}
        detail_index = row["missing_details"].index(public)
        option_index = public["options"].index(detail["selected_option"])
    table.append(f"| {request['id']} | {index} | {index + 1} | {str(row['vague']).lower()} | "
                 f"{detail_index} | {option_index} |")
note = ROOT / "notes/source-in3.md"
prefix = note.read_text(encoding="utf-8").split("\n| Request id |", 1)[0].rstrip()
note.write_text(prefix + "\n" + "\n".join(table) + "\n", encoding="utf-8")
print(json.dumps({"verified_public_payloads": len(requests),
                  "source_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest()}))
