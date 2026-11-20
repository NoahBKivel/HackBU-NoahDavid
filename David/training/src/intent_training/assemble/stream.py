"""Resolve verified completed model rows without waiting for an entire source."""

from copy import deepcopy
from pathlib import Path
import json

from intent_training.teacher import validate_vote
from intent_training.teacher.dispatch import digest
from intent_training.teacher.vote_allocation import required_families

from .labels import resolve_record
from .quality import receipt_holds, receipt_held


def _vote_lines(output):
    text = output.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        try:
            return [(index, json.dumps(value)) for index, value in enumerate(json.loads(text), 1)]
        except ValueError:
            return [(1, text)]
    return list(enumerate(text.splitlines(), 1))


def _origin(vote, output):
    return {"output": str(output), "batch_id": vote["batch_id"], "input_sha256": vote["input_sha256"],
            "vote_slot": vote.get("vote_slot", vote["model_family"]), "model_family": vote["model_family"],
            "actual_model": vote.get("actual_model", vote["model"])}


def _path(value, repository):
    path = Path(value)
    if path.exists():
        return path
    return Path(repository) / path


def queue_tasks(path):
    """Stream committed journal lines without retaining the complete queue text."""
    with Path(path).open("rb") as handle:
        for line in handle:
            if not line.endswith(b"\n"):
                break
            if line.strip():
                yield json.loads(line)


def completed_votes(manifests, *, repository):
    """Validate existing output rows individually against their actual frozen inputs."""
    prepared, votes, fingerprints, origins, blocked, errors = {}, {}, {}, {}, set(), []
    holds = receipt_holds()
    for manifest in manifests:
        entries = json.loads(Path(manifest).read_text(encoding="utf-8"))
        for entry in entries:
            output = _path(entry["output"], repository)
            if not output.exists():
                continue
            batch = json.loads(_path(entry["input"], repository).read_text(encoding="utf-8"))
            if receipt_held(batch["batch_id"], entry["model_family"], holds):
                continue
            inputs = {row["record_id"]: row for row in batch["records"]}
            for number, line in _vote_lines(output):
                if not line.strip():
                    continue
                identity = None
                try:
                    vote = json.loads(line)
                    identity = vote["record_id"]
                    if vote["pass"] != "main":
                        continue
                    validate_vote(vote, batch, entry["model_family"])
                    row = inputs[identity]
                    fingerprint = digest(row)
                    if identity in fingerprints and fingerprints[identity] != fingerprint:
                        raise ValueError("The same record identity has different complete teacher inputs.")
                    fingerprints[identity] = fingerprint
                    prepared[identity] = row
                    family = vote.get("vote_slot", vote["model_family"])
                    previous = votes.setdefault(identity, {}).get(family)
                    if previous is not None and previous != vote["votes"]:
                        raise ValueError("A teacher family supplied conflicting repeated votes.")
                    votes[identity][family] = vote["votes"]
                    origins.setdefault(identity, {})[family] = {**_origin(vote, output), "teacher_record_sha256": fingerprint}
                except (ValueError, KeyError, TypeError) as error:
                    if identity:
                        blocked.add(identity)
                    errors.append({"output": str(output), "line": number, "record_id": identity,
                                   "error": str(error)})
    return {"prepared": prepared, "votes": votes, "origins": origins, "blocked": blocked, "errors": errors}


def resolve_ready(collected, *, metadata=None, contexts=None):
    """Resolve each policy-complete record with all available private provenance."""
    metadata, contexts = metadata or {}, contexts or {}
    resolved, audits, pending, errors = [], [], [], list(collected["errors"])
    for identity, prepared in collected["prepared"].items():
        if identity in collected["blocked"]:
            continue
        context = contexts.get(identity, {})
        private = metadata.get(identity, {})
        meta = {**private.get("_meta", private), **context.get("_meta", {}),
                **prepared.get("_meta", {}), "record_id": identity}
        meta.setdefault("source", prepared.get("source"))
        side = context.get("side", {})
        construction = side.get("construction")
        if construction and construction.get("type"):
            meta["construction"] = construction["type"]
        try:
            required = required_families({"_meta": meta, "side": side})
        except (ValueError, KeyError, TypeError) as error:
            errors.append({"record_id": identity, "error": str(error)})
            continue
        available = collected["votes"].get(identity, {})
        if not set(required) <= set(available):
            pending.append({"record_id": identity, "required": list(required), "available": sorted(available)})
            continue
        joined = {}
        for family, answers in available.items():
            for key, value in answers.items():
                joined.setdefault(key, {})[family] = value
        record = {"state": prepared["state"], "questions": deepcopy(prepared["questions"]), "_meta": meta}
        try:
            result, audit = resolve_record(record, joined,
                source_labels=prepared.get("teacher_side", {}).get("source_labels", []), construction=construction)
        except (ValueError, KeyError, TypeError) as error:
            errors.append({"record_id": identity, "error": str(error)})
            continue
        result["_meta"]["teacher_vote_origins"] = collected["origins"].get(identity, {})
        result["_meta"]["assembly_context_available"] = identity in contexts
        resolved.append(result)
        audits.append({"record_id": identity, **audit})
    return resolved, {"resolved_records": len(resolved), "awaiting_required_families": pending,
                      "blocked_record_ids": sorted(collected["blocked"]), "errors": errors, "resolution": audits}


