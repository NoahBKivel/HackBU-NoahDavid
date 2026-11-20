"""Bound explicit review holds to their actual batch and logical receipt slot."""

import json
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[3] / "results/assembly/receipt-holds.json"
RELABEL_REGISTRY = REGISTRY.with_name("main-relabel-required.json")


def receipt_holds():
    return json.loads(REGISTRY.read_text(encoding="utf-8")) if REGISTRY.exists() else {}


def receipt_held(batch_id, slot, holds):
    return batch_id in holds.get("batch_ids", []) or slot in holds.get("family_slots", {}).get(batch_id, [])


def relabel_requirements():
    return json.loads(RELABEL_REGISTRY.read_text(encoding="utf-8")) if RELABEL_REGISTRY.exists() else {}


def relabel_pending(record, requirements):
    meta = record.get("_meta", {})
    identity = meta.get("main_relabel_parent_record_id", meta.get("record_id", record.get("record_id")))
    if identity not in requirements.get("record_ids", []):
        return False
    proofs = meta.get("main_relabel_vote_origins", {})
    return not meta.get("main_relabel_complete") or any(
        not {"sol", "terra"} <= set(proofs.get(key, {})) for key in requirements.get("questions", []))


def record_held(record, holds):
    meta = record.get("_meta", {})
    stages = [meta.get("teacher_vote_origins", {}), *meta.get("question_pass_origins", {}).values(),
              *meta.get("main_relabel_vote_origins", {}).values()]
    return any(receipt_held(origin.get("batch_id"), slot, holds)
               for origins in stages for slot, origin in origins.items())
