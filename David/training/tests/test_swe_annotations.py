"""Check annotation isolation and fail-closed first-action conversion."""

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))
from intent_training.sources.swe_annotations import convert, joined_rows, join_originals, prepare, request_for
from monitor_format import validate_events


@pytest.fixture
def source(tmp_path):
    raw = tmp_path / "data/downloads/swe_annotations"
    raw.mkdir(parents=True)
    row = {"instance_id": "fixture-issue", "problem_statement": "Please support the new format.",
           "annotations": [{"underspecified": 2, "notes": "Fixture ambiguity note."},
                           {"underspecified": 0, "notes": "Fixture dissent."}]}
    (raw / "joined.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    return tmp_path, raw, row


def test_absent_source_and_responses_emit_nothing(source):
    root, raw, _ = source
    assert list(convert(root / "missing")) == []
    assert list(convert(raw)) == []


def test_requests_hide_annotation_notes_and_scores(source):
    root, raw, row = source
    request = request_for(row)
    assert "Fixture ambiguity" not in json.dumps(request)
    assert "underspecified" not in json.dumps(request)
    assert prepare(raw, root) == 1
    exclusion = json.loads((root / "data/exclusions/swe_annotations.jsonl").read_text())
    assert exclusion["instance_id"] == row["instance_id"]


def test_generated_message_keeps_annotations_in_outcome_hints(source):
    root, raw, row = source
    responses = root / "data/generation/responses"
    responses.mkdir(parents=True)
    text = "Which format version should be supported?"
    (responses / (request_for(row)["id"] + ".json")).write_text(json.dumps({"id": request_for(row)["id"], "text": text}))
    events, side, meta = next(convert(raw))
    validate_events(events)
    assert events[-1]["agent_text"] == text
    assert events[0]["new_items"][0]["text"] == row["problem_statement"]
    assert "Fixture ambiguity" not in json.dumps(events)
    assert side["source_labels"] == []
    assert side["outcomes"]["annotation_hints"]["basis"] == "outcome"
    assert side["outcomes"]["annotation_hints"]["annotations"] == row["annotations"]
    assert meta["cut_seq"] == events[-1]["seq"]


def test_invalid_annotation_rejected(source):
    _, raw, row = source
    row["annotations"][0]["underspecified"] = True
    (raw / "joined.jsonl").write_text(json.dumps(row))
    with pytest.raises(ValueError):
        list(joined_rows(raw))


def test_csv_join_retains_decimal_scores_disagreement_and_missing_values(source):
    import csv
    _, raw, row = source
    originals = raw / "originals.jsonl"
    originals.write_text(json.dumps(row) + "\n")
    fields = ["instance_id", "user_id", "underspecified", "underspecified_notes"]
    with (raw / "samples_with_3_annotations_public.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for score in ("1.0", "3.0", ""):
            writer.writerow(dict(instance_id=row["instance_id"], user_id="fixture", underspecified=score,
                                 underspecified_notes="Fixture note."))
    stats = join_originals(raw, originals)
    assert stats["selected_issues"] == 1
    assert [item["underspecified"] for item in next(joined_rows(raw))["annotations"]] == [1, 3, None]
