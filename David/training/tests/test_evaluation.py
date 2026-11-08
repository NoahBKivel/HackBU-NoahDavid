"""Known answers and planted faults for evaluation denominators and serving parity."""

from copy import deepcopy
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from intent_training.evaluate.execution import claim_heldout_run, join_scored_candidates
from intent_training.evaluate.parity import compare_serving_paths
from intent_training.evaluate.reports import benign_rates, lift_report, preference_accuracy, requirement_recall, retention_report
from intent_training.evaluate.statistics import paired_accuracy, proportion_interval


def row(index=0, question="M1", *, label="true", selected=None, stock=None):
    return {"record_id": str(index), "group_id": str(index), "question_id": question,
            "options": ["false", "true"], "label": label,
            "selected": selected or [0.1, 0.9], "stock": stock or [0.9, 0.1]}


def endpoints():
    probe = [{**row(f"probe-{i}"), "intent_kind": "implicit_goal"} for i in range(200)]
    trace = [{**row(f"trace-{i}", question), "group_id": f"conversation-{i}",
              "hacked": i < 100, "cut_before_exposure": True}
             for i in range(200) for question in ("M4", "G5")]
    return probe, trace


def test_paired_difference_known_answer_and_reversed_labels():
    observations = [{"record_id": str(i), "group_id": str(i), "question_id": "M1",
                     "selected_correct": True, "stock_correct": False} for i in range(8)]
    result = paired_accuracy(observations, resamples=100)
    assert result["difference"] == 1
    assert result["interval"] == [1, 1]
    reversed_result = paired_accuracy([{**r, "selected_correct": False, "stock_correct": True} for r in observations], resamples=100)
    assert reversed_result["difference"] == -1
    assert reversed_result["interval"] == [-1, -1]


def test_cluster_bootstrap_keeps_correlated_questions_together():
    observations = [{"record_id": str(i), "group_id": str(i), "question_id": question,
                     "selected_correct": i == 0, "stock_correct": i == 1}
                    for i in range(2) for question in ("M4", "G5")]
    result = paired_accuracy(observations, resamples=1000)
    assert result["groups"] == 2
    assert result["n"] == 4
    assert result["difference"] == 0
    assert result["interval"] == [-1, 1]
    with pytest.raises(ValueError, match="Repeated"):
        paired_accuracy(observations + observations[:1])
    with pytest.raises(ValueError, match="identities"):
        paired_accuracy([{**observation, "group_id": None} for observation in observations])


def test_wilson_known_boundary_and_invalid_denominator():
    result = proportion_interval(0, 10)
    assert result["value"] == 0
    assert result["interval"][0] == pytest.approx(0, abs=1e-15)
    assert result["interval"][1] == pytest.approx(0.2775327998628892)
    with pytest.raises(ValueError):
        proportion_interval(0, 0)


def test_lift_requires_both_fixed_endpoints_and_detects_null():
    probe, trace = endpoints()
    result = lift_report(probe, trace, selected_candidate="selected", stock_candidate="stock", resamples=100)
    assert result["pass"]
    assert result["endpoints"]["trace"]["n"] == 400
    assert result["endpoints"]["trace"]["groups"] == 200
    for observation in trace:
        observation["selected"] = observation["stock"]
    null = lift_report(probe, trace, selected_candidate="selected", stock_candidate="stock", resamples=100)
    assert not null["pass"]
    assert null["endpoints"]["trace"]["interval"] == [0, 0]


@pytest.mark.parametrize("fault", ["count", "mapping", "strata", "overlap", "exposure", "question"])
def test_lift_protocol_planted_faults(fault):
    probe, trace = endpoints()
    if fault == "count":
        probe.pop()
    elif fault == "mapping":
        probe[0]["question_id"] = "M2"
    elif fault == "strata":
        trace[0]["hacked"] = trace[1]["hacked"] = False
    elif fault == "overlap":
        probe[0]["conversation_id"] = trace[0]["group_id"]
    elif fault == "exposure":
        trace[0]["cut_before_exposure"] = False
    else:
        trace[0]["question_id"] = "M1"
    with pytest.raises(ValueError):
        lift_report(probe, trace, selected_candidate="selected", stock_candidate="stock", resamples=10)


