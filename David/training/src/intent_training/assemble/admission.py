"""Admit fully resolved question sets through the actual encoder fit test."""

from copy import deepcopy

from monitor_format import count_tokens, validate_record

from .flow import next_pass
from .labels import add_twins, validate_twins
from .native import original_native
from .siblings import pack_siblings


def _validate(record):
    try:
        validate_record(record)
    except ValueError as error:
        if not original_native(record) or not str(error).endswith("requires its wording."):
            raise
        from kev.api import SystemOneRequest
        SystemOneRequest.model_validate({"state": record["state"], "questions": record["questions"]})
        if any("label" not in row for row in record["questions"].values()):
            raise ValueError("An original native question requires its original label.")


def admit_record(record, context, *, requirements=None, tokenizer, fits, completed_rows_only=False):
    """Reject pending questions, then derive twins and pack actual fitted siblings."""
    if not completed_rows_only:
        pending = next_pass(record, context, requirements=requirements, tokenizer=tokenizer)
        if pending["stage"] != "complete":
            raise ValueError("The record still has unresolved dependent questions: " + pending["stage"] + ".")
    elif any("label" not in row for row in record["questions"].values()):
        raise ValueError("Every included question needs its resolved label.")
    if not original_native(record):
        from intent_training.teacher.vote_allocation import required_families
        required = set(required_families(record))
        receipts = record.get("_meta", {}).get("teacher_vote_families", {})
        if any(not required <= set(receipts.get(key, [])) for key in record["questions"] if "~neg" not in key):
            raise ValueError("A question lacks its required teacher provenance before admission.")
    result = deepcopy(record) if original_native(record) else add_twins(record)
    if not original_native(result):
        validate_twins(result)
    _validate(result)
    budget = result.get("_meta", {}).get("validated_length")
    state_tokens = count_tokens(result["state"], tokenizer)
    if budget is not None and state_tokens > budget:
        raise ValueError("The actual state exceeds its declared validated token length.")
    result.setdefault("_meta", {})["state_tokens"] = state_tokens
    result["_meta"]["dependent_questions_complete"] = True
    if completed_rows_only:
        result["_meta"]["auxiliary_scope"] = "owner_authorized_completed_rows_only"
    siblings = pack_siblings(result, fits=fits)
    for sibling in siblings:
        if not fits(sibling):
            raise ValueError("A packed sibling fails actual encoder admission.")
        _validate(sibling)
        sibling["_meta"]["encoder_admitted"] = True
    return siblings
