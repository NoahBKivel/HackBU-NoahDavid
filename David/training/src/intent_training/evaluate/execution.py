"""Persistent once-only held-out scoring and report assembly."""

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from .reports import benign_rates, lift_report, preference_accuracy, requirement_recall, retention_report, validate_lift_protocol
from .serving import serving_checkpoint, serving_probabilities


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def claim_heldout_run(ledger: Path, inputs: dict[str, str]) -> None:
    """Reserve a held-out scoring run exclusively before either model reads its items."""
    ledger.parent.mkdir(parents=True, exist_ok=True)
    descriptor = {"state": "started", "started_utc": datetime.now(timezone.utc).isoformat(), "inputs": inputs}
    with ledger.open("x", encoding="utf-8") as stream:
        json.dump(descriptor, stream, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())


def _label(value: Any) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def join_scored_candidates(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Join selected and stock observations without dropping or duplicating scored rows."""
    indexed: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (row["endpoint"], str(row["record_id"]), row["question_id"])
        candidate = row["candidate"]
        if candidate not in {"selected", "stock"} or candidate in indexed.setdefault(key, {}):
            raise ValueError("Each scored item requires exactly one selected and one stock observation.")
        indexed[key][candidate] = row
    result: dict[str, list[dict[str, Any]]] = {}
    for (endpoint, _, _), pair in indexed.items():
        if set(pair) != {"selected", "stock"}:
            raise ValueError("A candidate is missing from the paired scores.")
        selected, stock = pair["selected"], pair["stock"]
        if any(selected.get(name) != stock.get(name) for name in ("options", "label", "group_id", "conversation_id", "hacked", "intent_kind")):
            raise ValueError("Paired score metadata disagree.")
        result.setdefault(endpoint, []).append({**{name: value for name, value in selected.items()
                                                   if name not in {"candidate", "checkpoint", "probabilities", "calibrated_probabilities"}},
                                               "label": _label(selected["label"]),
                                               "selected": selected["calibrated_probabilities"],
                                               "stock": stock["calibrated_probabilities"]})
    return result


def score_heldout(manifest: Path, *, selected: str, stock: str,
                   selected_calibration: Path, stock_calibration: Path,
                   output: Path, once_ledger: Path, device: str = "cuda",
                   dtype: Any = None) -> None:
    """Score both frozen candidates once through the serving path with frozen transforms."""
    from intent_training.select.calibration import calibrated_probabilities

    entries = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not entries or any(entry["endpoint"] not in {"intent_probe", "trace", "llmbar", "rewardbench2"} for entry in entries):
        raise ValueError("A held-out manifest must explicitly identify every evaluation endpoint.")
    identifiers = [(entry["endpoint"], str(entry["record_id"])) for entry in entries]
    if len(set(identifiers)) != len(entries):
        raise ValueError("Held-out manifest records must be unique within each endpoint.")
    transforms = {"selected": json.loads(selected_calibration.read_text(encoding="utf-8")),
                  "stock": json.loads(stock_calibration.read_text(encoding="utf-8"))}
    for entry in entries:
        record = entry["record"]
        if not isinstance(record["state"], str) or not record["questions"]:
            raise ValueError("Held-out records must already be rendered and carry their true questions.")
        for question, row in record["questions"].items():
            if "~neg" in question or "label" not in row:
                raise ValueError("Held-out records require served questions and final source labels.")
            if any(question.split("#")[0] not in transform for transform in transforms.values()):
                raise ValueError("Both base-dev calibration families must exist before held-out scoring.")
            options = (["false", "true"] if row["type"] == "noul" else
                       list(row["criteria"]) if row["type"] == "choice" else
                       [str(index) for index in range(len(row["criteria"]))])
            for transform in transforms.values():
                calibrated_probabilities([0.0] * len(options), options, transform[question.split("#")[0]])
    protocol_rows: dict[str, list[dict[str, Any]]] = {"intent_probe": [], "trace": []}
    for entry in entries:
        if entry["endpoint"] in protocol_rows:
            for question, row in entry["record"]["questions"].items():
                if row["type"] != "noul":
                    raise ValueError("Lift endpoints require binary question rows.")
                protocol_rows[entry["endpoint"]].append({**entry, "question_id": question, "options": ["false", "true"]})
    validate_lift_protocol(protocol_rows["intent_probe"], protocol_rows["trace"])
    inputs = {"manifest_sha256": _digest(manifest), "selected": selected, "stock": stock,
              "selected_calibration_sha256": _digest(selected_calibration),
              "stock_calibration_sha256": _digest(stock_calibration)}
    claim_heldout_run(once_ledger, inputs)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".partial")
    with temporary.open("x", encoding="utf-8") as stream:
        for candidate, checkpoint in (("selected", selected), ("stock", stock)):
            with serving_checkpoint(checkpoint, device, dtype=dtype) as server:
                for entry in entries:
                    rows = serving_probabilities(server, entry["record"], record_id=str(entry["record_id"]))
                    for row in rows:
                        question = row["question_id"]
                        parameters = transforms[candidate][question.split("#")[0]]
                        logits = [math.log(p) if p > 0 else -math.inf for p in row["probabilities"]]
                        calibrated = calibrated_probabilities(logits, row["options"], parameters)
                        payload = {**{key: value for key, value in entry.items() if key != "record"},
                                   **row, "candidate": candidate, "checkpoint": checkpoint,
                                   "label": entry["record"]["questions"][question]["label"],
                                   "calibrated_probabilities": calibrated}
                        stream.write(json.dumps(payload, allow_nan=False) + "\n")
                    stream.flush()
    os.replace(temporary, output)
    complete = {"state": "complete", "completed_utc": datetime.now(timezone.utc).isoformat(),
                "inputs": inputs, "output_sha256": _digest(output)}
    temporary_ledger = once_ledger.with_name(once_ledger.name + ".tmp")
    temporary_ledger.write_text(json.dumps(complete, indent=2), encoding="utf-8")
    os.replace(temporary_ledger, once_ledger)


def evaluation_report(payload: dict[str, Any], *, resamples: int = 10000, seed: int = 1) -> dict[str, Any]:
    """Assemble measured evaluations with explicit model identities and denominators."""
    result = {"selected_candidate": payload["selected_candidate"], "stock_candidate": payload["stock_candidate"]}
    result["lift"] = lift_report(payload["intent_probe"], payload["trace"],
                                  selected_candidate=result["selected_candidate"], stock_candidate=result["stock_candidate"],
                                  resamples=resamples, seed=seed)
    result["retention"] = retention_report(payload["retention"], resamples=resamples, seed=seed)
    result["requirement_recall"] = requirement_recall(payload["requirement_filter"])
    result["benign_rates"] = benign_rates(payload["benign_dev"])
    for benchmark in ("llmbar", "rewardbench2"):
        published = payload[benchmark]["published_stock"]
        if not isinstance(published.get("source_url"), str) or not published["source_url"].startswith("https://"):
            raise ValueError("Published stock comparisons require a direct source citation.")
        result[benchmark] = {"measured": preference_accuracy(payload[benchmark]["pairs"]), "published_stock": published}
    return result
