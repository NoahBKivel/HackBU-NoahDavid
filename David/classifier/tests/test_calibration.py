import math

import pytest

from intent_runtime.calibration import Calibrator
from intent_runtime.model import QuestionRunner, STOCK_CHECKPOINT, selection


def test_calibration_scalar_suffix_and_fallback():
    calibrator = Calibrator({"M4": {"T": 2.0, "b": 0.7}}, 3.0)
    result = calibrator.apply("M4#E8", [0.2, 0.8], ["false", "true"])
    expected = 1 / (1 + math.exp(-(math.log(4) / 2 + 0.7)))
    assert result["true"] == pytest.approx(expected, abs=1e-14)
    fallback = calibrator.apply("G1", [0.1, 0.9], ["false", "true"])
    assert fallback["true"] == pytest.approx(1 / (1 + math.exp(-math.log(9) / 3)))
    assert selection(__import__('pathlib').Path('nonexistent')) == {"checkpoint": STOCK_CHECKPOINT, "calibration": None, "source": "stock-kev"}


def test_choice_offsets_and_metadata_order():
    runner = QuestionRunner.__new__(QuestionRunner)
    runner.calibrator = Calibrator({"G2": {"T": 2, "b": {"done": -2, "broken": 1, "not done": 0}}}, 1)
    decoded = runner.decode([[0.8, 0.1, 0.1]], [{"id": "G2#R3", "keys": ["done", "broken", "not done"]}])
    weights = [math.sqrt(.8) * math.exp(-2), math.sqrt(.1) * math.e, math.sqrt(.1)]
    assert decoded["G2#R3"]["broken"] == pytest.approx(weights[1] / sum(weights))
    assert max(decoded["G2#R3"], key=decoded["G2#R3"].get) == "broken"


def test_exact_zero_probability_stays_zero():
    calibrator = Calibrator({'M4': {'T': 2, 'b': .7}}, 3)
    assert calibrator.apply('M4', [0, 1], ['false', 'true']) == {'false': 0, 'true': 1}
    assert calibrator.apply('M4', [1, 0], ['false', 'true']) == {'false': 1, 'true': 0}


def test_runner_uses_probs_and_submits_all_before_wait():
    from concurrent.futures import Future
    class Server:
        def __init__(self):
            self.submitted = []
        def probs(self, record):
            return [[.123456789, .876543211]], {}
        def submit(self, record):
            self.submitted.append(record)
            future = Future()
            if len(self.submitted) == 2:
                self.first.set_result(([[.9, .1]], {}))
                future.set_result(([[.8, .2]], {}))
            else:
                self.first = future
            return future
    runner = QuestionRunner.__new__(QuestionRunner)
    runner.server = Server()
    runner.calibrator = Calibrator({}, 1)
    runner.prepare = lambda state, rows: (state, [{"id": "M4", "keys": ["false", "true"]}])
    assert runner.ask('state', {'M4': {}})['M4']['true'] == pytest.approx(.876543211, abs=1e-14)
    assert [r['M4']['true'] for r in runner.ask_many([('one', {}), ('two', {})])] == pytest.approx([.1, .2])
