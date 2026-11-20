"""Exercise scanner calls and immutable frozen-byte checks on real fixture rows."""

from copy import deepcopy
from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.splits import build_manifest, freeze, scan_records


def inputs():
    record = {"state": "An observed action.", "questions": {"M2": {"type": "noul", "instructions": "Does it break the requirement?", "label": True}},
              "_meta": {"source": "fixture", "trajectory_id": "trace", "record_kind": "task", "split": "train",
                        "dependent_questions_complete": True, "encoder_admitted": True}}
    return {"train": [record], "base_dev": []}


def manifest(splits):
    return build_manifest(splits, preregistration={"floors": {"M2": 1}},
        instruments={"M2": {"rows": 1, "positive_specific_agreement": 1., "cant_tell_rate": 0.}},
        balance_metrics={"collected": {}, "post_cap": {}}, scanner=ROOT / "scripts/scan_secrets.py",
        composition={"expected": {"train": 1, "replay": 0, "long": 0, "screen": 0},
                     "fallback_evidence": "This isolated test fixture contains one measured row."})


def test_real_scanner_rejects_planted_credential_without_echoing_it():
    splits = inputs()
    token = "hf_" + "a" * 34
    splits["train"][0]["state"] = "Credential " + token
    report = scan_records(splits, scanner=ROOT / "scripts/scan_secrets.py")
    assert report["rows_scanned"] == 1
    assert not report["passed"]
    assert token not in report["output"]
    assert "credential findings=1" in report["output"]


def test_manifest_counts_and_hashes_real_rows_then_freeze_refuses_mutation(tmp_path):
    splits = inputs()
    report = manifest(splits)
    assert report["passed"]
    assert report["counts"]["train"]["M2"]["positives"] == 1
    assert report["secrets_scan"]["rows_scanned"] == 1
    assert report["pair_integrity"]["cross_split_groups"] == 0
    with pytest.raises(PermissionError, match="authorize"):
        freeze(splits, manifest=report, directory=tmp_path)
    corrupt = deepcopy(splits)
    corrupt["train"][0]["questions"]["M2"]["label"] = False
    with pytest.raises(ValueError, match="changed"):
        freeze(corrupt, manifest=report, directory=tmp_path, authorized=True)
    paths = freeze(splits, manifest=report, directory=tmp_path, authorized=True)
    actual = json.loads(Path(paths["train.jsonl"]).read_text(encoding="utf-8"))
    assert actual == splits["train"][0]
    with pytest.raises(FileExistsError, match="cannot be overwritten"):
        freeze(splits, manifest=report, directory=tmp_path, authorized=True)


def test_default_composition_cannot_silently_shrink_to_small_input():
    report = build_manifest(inputs(), preregistration={"floors": {"M2": 60}},
        instruments={}, balance_metrics={}, scanner=ROOT / "scripts/scan_secrets.py")
    assert not report["passed"]
    assert {"composition:train", "composition:replay", "composition:long", "composition:screen", "positive_floor:M2", "missing_teacher_instrument:M2"} <= set(report["failures"])


def test_suffixed_requirements_aggregate_under_the_question():
    splits = inputs()
    row = splits["train"][0]
    row["questions"] = {"G2#R1": {"type": "choice", "instructions": "Requirement one", "label": "broken"},
                        "G2#R2": {"type": "choice", "instructions": "Requirement two", "label": "done"}}
    from intent_training.assemble import question_counts
    assert question_counts([row])["G2"] == {"rows": 2, "positives": 1, "rate": .5}


def test_heldout_dataset_provenance_cannot_hide_under_an_allowed_source_name():
    splits = inputs()
    splits["train"][0]["_meta"]["dataset"] = "PatronusAI/TRACE"
    with pytest.raises(ValueError, match="held-out source"):
        manifest(splits)


@pytest.mark.parametrize("field", ["dataset", "original_source", "repo"])
def test_registered_trace_revision_cannot_hide_in_wrapped_provenance(field):
    splits = inputs()
    splits["train"][0]["_meta"][field] = "PatronusAI/trace-dataset@31d87f06"
    with pytest.raises(ValueError, match="held-out source"):
        manifest(splits)


def test_unfinished_dependent_questions_cannot_pass_a_count_only_freeze_gate():
    splits = inputs()
    splits["train"][0]["_meta"]["dependent_questions_complete"] = False
    report = manifest(splits)
    assert not report["passed"] and report["admission"]["admitted"] == 0
    assert any(value.startswith("admission:") for value in report["failures"])
