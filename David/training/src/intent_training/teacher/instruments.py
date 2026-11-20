"""Measure actual paired votes without manufacturing agreement for empty classes."""

from collections import defaultdict
from .prepare import positive


def is_cant_tell(value):
    """Recognize the binary sentinel and the exact G2 uncertainty option."""
    return value in {"cant_tell", "can't tell from the evidence"}


def agreement_report(pairs):
    """Accept (question_key, Sol answer, Terra answer) triples and report question counts."""
    counts = defaultdict(lambda: {"rows": 0, "agreements": 0, "both_positive": 0,
                                  "sol_only_positive": 0, "terra_only_positive": 0,
                                  "cant_tell_votes": 0})
    for key, sol, terra in pairs:
        q = key.split("#")[0]
        c = counts[q]
        c["rows"] += 1
        c["agreements"] += int(sol == terra)
        c["cant_tell_votes"] += int(is_cant_tell(sol)) + int(is_cant_tell(terra))
        a, b = positive(q, sol), positive(q, terra)
        c["both_positive"] += int(a and b)
        c["sol_only_positive"] += int(a and not b)
        c["terra_only_positive"] += int(b and not a)
    for q, c in counts.items():
        denominator = 2 * c["both_positive"] + c["sol_only_positive"] + c["terra_only_positive"]
        c["positive_specific_agreement"] = 2 * c["both_positive"] / denominator if denominator else None
        c["raw_agreement"] = c["agreements"] / c["rows"]
        c["cant_tell_rate"] = c["cant_tell_votes"] / (2 * c["rows"])
        c["tightening_required"] = ((c["positive_specific_agreement"] is not None
                                     and c["positive_specific_agreement"] < 0.70)
                                    or c["cant_tell_rate"] > 0.25)
        if q in {"D5", "L7"}:
            c["positive_specific_agreement"] = None
    return dict(counts)
