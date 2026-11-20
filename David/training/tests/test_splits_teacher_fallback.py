"""Verify actual artifact links before accepting the single relabel fallback."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.teacher import agreement_report
from intent_training.teacher.dispatch import MODELS, digest, write_batches
from intent_training.splits.teacher_fallback import RULE, verify_teacher_fallback


def reference(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def fixture_evidence(tmp_path):
    text = "Use the visible edit as evidence for the changed requirement."
    prompt = tmp_path / "tightened.txt"
    prompt.write_text(text, encoding="utf-8")
    instrument = agreement_report([("M2", True, False)])["M2"]
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps([{"question": "M2", "action": "relabel_once",
        "supplementary_instructions": text, "instructions_sha256": reference(prompt)["sha256"],
        "instrument": instrument}]), encoding="utf-8")
    manifests = []
    for stage in ("main", "main_relabel"):
        row = {"record_id": "row", "source": "fixture", "pass": stage, "state": "Observed edit",
               "questions": {"M2": {"type": "noul", "instructions": "Does the edit break the requirement?"}},
               "teacher_side": {}}
        batch = {"batch_id": "fixture-" + stage, "source": "fixture", "pass": stage, "records": [row]}
        content = batch["records"]
        if stage == "main_relabel":
            batch["instruction_supplement"] = text
            content = {"records": batch["records"], "instruction_supplement": text}
        batch["input_sha256"] = digest(content)
        folder = tmp_path / stage
        manifest = write_batches([batch], folder)
        for entry in manifest:
            family = entry["model_family"]
            vote = {"record_id": "row", "batch_id": batch["batch_id"], "model_family": family,
                    "model": MODELS[family], "pass": stage, "input_sha256": batch["input_sha256"],
                    "votes": {"M2": family == "sol"}, "evidence": {"M2": "The visible edit changes the requirement."}}
            Path(entry["output"]).write_text(json.dumps(vote) + "\n", encoding="utf-8")
        manifests.append(reference(folder / "manifest.json"))
    return {"question": "M2", "relabel_attempts": 1, "rule": RULE,
            "tightened_prompt": reference(prompt), "relabel_ledger": reference(ledger),
            "initial_vote_manifest": manifests[0], "relabel_vote_manifest": manifests[1],
            "initial_vote_ids": ["row:M2"], "relabel_vote_ids": ["row:M2"],
            "initial_instrument": instrument, "second_instrument": deepcopy(instrument)}, instrument


def test_second_failure_stands_only_after_verified_single_tightened_relabel(tmp_path):
    evidence, instrument = fixture_evidence(tmp_path)
    result = verify_teacher_fallback("M2", evidence, instrument)
    assert result["verified"]
    assert result["rule"] == "reported failure; labels stand"
    assert result["initial"]["positive_specific_agreement"] == 0
    assert result["second"]["positive_specific_agreement"] == 0
    from intent_training.splits import build_manifest
    row = {"state": "Observed edit", "questions": {"M2": {"type": "noul", "instructions": "Requirement?", "label": True}},
           "_meta": {"source": "fixture", "trajectory_id": "row", "record_kind": "task",
                     "dependent_questions_complete": True, "encoder_admitted": True}}
    manifest = build_manifest({"train": [row], "base_dev": []},
        preregistration={"floors": {"M2": 1}}, instruments={"M2": instrument}, balance_metrics={},
        scanner=ROOT / "scripts/scan_secrets.py", teacher_fallbacks={"M2": evidence},
        composition={"expected": {"train": 1, "replay": 0, "long": 0, "screen": 0},
                     "fallback_evidence": "This isolated measured fixture contains one row."})
    assert manifest["passed"]
    assert manifest["teacher_instruments"]["M2"]["passed"] is False
    assert manifest["teacher_instruments"]["M2"]["fallback_verified"]
    assert manifest["reported_teacher_failures"]["M2"]["initial"]["rows"] == 1


@pytest.mark.parametrize("corruption", ["second_metrics", "prompt_bytes", "extra_attempt", "wrong_ids"])
def test_fallback_rejects_forged_metrics_prompt_repeated_attempt_or_vote_ids(tmp_path, corruption):
    evidence, instrument = fixture_evidence(tmp_path)
    if corruption == "second_metrics":
        evidence["second_instrument"]["rows"] += 1
    elif corruption == "prompt_bytes":
        Path(evidence["tightened_prompt"]["path"]).write_text("Changed instructions", encoding="utf-8")
    elif corruption == "extra_attempt":
        path = Path(evidence["relabel_ledger"]["path"])
        ledger = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps(ledger + ledger), encoding="utf-8")
        evidence["relabel_ledger"] = reference(path)
    else:
        evidence["relabel_vote_ids"] = ["other:M2"]
    with pytest.raises(ValueError):
        verify_teacher_fallback("M2", evidence, instrument)
