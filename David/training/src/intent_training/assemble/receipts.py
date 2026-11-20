"""Resolve duplicate votes by authorized completion receipts, never their labels."""

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

from intent_training.teacher.claims import batch_claim_path, claim_path
from intent_training.teacher.dispatch import batch_for_validation, digest, validate_vote
from intent_training.teacher.vote_allocation import required_families
from .quality import receipt_holds, receipt_held


def canonical_payload(record):
    """Use the exact model-visible allowlist of the canonical preparation writer."""
    return {key: record[key] for key in ("record_id", "state", "questions", "source", "pass", "teacher_side", "purpose", "row_context") if key in record}


def _existing(value, repository):
    path = Path(value)
    return path if path.exists() else Path(repository) / path


def _receipt(batch, slot, output, claims_dir, repository):
    if receipt_held(batch["batch_id"], slot, receipt_holds()):
        return None
    path = batch_claim_path(claims_dir, batch)
    legacy = False
    if not path.exists():
        path = claim_path(claims_dir, batch["batch_id"], slot, batch["input_sha256"])
        legacy = True
    if not path.exists():
        return None
    claim = json.loads(path.read_text(encoding="utf-8"))
    receipt = claim if legacy else claim.get("families", {}).get(slot, {})
    if receipt.get("status") != "completed":
        return None
    owner = claim.get("owner")
    if not isinstance(owner, str) or not owner.strip() or receipt.get("owner", owner) != owner:
        raise ValueError("A completed receipt does not identify its authorized execution owner.")
    if set(claim.get("record_ids", [])) != {row["record_id"] for row in batch["records"]}:
        raise ValueError("A completed receipt does not cover the frozen batch record identities.")
    if _existing(receipt.get("vote_output", ""), repository).resolve() != output.resolve():
        raise ValueError("A completed receipt points to a different vote artifact.")
    if legacy:
        if (claim.get("batch_id") != batch["batch_id"] or claim.get("input_sha256") != batch["input_sha256"]
                or claim.get("model_family") != slot or digest(batch["records"]) != batch["input_sha256"]):
            raise ValueError("The legacy receipt does not authorize this exact frozen slot.")
        restored = dict(batch)
        restored.pop("model_overrides", None)
    else:
        normalized = deepcopy(claim)
        normalized["families"][slot]["vote_output"] = str(output.resolve())
        restored = batch_for_validation(batch, normalized, slot, output)
    completed = receipt.get("completed_at")
    timestamp = datetime.fromisoformat(completed)
    if timestamp.tzinfo is None:
        raise ValueError("A completed receipt lacks its actual completion timezone.")
    summary = {"batch_id": batch["batch_id"], "input_sha256": batch["input_sha256"], "owner": owner,
               "record_ids": sorted(claim["record_ids"]), "slot": slot, "receipt": receipt}
    return restored, {"claim_path": str(path), "claim_owner": owner, "completed_at": completed,
                      "receipt_sha256": digest(summary), "output": str(output), "batch_id": batch["batch_id"],
                      "input_sha256": batch["input_sha256"], "vote_slot": slot}


def resolve_duplicate_receipts(collected, *, manifests, queue, canonical, contexts, claims_dir, repository):
    """Apply the first-completed authorized canonical-input rule to held identities."""
    result = deepcopy(collected)
    for identity, prepared in result["prepared"].items():
        if identity in canonical and digest(prepared) != digest(canonical_payload(canonical[identity])):
            result["blocked"].add(identity)
            result["errors"].append({"record_id": identity,
                "error": "The completed teacher input differs from the current canonical full input.",
                "completed_record_sha256": digest(prepared),
                "canonical_record_sha256": digest(canonical_payload(canonical[identity]))})
    held = set(result["blocked"])
    candidates, receipt_errors = {}, []
    artifacts = []
    for manifest in manifests:
        for entry in json.loads(Path(manifest).read_text(encoding="utf-8")):
            output = _existing(entry["output"], repository)
            if output.exists():
                batch = json.loads(_existing(entry["input"], repository).read_text(encoding="utf-8"))
                if held & {row["record_id"] for row in batch["records"]}:
                    artifacts.append((batch, entry["model_family"], output))
    from .stream import queue_tasks
    for task in queue_tasks(queue):
        batch = task["batch"]
        if batch["pass"] == "main" and held & {row["record_id"] for row in batch["records"]}:
            artifacts.extend((batch, slot, Path(output)) for slot, output in task["outputs"].items() if Path(output).exists())
    for batch, slot, output in artifacts:
        try:
            authorized = _receipt(batch, slot, output, claims_dir, repository)
            if authorized is None:
                continue
            restored, receipt = authorized
            text = output.read_text(encoding="utf-8")
            envelopes = json.loads(text) if text.lstrip().startswith("[") else [json.loads(line) for line in text.splitlines() if line.strip()]
            if {vote["record_id"] for vote in envelopes} != {row["record_id"] for row in batch["records"]}:
                raise ValueError("A completed artifact does not cover all authorized batch records.")
            prepared = {row["record_id"]: row for row in batch["records"]}
            for vote in envelopes:
                validate_vote(vote, restored, slot)
                identity = vote["record_id"]
                if identity not in held or identity not in canonical:
                    continue
                fingerprint = digest(prepared[identity])
                if fingerprint != digest(canonical_payload(canonical[identity])):
                    continue
                candidates.setdefault(identity, {}).setdefault(slot, []).append({
                    "votes": vote["votes"], "prepared": prepared[identity],
                    "origin": {**receipt, "teacher_record_sha256": fingerprint, "model_family": vote["model_family"],
                               "actual_model": vote.get("actual_model", vote["model"])}})
        except (ValueError, KeyError, TypeError) as error:
            receipt_errors.append({"output": str(output), "error": str(error)})
    resolved, later = [], []
    for identity in sorted(held):
        if identity not in canonical or identity not in contexts:
            continue
        required = required_families(contexts[identity])
        slots = candidates.get(identity, {})
        if not set(required) <= set(slots):
            continue
        chosen = {}
        for slot, values in slots.items():
            ordered = sorted(values, key=lambda value: (datetime.fromisoformat(value["origin"]["completed_at"]), value["origin"]["receipt_sha256"]))
            chosen[slot] = ordered[0]
            later.extend({"record_id": identity, "slot": slot, **value} for value in ordered[1:])
        result["prepared"][identity] = chosen[required[0]]["prepared"]
        result["votes"][identity] = {slot: value["votes"] for slot, value in chosen.items()}
        result["origins"][identity] = {slot: value["origin"] for slot, value in chosen.items()}
        result["blocked"].discard(identity)
        resolved.append({"record_id": identity, "required_slots": list(required),
                         "chosen": {slot: {"votes": value["votes"], **value["origin"]} for slot, value in chosen.items()}})
    resolved_ids = {value["record_id"] for value in resolved}
    original_errors = [error for error in result["errors"] if error.get("record_id") in resolved_ids]
    result["errors"] = [error for error in result["errors"] if error.get("record_id") not in resolved_ids]
    result["receipt_resolution"] = {"resolved": resolved, "unresolved_ids": sorted(result["blocked"]),
        "later_duplicate_audit": later, "prior_conflict_audit": original_errors, "receipt_errors": receipt_errors}
    return result
