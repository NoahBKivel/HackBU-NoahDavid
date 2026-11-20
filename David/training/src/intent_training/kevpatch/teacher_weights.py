"""Small, provenance-only loss weights for teacher-labelled training records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


MODEL_WEIGHTS = {
    "gpt-6.1-sol": 3.0,
    "gpt-6-sol": 3.0,
    "gpt-6.1-terra": 2.0,
    "gpt-6-terra": 2.0,
    "claude-sonnet-5-5": 2.0,
    "gpt-6-luna": 1.0,
}
TRUSTED_DEFAULT = 1.0


def _models(value):
    if isinstance(value, Mapping):
        model = value.get("actual_model")
        if isinstance(model, str):
            yield model
        else:
            for child in value.values():
                yield from _models(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            yield from _models(child)


def record_weight(record):
    """Average known actual-teacher weights; missing provenance stays at trusted default."""
    meta = record.get("_meta", {})
    if not isinstance(meta, Mapping):
        return TRUSTED_DEFAULT
    stages = [meta.get("teacher_vote_origins", {}), *meta.get("question_pass_origins", {}).values()]
    weights = [MODEL_WEIGHTS[model] for stage in stages for model in _models(stage)
               if model in MODEL_WEIGHTS]
    return sum(weights) / len(weights) if weights else TRUSTED_DEFAULT


def weighted_normalizer(records):
    """Global objective denominator: sum of record weights, including trusted defaults."""
    return sum(record_weight(record) for record in records)


def weight_variants(variants, weights_by_id):
    """Scale each encoded record's share without changing its forward or row packing."""
    for variant in variants:
        weight = weights_by_id.get(variant.request_id, TRUSTED_DEFAULT)
        variant.share *= weight
    return variants
