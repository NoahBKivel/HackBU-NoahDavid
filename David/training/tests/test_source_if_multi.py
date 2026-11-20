"""Check source alignment, literal safety, RF basis and missing-answer isolation."""

import json
import hashlib
from pathlib import Path

import pytest

from intent_training.sources.if_multi import (
    convert, generated_context, generation_requests, parse_row, requirement_units,
)
from monitor_format import validate_events


def fixture_row() -> dict:
    constraints = ["Use lowercase letters.", "End with the word blue."]
    return {"key": "fixture-task", "messages": [{"role": "user", "content":
            "The project concerns a color. Explain the choice. " + " ".join(constraints)}],
            "constraint": "\t".join(constraints), "ground_truth": repr([{
                "instruction_id": ["change_case:english_lowercase", "last_word:last_word_answer"],
                "kwargs": [None, {"last_word": "blue"}]}])}


def write_rows(path: Path, values: list[tuple[int, dict]]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "rows.jsonl").write_text("".join(json.dumps({"row_idx": i, "row": row}) + "\n"
                                               for i, row in values), encoding="utf-8")


def test_literals_and_alignment_are_checked_without_execution():
    row = fixture_row()
    assert parse_row(row)[1] == row["constraint"].split("\t")
    row["ground_truth"] = "__import__('os').getcwd()"
    with pytest.raises(ValueError):
        parse_row(row)
    row = fixture_row()
    row["constraint"] += "\tAnother requirement."
    with pytest.raises(ValueError, match="align"):
        parse_row(row)


def test_rf_preserves_units_and_filters_imperatives(tmp_path: Path):
    raw = tmp_path / "data/downloads/if_multi"
    row = fixture_row()
    write_rows(raw, [(2, row)])
    records = list(convert(raw))
    assert len(records) == 1
    events, side, meta = records[0]
    validate_events(events)
    assert len(events) == 1 and events[0]["agent_text"] == ""
    assert "cut_seq" not in meta
    assert meta["cut_kind"] == "unspecified"
    positives = [x for x in side["requirement_units"] if x["value"]]
    negatives = [x for x in side["requirement_units"] if not x["value"]]
    assert [x["text"].strip() for x in positives] == row["constraint"].split("\t")
    assert all(x["original_basis"] for x in positives)
    assert [x["text"].strip() for x in negatives] == ["The project concerns a color."]
    assert events[0]["new_items"][0]["text"].startswith("Use lowercase letters.")


def test_missing_generation_creates_requests_and_no_answers(tmp_path: Path):
    raw = tmp_path / "data/downloads/if_multi"
    write_rows(raw, [(0, fixture_row()), (1, fixture_row()), (2, fixture_row()), (200, fixture_row())])
    requests = list(generation_requests(raw))
    assert [x["id"] for x in requests] == ["if_multi-00000", "if_multi-00001", "if_multi-00200"]
    assert all({"id", "purpose", "prompt", "max_output_tokens", "refs"} <= x.keys() for x in requests)
    assert len(list(convert(raw))) == 1
    assert generated_context(200, fixture_row(), tmp_path / "responses") is None


def test_unknown_language_base_is_not_guessed_negative():
    context = {"instruction": "Use lowercase letters.\n\nLe projet concerne une couleur.",
               "constraints": ["Use lowercase letters."], "document": None}
    # The test only asserts omission of unknown scripts, not language detection.
    context["instruction"] = "Use lowercase letters.\n\n项目与颜色有关。"
    units = requirement_units(context, context["constraints"], "项目与颜色有关。")
    assert units and all(x["value"] for x in units)


@pytest.mark.parametrize("verb", ["Compute", "Prove", "Evaluate", "Construct", "Design", "Suggest",
                                  "Convert", "Select", "Choose", "Help", "Draft", "Print", "Output",
                                  "Compare", "Analyze", "Check", "Assume", "Let", "Add", "Remove",
                                  "Replace", "Format", "Read", "Solve"])
def test_imperative_base_sentences_never_become_negative(verb: str):
    base = f"{verb} the solution."
    context = {"instruction": "Use lowercase letters.\n\n" + base,
               "constraints": ["Use lowercase letters."], "document": None}
    assert all(unit["value"] for unit in requirement_units(context, context["constraints"], base))


def test_checked_response_labels_visible_requirement_and_rejects_stale_evidence(tmp_path: Path):
    raw = tmp_path / "data/downloads/if_multi"
    row = fixture_row()
    write_rows(raw, [(200, row)])
    base, constraints, ids, _ = parse_row(row)
    response = "TEST FIXTURE RESPONSE"
    responses = tmp_path / "data/generation/responses"
    responses.mkdir(parents=True)
    envelope = {"id": "if_multi-00200", "model": "test-fixture-model", "text": json.dumps({
        "instruction": "\n\n".join(constraints) + "\n\n" + base, "constraints": constraints,
        "document": None, "response": response})}
    (responses / "if_multi-00200.json").write_text(json.dumps(envelope), encoding="utf-8")
    checks = raw / "checks"
    checks.mkdir()
    check = {"response_sha256": hashlib.sha256(response.encode()).hexdigest(), "instruction_ids": ids,
             "isolation": "docker", "errors": [], "passed": [True, False]}
    check_path = checks / "if_multi-00200.json"
    check_path.write_text(json.dumps(check), encoding="utf-8")
    events, side, meta = list(convert(raw))[0]
    validate_events(events)
    assert meta["cut_seq"] == 2 and meta["cut_kind"] == "positive"
    assert all(label["basis"] == "visible" for label in side["source_labels"])
    broken = [label for label in side["source_labels"] if label["question"] == "D2"]
    assert broken == [{"question": "D2", "value": True, "event_seq": 2, "basis": "visible",
                       "origin": "rule", "requirement_text": constraints[1]}]
    check["response_sha256"] = "stale"
    check_path.write_text(json.dumps(check), encoding="utf-8")
    with pytest.raises(ValueError, match="Verifier evidence"):
        list(convert(raw))
