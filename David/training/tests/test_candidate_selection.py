"""Check discrimination, group alignment and natural-prevalence calibration."""

from copy import deepcopy
from contextlib import nullcontext
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intent_training.select import (
    auroc, calibrated_probabilities, fit_calibration, fit_question, macro_auroc,
    prior_offset, select_candidate,
)
from intent_training.select.scoring import load_and_score, score_records
from intent_training.select.selection import _plans, _sampled_score


def row(index, question="M1", label=None, logits=None):
    label = bool(index % 2) if label is None else label
    return {"record_id": str(index), "group_id": str(index // 2), "question_id": question,
            "options": ["false", "true"], "label": str(label).lower(),
            "target": [float(not label), float(label)],
            "logits": logits if logits is not None else ([0.0, 2.0] if label else [2.0, 0.0]),
            "is_intent": True, "is_base_dev": True}


def test_auc_has_known_tie_answer_and_detects_score_inversion():
    labels, scores = [False, False, True, True], [0.1, 0.5, 0.5, 0.9]
    assert auroc(labels, scores) == 0.875
    assert auroc(labels, [-score for score in scores]) == 0.125
    with pytest.raises(ValueError, match="both positive and negative"):
        auroc([True, True], [0.1, 0.9])


def test_macro_averages_questions_instead_of_weighting_frequent_rows():
    records = [row(i, "M1") for i in range(20)]
    records += [row(i + 20, "M2", logits=[0, 0]) for i in range(2)]
    records += [row(i + 22, "M1~neg", logits=[0, 0]) for i in range(2)]
    assert macro_auroc(records) == 0.75


def test_multiclass_uses_macro_one_vs_rest():
    records = []
    for index in range(3):
        item = row(index, "D5")
        item.update(options=["0", "1", "2"], label=str(index), logits=[float(i == index) for i in range(3)])
        records.append(item)
    assert macro_auroc(records) == 1.0


def test_selection_uses_aligned_groups_and_same_resamples():
    rows = [row(i, q) for i in range(16) for q in ("M1", "M7", "L4", "G1")]
    bad = [{**item, "logits": list(reversed(item["logits"]))} for item in rows]
    result = select_candidate({"tuned": rows, "stock": bad}, stock="stock", resamples=30, seed=7)
    assert result["selected"] == "tuned"
    assert result["kept"] == ["tuned"]
    assert result["pick_order"] == ["tuned", "stock"]
    assert result["paired_difference_se"]["stock"] == 0
    broken = deepcopy(rows)
    broken[0]["group_id"] = "broken"
    with pytest.raises(ValueError, match="groups"):
        select_candidate({"stock": rows, "tuned": broken}, stock="stock", resamples=3)


def test_selection_keeps_exactly_tied_candidates_and_is_reproducible():
    rows = [row(i) for i in range(12)]
    result = select_candidate({"stock": rows, "tuned": deepcopy(rows)}, stock="stock", resamples=12)
    assert result["kept"] == ["stock", "tuned"]
    assert result == select_candidate({"stock": rows, "tuned": deepcopy(rows)}, stock="stock", resamples=12)


def test_weighted_group_bootstrap_matches_literal_duplicate_rows():
    import numpy as np

    rows = [row(i, logits=[0, value]) for i, value in enumerate([0.2, 0.4, 0.4, 0.3, 0.8, 0.9])]
    counts = np.array([2, 2, 0, 0, 1, 1])
    literal = [item for item, count in zip(rows, counts) for _ in range(count)]
    assert _sampled_score(_plans(rows), counts) == pytest.approx(macro_auroc(literal))


def test_prior_pseudocounts_are_finite_and_use_soft_targets():
    train = [row(i, label=False) for i in range(2)]
    dev = [row(i, label=True) for i in range(2)]
    assert prior_offset(train, dev, ["false", "true"]) == pytest.approx(2 * math.log(5))
    dev[0]["target"] = [0.5, 0.5]
    assert prior_offset(train, dev, ["false", "true"]) == pytest.approx(math.log(2) + math.log(5))


def test_calibration_applies_offset_after_temperature_and_can_fail():
    assert calibrated_probabilities([0, 4], ["false", "true"], {"T": 2, "b": -2}) == pytest.approx([0.5, 0.5])
    assert calibrated_probabilities([0, 4], ["false", "true"], {"T": 2, "b": 0})[1] > 0.8
    with pytest.raises(ValueError, match="at least one"):
        calibrated_probabilities([0, 1], ["false", "true"], {"T": 0.9, "b": 0})


def test_temperature_fit_reduces_overconfident_nll_without_sharpening():
    records = [row(i, label=i < 3, logits=[0, 8]) for i in range(4)]
    parameters = fit_question(records, offset=0.0)
    assert parameters["T"] >= 1
    probability = calibrated_probabilities([0, 8], ["false", "true"], parameters)[1]
    assert probability == pytest.approx(0.75, abs=1e-5)


def test_stock_joint_fit_and_topup_exclusion():
    records = [row(i, label=i < 3, logits=[0, 0]) for i in range(4)]
    topup = row(100, label=False, logits=[0, 0])
    topup["is_base_dev"] = False
    fit = fit_calibration(records + [topup], stock=True)
    assert calibrated_probabilities([0, 0], ["false", "true"], fit["M1"])[1] == pytest.approx(0.75, abs=1e-5)
    with pytest.raises(ValueError, match="base dev"):
        fit_question([topup], jointly_fit_offset=True)


def test_scoring_batches_full_cap_and_preserves_canonical_row_alignment(monkeypatch):
    class Tensor:
        def __init__(self, values):
            self.values = values

        def detach(self):
            return self

        def float(self):
            return self

        def cpu(self):
            return self

        def tolist(self):
            return self.values

    def materialize(request):
        qid, q = next(iter(request["questions"].items()))
        return {"questions": [{"qid": qid, "keys": ["false", "true"],
                               "label": int(q["label"]), "src": q["src"]}]}

    torch = ModuleType("torch")
    torch.inference_mode = nullcontext
    torch.autocast = lambda **kwargs: nullcontext()
    torch.bfloat16 = "bf16"
    data = ModuleType("kev.data")
    data.materialize = materialize
    model_module = ModuleType("kev.model")
    model_module.training_context = lambda limit: {"max_state": limit, "max_branch": limit + 640, "max_packed": limit + 1664}
    train = ModuleType("kev.train")
    train.shape = lambda encoding: (2, [1])
    train.pass_tokens = lambda shapes, shared: len(shapes) * 3
    for name, module in {"torch": torch, "kev": ModuleType("kev"), "kev.data": data,
                         "kev.model": model_module, "kev.train": train}.items():
        monkeypatch.setitem(sys.modules, name, module)

    class Model:
        device = "cpu"
        head = SimpleNamespace(temperature=5)

        def __init__(self):
            self.batches = []
            self.evaluation = False

        def eval(self):
            self.evaluation = True

        def encode(self, tokenizer, record, **kwargs):
            assert kwargs["strict"] is True
            return {"ids": [0] * 4, "label": record["questions"][0]["label"]}

        def forward_batch(self, encodings, shared_prefix=False):
            assert shared_prefix is True
            self.batches.append(len(encodings))
            return [[Tensor([0, e["label"] + 1])] for e in encodings]

    records = [{"state": "state", "questions": {"M1": {"type": "noul", "label": bool(i % 2)}},
                "_meta": {"id": str(i), "group_id": str(i), "source": "source"}} for i in range(3)]
    original = deepcopy(records)
    model = Model()
    outputs = list(score_records(model, None, records, max_state=400, pass_tokens_max=6,
                                is_base_dev=True, intent_ids={"1"}))
    assert model.batches == [2, 1]
    assert model.evaluation and model.head.temperature == 1
    assert records == original
    assert [r["record_id"] for r in outputs] == ["0", "1", "2"]
    assert outputs[1]["label"] == "true" and outputs[1]["is_intent"]
    assert outputs[1]["target"] == [0, 1]
    assert outputs[1]["temperature"] == 1.0
    with pytest.raises(ValueError, match="alone exceeds"):
        list(score_records(Model(), None, records, max_state=400, pass_tokens_max=2))


def test_cuda_loader_binds_required_kernels_and_unit_temperature(monkeypatch):
    import intent_training.select.scoring as scoring

    events = []
    torch = ModuleType("torch")
    torch.float32 = "fp32"
    checkpoint_module = ModuleType("kev.checkpoint")
    checkpoint_module.LoadOptions = lambda **kwargs: kwargs

    class Checkpoint:
        def __init__(self, path):
            assert path == "candidate"

        def load(self, device, options):
            assert events == ["kernels"]
            assert options == {"dtype": "fp32", "temperature": 1.0, "attn": "sdpa"}
            assert device == "cuda"
            events.append("load")
            return "tokenizer", "model"

    checkpoint_module.Checkpoint = Checkpoint
    kernels = ModuleType("intent_training.kevpatch.kernels")
    kernels.install_required_kernels = lambda: events.append("kernels")
    for name, module in {"torch": torch, "kev": ModuleType("kev"), "kev.checkpoint": checkpoint_module,
                         "intent_training.kevpatch.kernels": kernels}.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(scoring, "score_records", lambda model, tokenizer, records, **kwargs: iter([{"ok": model == "model"}]))
    assert list(load_and_score("candidate", [], device="cuda", max_state=400, pass_tokens_max=6)) == [{"ok": True}]
    assert events == ["kernels", "load"]
