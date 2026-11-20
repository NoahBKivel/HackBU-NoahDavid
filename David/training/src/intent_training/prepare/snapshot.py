"""Publish complete staged records while a large preparation run continues."""

from collections import Counter
import json
import os


def complete_lines(path):
    """Ignore an incomplete final write and reject malformed completed lines."""
    with path.open("rb") as handle:
        for line in handle:
            if not line.endswith(b"\n"):
                break
            yield json.loads(line), line


def publish(root):
    folder = root / "data" / "prepared"
    main = {row["record_id"]: row for row, _ in complete_lines(folder / "main.jsonl.tmp")}
    contexts = set()
    for row, _ in complete_lines(folder / "context.jsonl.tmp"):
        contexts.add(row["record_id"])
    rf_counts = Counter()
    for row, _ in complete_lines(folder / "requirements.jsonl.tmp"):
        rf_counts[row["parent_record_id"]] += 1
    keep = {key for key, row in main.items() if key in contexts
            and (row["_meta"].get("form") == "screen"
                 or rf_counts[key] == len(row.get("requirement_units", [])))}
    counts, by_source = Counter(), {}
    for name in ("main", "native", "requirements", "context"):
        destination = folder / f"{name}.jsonl"
        temporary = destination.with_suffix(".jsonl.snapshot.tmp")
        with temporary.open("wb") as target:
            for row, raw in complete_lines(folder / f"{name}.jsonl.tmp"):
                parent = row.get("parent_record_id", row["record_id"])
                if name != "native" and parent not in keep:
                    continue
                target.write(raw)
                counts[name] += 1
                source = row.get("source", row.get("_meta", {}).get("source"))
                if source:
                    by_source.setdefault(source, Counter())[name] += 1
        os.replace(temporary, destination)
    report = {"counts": counts, "by_source": by_source, "complete": False,
              "snapshot_kind": "complete_records_from_running_preparation",
              "full_preparation_still_running": True,
              "all_included_RF_parents_complete": True,
              "deferred_incomplete_main_records": len(main) - len(keep),
              "label_authorization": "root_confirmed_sealed_preregistration"}
    destination = root / "results" / "preparation" / "manifest.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
    os.replace(temporary, destination)
    print(json.dumps(report), flush=True)
    return report
