"""Score prepared records through Kev's batched shared-prefix forward."""

from copy import deepcopy
import math
from typing import Any, Iterable, Iterator


def target_rows(records: Iterable[dict[str, Any]], *, is_base_dev: bool = False,
                intent_ids: set[str] | None = None) -> Iterator[dict[str, Any]]:
    """Expose canonical target vectors without loading a model or its tokenizer."""
    from kev.data import materialize

    for request in records:
        request = deepcopy(request)
        meta = request["_meta"]
        record_id = str(meta["id"])
        for question in request["questions"].values():
            question.setdefault("src", meta["source"])
        record = materialize(request)
        for question in record["questions"]:
            options = [str(value) for value in question["keys"]]
            yield {"record_id": record_id, "group_id": str(meta["group_id"]),
                   "question_id": question["qid"], "options": options,
                   "label": options[question["label"]],
                   "target": question.get("target", [float(i == question["label"]) for i in range(len(options))]),
                   "is_intent": record_id in (intent_ids or set()), "is_base_dev": is_base_dev}


def score_records(model: Any, tokenizer: Any, records: Iterable[dict[str, Any]], *,
                  max_state: int, pass_tokens_max: int, is_base_dev: bool = False,
                  intent_ids: set[str] | None = None, autocast_bf16: bool = True) -> Iterator[dict[str, Any]]:
    """Yield raw-logit rows with every physical batch under the padded pass cap."""
    import torch
    from kev.data import materialize
    from kev.model import training_context
    from kev.train import pass_tokens, shape

    if pass_tokens_max <= 0:
        raise ValueError("The scoring pass cap must be positive.")
    context = training_context(max_state)
    model.eval()
    model.head.temperature = 1.0
    batch: list[tuple[dict[str, Any], Any, list[dict[str, Any]]]] = []

    def flush() -> Iterator[dict[str, Any]]:
        if not batch:
            return
        enabled = autocast_bf16 and str(model.device).startswith("cuda")
        with torch.inference_mode(), torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=enabled):
            outputs = model.forward_batch([item[1] for item in batch], shared_prefix=True)
        if len(outputs) != len(batch):
            raise ValueError("Model output record count differs from the scoring batch.")
        for (_, _, rows), values in zip(batch, outputs):
            if len(rows) != len(values):
                raise ValueError("Model output question count differs from the request.")
            for row, logits in zip(rows, values):
                raw = logits.detach().float().cpu().tolist()
                if len(raw) != len(row["options"]):
                    raise ValueError("Model output options differ from the request.")
                if not all(math.isfinite(value) for value in raw):
                    raise ValueError("The scoring forward returned nonfinite logits.")
                yield {**row, "logits": raw}
        batch.clear()

    for original in records:
        request = deepcopy(original)
        for question in request["questions"].values():
            question.setdefault("src", request["_meta"]["source"])
        record = materialize(request)
        encoded = model.encode(tokenizer, record, strict=True,
                               max_state=context["max_state"], max_branch=context["max_branch"])
        if len(encoded["ids"]) > context["max_packed"]:
            raise ValueError("The scoring record exceeds Kev's packed token allowance.")
        if pass_tokens([shape(encoded)], True) > pass_tokens_max:
            raise ValueError("A scoring record alone exceeds the padded pass cap.")
        if batch and pass_tokens([shape(item[1]) for item in batch] + [shape(encoded)], True) > pass_tokens_max:
            yield from flush()
        rows = list(target_rows([request], is_base_dev=is_base_dev, intent_ids=intent_ids))
        batch.append((request, encoded, rows))
    yield from flush()


def load_and_score(checkpoint: str, records: Iterable[dict[str, Any]], *, device: str,
                   max_state: int, pass_tokens_max: int, is_base_dev: bool = False,
                   intent_ids: set[str] | None = None) -> Iterator[dict[str, Any]]:
    """Load a checkpoint at unit temperature and stream shared-prefix predictions."""
    import torch
    from kev.checkpoint import Checkpoint, LoadOptions

    tokenizer, model = Checkpoint(checkpoint).load(device, LoadOptions(dtype=torch.float32, temperature=1.0))
    yield from score_records(model, tokenizer, records, max_state=max_state, pass_tokens_max=pass_tokens_max,
                            is_base_dev=is_base_dev, intent_ids=intent_ids)
