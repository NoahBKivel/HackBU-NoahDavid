"""Exact auxiliary RF decision reuse with original parent/unit provenance."""

from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from .dispatch import digest, encoded
from .vote_allocation import rf_quorum_slots


def snapshot_input(source, folder):
    """Capture one complete input before inspecting or publishing its records."""
    source, folder = Path(source), Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / ("capture-" + uuid4().hex + ".tmp")
    fingerprint = sha256()
    with source.open("rb") as src, temporary.open("wb") as dst:
        while chunk := src.read(1024 * 1024):
            fingerprint.update(chunk)
            dst.write(chunk)
    value = fingerprint.hexdigest()
    frozen = folder / (value + ".jsonl")
    if frozen.exists():
        temporary.unlink()
    else:
        temporary.replace(frozen)
    return frozen, value


def rf_decision_hash(row):
    """Hash the complete visible RF judgment, excluding only its output ID."""
    if (row.get("pass") != "requirements"
            or row.get("purpose") != "requirement_selection"
            or set(row.get("questions", {})) != {"RF"}):
        raise ValueError("Only auxiliary requirement-selection RF may use this cache.")
    return digest({key: value for key, value in row.items() if key != "record_id"})


def _queued_canonicals(queue, claims_directory):
    from .claims import batch_claim_path
    result = {}
    if not queue.exists():
        return result
    with queue.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.endswith("\n"):
                break
            task = json.loads(line)
            batch = task["batch"]
            if batch.get("pass") != "requirements" or batch.get("instruction_supplement"):
                continue
            families = tuple(task["required_families"])
            try:
                claim = json.loads(batch_claim_path(claims_directory, batch).read_text(encoding="utf-8"))
                receipts = [claim.get("families", {}).get(slot, {}) for slot in families]
                complete = any(item.get("status") == "completed" for item in receipts)
                completed_at = max(item.get("completed_at", "") for item in receipts)
            except (OSError, ValueError):
                complete, completed_at = False, ""
            for row in batch["records"]:
                if row.get("purpose") != "requirement_selection":
                    continue
                rf_quorum_slots(row, families)
                key = rf_decision_hash(row)
                rank = (not complete, completed_at or "9999", row["record_id"], batch["input_sha256"])
                candidate = {"canonical_record_id": row["record_id"],
                             "canonical_record_sha256": digest(row),
                             "canonical_batch_id": batch["batch_id"],
                             "canonical_frozen_input_sha256": batch["input_sha256"],
                             "rank": rank}
                if key not in result or rank < result[key]["rank"]:
                    result[key] = candidate
    return result


def deduplicate_rf(source, queue, output_root, *, visible, required_families, claims_directory):
    """Reuse compatible queued decisions; stage new canonical inputs and all aliases.

    Completed claim metadata only prioritizes candidates. Consumers must validate
    the actual canonical model receipts before resolving any alias.
    """
    source, queue, output_root = Path(source), Path(queue), Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    frozen, source_hash = snapshot_input(source, output_root / "inputs")
    output = output_root / (source_hash[:16] + "-" + uuid4().hex[:8])
    output.mkdir()
    canonical = _queued_canonicals(queue, Path(claims_directory))
    unique = output / "requirements_unique.jsonl"
    fanout = output / "requirements_fanout.jsonl"
    counts = {"original": 0, "new_canonical": 0, "queued_reuse_candidates": 0,
              "within_run_duplicates": 0}
    new_keys = set()
    with frozen.open(encoding="utf-8") as src, unique.with_suffix(".tmp").open("w", encoding="utf-8") as dst, fanout.with_suffix(".tmp").open("w", encoding="utf-8") as links:
        for line in src:
            original = json.loads(line)
            row = visible(original)
            families = tuple(required_families(original))
            fingerprint = rf_decision_hash(row)
            rf_quorum_slots(row, families)
            key = fingerprint
            candidate = canonical.get(key)
            if candidate is None:
                candidate = {"canonical_record_id": row["record_id"],
                             "canonical_record_sha256": digest(row),
                             "canonical_batch_id": None,
                             "canonical_frozen_input_sha256": None}
                canonical[key] = candidate
                new_keys.add(key)
                dst.write(encoded(original) + "\n")
                counts["new_canonical"] += 1
            elif key in new_keys:
                counts["within_run_duplicates"] += 1
            else:
                counts["queued_reuse_candidates"] += 1
            alias = {field: original[field] for field in ("record_id", "parent_record_id", "unit_id", "unit")}
            alias.update({field: value for field, value in candidate.items() if field != "rank"})
            alias.update(judgment_content_hash=fingerprint,
                         content_sha256=digest({"state": row["state"], "questions": row["questions"]}),
                         required_families=list(families),
                         source_snapshot_sha256=source_hash)
            links.write(encoded(alias) + "\n")
            counts["original"] += 1
    unique.with_suffix(".tmp").replace(unique)
    fanout.with_suffix(".tmp").replace(fanout)
    report = {"counts": counts, "source_snapshot": str(frozen), "source_sha256": source_hash,
              "unique_input": str(unique), "fanout": str(fanout),
              "decision_key": "all frozen visible fields except record_id; single requirement-selection vote"}
    (output / "report.json").write_text(encoded(report) + "\n", encoding="utf-8")
    return report
