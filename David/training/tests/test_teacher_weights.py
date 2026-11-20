from types import SimpleNamespace

import pytest

from intent_training.kevpatch.teacher_weights import (
    record_weight,
    weighted_normalizer,
    weight_variants,
)


def test_actual_model_weights_and_global_weighted_reduction():
    records = [
        {"_meta": {"teacher_vote_origins": {"sol": {"actual_model": "gpt-6.1-sol"}}}},
        {"_meta": {"teacher_vote_origins": {
            "terra": {"actual_model": "gpt-6.1-terra"},
            "sol": {"actual_model": "claude-sonnet-5-5"},
        }}},
        {"_meta": {"teacher_vote_origins": {"sol": {"actual_model": "gpt-6-luna"}}}},
        {"_meta": {"native_record": True}},
        {"_meta": {"teacher_vote_origins": {"sol": {"model": "missing-actual-model"}}}},
    ]
    weights = [record_weight(record) for record in records]
    assert weights == [3.0, 2.0, 1.0, 1.0, 1.0]
    assert weighted_normalizer(records) == 8.0

    losses = [1.0, 4.0, 10.0, 2.0, 6.0]
    assert sum(loss * weight for loss, weight in zip(losses, weights)) / weighted_normalizer(records) == pytest.approx(29.0 / 8.0)

    variants = [SimpleNamespace(request_id=str(i), share=1.0) for i in range(len(weights))]
    weight_variants(variants, {str(i): weight for i, weight in enumerate(weights)})
    assert [variant.share for variant in variants] == weights
