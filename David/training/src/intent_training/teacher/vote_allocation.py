"""Choose the owner-prescribed teacher families from private source provenance."""

import json
from pathlib import Path

POLICY = json.loads(Path(__file__).with_name("vote_policy.json").read_text(encoding="utf-8"))


def allocation(record):
    """Return paired or single_sol; never expose this control data to the teacher."""
    meta = record.get("parent_meta") or record.get("_meta") or record.get("meta") or record
    side = record.get("side", {})
    construction = meta.get("construction") or meta.get("construction_type") or side.get("construction")
    if construction or meta.get("record_kind") == "construction":
        return "single_sol"
    source = meta.get("source", record.get("source", ""))
    section = str(meta.get("slice", record.get("slice", ""))).lower().replace("-", "_")
    if section in POLICY["single_slices"]:
        return "single_sol"
    if source in POLICY["construction_types"]:
        return "single_sol"
    if source in POLICY["paired_sources"]:
        return "paired"
    if source in POLICY["single_sources"]:
        return "single_sol"
    if source in POLICY["paired_slices"]:
        if section in POLICY["paired_slices"][source]:
            return "paired"
        if section:
            raise ValueError(f"No vote allocation is declared for source {source} slice {section}.")
        raise ValueError(f"Source {source} requires its private source slice for vote allocation.")
    labels = side.get("source_labels") or meta.get("merged_cut_source_labels", ())
    bases = meta.get("label_bases", ())
    if "V" in bases or "visible" in bases or (labels and all(x.get("basis") in {"V", "visible"} for x in labels)):
        return "single_sol"
    raise ValueError(f"No vote allocation is declared for source {source}.")


def required_families(record):
    """Return exactly the teachers required for this record and inherited diagnostics."""
    return ("sol", "terra") if allocation(record) == "paired" else ("sol",)


def rf_quorum_slots(record, available):
    """Return all available RF slots when the owner's single-vote quorum is met."""
    if (record.get("pass") != "requirements" or record.get("purpose") != "requirement_selection"
            or set(record.get("questions", {})) != {"RF"}):
        raise ValueError("The single-vote quorum applies only to requirement selection RF.")
    slots = set(available)
    if not slots <= {"sol", "terra"}:
        raise ValueError("Unsupported vote slot.")
    return tuple(slot for slot in ("sol", "terra") if slot in slots)
