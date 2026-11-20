"""Resolve explicit RF fanout links only through actual authorized receipts."""

from copy import deepcopy
import json
from pathlib import Path

from .receipts import _receipt, canonical_payload
from intent_training.teacher.dispatch import digest
from intent_training.teacher.rf_cache import rf_decision_hash
from intent_training.teacher.vote_allocation import required_families, rf_quorum_slots


def load_fanout(paths):
    links = {}
    for path in paths:
        path = Path(path)
        if not (path.parent / "report.json").is_file():
            raise ValueError("An RF fanout run is not committed.")
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                item = json.loads(line)
                links[item["record_id"]] = item
    return links


def reuse(collection, prepared, *, claims_dir, repository):
    """Project a proved canonical decision privately; never create vote envelopes."""
    identity = prepared["record_id"]
    link = collection.get("rf_aliases", {}).get(identity)
    if link is None:
        return False
    row = canonical_payload(prepared)
    families = tuple(required_families(prepared))
    if (link["parent_record_id"] != prepared.get("parent_record_id")
            or link["unit_id"] != prepared.get("unit_id") or link["unit"] != prepared.get("unit")
            or tuple(link["required_families"]) != families
            or link["judgment_content_hash"] != rf_decision_hash(row)
            or link["content_sha256"] != digest({"state": row["state"], "questions": row["questions"]})):
        raise ValueError("An RF alias does not match its exact frozen parent unit and decision.")
    canonical = link["canonical_record_id"]
    variant = collection.get("variants", {}).get(canonical, {}).get(link["canonical_record_sha256"])
    if not variant or variant["blocked"]:
        return False
    slots = rf_quorum_slots(row, variant["votes"])
    if not slots:
        return False
    original = canonical_payload(variant["prepared"])
    if digest(original) != link["canonical_record_sha256"] or rf_decision_hash(original) != link["judgment_content_hash"]:
        raise ValueError("An RF canonical receipt has different frozen decision fields.")
    receipts = {}
    for slot in slots:
        origin = variant["origins"][slot]
        batch = collection["batches"][(origin["batch_id"], origin["input_sha256"])]
        if (link.get("canonical_batch_id") and link["canonical_batch_id"] != batch["batch_id"]
                or link.get("canonical_frozen_input_sha256") and link["canonical_frozen_input_sha256"] != batch["input_sha256"]):
            raise ValueError("An RF fanout points to a different frozen canonical batch.")
        cache_key = (batch["batch_id"], batch["input_sha256"], slot, origin["output"])
        receipt_cache = collection.setdefault("authorized_receipt_cache", {})
        if cache_key not in receipt_cache:
            receipt_cache[cache_key] = _receipt(batch, slot, Path(origin["output"]), Path(claims_dir), Path(repository))
        authorized = receipt_cache[cache_key]
        if authorized is None:
            return False
        receipts[slot] = authorized[1]
    collection["votes"][identity] = {slot: variant["votes"][slot] for slot in slots}
    collection["origins"][identity] = {slot: {**variant["origins"][slot], **receipts[slot],
        "canonical_record_id": canonical, "alias_record_id": identity} for slot in slots}
    collection.setdefault("reuse_provenance", {})[identity] = {
        "canonical_record_id": canonical, "canonical_record_sha256": link["canonical_record_sha256"],
        "judgment_content_hash": link["judgment_content_hash"], "receipts": deepcopy(receipts)}
    return True
