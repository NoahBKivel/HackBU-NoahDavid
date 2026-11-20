"""Preserve WildFeedback reply prefixes with subsequent feedback kept aside."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

from monitor_format import validate_events

from .events import instruction, message


def _rows(raw_dir):
    for path in sorted(raw_dir.glob("rows-*.json")):
        yield from json.loads(path.read_bytes())["rows"]


def convert(raw_dir: Path):
    """Yield every ordered assistant prefix without its following user turn."""
    rows = list(_rows(raw_dir))
    events = []
    conversation = None
    expected = 0
    for index, item in enumerate(rows):
        row = item["row"]
        utterance = row["UtterranceId"]
        if utterance == 0:
            conversation = item["row_idx"]
            events = []
            expected = 0
        if conversation is None or utterance != expected:
            raise ValueError("The source conversation is incomplete or unordered.")
        expected += 1
        text = row["Content"]
        if not isinstance(text, str) or not text:
            raise ValueError("Source utterances require nonempty text.")
        if row["Role"] == "User":
            events.append(instruction(text, len(events) + 1))
            continue
        if row["Role"] != "Agent" or not events:
            raise ValueError("The source role or initial instruction is invalid.")
        events.append(message(text, len(events) + 1))
        side = {"reasoning": {}, "source_labels": [], "licence": "ODC-By"}
        if index + 1 < len(rows):
            following = rows[index + 1]["row"]
            if following["Role"] == "User" and following["UtterranceId"] == utterance + 1:
                side["outcomes"] = {"feedback": {
                    "basis": "outcome", "origin": "source GPT-4o annotation",
                    "next_user_text": following["Content"],
                    **{key: following[key] for key in (
                        "Satisfaction", "Satisfaction-Justificiation", "Disatisfaction",
                        "Dissatisfaction-Justificiation", "State") if key in following},
                }}
        meta = {
            "source": "wildfeedback", "source_record_id": f"sat_dsat_annotation:train:{item['row_idx']}",
            "trajectory_id": f"sat_dsat_annotation:train:{conversation}",
            "objective": ["M1", "G1"], "licence": "ODC-By", "harness": "WildChat",
            "cut_seq": events[-1]["seq"],
        }
        validate_events(events)
        yield list(events), side, meta


def main():
    """Download bounded ordered pages or convert and count the saved pages."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--limit", type=int, default=330)
    args = parser.parse_args()
    raw = Path("data/downloads/wildfeedback")
    raw.mkdir(parents=True, exist_ok=True)
    if args.download:
        for offset in range(0, 800, 100):
            url = ("https://datasets-server.huggingface.co/rows?dataset=microsoft/WildFeedback"
                   f"&config=sat_dsat_annotation&split=train&offset={offset}&length=100")
            (raw / f"rows-{offset:04d}.json").write_bytes(urlopen(url, timeout=45).read())
    output = Path("data/converted/wildfeedback.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    trajectories = set()
    with output.open("w", encoding="utf-8") as handle:
        for events, side, meta in convert(raw):
            if counts["output_records"] >= args.limit:
                break
            validate_events(events)
            handle.write(json.dumps(dict(events=events, side=side, meta=meta), ensure_ascii=False) + "\n")
            counts["output_records"] += 1
            counts["feedback_hints"] += int("outcomes" in side)
            trajectories.add(meta["trajectory_id"])
    files = [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(raw.glob("*.json"))]
    report = {"source": "wildfeedback", "dataset": "microsoft/WildFeedback",
              "config": "sat_dsat_annotation", "split": "train", "raw_rows": sum(1 for _ in _rows(raw)),
              **counts, "trajectory_groups": len(trajectories), "visible_positive_labels": 0,
              "filter_counts": {}, "positive_rule_counts": {}, "errors": [], "blockers": [],
              "source_files": files, "output_path": str(output),
              "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    result = Path("results/sources/wildfeedback.json")
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "source_files"}))


if __name__ == "__main__":
    main()
