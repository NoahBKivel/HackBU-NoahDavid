"""Claim one frozen batch and model family without racing another label client."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .dispatch import MODELS, LUNA_MODEL, digest, vote_model, batch_input_hash
from .vote_allocation import rf_quorum_slots
from filelock import FileLock


def teacher_input_hash(record):
    """Hash every field in the actual model-visible record, without implicit exclusions."""
    return digest(record)


def claim_path(directory, batch_id, family, input_sha256):
    """Return the stable key shared by API and collaboration dispatchers."""
    if family not in {"sol", "terra"}:
        raise ValueError("The teacher family must be sol or terra.")
    identity = digest({"batch_id": batch_id, "model_family": family, "input_sha256": input_sha256})
    return Path(directory) / f"{identity}.json"


def claim_batch(directory, batch, family, owner):
    """Return a new atomic claim, or None when an owner has already reserved the call."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = claim_path(directory, batch["batch_id"], family, batch["input_sha256"])
    payload = {"batch_id": batch["batch_id"], "model_family": family,
               "input_sha256": batch["input_sha256"], "owner": owner, "status": "claimed",
               "record_ids": [row["record_id"] for row in batch["records"]],
               "claimed_at": datetime.now(timezone.utc).isoformat()}
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return None
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    return payload


def complete_claim(directory, batch, family, owner, vote_output):
    """Mark a call completed only for its original owner after output validation."""
    path = claim_path(directory, batch["batch_id"], family, batch["input_sha256"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["owner"] != owner or payload["status"] != "claimed":
        raise ValueError("Only the current claim owner can complete the vote call.")
    payload.update(status="completed", vote_output=str(vote_output),
                   completed_at=datetime.now(timezone.utc).isoformat())
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return payload


def batch_claim_path(directory, batch):
    """Return one ownership file for the complete logical batch."""
    return Path(directory) / ("batch_" + digest({"batch_id": batch["batch_id"],
            "input_sha256": batch["input_sha256"]}) + ".json")


def validated_rf_slots(directory, batch, claim):
    """Find completed RF slots backed by exact receipts and validated full outputs."""
    from .dispatch import validate_vote
    from intent_training.assemble.receipts import _receipt
    rows = batch.get("records", [])
    if not rows:
        return ()
    try:
        for row in rows:
            rf_quorum_slots(row, ())
    except ValueError:
        return ()
    valid = []
    for slot in rf_quorum_slots(rows[0], claim.get("families", {})):
        receipt = claim["families"][slot]
        if receipt.get("status") != "completed" or not receipt.get("vote_output"):
            continue
        try:
            output = Path(receipt["vote_output"])
            authorization = _receipt(batch, slot, output, Path(directory), Path.cwd())
            if authorization is None:
                continue
            text = output.read_text(encoding="utf-8")
            votes = json.loads(text) if text.lstrip().startswith("[") else [json.loads(line) for line in text.splitlines() if line.strip()]
            ids = [vote["record_id"] for vote in votes]
            if len(ids) != len(rows) or set(ids) != {row["record_id"] for row in rows}:
                continue
            for vote in votes:
                validate_vote(vote, authorization[0], slot)
            valid.append(slot)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return rf_quorum_slots(rows[0], valid)


def claim_batch_once(directory, batch, owner, required_families, *, legacy_quiescent=False):
    """Atomically own all required votes, preserving unresolved legacy ownership."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    families = tuple(sorted(set(required_families)))
    if not families or not set(families) <= {"sol", "terra"}:
        raise ValueError("A batch requires supported teacher families.")
    if batch_input_hash(batch) != batch["input_sha256"]:
        raise ValueError("The logical batch differs from its frozen hash.")
    path = batch_claim_path(directory, batch)
    with FileLock(str(path) + ".lock"):
        if path.exists():
            return None
        legacy = {}
        for family in families:
            old = claim_path(directory, batch["batch_id"], family, batch["input_sha256"])
            if old.exists():
                value = json.loads(old.read_text(encoding="utf-8"))
                if value.get("owner") != owner or not legacy_quiescent:
                    return None
                legacy[family] = value
        payload = {"batch_id": batch["batch_id"], "input_sha256": batch["input_sha256"],
                   "owner": owner, "status": "claimed", "required_families": list(families),
                   "record_ids": [row["record_id"] for row in batch["records"]],
                   "claimed_at": datetime.now(timezone.utc).isoformat(),
                   "families": {family: {"status": "pending"} for family in families}}
        for family, value in legacy.items():
            payload["families"][family]["legacy_claim"] = str(claim_path(
                directory, batch["batch_id"], family, batch["input_sha256"]))
            if value.get("status") == "completed":
                payload["families"][family].update(status="completed", vote_output=value["vote_output"],
                                                  completed_at=value["completed_at"])
        if all(value["status"] == "completed" for value in payload["families"].values()):
            payload["status"] = "completed"
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        return payload


def finish_family(directory, batch, owner, family, vote_output, *, actual_model=None):
    """Complete one validated family in the same batch ownership file."""
    path = batch_claim_path(directory, batch)
    with FileLock(str(path) + ".lock"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["owner"] != owner or family not in payload["required_families"]:
            raise ValueError("Only the batch owner may finish a required family.")
        actual_model = actual_model or batch.get("model_overrides", {}).get(family, MODELS[family])
        checked = dict(batch, model_overrides={**batch.get("model_overrides", {}), family: actual_model})
        vote_model(checked, family)
        payload["families"][family].update(status="completed", vote_output=str(vote_output),
                                          completed_at=datetime.now(timezone.utc).isoformat(),
                                          vote_slot=family, actual_model=actual_model)
        if actual_model in {MODELS["terra"], LUNA_MODEL}:
            payload["families"][family]["model_policy"] = "Owner instruction authorizes the actual teacher model."
        if all(value["status"] == "completed" for value in payload["families"].values()):
            payload.update(status="completed", completed_at=datetime.now(timezone.utc).isoformat())
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)
        return payload


_QUEUE_OFFSETS = {}


def delegate_family(directory, batch, owner, family, delegate, *, quiescent=False):
    """Reserve one quiescent pending slot for a delegate without changing its owner."""
    if not quiescent or batch_input_hash(batch) != batch["input_sha256"]:
        raise ValueError("Delegation requires quiescent ownership and the canonical input.")
    path = batch_claim_path(directory, batch)
    with FileLock(str(path) + ".lock"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["owner"] != owner or family not in payload["required_families"]:
            raise ValueError("Only the current owner may delegate its required slot.")
        slot = payload["families"][family]
        if slot["status"] != "pending" or slot.get("delegated_to") not in {None, delegate}:
            return None
        slot.update(delegated_to=delegate, delegated_at=datetime.now(timezone.utc).isoformat())
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)
        from .queue_index import request_rescan
        request_rescan(directory)
        return slot


def claim_next(queue_path, directory, owner, allowed_allocations=("paired",), *, resume_owned=False,
               allowed_passes=None, excluded_questions=(), actual_model_override=None):
    """Claim the next appended canonical batch without writing prompts or record claims."""
    queue_path = Path(queue_path)
    if actual_model_override not in {None, MODELS["terra"], LUNA_MODEL}:
        raise ValueError("The requested teacher model is not authorized.")
    if not queue_path.exists():
        return None
    from .queue_index import refresh_index, read_batch, rescan_epoch
    state = refresh_index(queue_path, directory)
    key = (str(queue_path.resolve()), owner, state["generation"], rescan_epoch(directory),
           tuple(sorted(allowed_allocations)), tuple(sorted(allowed_passes)) if allowed_passes is not None else None,
           tuple(sorted(excluded_questions)), actual_model_override)
    with Path(state["index"]).open("rb") as handle:
        handle.seek(_QUEUE_OFFSETS.get(key, 0))
        while True:
            start = handle.tell()
            line = handle.readline()
            if not line:
                return None
            if not line.endswith(b"\n"):
                _QUEUE_OFFSETS[key] = start
                return None
            _QUEUE_OFFSETS[key] = handle.tell()
            if not line.strip():
                continue
            meta = json.loads(line)
            if meta.get("allocation") not in allowed_allocations:
                continue
            if allowed_passes is not None and meta["pass"] not in allowed_passes:
                continue
            if set(meta["question_bases"]) & set(excluded_questions):
                continue
            families = meta["required_families"]
            existing_path = batch_claim_path(directory, meta)
            if existing_path.exists():
                try:
                    existing = json.loads(existing_path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    continue
                if not (resume_owned and existing.get("owner") == owner and existing.get("status") == "claimed"):
                    continue
            elif any(claim_path(directory, meta["batch_id"], family, meta["input_sha256"]).exists() for family in families):
                continue
            item = read_batch(queue_path, meta)
            if existing_path.exists() and validated_rf_slots(directory, item["batch"], existing):
                continue
            claim = claim_batch_once(directory, item["batch"], owner, families)
            if claim is None and resume_owned:
                path = batch_claim_path(directory, item["batch"])
                if path.exists():
                    existing = json.loads(path.read_text(encoding="utf-8"))
                    if existing.get("owner") == owner and existing.get("status") == "claimed":
                        claim = existing
            if claim is not None:
                batch = dict(item["batch"])
                actual = actual_model_override or MODELS["terra"]
                batch["model_overrides"] = {**batch.get("model_overrides", {}), "sol": actual}
                if actual == LUNA_MODEL:
                    batch["model_overrides"]["terra"] = actual
                effective = families
                try:
                    if batch["records"]:
                        for row in batch["records"]:
                            rf_quorum_slots(row, ())
                        effective = ["sol"] if "sol" in families else ["terra"]
                except ValueError:
                    pass
                return dict(item, batch=batch, claim=claim, required_families=effective)
