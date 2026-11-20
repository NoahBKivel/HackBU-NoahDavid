"""Measure actual native encoder shapes without persisting synthetic labels."""

from collections import Counter
from copy import deepcopy
import json
import os
import sys

from .records import load_tokenizer


def measure(root):
    sys.path.insert(0, str(root / "vendor" / "kev"))
    from kev.api import SystemOneRequest, to_record
    from kev.model import encode, fits, training_context, rows_of
    tokenizer = load_tokenizer(root / "data" / "tokenizer")
    context = training_context(32768)
    maxima = {}
    counts = Counter()
    rejected = []
    for name in ("main", "native"):
        path = root / "data" / "prepared" / f"{name}.jsonl"
        if not path.exists():
            continue
        for line in path.open(encoding="utf-8"):
            record = json.loads(line)
            request = {"state": record["state"], "questions": deepcopy(record["questions"])}
            # Temporary placeholders satisfy materialize's label field only. Shapes do
            # not depend on their values, and these labels never leave this function.
            for question in request["questions"].values():
                question.setdefault("src", record.get("source", record.get("_meta", {}).get("source", name)))
                if "label" not in question:
                    question["label"] = (False if question["type"] == "noul" else
                        next(iter(question["criteria"])) if question["type"] == "choice" else 0)
            native, _ = to_record(SystemOneRequest.model_validate(request))
            accepted = fits(native, tokenizer, **context)
            counts[f"{name}_records"] += 1
            counts[f"{name}_fits"] += int(accepted)
            try:
                encoded = encode(tokenizer, native, strict=True,
                                 max_state=context["max_state"], max_branch=context["max_branch"])
                state, _, branches = rows_of(encoded)
                actual_shape = len(state), [len(branch["ids"]) for branch in branches]
                values = {"state_tokens": actual_shape[0], "question_count": len(actual_shape[1]),
                          "longest_branch": max(actual_shape[1]), "packed_tokens": len(encoded["ids"]),
                          "padded_tokens_shared": actual_shape[0] + len(actual_shape[1]) * max(actual_shape[1]),
                          "padded_tokens_rows": len(actual_shape[1]) * (actual_shape[0] + max(actual_shape[1]))}
                for key, value in values.items():
                    if value > maxima.get(key, {}).get("value", -1):
                        maxima[key] = {"value": value, "record_id": record["record_id"], "file": name}
            except Exception as error:
                rejected.append({"record_id": record["record_id"], "error": str(error)})
            if not accepted:
                counts[f"{name}_needs_splitting_or_rejection"] += 1
    report = {"context": context, "counts": counts, "maxima": maxima,
              "encoding_errors": rejected, "method": "kev.api.to_record; kev.model.fits/encode/rows_of; native padded shape formula",
              "placeholder_labels": "in_memory_shape_only_never_persisted",
              "scope": "prepared_main_and_native_before_RF_G2_enrichment_and_assembly_twins",
              "requirements_selection": "not_training_rows"}
    destination = root / "results" / "preparation" / "shapes.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
    os.replace(temporary, destination)
    print(json.dumps(report), flush=True)
    return report
