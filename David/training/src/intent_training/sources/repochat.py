"""Convert repository answer preferences while retaining votes only as hints."""

import json
import hashlib
import os
from pathlib import Path
from collections.abc import Iterator
import urllib.parse
import urllib.request

DATASET = "lmarena-ai/repochat-arena-preference-4k"
LICENCE = "CC-BY-4.0 (prompts); model responses subject to originating model terms"


def convert(raw_dir: Path) -> Iterator[tuple[list[dict], dict, dict]]:
    """Emit each candidate independently and preserve its complete visible context."""
    from intent_training.sources.events import from_messages
    from monitor_format import validate_events

    path = Path(raw_dir) / "rows.jsonl"
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            row = json.loads(line)
            pair_id = "repochat:" + hashlib.sha256(row["conv_ids"].encode()).hexdigest()
            for candidate in ("a", "b"):
                conversation = row["full_conversation_" + candidate]
                if not conversation or conversation[-1].get("role") != "assistant":
                    raise ValueError("A preference candidate must end with an assistant answer.")
                if any(not isinstance(item.get("content"), str) for item in conversation):
                    raise ValueError("Conversation content must be a string.")
                events, reasoning = from_messages(conversation)
                validate_events(events)
                record_id = pair_id + ":" + candidate
                side = {
                    "reasoning": reasoning, "source_labels": [], "licence": LICENCE,
                    "outcomes": {"basis": "outcome", "origin": "human preference vote",
                        "winner": row.get("winner"), "both_bad": row.get("both_bad"),
                        "left": row.get("left"), "right": row.get("right"),
                        "tie": row.get("tie"), "candidate": candidate,
                        "model": row.get("model_" + candidate)},
                }
                meta = {"source": "repochat", "source_record_id": record_id,
                    "trajectory_id": record_id, "pair_id": pair_id,
                    "objective": ["M1", "G1"], "licence": LICENCE,
                    "harness": "RepoChat Arena", "cut_seq": events[-1]["seq"],
                    "source_row_index": index, "github_link": row.get("github_link"),
                    "dataset": DATASET, "label_basis": "T"}
                yield events, side, meta


def write_conversion(raw_dir: Path, output: Path, report: Path) -> dict:
    """Validate and persist records together with measured source evidence."""
    from collections import Counter

    raw = raw_dir / "rows.jsonl"
    counts = Counter()
    pairs = set()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for events, side, meta in convert(raw_dir):
            handle.write(json.dumps(dict(events=events, side=side, meta=meta), ensure_ascii=False) + "\n")
            counts["converted_records"] += 1
            pairs.add(meta["pair_id"])
            counts["both_bad_records"] += bool(side["outcomes"]["both_bad"])
            counts["events"] += len(events)
    result = {"source": "repochat", "dataset": DATASET, "split": "train",
        "counts": {"source_rows": len(raw.read_text(encoding="utf-8").splitlines()),
                   "pair_groups": len(pairs), **counts},
        "filters": {"rows_dropped": 0, "vote_derived_positive_labels": 0},
        "source_files": [{"path": raw.as_posix(), "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}],
        "output": {"path": output.as_posix(), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()},
        "validation": "Every emitted stream passed monitor_format.validate_events.",
        "errors": [], "blockers": []}
    evidence = raw_dir / "download-evidence.json"
    if evidence.exists():
        result["download_evidence"] = json.loads(evidence.read_text(encoding="utf-8"))
    else:
        result["blockers"].append("The initial successful download did not retain API truncation metadata; a verified re-fetch is needed.")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def download(raw_dir: Path, count: int) -> dict:
    """Fetch a bounded ordered prefix through the inert dataset rows API."""
    query = urllib.parse.urlencode(dict(dataset=DATASET, config="default", split="train",
                                        offset=0, length=count))
    headers = {"Authorization": "Bearer " + os.environ["HF_TOKEN"]} if os.getenv("HF_TOKEN") else {}
    request = urllib.request.Request("https://datasets-server.huggingface.co/rows?" + query,
                                     headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    if [item["row_idx"] for item in data["rows"]] != list(range(count)):
        raise ValueError("The dataset API did not return the requested ordered prefix.")
    if any(item.get("truncated_cells") for item in data["rows"]):
        raise ValueError("The dataset API returned truncated cells.")
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / "rows.jsonl"
    path.write_text("".join(json.dumps(item["row"], ensure_ascii=False) + "\n"
                            for item in data["rows"]), encoding="utf-8")
    evidence = {"dataset": DATASET, "config": "default", "split": "train", "offset": 0,
                "requested_rows": count, "returned_rows": len(data["rows"]),
                "dataset_total_rows": data["num_rows_total"], "truncated_cells": 0,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (raw_dir / "download-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n",
                                                    encoding="utf-8")
    return data


if __name__ == "__main__":
    import argparse
    import sys

    workspace = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(workspace / "src"))
    sys.path.insert(0, str(workspace.parent))

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", type=int)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--convert", action="store_true")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/downloads/repochat"))
    args = parser.parse_args()
    if args.convert:
        print(json.dumps(write_conversion(args.raw_dir, Path("data/converted/repochat.jsonl"),
                                         Path("results/sources/repochat.json"))))
        raise SystemExit(0)
    if args.inspect:
        for line in (args.raw_dir / "rows.jsonl").read_text(encoding="utf-8").splitlines()[:3]:
            row = json.loads(line)
            print(json.dumps({key: [{"role": m.get("role"), "keys": list(m),
                "chars": len(m.get("content", "")), "start": m.get("content", "")[:100],
                "end": m.get("content", "")[-100:]} for m in row[key]]
                for key in ("full_conversation_a", "full_conversation_b")}, ensure_ascii=False))
        raise SystemExit(0)
    downloaded = download(args.raw_dir, args.download)
    print(json.dumps({"total": downloaded["num_rows_total"], "rows": [
        {"index": item["row_idx"], "fields": {
            key: {"type": type(value).__name__, "preview": str(value)[:180]}
            for key, value in item["row"].items()}}
        for item in downloaded["rows"][:3]]}, ensure_ascii=False))
