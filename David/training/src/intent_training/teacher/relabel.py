"""Record at most one instruction-tightening relabel per failing question."""

from hashlib import sha256


def request_relabel(question, instrument, tightened_instructions, previous=()):
    """Return a reviewable relabel record or a second-failure report with standing labels."""
    if not instrument["tightening_required"]:
        raise ValueError("The question has no measured relabel trigger.")
    if any(entry["question"] == question for entry in previous):
        return {"question": question, "action": "report_second_failure", "labels_stand": True,
                "instrument": instrument}
    if not tightened_instructions or not tightened_instructions.strip():
        raise ValueError("Tightened supplementary instructions are required before relabelling.")
    return {"question": question, "action": "relabel_once", "labels_stand": False,
            "supplementary_instructions": tightened_instructions,
            "instructions_sha256": sha256(tightened_instructions.encode("utf-8")).hexdigest(),
            "instrument": instrument}
