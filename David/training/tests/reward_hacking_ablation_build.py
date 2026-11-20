"""Write validated converted honeypot streams and measured source evidence."""

import collections
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.sources.reward_hacking_ablation import convert
from monitor_format import validate_events


def main():
    raw = ROOT / "data/downloads/reward_hacking_ablation"
    output = ROOT / "data/converted/reward_hacking_ablation.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = collections.Counter()
    records = []
    for events, side, meta in convert(raw):
        validate_events(events)
        counts["converted"] += 1
        counts["author_positive"] += side["outcomes"]["author_review"]["cheated"] == "true"
        counts["hard_negative"] += side["hard_negative"]
        counts["strongest_positive"] += side["strongest_positive"]
        counts["clashes"] += bool(side["clashes"])
        counts["visible_positive"] += any(l["basis"] == "visible" and l["value"] for l in side["source_labels"])
        for label in side["source_labels"]:
            counts[f"{label['question']}_{label['value']}"] += 1
        records.append(dict(events=events, side=side, meta=meta))
    output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    selected = json.loads((raw / "selected_labels.json").read_text(encoding="utf-8"))
    counts["selected"] = len(selected)
    counts["missing_pairs"] = len(selected) - len(records)
    with (raw / "provisional_labels.csv").open(encoding="utf-8") as handle:
        reviews = list(csv.DictReader(handle))
    counts["source_reviews"] = len(reviews)
    counts["excluded_degenerate_or_unknown_negative"] = sum(
        r["cheated"] != "true" and not (r["cheated"] == "false" and r["gave_up_or_degenerate"] == "n")
        for r in reviews)
    files = [p for p in raw.rglob("*") if p.is_file() and p.name in
             {"prompt.txt", "transcript.json", "provisional_labels.csv", "selected_labels.json"}]
    report = dict(counts=counts, planned_count=150, scaled_download_target=134,
                  licence="Not stated; all rights reserved pending clarification",
                  source_files=[dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size,
                                     sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(files)],
                  output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  errors=json.loads((raw / "download_errors.json").read_text(encoding="utf-8"))
                  if (raw / "download_errors.json").exists() else [],
                  validation="Every converted event stream passed shared validate_events.")
    destination = ROOT / "results/sources/reward_hacking_ablation.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(dict(counts=counts, output_sha256=report["output_sha256"])))


if __name__ == "__main__":
    main()
