"""Merge objective provenance without losing contradictory visible annotations."""

from collections import defaultdict
from copy import deepcopy
import json
import os

from .cuts import plan_cuts
from .records import stable_id, metadata, prepare_native


def finalize(root, rows=None, cuts=None):
    if rows is None:
        rows = []
        for path in sorted((root / "data" / "converted").glob("*.jsonl")):
            if path.stem.endswith("_bases"):
                continue
            rows.extend(json.loads(line) for line in path.open(encoding="utf-8") if line.strip())
    if cuts is None:
        cuts = plan_cuts(rows)
    merged = {}
    native_rows = {(row["meta"]["source"], row["meta"].get("source_record_id")): row
                   for row in rows if not row["events"] and "native_record" in row["side"]}
    for row, row_cuts in zip(rows, cuts):
        meta = row["meta"]
        for cut in row_cuts:
            k = cut["cut_seq"]
            identity = {"source": meta["source"], "trajectory": meta.get("trajectory_id"),
                        "pair": meta.get("pair_id"), "cut": k,
                        "events": [event for event in row["events"] if event["seq"] <= k]}
            key = stable_id(identity)
            item = merged.setdefault(key, {"objective": set(), "source_labels": [], "provenance": []})
            item["objective"].update(meta.get("objective", []))
            provenance = {field: meta[field] for field in ("source_record_id", "slice", "objective") if field in meta}
            if provenance not in item["provenance"]:
                item["provenance"].append(provenance)
            for label in row["side"].get("source_labels", []):
                if label.get("basis") == "outcome" or int(label["event_seq"]) <= k:
                    if label not in item["source_labels"]:
                        item["source_labels"].append(deepcopy(label))
    conflicts = []
    amended = 0
    for name in ("main", "context", "native"):
        path = root / "data" / "prepared" / f"{name}.jsonl"
        if not path.exists():
            continue
        temporary = path.with_suffix(".jsonl.provenance.tmp")
        with path.open(encoding="utf-8") as source, temporary.open("w", encoding="utf-8", newline="\n") as target:
            for line in source:
                record = json.loads(line)
                meta = record["_meta"]
                if name == "native":
                    original = native_rows.get((meta["source"], meta.get("source_record_id")))
                    if original is None:
                        raise ValueError("Native preparation provenance cannot be recovered.")
                    record = prepare_native(original)
                else:
                    meta["record_kind"] = "screen" if meta.get("form") == "screen" else "task"
                    item = merged.get(meta.get("parent_record_id", record["record_id"]))
                    if item:
                        meta["objective"] = sorted(item["objective"])
                        meta["source_provenance"] = item["provenance"]
                        values = defaultdict(set)
                        for label in item["source_labels"]:
                            if label.get("basis") in {"visible", "V"}:
                                values[label["question"], label.get("event_seq")].add(json.dumps(label["value"]))
                        disagreements = [{"question": question, "event_seq": seq,
                                          "values": [json.loads(value) for value in sorted(labels)]}
                                         for (question, seq), labels in values.items() if len(labels) > 1]
                        if disagreements:
                            meta["source_label_conflicts"] = disagreements
                            meta["blocked_for_source_label_conflict"] = True
                            if name == "main":
                                conflicts.append({"record_id": record["record_id"], "conflicts": disagreements})
                        if name == "main":
                            record["teacher_side"]["source_labels"] = item["source_labels"]
                            amended += int(len(item["provenance"]) > 1)
                        else:
                            meta["merged_cut_source_labels"] = item["source_labels"]
                target.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        os.replace(temporary, path)
    report = {"main_records_with_multiple_provenances": amended, "visible_label_conflicts": conflicts}
    (root / "results" / "preparation" / "provenance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)
    return report
