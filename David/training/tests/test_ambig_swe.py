"""Check that missing oracles never become grounded ambiguity examples."""

import csv
import json
from pathlib import Path
import zipfile

from intent_training.sources.ambig_swe import convert, generation_requests, originals
from monitor_format import validate_events


def fixture(tmp_path: Path):
    raw = tmp_path / "downloads" / "ambig_swe"
    raw.mkdir(parents=True)
    with (raw / "underspecified.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["instance_id", "problem_statement", "model"])
        writer.writeheader()
        writer.writerow({"instance_id": "project__repo-issue", "problem_statement": "Fix the output.", "model": "1"})
    return raw


def test_missing_oracle_is_not_replaced_by_summary(tmp_path):
    raw = fixture(tmp_path)
    assert list(convert(raw)) == []
    assert list(generation_requests(raw)) == []


def test_workbook_sparse_cells_preserve_column_identity(tmp_path):
    raw = fixture(tmp_path)
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    strings = ["instance_id", "missing_column", "original_issue", "repo-issue", "Full issue."]
    shared = f'<sst {ns}>' + ''.join(f'<si><t>{value}</t></si>' for value in strings) + '</sst>'
    sheet = (f'<worksheet {ns}><sheetData><row r="1">'
             '<c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
             '<c r="C1" t="s"><v>2</v></c></row><row r="2">'
             '<c r="A2" t="s"><v>3</v></c><c r="C2" t="s"><v>4</v></c>'
             '</row></sheetData></worksheet>')
    with zipfile.ZipFile(raw / "full_summaries_verified.xlsx", "w") as archive:
        archive.writestr("xl/sharedStrings.xml", shared)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    assert originals(raw) == {"repo-issue": "Full issue."}


def test_generated_text_keeps_oracle_hidden_and_outcomes_unlabelled(tmp_path):
    raw = fixture(tmp_path)
    (raw / "originals").mkdir()
    original = "The output must retain a trailing newline."
    (raw / "originals" / "issues.jsonl").write_text(json.dumps({
        "instance_id": "project__repo-issue", "problem_statement": original}) + "\n", encoding="utf-8")
    request = next(generation_requests(raw))
    response_dir = tmp_path / "generation" / "responses"
    response_dir.mkdir(parents=True)
    response = {"id": request["id"], "text": "Should the output include a newline?"}
    (response_dir / (request["id"] + ".json")).write_text(json.dumps(response), encoding="utf-8")
    events, side, meta = next(convert(raw))
    validate_events(events)
    assert events[0]["new_items"][0]["id"] == "I1"
    assert original not in json.dumps(events)
    assert side["full_original_issue"] == original
    assert side["source_labels"] == []
    assert meta["task_id"] == "project__repo-issue"
    assert meta["cut_kind"] == "unspecified"
    assert all(event["agent_thinking"] == "" for event in events)
