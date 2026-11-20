"""Select complete admitted groups and bind training gates to immutable bytes."""

from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .balance import balance_cap
from .instruments import policy_instruments
from .freeze_groups import composition_kind, exact_groups, joint_groups
from .native import original_native
from .quality import receipt_holds, record_held
from .siblings import pack_siblings
from intent_training.splits.freeze import build_manifest, _serialized
from intent_training.splits.grouping import grouped_records
from intent_training.splits.reservations import load_reservations, reserved


def file_reference(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def read_rows(path):
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def select_records(records, *, composition, preregistration, seed):
    """Exclude held and reserved groups before choosing the declared composition."""
    identities = [row.get("_meta", {}).get("record_id", row.get("record_id")) for row in records]
    if any(not identity for identity in identities) or len(set(identities)) != len(identities):
        raise ValueError("Every admitted training line needs a unique stable record identifier.")
    holds, reservations = receipt_holds(), load_reservations()
    eligible, excluded = [], Counter()
    for group in grouped_records(records).values():
        if any(record_held(row, holds) for row in group):
            excluded["receipt_hold_lines"] += len(group)
        elif any(reserved(row, reservations) for row in group):
            excluded["dev_reserved_lines"] += len(group)
        else:
            eligible.append(group)
    selected = joint_groups(eligible, composition=composition,
                            floors=preregistration["floors"], seed=seed)
    selected = deepcopy(selected)
    for record in selected:
        record["_meta"]["record_kind"] = composition_kind(record)
    return selected, {"excluded": dict(excluded), "selected_lines": len(selected),
                      "source_quotas": composition.get("source_quotas", {})}


def receipt_instruments(records):
    """Read actual logical-slot receipts for every selected question and pass."""
    files, joined, cache = {}, {}, {}
    for record in records:
        if original_native(record):
            continue
        meta = record["_meta"]
        identity = meta["record_id"]
        parent = identity.split(":sibling:", 1)[0]
        stages = [meta.get("teacher_vote_origins", {}), *meta.get("question_pass_origins", {}).values()]
        answers = {}
        for stage in stages:
            for slot, origin in stage.items():
                path = Path(origin["output"])
                if path not in cache:
                    files[str(path)] = file_reference(path)
                    raw_votes = path.read_text(encoding="utf-8-sig")
                    try:
                        parsed = json.loads(raw_votes)
                        cached_rows = parsed if isinstance(parsed, list) else [parsed]
                    except json.JSONDecodeError:
                        cached_rows = [json.loads(line) for line in raw_votes.splitlines() if line.strip()]
                    cache[path] = [vote for item in cached_rows for vote in (item if isinstance(item, list) else [item])]
                matches = [vote for vote in cache[path] if vote.get("record_id") == parent
                           and vote.get("batch_id") == origin["batch_id"]
                           and vote.get("input_sha256") == origin["input_sha256"]
                           and vote.get("vote_slot", vote.get("model_family")) == slot]
                if not matches:
                    raise ValueError("A selected receipt origin has no matching actual vote envelope.")
                for vote in matches:
                    for key, value in vote["votes"].items():
                        if key not in record["questions"]:
                            continue
                        previous = answers.setdefault(key, {}).get(slot)
                        if previous is not None and previous != value:
                            raise ValueError("A selected question has conflicting actual receipt votes.")
                        answers[key][slot] = value
        joined[identity] = answers
    return policy_instruments(records, joined), list(files.values())


def prepare_freeze(records, *, preregistration, composition, fits, scanner, input_paths,
                   seed, base_dev=(), dev_topup=(), teacher_fallbacks=None, source_plan=None):
    """Measure gates on the selected, capped, actually fitted training lines."""
    if preregistration.get("status") != "sealed" or preregistration.get("blockers"):
        raise ValueError("The positive expectation plan must already be sealed.")
    selected, selection = select_records(records, composition=composition,
                                         preregistration=preregistration, seed=seed)
    selected, balance = balance_cap(selected, seed=seed)
    for record in selected:
        if len(pack_siblings(record, fits=fits)) != 1 or not fits(record):
            raise ValueError("A selected capped line no longer passes the actual encoder fit test.")
        meta = record["_meta"]
        if not meta.get("licence") or not meta.get("source"):
            raise ValueError("Every selected line needs its original source and licence provenance.")
        if not original_native(record) and not meta.get("teacher_vote_origins"):
            raise ValueError("Every selected monitor line needs its actual teacher origins.")
        if meta.get("record_kind") == "screen" and meta.get("construction") != "overflow_screen":
            raise ValueError("The screen allocation requires explicit overflow-screen construction provenance.")
    instruments, receipts = receipt_instruments(selected)
    splits = {"train": selected}
    if base_dev:
        splits["base_dev"] = list(base_dev)
    if dev_topup:
        splits["dev_topup"] = list(dev_topup)
    manifest = build_manifest(splits, preregistration=preregistration, instruments=instruments,
        balance_metrics=balance, scanner=scanner, input_paths=input_paths,
        composition=composition, teacher_fallbacks=teacher_fallbacks)
    manifest.update(selection=selection, receipt_inputs=receipts,
                    code_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip())
    if not composition.get("source_quotas") or not composition.get("allocation_evidence"):
        manifest["failures"].append("source_allocation_evidence")
    if not composition.get("replay_quotas"):
        manifest["failures"].append("native_replay_suite_allocation")
    manifest["native_replay_suites"] = dict(Counter(
        row["_meta"].get("suite", row["_meta"]["source"])
        for row in selected if original_native(row)))
    if source_plan is None:
        manifest["failures"].append("source_basis_plan")
    else:
        known = {entry.get("source", entry.get("id")) for entry in source_plan["sources"]
                 if entry.get("kind") and entry.get("objective") is not None}
        missing = {row["_meta"]["source"] for row in selected if not original_native(row)} - known
        manifest["failures"].extend("source_basis:" + source for source in sorted(missing))
    manifest["passed"] = not manifest["failures"]
    return splits, manifest


def publish_freeze(splits, manifest, directory, *, authorized=False):
    """Publish the complete private directory atomically after rechecking evidence."""
    if not authorized:
        raise PermissionError("The root orchestrator must explicitly authorize the freeze.")
    if not manifest.get("passed"):
        raise ValueError("All required training data gates must pass before publication.")
    for path, reference in manifest["inputs"].items():
        if file_reference(path)["sha256"] != reference["sha256"]:
            raise ValueError("A source input changed after the data gates ran.")
    for reference in manifest["receipt_inputs"]:
        if file_reference(reference["path"])["sha256"] != reference["sha256"]:
            raise ValueError("A teacher receipt changed after the data gates ran.")
    if any(record_held(row, receipt_holds()) or reserved(row, load_reservations())
           for row in splits["train"]):
        raise ValueError("A selected training group is held or dev reserved.")
    destination = Path(directory)
    if destination.exists():
        raise FileExistsError("Frozen artifacts cannot be overwritten.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".freeze-", dir=destination.parent))
    for name, rows in splits.items():
        raw = _serialized(rows)
        if hashlib.sha256(raw).hexdigest() != manifest["outputs"][name]["sha256"]:
            raise ValueError("The selected rows changed after the data gates ran.")
        path = staging / (name + ".jsonl")
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["outputs"][name]["sha256"]:
            raise ValueError("The frozen file bytes differ from the gated digest.")
    raw = (json.dumps(manifest, sort_keys=True, ensure_ascii=False) + "\n").encode()
    (staging / "manifest.json").write_bytes(raw)
    staging.rename(destination)
    return {"train": str((destination / "train.jsonl").resolve()),
            "sha256": manifest["outputs"]["train"]["sha256"],
            "training_lines": manifest["record_counts"]["train"],
            "manifest": str((destination / "manifest.json").resolve()),
            "manifest_sha256": hashlib.sha256(raw).hexdigest()}
