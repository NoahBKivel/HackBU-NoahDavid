"""Check actual tokenizer preparation and separation of future private evidence."""

from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from intent_training.prepare.records import load_tokenizer, prepare_stream, prepare_native
from intent_training.sources.events import instruction, message, tool
from monitor_format import EVERY_EVENT, fill_question, count_tokens


def fixture_row():
    return {"events": [instruction("Use the public API."), message("Working.", 2),
                       instruction("FUTURE INSTRUCTION", 3), message("Future result", 4)],
            "side": {"reasoning": {"2": "visible reasoning", "4": "future reasoning"},
                     "source_labels": [{"question": "M4", "value": True, "event_seq": 4,
                                        "basis": "visible", "origin": "rule"}],
                     "outcomes": {"reward": 0}},
            "meta": {"source": "helpsteer3", "trajectory_id": "example", "pair_id": "real-pair",
                     "objective": ["M1"], "licence": "MIT", "harness": "chat"}}


def test_future_evidence_is_not_teacher_visible():
    tokenizer = load_tokenizer(Path(__file__).resolve().parents[1] / "data" / "tokenizer")
    row = fixture_row()
    records, requirements, contexts = prepare_stream(row, {"cut_seq": 2}, tokenizer)
    record = records[0]
    assert "FUTURE" not in record["state"]
    assert record["teacher_side"]["reasoning"] == {"2": "visible reasoning"}
    assert record["teacher_side"]["source_labels"] == []
    assert set(record["questions"]) == set(EVERY_EVENT) | {"G5"}
    assert all("label" not in question for question in record["questions"].values())
    assert not any(key.startswith("G2") for key in record["questions"])
    assert contexts[0]["events"] == row["events"]
    assert requirements[0]["purpose"] == "requirement_selection"
    assert count_tokens(record["state"], tokenizer) <= 32767


def test_native_preserves_real_labels_and_pair():
    native = {"state": "real prompt", "questions": {"actual": {
        "type": "noul", "instructions": "actual question", "label": True}},
        "_meta": {"original_source": "actual source", "pair_id": "original pair"}}
    row = {"events": [], "side": {"native_record": native},
           "meta": {"source": "tasksource", "trajectory_id": "real", "licence": "MIT"}}
    output = prepare_native(row)
    assert output["questions"] == native["questions"]
    assert output["_meta"]["original_source"] == "actual source"
    assert output["_meta"]["pair_id"] == "original pair"


def test_tool_cut_has_no_g5():
    tokenizer = load_tokenizer(Path(__file__).resolve().parents[1] / "data" / "tokenizer")
    row = fixture_row()
    row["events"] = [instruction("Check output."), tool("Bash", {"command": "pytest"}, "1 passed", 2)]
    records, _, _ = prepare_stream(row, {"cut_seq": 2}, tokenizer)
    assert "G5" not in records[0]["questions"]


def test_document_overflow_asks_only_section_questions():
    tokenizer = load_tokenizer(Path(__file__).resolve().parents[1] / "data" / "tokenizer")
    row = fixture_row()
    document = "".join(f"## Section {index}\n\nKeep the public API stable.\n\n" for index in range(100))
    row["events"] = [instruction("Review the API.", documents={"POLICY.md": document}),
                     message("I reviewed the API.", 2)]
    records, requirements, _ = prepare_stream(row, {"cut_seq": 2}, tokenizer, state_budget=1000)
    assert records and not requirements
    assert all(key.split("#")[0] in {"SCR", "M8"} for record in records for key in record["questions"])
    recovered = "".join(section["text"] for record in records for section in record["_meta"]["sections"])
    assert recovered == document
    assert all(count_tokens(record["state"], tokenizer) <= 8192 for record in records)


def test_g2_requires_exact_approved_parent_unit(tmp_path, monkeypatch):
    from intent_training.prepare import requirements as module
    tokenizer = load_tokenizer(Path(__file__).resolve().parents[1] / "data" / "tokenizer")
    monkeypatch.setattr(module, "load_tokenizer", lambda path: tokenizer)
    prepared = tmp_path / "data" / "prepared"
    prepared.mkdir(parents=True)
    (tmp_path / "results" / "preparation").mkdir(parents=True)
    records, _, _ = prepare_stream(fixture_row(), {"cut_seq": 2}, tokenizer)
    record = records[0]
    (prepared / "main.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
    selected = tmp_path / "selected.jsonl"
    selected.write_text(json.dumps({"parent_record_id": record["record_id"],
        "requirements": [dict(record["requirement_units"][0], unit_id="R1")]}) + "\n", encoding="utf-8")
    assert module.enrich(tmp_path, selected)["g2_rows"] == 1
    output = json.loads((prepared / "main.jsonl").read_text(encoding="utf-8"))
    assert output["questions"]["G2#R1"] == fill_question("G2", requirement_text=record["requirement_units"][0]["text"], tokenizer=tokenizer)


def test_duplicate_objectives_and_disagreeing_labels_survive(tmp_path):
    from copy import deepcopy
    from intent_training.prepare.provenance import finalize
    tokenizer = load_tokenizer(Path(__file__).resolve().parents[1] / "data" / "tokenizer")
    first = fixture_row()
    first["side"]["source_labels"] = [{"question": "M4", "value": True,
        "event_seq": 2, "basis": "visible", "origin": "rule"}]
    second = deepcopy(first)
    second["meta"]["objective"] = ["M4"]
    second["side"]["source_labels"][0]["value"] = False
    records, _, _ = prepare_stream(first, {"cut_seq": 2}, tokenizer)
    prepared = tmp_path / "data" / "prepared"
    prepared.mkdir(parents=True)
    (tmp_path / "results" / "preparation").mkdir(parents=True)
    (prepared / "main.jsonl").write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
    finalize(tmp_path, [first, second], [[{"cut_seq": 2}], [{"cut_seq": 2}]])
    result = json.loads((prepared / "main.jsonl").read_text(encoding="utf-8"))
    assert result["_meta"]["objective"] == ["M1", "M4"]
    assert len(result["teacher_side"]["source_labels"]) == 2
    assert result["_meta"]["source_label_conflicts"][0]["values"] == [False, True]
