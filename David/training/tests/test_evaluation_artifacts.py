"""Check scored artifact compatibility and executable evaluation commands."""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intent_training.evaluate.artifacts import write_results
from intent_training.evaluate.parity import compare_serving_paths
from intent_training.evaluate.__main__ import main


def test_raw_forward_logits_match_unrounded_serving_probability():
    training = [{"record_id": "one", "question_id": "M1", "options": ["false", "true"],
                 "logits": [0.0, 0.0], "temperature": 1.0}]
    serving = [{**training[0], "probabilities": [0.5, 0.5]}]
    result = compare_serving_paths(training, serving, training, serving,
                                   selected_hardware_pair=("a", "b"), stock_hardware_pair=("a", "b"), expected_records=1)
    assert result["pass"] and result["selected_mean_absolute_gap"] == 0


def test_markdown_has_measured_candidates_counts_intervals_and_sources(tmp_path):
    proportion = {"n": 12, "value": 0.75, "interval": [0.4, 0.9]}
    difference = {"n": 200, "difference": 0.1, "interval": [0.02, 0.2]}
    benchmark = {"measured": {"M1": {"selected": proportion, "stock": proportion}},
                 "published_stock": {"value": 0.7, "source_url": "https://example.org/measurement"}}
    report = {"selected_candidate": "trained-checkpoint", "stock_candidate": "stock-checkpoint",
              "lift": {"endpoints": {"intent_probe": difference, "trace": difference}, "pass": True},
              "retention": difference, "requirement_recall": {"selected": proportion, "stock": proportion},
              "benign_rates": {"M1": {"selected": proportion, "stock": proportion, "teacher": proportion}},
              "llmbar": benchmark, "rewardbench2": benchmark}
    output = tmp_path / "RESULTS.md"
    write_results(report, output)
    rendered = output.read_text(encoding="utf-8")
    assert "trained-checkpoint" in rendered and "stock-checkpoint" in rendered
    assert "200 | 0.10000000 | [0.02000000, 0.20000000]" in rendered
    assert "https://example.org/measurement" in rendered


def test_cli_has_explicit_scoring_parity_demo_and_report_paths(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["evaluate", "--help"])
    with pytest.raises(SystemExit) as exit:
        main()
    assert exit.value.code == 0
    help_text = capsys.readouterr().out
    for command in ("score-heldout", "score-serving", "parity", "demo", "report"):
        assert command in help_text