def queue_votes(queue, *, passes, claims_dir=None):
    """Collect completed dependent votes from the shared embedded-batch queue."""
    prepared, votes, origins, blocked, errors, fingerprints = {}, {}, {}, set(), [], {}
    from intent_training.teacher.claims import batch_claim_path
    from intent_training.teacher.dispatch import batch_for_validation
    from .receipts import canonical_payload
    variants = {}
    batches = {}
    holds = receipt_holds()
    encountered_holds = set()
    claims_dir = Path(claims_dir) if claims_dir else Path(__file__).resolve().parents[3] / "data/votes/claims"
    for task in queue_tasks(queue):
        batch = task["batch"]
        if batch["pass"] not in passes:
            continue
        if batch["batch_id"] in holds.get("batch_ids", []):
            encountered_holds.add(batch["batch_id"])
            continue
        batches[(batch["batch_id"], batch["input_sha256"])] = batch
        inputs = {row["record_id"]: row for row in batch["records"]}
        for family, filename in task["outputs"].items():
            if receipt_held(batch["batch_id"], family, holds):
                encountered_holds.add(batch["batch_id"] + ":" + family)
                continue
            output = Path(filename)
            validation_batch = dict(batch)
            validation_batch.pop("model_overrides", None)
            claim_path = batch_claim_path(claims_dir, batch)
            if claim_path.exists():
                claim = json.loads(claim_path.read_text(encoding="utf-8"))
                if claim.get("families", {}).get(family, {}).get("status") == "completed":
                    receipt_output = claim["families"][family].get("vote_output")
                    if receipt_output:
                        output = Path(receipt_output)
                    try:
                        validation_batch = batch_for_validation(batch, claim, family, output)
                    except ValueError as error:
                        errors.append({"output": str(output), "error": str(error)})
                        continue
            if not output.exists():
                continue
            for number, value in _vote_lines(output):
                identity = None
                try:
                    vote = json.loads(value)
                    identity = vote["record_id"]
                    validate_vote(vote, validation_batch, family)
                    canonical_hash = digest(canonical_payload(inputs[identity]))
                    variant = variants.setdefault(identity, {}).setdefault(canonical_hash,
                        {"prepared": inputs[identity], "votes": {}, "origins": {}, "blocked": False})
                    if family in variant["votes"] and variant["votes"][family] != vote["votes"]:
                        variant["blocked"] = True
                    else:
                        variant["votes"][family] = vote["votes"]
                        variant["origins"][family] = _origin(vote, output)
                    fingerprint = digest(inputs[identity])
                    if identity in fingerprints and fingerprints[identity] != fingerprint:
                        raise ValueError("A dependent record has conflicting frozen inputs.")
                    fingerprints[identity] = fingerprint
                    prepared[identity] = inputs[identity]
                    previous = votes.setdefault(identity, {}).get(family)
                    if previous is not None and previous != vote["votes"]:
                        raise ValueError("A dependent teacher family supplied conflicting repeated votes.")
                    votes[identity][family] = vote["votes"]
                    origins.setdefault(identity, {})[family] = _origin(vote, output)
                except (ValueError, KeyError, TypeError) as error:
                    if identity:
                        blocked.add(identity)
                    errors.append({"output": str(output), "line": number, "record_id": identity, "error": str(error)})
    return {"prepared": prepared, "votes": votes, "origins": origins, "blocked": blocked, "errors": errors,
            "variants": variants, "batches": batches, "held_batch_ids": sorted(encountered_holds)}


def merge_collections(left, right):
    """Combine independent output locations while rejecting conflicting repeats."""
    result = deepcopy(left)
    result["blocked"].update(right["blocked"])
    result["errors"].extend(right["errors"])
    for identity, prepared in right["prepared"].items():
        if identity in result["prepared"] and digest(result["prepared"][identity]) != digest(prepared):
            result["blocked"].add(identity)
            result["errors"].append({"record_id": identity, "error": "The merged output locations disagree on the full frozen input."})
            continue
        result["prepared"][identity] = prepared
        for family, answers in right["votes"].get(identity, {}).items():
            previous = result["votes"].setdefault(identity, {}).get(family)
            if previous is not None and previous != answers:
                result["blocked"].add(identity)
                result["errors"].append({"record_id": identity, "slot": family,
                    "error": "The merged output locations contain conflicting family votes.",
                    "existing": {"votes": previous, **result["origins"].get(identity, {}).get(family, {})},
                    "incoming": {"votes": answers, **right["origins"].get(identity, {}).get(family, {})}})
            else:
                result["votes"][identity][family] = answers
                result["origins"].setdefault(identity, {})[family] = right["origins"].get(identity, {}).get(family, {})
    return result