def test_retention_rf_and_benign_counts_have_right_denominators():
    rows = [row(0), row(1, label="false")]
    result = retention_report(rows, expected_records=2, resamples=100)
    assert result["difference"] == 0
    rf = requirement_recall([{**r, "question_id": "RF"} for r in rows])
    assert rf["selected"]["n"] == 1 and rf["selected"]["value"] == 1
    assert rf["stock"]["value"] == 0
    benign = benign_rates([{**row(0, "G1", label="false"), "is_benign": True}])
    assert benign["G1"]["teacher"]["value"] == 1
    assert benign["G1"]["selected"]["value"] == 0
    assert benign["G1"]["stock"]["value"] == 1


def test_preference_direction_and_tie_policy():
    pairs = [{"question_id": question, "comparison_id": "one", "selected_preferred_problem": 0.1, "selected_rejected_problem": 0.9,
              "stock_preferred_problem": 0.8, "stock_rejected_problem": 0.8} for question in ("M1", "M2")]
    result = preference_accuracy(pairs)
    assert result["M2"]["selected"]["value"] == 1
    assert result["M2"]["stock"]["ties"] == 1
    assert result["M2"]["stock"]["value"] == 0
    with pytest.raises(ValueError, match="Both M1"):
        preference_accuracy(pairs[:1])
    with pytest.raises(ValueError, match="distinct"):
        preference_accuracy(pairs + pairs[:1])
    pairs[0]["selected_preferred_problem"] = 2
    with pytest.raises(ValueError):
        preference_accuracy(pairs)


def parity_row(true_probability, question="M1", options=None):
    return {"record_id": "dev", "question_id": question, "options": options or ["false", "true"],
            "probabilities": [1 - true_probability, true_probability], "temperature": 1.0}


def test_parity_uses_both_softmax_entries_and_stock_relative_limit():
    train, serve = [parity_row(0.5)], [parity_row(0.6)]
    result = compare_serving_paths(train, serve, train, serve, selected_hardware_pair=("train", "serve"),
                                   stock_hardware_pair=("train", "serve"), expected_records=1)
    assert result["pass"]
    assert result["selected_mean_absolute_gap"] == pytest.approx(math.log(0.6) - math.log(0.4))
    broken = compare_serving_paths(train, [parity_row(0.9)], train, serve,
                                   selected_hardware_pair=("train", "serve"), stock_hardware_pair=("train", "serve"),
                                   expected_records=1)
    assert not broken["pass"]


@pytest.mark.parametrize("fault", ["temperature", "hardware", "keys", "options", "count", "zero"])
def test_parity_rejects_wrong_comparison(fault):
    rows = [[parity_row(0.5)] for _ in range(4)]
    kwargs = {"selected_hardware_pair": ("a", "b"), "stock_hardware_pair": ("a", "b"), "expected_records": 1}
    if fault == "temperature":
        rows[0][0]["temperature"] = 2
    elif fault == "hardware":
        kwargs["stock_hardware_pair"] = ("a", "c")
    elif fault == "keys":
        rows[1][0]["question_id"] = "M2"
    elif fault == "options":
        rows[1][0]["options"] = ["true", "false"]
    elif fault == "count":
        kwargs["expected_records"] = 300
    else:
        rows[0][0]["probabilities"] = [0, 1]
    with pytest.raises(ValueError):
        compare_serving_paths(*rows, **kwargs)


def test_once_only_claim_is_persistent_before_any_scoring(tmp_path):
    ledger = tmp_path / "once.json"
    claim_heldout_run(ledger, {"manifest_sha256": "sample"})
    assert json.loads(ledger.read_text())["state"] == "started"
    with pytest.raises(FileExistsError):
        claim_heldout_run(ledger, {"manifest_sha256": "different"})


def test_join_rejects_missing_candidate_and_label_mismatch():
    base = {**row(0), "endpoint": "intent_probe", "calibrated_probabilities": [0.2, 0.8]}
    selected = {**base, "candidate": "selected"}
    stock = {**base, "candidate": "stock"}
    joined = join_scored_candidates([selected, stock])
    assert joined["intent_probe"][0]["selected"] == [0.2, 0.8]
    with pytest.raises(ValueError):
        join_scored_candidates([selected])
    with pytest.raises(ValueError):
        join_scored_candidates([selected, {**stock, "label": "false"}])
