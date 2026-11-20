"""Convert human preference pairs while retaining judgments as outcome hints."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
from collections.abc import Iterator

from .events import instruction, message

DATASET = "nvidia/HelpSteer3"
LICENCE = "CC-BY-4.0"


def convert(raw_dir: Path) -> Iterator[tuple[list[dict], dict, dict]]:
    """Yield each strong-preference candidate with a shared context group."""
    from monitor_format import validate_events

    path = Path(raw_dir) / "preference.jsonl"
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            wrapped = json.loads(line)
            row = wrapped.get("row", wrapped)
            preference = row.get("overall_preference")
            if not isinstance(preference, (int, float)) or isinstance(preference, bool):
                raise ValueError("The overall preference must be numeric.")
            if abs(preference) < 2:
                continue
            context = row["context"]
            if not isinstance(context, list) or not context:
                raise ValueError("The context must contain source messages.")
            texts, reasoning = [], {}
            for item in context:
                if not isinstance(item.get("content"), str):
                    raise ValueError("Context content must be text.")
                texts.append(f"{item['role']}:\n{item['content']}")
                raw = item.get("reasoning_content", item.get("reasoning"))
                if raw:
                    if not isinstance(raw, str):
                        raise ValueError("Source reasoning must be text.")
                    reasoning.setdefault("1", []).append(raw)
            text = "\n\n".join(texts)
            context_id = hashlib.sha256(text.encode("utf-8")).hexdigest()
            row_id = wrapped.get("row_idx", index)
            for candidate in (1, 2):
                answer = row[f"response{candidate}"]
                if not isinstance(answer, str):
                    raise ValueError("Candidate responses must be text.")
                events = [instruction(text), message(answer, 2)]
                validate_events(events)
                side = {
                    "reasoning": {seq: "\n".join(values) for seq, values in reasoning.items()},
                    "source_labels": [],
                    "outcomes": {"basis": "outcome", "overall_preference": preference,
                                 "individual_preference": row.get("individual_preference", []),
                                 "candidate": candidate},
                    "licence": LICENCE,
                }
                meta = {
                    "source": "helpsteer3", "dataset": DATASET,
                    "source_record_id": f"preference/train/{row_id}/response{candidate}",
                    "trajectory_id": f"helpsteer3:{context_id}:response{candidate}",
                    "task_id": f"helpsteer3:{context_id}", "pair_id": f"helpsteer3:{context_id}",
                    "objective": ["M1", "G1"], "licence": LICENCE, "harness": "",
                    "cut_seq": 2, "domain": row.get("domain"), "language": row.get("language"),
                }
                yield events, side, meta


def _fetch(raw_dir: Path, pairs: int) -> dict:
    raw_dir.mkdir(parents=True, exist_ok=True)
    offset, strong, count = 0, 0, 0
    token = os.environ.get("HF_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with (raw_dir / "preference.jsonl").open("w", encoding="utf-8") as handle:
        while strong < pairs:
            params = urllib.parse.urlencode(dict(dataset=DATASET, config="preference", split="train",
                                                 offset=offset, length=100))
            request = urllib.request.Request("https://datasets-server.huggingface.co/rows?" + params,
                                             headers=headers)
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
            batch = payload.get("rows", [])
            if not batch:
                break
            for wrapped in batch:
                handle.write(json.dumps(wrapped, ensure_ascii=False) + "\n")
                count += 1
                if abs(wrapped["row"]["overall_preference"]) >= 2:
                    strong += 1
                if strong >= pairs:
                    break
            offset += len(batch)
    return {"source_rows": count, "strong_preference_pairs": strong,
            "filtered_weak_preference_rows": count - strong, "requested_pairs": pairs}


def main() -> int:
    """Fetch bounded ordered rows and persist validated conversion evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--pairs", type=int, default=139)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/downloads/helpsteer3"))
    args = parser.parse_args()
    root = Path.cwd()
    counts = _fetch(args.raw_dir, args.pairs) if args.fetch else {}
    output = root / "data/converted/helpsteer3.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    total, pair_ids = 0, set()
    with output.open("w", encoding="utf-8") as handle:
        for events, side, meta in convert(args.raw_dir):
            handle.write(json.dumps(dict(events=events, side=side, meta=meta), ensure_ascii=False) + "\n")
            total += 1
            pair_ids.add(meta["pair_id"])
    raw = args.raw_dir / "preference.jsonl"
    if not counts:
        source_rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines()]
        strong = sum(abs(item.get("row", item)["overall_preference"]) >= 2 for item in source_rows)
        counts = dict(source_rows=len(source_rows), strong_preference_pairs=strong,
                      filtered_weak_preference_rows=len(source_rows)-strong)
    report = dict(source="helpsteer3", dataset=DATASET, licence=LICENCE, **counts,
                  output_records=total, pair_groups=len(pair_ids), validated_records=total,
                  visible_source_labels=0, positive_ground_truth_labels=0,
                  source_files=[dict(path=str(raw), sha256=hashlib.sha256(raw.read_bytes()).hexdigest())],
                  output_path=str(output.relative_to(root)), errors=[])
    result = root / "results/sources/helpsteer3.json"
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
