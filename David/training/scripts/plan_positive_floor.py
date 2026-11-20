"""Snapshot source capacities and write the positive expectation preregistration."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from intent_training.assemble.positive_plan import distribute, is_positive, preregister


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _measure(entry):
    path = ROOT / "data" / "converted" / (entry["source"] + ".jsonl")
    counts, labels, total, incomplete = Counter(), Counter(), 0, False
    if not path.exists():
        return {"count": 0, "positive_counts": {}, "label_counts": {}, "path": str(path.relative_to(ROOT))}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for raw in handle:
            digest.update(raw)
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                incomplete = True
                break
            meta = row.get("meta", {})
            assigned_slice = meta.get("slice")
            if entry.get("capacity_slice_priority"):
                eligible = meta.get(entry["capacity_slice_field"], [])
                assigned_slice = next((name for name in entry["capacity_slice_priority"] if name in eligible), None)
            if entry.get("capacity_objective"):
                if set(meta.get("objective", [])) != set(entry["capacity_objective"]):
                    continue
                assigned_slice = entry.get("slice")
            if entry.get("slice") is not None and assigned_slice != entry["slice"]:
                continue
            total += 1
            positive = set()
            for label in row.get("side", {}).get("source_labels", []):
                if str(label.get("basis", "")).lower() not in {"v", "visible", "rule"}:
                    continue
                question = label["question"]
                labels[question] += 1
                if is_positive(question, label.get("value")):
                    positive.add(question)
            counts.update(positive)
    return {"count": total, "positive_counts": dict(counts), "label_counts": dict(labels),
            "path": str(path.relative_to(ROOT)), "sha256": digest.hexdigest(), "incomplete_snapshot": incomplete}


def main():
    """Write reproducible evidence, plan and source counts from the current files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--task-records", type=int)
    parser.add_argument("--omit-part", action="append", default=[])
    parser.add_argument("--capacity-snapshot", type=Path)
    parser.add_argument("--output-name", default="positive-plan")
    parser.add_argument("--save-input", type=Path)
    args = parser.parse_args()
    config = _read(args.input)
    if args.task_records is not None:
        config["task_records"] = args.task_records
    config["entries"] = [entry for entry in config["entries"] if entry["part"] not in args.omit_part]
    snapshot = _read(args.capacity_snapshot) if args.capacity_snapshot else None
    historical = {entry["id"]: entry["evidence"] for entry in snapshot["sources"]} if snapshot else {}
    if snapshot:
        config["amendment"] = {"prior_preregistration_sha256": hashlib.sha256(args.capacity_snapshot.read_bytes()).hexdigest(),
                               "task_records": config["task_records"], "omitted_parts": args.omit_part,
                               "positive_share_policy": "Original preteacher reference fractions remain fixed.",
                               "teacher_calls_at_original_share_seal": config.pop("teacher_calls_at_seal", None),
                               "capacity_snapshot_at": snapshot["created_at"]}
    entries = config["entries"]
    scale = Fraction(config["task_records"], config["raw_task_total"])
    task_weights = {e["id"]: Fraction(str(e["effective_nplan"])) for e in entries if e["part"] == "task"}
    quotas = distribute(config["task_records"], task_weights)
    blockers = list(config.get("blockers", []))
    if sum(task_weights.values()) != config["raw_task_total"]:
        blockers.append("The raw task quotas do not close to the declared raw total.")
    for entry in entries:
        entry["evidence"] = historical[entry["id"]] if snapshot else (_measure(entry) if entry["kind"] != "construction" else entry.get("evidence", {"count": 0}))
        entry["planned_quota"] = quotas.get(entry["id"], int(Fraction(str(entry["effective_nplan"]))))
        entry["available_count"] = entry["evidence"]["count"]
        entry["capacity_shortfall"] = max(0, entry["planned_quota"] - entry["available_count"])
        if entry["kind"] == "dataset_visible" and entry.get("fixed_evidence"):
            entry["positive_shares"] = entry["fixed_evidence"]["positive_shares"]
        elif entry["kind"] == "dataset_visible":
            denominator = entry["evidence"]["count"]
            entry["positive_shares"] = {q: str(Fraction(n, denominator)) for q, n in entry["evidence"]["positive_counts"].items()} if denominator else {}
            if not denominator and not entry.get("blocked"):
                entry["evidence_fixed"] = False
        elif entry["kind"] != "construction":
            entry["positive_shares"] = {}
    if args.save_input:
        args.save_input.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    plan = preregister(entries, scale=scale, blockers=blockers)
    plan["created_at"] = datetime.now(timezone.utc).isoformat()
    plan["parts"] = {part: sum(e["planned_quota"] for e in entries if e["part"] == part) for part in ("task", "replay", "long", "screen")}
    plan["planned_total"] = sum(plan["parts"].values())
    plan["input_sha256"] = hashlib.sha256((args.save_input or args.input).read_bytes()).hexdigest()
    for key in ("allocation", "share_seal_at", "teacher_calls_at_seal", "composition_status", "amendment"):
        if key in config:
            plan[key] = config[key]
    target = ROOT / "results" / (args.output_name + ".json")
    target.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Training Data Report", "", f"The positive expectation plan is **{plan['status']}** as of {plan['created_at']}.",
             "No teacher observations enter this calculation. These are planned expectations and measured capacities, not a passed data gate.", "",
             f"The task scale is exactly {scale}. The planned training total is {plan['planned_total']} records: " + ", ".join(f"{part} {count}" for part, count in plan["parts"].items()) + ".", "",
             "P_q is the sum of s times each effective raw task quota times its fixed positive share. Replay, long-document and screen counts use their unscaled quotas. Teacher sources, generated responses and agent-run sources contribute zero. Dataset V shares use natural kept record counts with at least one positive row for that question; unit-label counts are recorded separately. G1 false is positive. G2 broken and not done are positive.", "",
             "Goal-flip pairs occupy 300 raw planned records inside the 1,750-record user-intent objective. The other sources in that objective have their raw quotas multiplied by 29/35, leaving 1,450; adding the 300 goal-flip records restores 1,750. The total raw task quota remains 10,630. The table's raw nplan column shows nominal quotas before this carve; effective nplan is the disjoint quota used in every calculation. This allocation is separate from capacity redistribution.", ""]
    if plan["blockers"]:
        lines += ["The following facts prevent a seal:", ""] + [f"- {reason}" for reason in plan["blockers"]] + [""]
    if snapshot:
        lines += ["The owner's scope amendment reallocates the removed 400 long-document records to task records. The task count is now 9,000, replay remains 3,000, screen remains 200, and the total remains 12,200. Original reference fractions are unchanged; no teacher labels were read. Available counts below are historical capacities from " + snapshot["created_at"] + ", rather than a fresh data scan. The prior sealed artifacts remain unchanged.", ""]
    incomplete = [entry["id"] for entry in entries if entry["evidence"].get("incomplete_snapshot")]
    if incomplete:
        lines += ["Concurrent source writes left incomplete JSONL snapshots for " + ", ".join(incomplete) + ". Their available counts include only complete records before the interrupted line; no completion or data gate is claimed.", ""]
    lines += ["| Question | Expected positives P_q | Required training positives |", "|---|---:|---:|"]
    for question, floor in plan["floors"].items():
        lines.append(f"| {question} | {plan['expected'][question]:.6f} | {floor:.6f} |")
    lines += ["", "SCR, M8, D1, D3 and D2 are reported rather than positive-floor gates. L7 and D5 do not have a binary positive-floor class. Their observed distributions remain due at freeze.", "",
              "| Source or slice | Part | Raw nplan | Effective nplan | Planned quota | Available | Shortfall | Positive shares |", "|---|---|---:|---:|---:|---:|---:|---|"]
    for entry in entries:
        shares = ", ".join(f"{q}={v}" for q, v in sorted(entry.get("positive_shares", {}).items())) or "0"
        lines.append(f"| {entry['id']} | {entry['part']} | {entry['raw_nplan']} | {entry['effective_nplan']} | {entry['planned_quota']} | {entry['available_count']} | {entry['capacity_shortfall']} | {shares} |")
    lines += ["", "The following reference populations fix dataset V shares before teacher calls. Later downloads change available capacity while these shares stay fixed.", "",
              "| Source or slice | Reference kept records | Positive records by question | Converted-file SHA256 |", "|---|---:|---|---|"]
    for entry in entries:
        evidence = entry.get("fixed_evidence")
        if evidence:
            lines.append(f"| {entry['id']} | {evidence['population_count']} | {json.dumps(evidence['positive_counts'], sort_keys=True)} | {evidence.get('sha256')} |")
    lines += ["", "Counts are exact finite-file counts, so sampling confidence intervals do not apply. They do not estimate deployment prevalence. The machine-readable snapshot records the converted-file SHA256 and per-question V counts. Capacity shortfalls do not authorize changing fixed composition or moving a quota between objectives.", "",
              "Terminal-bench-science stores eligibility lists rather than duplicated slice records. Each benign-eligible stream is counted once in benign; every other claim-eligible stream is counted in claim. The source total therefore counts distinct streams once.", "",
              "No redistribution is claimed complete unless its donor, recipient and exact objective-preserving allocation appear in the machine-readable plan. Data availability, positive-label resolution, teacher agreement, cannot-tell rates, pair integrity, secrets scans and final counts remain separate checks.", "",
              "Evidence: `" + str(target.relative_to(ROOT)).replace("\\", "/") + "`, `" + str(args.save_input or args.input).replace("\\", "/") + "`, `results/sources/*.json`, and the converted paths and hashes recorded in the snapshot."]
    sealed = target if args.output_name != "positive-plan" else ROOT / "results" / "positive-plan-sealed.json"
    if sealed.exists():
        matching_input = str(args.save_input).replace("\\", "/") if args.save_input else "results/positive-plan-sealed-input.json"
        lines += ["", "The immutable positive-share preregistration is `" + str(sealed.relative_to(ROOT)).replace("\\", "/") + "`, SHA256 `" + hashlib.sha256(sealed.read_bytes()).hexdigest() + "`. Its matching input is `" + matching_input + "`. Capacity refreshes preserve its reference populations and positive shares."]
    (ROOT / "reports" / "DATA-REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": plan["status"], "parts": plan["parts"], "blockers": plan["blockers"], "floors": plan["floors"]}))


if __name__ == "__main__":
    main()
