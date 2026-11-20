"""Preserve target evidence while limiting incidental negative question rows."""

from collections import defaultdict
from copy import deepcopy
import hashlib
import json

from .labels import base_question, positive, validate_twins
from .native import original_native


def question_counts(records):
    counts = defaultdict(lambda: {"rows": 0, "positives": 0})
    for record in records:
        for key, row in record["questions"].items():
            question = key.split("#", 1)[0]
            counts[question]["rows"] += 1
            counts[question]["positives"] += int(positive(key, row["label"]))
    return {key: {**value, "rate": value["positives"] / value["rows"]}
            for key, value in sorted(counts.items())}


def _rank(seed, record, key):
    content = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(f"{seed}:{key}:{content}".encode()).hexdigest()


def balance_cap(records, *, seed):
    """Keep all positive, paired, target, severity and correction rows."""
    output = deepcopy(records)
    optional = defaultdict(list)
    positives = defaultdict(int)
    keep = [set() for _ in output]
    for index, record in enumerate(output):
        meta = record.get("_meta", {})
        if original_native(record):
            keep[index].update(record["questions"])
            continue
        validate_twins(record)
        objective = meta.get("objective", []) or []
        if isinstance(objective, str):
            objective = [objective]
        objective = set(objective)
        if meta.get("form") == "screen" or meta.get("record_kind") == "screen":
            objective = {"SCR", "M8"}
            meta["objective"] = sorted(objective)
        for key, row in record["questions"].items():
            if "~neg" in key:
                continue
            base = base_question(key)
            is_positive = positive(key, row["label"])
            positives[base] += int(is_positive)
            if is_positive or meta.get("pair_id") is not None or base in objective or base in {"D5", "L7"}:
                keep[index].add(key)
            else:
                optional[base].append((index, key))
    for base, candidates in optional.items():
        ranked = sorted(candidates, key=lambda item: _rank(seed, output[item[0]], item[1]))
        for index, key in ranked[:10 * positives[base]]:
            keep[index].add(key)
    for index, record in enumerate(output):
        if not keep[index]:
            candidates = [key for key in record["questions"] if "~neg" not in key]
            if not candidates:
                raise ValueError("An input record has no base question rows.")
            keep[index].add(min(candidates, key=lambda key: _rank(seed, record, key)))
        keep[index].update(key + "~neg" for key in list(keep[index]) if key + "~neg" in record["questions"])
        record["questions"] = {key: row for key, row in record["questions"].items() if key in keep[index]}
        if not original_native(record):
            validate_twins(record)
    return output, {"collected": question_counts(records), "post_cap": question_counts(output),
                    "records_before": len(records), "records_after": len(output)}
