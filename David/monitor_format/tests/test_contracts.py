"""Exercise event, question, requirement and correction contracts."""

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from monitor_format import (
    CORRECTION_ORDER, EVERY_EVENT, NEGATED_BASES, QUESTION_TABLE, build_instructions,
    collect_documents, correction_text, fill_question, is_cut_point, open_findings_line,
    question_token_cost, rf_window, row_key, short_names, split_sections, split_units,
    token_ids, validate_events, validate_event, validate_record,
)


def test_corrected_runtime_fixture_schema(sample_events, tool_events):
    validate_events(sample_events)
    validate_events(tool_events)
    for events in (sample_events, tool_events):
        for event in events:
            assert event["type"] in {"session_started", "tool_completed", "turn_completed"}


def test_schema_rejects_shell_file_changes_and_unstructured_patch(sample_events):
    shell = deepcopy(sample_events[2])
    shell["action"]["file_changes"] = [{"path": "tests/a.py", "op": "edit", "patch": None}]
    with pytest.raises(ValueError, match="Only Edit and Write"):
        validate_event(shell)
    edit = deepcopy(sample_events[1])
    edit["action"]["file_changes"][0]["patch"] = "@@ -1 +1 @@"
    with pytest.raises(ValueError, match="structured hunks"):
        validate_event(edit)
    turn = deepcopy(sample_events[-1])
    turn["turn"] = {}
    with pytest.raises(ValueError, match="end reason"):
        validate_event(turn)


def test_schema_rejects_out_of_order_duplicate_sequence_and_invalid_target(sample_events):
    with pytest.raises(ValueError, match="increase strictly"):
        validate_events([sample_events[0], sample_events[0]])
    record = {"state": "visible", "questions": {"M2": {"type": "noul", "instructions": "q",
              "label": True, "target": {"false": 0.5, "true": 0.75}}}}
    with pytest.raises(ValueError, match="sum to one"):
        validate_record(record)


def test_instruction_arrival_order_and_verbatim_clarification(tool_events):
    before = deepcopy(tool_events)
    instructions = build_instructions(list(reversed(tool_events)))
    assert instructions == [{"id": "I1", "text": "Keep every test. Profile before editing."},
                            {"id": "I2", "text": "src/app.py"}]
    assert tool_events == before
    assert collect_documents(tool_events)[0]["path"] == "CLAUDE.md"
    for event in tool_events:
        name = event["action"].get("tool")
        if name in {"Read", "Grep", "Glob", "WebFetch", "WebSearch", "LS", "NotebookRead", "AskUserQuestion"}:
            assert not is_cut_point(event)
    assert is_cut_point(tool_events[-1])


def test_questions_twins_choices_and_diagnostic_fillers():
    assert len(EVERY_EVENT) == len(set(EVERY_EVENT))
    assert set(EVERY_EVENT) <= set(QUESTION_TABLE)
    for base in NEGATED_BASES:
        assert QUESTION_TABLE[base + "~neg"]["instructions"] != QUESTION_TABLE[base]["instructions"]
    assert list(QUESTION_TABLE["G2"]["criteria"]) == ["done", "broken", "not done", "can't tell from the evidence"]
    assert len(QUESTION_TABLE["L7"]["criteria"]) == 6
    row = fill_question("D1", fired_questions=["M4", "M2"], event_seq=41)
    assert "stated requirement, gamed measure" in row["instructions"]
    assert "event E41" in row["instructions"]
    assert row_key("G2", 3) == "G2#R3"
    assert row_key("D1", 41) == "D1#E41"
    assert row_key("SCR", 2) == "SCR#S2"
    assert "[S2]" in fill_question("M8", section_id=2)["instructions"]
    assert short_names(["M8", "M2", "M4"]) == "stated requirement, gamed measure"


def test_requirement_units_preserve_every_character_and_list_items():
    text = "A fact. Another fact.\n\n- Keep tests. Do not skip them.\n  This continues the item.\n- Verify it.\n\nEnd here."
    units = split_units(text, "[I1]")
    assert "".join(unit["text"] for unit in units) == text
    assert any("Keep tests. Do not skip them." in unit["text"] for unit in units)
    assert all(unit["source"] == "[I1]" for unit in units)
    assert [unit["position"] for unit in units] == list(range(1, len(units) + 1))
    text_window = rf_window(units, 2)
    assert text_window.count("⟦") == text_window.count("⟧") == 1
    assert units[2]["text"] in text_window


def test_rf_neighbours_do_not_cross_sources():
    units = [{"source": "a", "position": i, "text": f"unit {i}"} for i in range(7)]
    window = rf_window(units, 3)
    assert "unit 0" not in window and "unit 6" not in window
    units[2]["source"] = "b"
    assert "unit 2" not in rf_window(units, 3)


def test_sections_preserve_text_and_bound_sizes(char_tokenizer):
    text = "Preface.\n\n# First\nAlpha.\n\n# Second\nBeta.\n\nGamma.\n"
    sections = split_sections({"path": "docs/rules.md", "text": text}, tokenizer=char_tokenizer, cap=30)
    assert "".join(section["text"] for section in sections) == text
    assert all(len(section["text"]) <= 30 for section in sections)
    assert all(section["path"] == "docs/rules.md" for section in sections)
    assert [section["id"] for section in sections] == [f"S{i}" for i in range(1, len(sections) + 1)]


def test_row_trim_keeps_head_tail_and_budget(char_tokenizer):
    requirement = "HEAD " + "middle " * 1000 + " TAIL"
    row = fill_question("G2", requirement_text=requirement, tokenizer=char_tokenizer, row_budget=350)
    assert "HEAD" in row["instructions"] and "TAIL" in row["instructions"]
    assert "[cut]" in row["instructions"]
    assert question_token_cost(row, char_tokenizer) <= 350


def test_correction_order_m8_mapping_and_evidence_limit():
    items = [{"question": question, "event_seqs": [index], "requirement": "Do not delete tests.",
              "probability": 0.87, "answer": "yes", "evidence": f"visible content {index}"}
             for index, question in enumerate(["M1", "M5", "M4", "M8"], 1)]
    text = correction_text(items, "Keep coverage.", serious=True)
    assert text.index("1. stated requirement") < text.index("2. gamed measure") < text.index("3. unsupported claim")
    assert text.count("Evidence:") == 3
    assert text.endswith("Stop and ask the user before continuing.")
    assert "Does the latest action or message break a requirement" in text
    assert open_findings_line({"id": "F3", "question": "M4", "event_seqs": [41], "correction_seq": 42}) == (
        "[F3] M4 at E41 · correction sent at E42 · L7 status: open")


def test_special_tokens_are_escaped_before_tokenization(char_tokenizer):
    assert token_ids("<|fim_prefix|>", char_tokenizer) == [ord(char) for char in "<¦fim_prefix¦>"]


def test_shared_package_has_no_training_dependency_or_io():
    package = Path(__file__).resolve().parents[1]
    forbidden = {"open", "read_text", "read_bytes", "write_text", "write_bytes", "from_pretrained"}
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [name.name for name in node.names] + [getattr(node, "module", "") or ""]
                assert all("training" not in name for name in names)
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                assert name not in forbidden
