"""Measure agreement only on records whose source policy requires two teachers."""

from collections import defaultdict

from .native import original_native


def policy_instruments(records, votes):
    """Accept actual private records and joined votes; count single-Sol rows separately."""
    from intent_training.teacher import agreement_report
    from intent_training.teacher.instruments import is_cant_tell
    from intent_training.teacher.vote_allocation import allocation, rf_quorum_slots
    paired = []
    counts = defaultdict(lambda: {"paired_rows": 0, "single_sol_rows": 0, "single_terra_rows": 0,
                                  "single_sol_cant_tell_votes": 0, "single_terra_cant_tell_votes": 0,
                                  "unused_terra_rows": 0})
    seen = set()
    for record in records:
        if original_native(record):
            continue
        meta = record.get("_meta", {})
        identity = record.get("record_id", meta.get("record_id"))
        if not identity:
            raise ValueError("A measured record needs a stable record identifier.")
        mode = allocation(record)
        for key in record["questions"]:
            if "~neg" in key:
                continue
            if (identity, key) in seen:
                raise ValueError("A question row cannot be counted twice in teacher instruments.")
            seen.add((identity, key))
            pair = votes.get(identity, {}).get(key, {})
            if record.get("purpose") == "requirement_selection":
                slots = rf_quorum_slots(record, pair)
                if not slots:
                    raise ValueError("A measured RF row lacks a teacher vote.")
                c = counts[key.split("#", 1)[0]]
                slot = slots[0]
                c[f"single_{slot}_rows"] += 1
                c[f"single_{slot}_cant_tell_votes"] += int(is_cant_tell(pair[slot]))
                continue
            required = {"sol", "terra"} if mode == "paired" else {"sol"}
            if not required <= set(pair):
                raise ValueError("A measured row lacks its policy-required teachers.")
            c = counts[key.split("#", 1)[0]]
            if mode == "paired":
                paired.append((key, pair["sol"], pair["terra"]))
                c["paired_rows"] += 1
            else:
                c["single_sol_rows"] += 1
                c["single_sol_cant_tell_votes"] += int(is_cant_tell(pair["sol"]))
                c["unused_terra_rows"] += int("terra" in pair)
    measured = agreement_report(paired)
    result = {}
    for key, c in sorted(counts.items()):
        item = measured.get(key, {"rows": 0, "agreements": 0, "both_positive": 0,
            "sol_only_positive": 0, "terra_only_positive": 0, "cant_tell_votes": 0,
            "positive_specific_agreement": None, "raw_agreement": None,
            "cant_tell_rate": None, "tightening_required": False})
        result[key] = {**item, **c, "total_rows": c["paired_rows"] + c["single_sol_rows"] + c["single_terra_rows"],
                       "agreement_applicable": c["paired_rows"] > 0}
    return result


def combine_instruments(*reports):
    """Combine disjoint measured row sets by counts, never by averaging rates."""
    fields = ("rows", "agreements", "both_positive", "sol_only_positive", "terra_only_positive",
              "cant_tell_votes", "paired_rows", "single_sol_rows", "single_sol_cant_tell_votes",
              "single_terra_rows", "single_terra_cant_tell_votes", "unused_terra_rows")
    result = {}
    for report in reports:
        for question, measured in report.items():
            item = result.setdefault(question, dict.fromkeys(fields, 0))
            for field in fields:
                item[field] += measured.get(field, 0)
    for question, item in result.items():
        denominator = 2 * item["both_positive"] + item["sol_only_positive"] + item["terra_only_positive"]
        psa = 2 * item["both_positive"] / denominator if denominator and question not in {"D5", "L7"} else None
        rows = item["paired_rows"]
        rate = item["cant_tell_votes"] / (2 * rows) if rows else None
        item.update(positive_specific_agreement=psa, raw_agreement=item["agreements"] / rows if rows else None,
                    cant_tell_rate=rate, agreement_applicable=bool(rows),
                    total_rows=rows + item["single_sol_rows"] + item["single_terra_rows"],
                    tightening_required=(psa is not None and psa < .70) or (rate is not None and rate > .25))
    return result
