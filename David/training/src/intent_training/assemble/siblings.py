"""Pack question rows with the pinned encoder's fit decision."""

from copy import deepcopy

from .labels import record_digest


def kev_fit(tokenizer, *, max_state=32768):
    """Build a fit predicate using Kev's actual tokenizer and materialization."""
    if tokenizer is None:
        raise ValueError("The actual tokenizer must be supplied.")
    from kev.api import SystemOneRequest, to_record
    from kev.model import fits, training_context
    def check(record):
        request = {"state": record["state"], "questions": {key: {
            field: value for field, value in row.items() if field in {"type", "instructions", "criteria"}}
            for key, row in record["questions"].items()}}
        # Kev's materialize function uses this same serving conversion. Labels do not affect token admission.
        internal, _ = to_record(SystemOneRequest.model_validate(request))
        return fits(internal, tokenizer, **training_context(max_state))
    return check


def pack_siblings(record, *, fits):
    """Split oversized question bundles without changing the state or rows."""
    if not record["questions"]:
        raise ValueError("A packed record must contain question rows.")
    if fits(record):
        return [deepcopy(record)]
    output = []
    current = deepcopy(record)
    current["questions"] = {}
    consumed = set()
    for key, row in record["questions"].items():
        if key in consumed:
            continue
        base = key.removesuffix("~neg")
        unit = {name: deepcopy(record["questions"][name]) for name in (base, base + "~neg")
                if name in record["questions"]}
        consumed.update(unit)
        trial = deepcopy(current)
        trial["questions"].update(unit)
        if fits(trial):
            current = trial
            continue
        if current["questions"]:
            output.append(current)
        current = deepcopy(record)
        current["questions"] = unit
        if not fits(current):
            raise ValueError("A single question row fails the actual encoder fit test.")
    output.append(current)
    if len(output) > 1:
        group = record.get("_meta", {}).get("sibling_group") or record_digest(record)
        for index, sibling in enumerate(output):
            meta = sibling.setdefault("_meta", {})
            meta["sibling_group"] = group
            meta["sibling_index"] = index
            meta["record_id"] = f"{meta.get('record_id', group)}:sibling:{index}"
    return output
