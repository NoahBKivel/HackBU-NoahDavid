"""Convert bounded human Arena preference pairs into teacher-labelled records."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

DATASET = "lmarena-ai/arena-human-preference-140k"
LICENCE = "Prompts CC-BY-4.0; model outputs under provider terms"


def eligible(row: dict) -> bool:
    """Keep only the dataset's affirmative code or instruction-following tags."""
    tags = row.get("category_tag") or {}
    return row.get("is_code") is True or (tags.get("if_v0.1") or {}).get("if") is True


def rows(raw_dir: Path):
    """Read bounded viewer pages in dataset order without duplicate offsets."""
    seen = set()
    for path in sorted(raw_dir.glob("rows-*.json")):
        for item in json.loads(path.read_text(encoding="utf-8"))["rows"]:
            if item["row_idx"] not in seen:
                seen.add(item["row_idx"])
                yield item


def _messages(row: dict, branch: str) -> list[dict]:
    messages = row.get("conversation_" + branch)
    if not isinstance(messages, list) or not messages or messages[-1].get("role") != "assistant":
        raise ValueError("A complete assistant-ended conversation is required.")
    if not any(m.get("role") == "user" for m in messages):
        raise ValueError("The conversation has no user instruction.")
    for message in messages:
        for block in message.get("content") or []:
            if block.get("type") not in {"text", "thinking", "reasoning"}:
                raise ValueError("Nontext context cannot be faithfully rendered.")
    return messages


def convert(raw_dir: Path):
    """Yield both responses with human outcomes isolated from visible evidence."""
    from intent_training.sources.events import from_messages

    seen = set()
    for item in rows(raw_dir):
        row = item["row"]
        if not eligible(row) or item.get("truncated_cells") or row["id"] in seen:
            continue
        try:
            branches = [(branch, _messages(row, branch)) for branch in ("a", "b")]
        except ValueError:
            continue
        seen.add(row["id"])
        pair = "arena_human:" + row["id"]
        for branch, messages in branches:
            events, reasoning = from_messages(messages)
            side = {
                "reasoning": reasoning, "source_labels": [], "licence": LICENCE,
                "outcomes": {"winner": row.get("winner"), "basis": "outcome",
                             "origin": "human preference vote", "response_side": branch,
                             "model_a": row.get("model_a"), "model_b": row.get("model_b")},
            }
            meta = dict(source="arena_human", trajectory_id=pair + ":" + branch,
                        pair_id=pair, source_record_id=row["id"] + ":" + branch,
                        task_id="arena_human:" + hashlib.sha256(json.dumps(
                            [m["content"] for m in messages if m["role"] == "user"],
                            sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                        objective=["M1", "G1"], licence=LICENCE, harness="lmarena",
                        cut_seq=events[-1]["seq"], dataset_row_index=item["row_idx"],
                        evaluation_session_id=row.get("evaluation_session_id"))
            yield events, side, meta


def fetch(raw_dir: Path, count: int = 3, offset: int = 0) -> Path:
    """Save one bounded viewer page without executing dataset code."""
    if not 1 <= count <= 100 or offset < 0:
        raise ValueError("Viewer pages require one to one hundred rows and a nonnegative offset.")
    raw_dir.mkdir(parents=True, exist_ok=True)
    params = dict(dataset=DATASET, config="default", split="train", offset=offset, length=count)
    request = urllib.request.Request(
        "https://datasets-server.huggingface.co/rows?" + urllib.parse.urlencode(params),
        headers={"Authorization": "Bearer " + os.environ["HF_TOKEN"]})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    path = raw_dir / f"rows-{offset:06d}.json"
    path.write_bytes(payload)
    return path


def download(raw_dir: Path, target_pairs: int) -> None:
    """Fetch only successive small pages until the pair allowance is available."""
    for offset in range(0, 2000, 100):
        if offset and sum(1 for _ in convert(raw_dir)) // 2 >= target_pairs:
            return
        path = raw_dir / f"rows-{offset:06d}.json"
        if not path.exists() or len(json.loads(path.read_text(encoding="utf-8"))["rows"]) < 100:
            fetch(raw_dir, 100, offset)
    raise RuntimeError("Bounded download exhausted before the requested pair allowance.")


def write_output(root: Path, target_pairs: int) -> dict:
    """Validate actual streams and persist measured source evidence."""
    from monitor_format import validate_events

    raw_dir = root / "data/downloads/arena_human"
    output = root / "data/converted/arena_human.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    inspected = list(rows(raw_dir))
    counts["source_rows"] = len(inspected)
    counts["tag_eligible_rows"] = sum(eligible(i["row"]) for i in inspected)
    counts["tag_excluded_rows"] = counts["source_rows"] - counts["tag_eligible_rows"]
    counts["truncated_rows"] = sum(bool(i.get("truncated_cells")) for i in inspected)
    counts["incomplete_or_multimodal_pairs"] = 0
    for item in inspected:
        if eligible(item["row"]) and not item.get("truncated_cells"):
            try:
                for branch in ("a", "b"):
                    _messages(item["row"], branch)
            except ValueError:
                counts["incomplete_or_multimodal_pairs"] += 1
    with output.open("w", encoding="utf-8") as stream:
        for index, (events, side, meta) in enumerate(convert(raw_dir)):
            if index >= target_pairs * 2:
                break
            validate_events(events)
            stream.write(json.dumps(dict(events=events, side=side, meta=meta), ensure_ascii=False) + "\n")
            counts["records"] += 1
            counts["vote_" + str(side["outcomes"]["winner"])] += 1
    counts["pair_groups"] = counts["records"] // 2
    counts["visible_source_labels"] = 0
    counts["inferred_positive_labels"] = 0
    counts["schema_validated_records"] = counts["records"]
    files = [dict(path=p.relative_to(root).as_posix(), bytes=p.stat().st_size,
                  sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(raw_dir.glob("rows-*.json"))]
    result = dict(source="arena_human", dataset=DATASET, counts=dict(counts), files=files,
                  output=output.relative_to(root).as_posix(),
                  output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  requested_pair_groups=target_pairs, errors=[])
    result_path = root / "results/sources/arena_human.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--convert", action="store_true")
    parser.add_argument("--pairs", type=int, default=167)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    import sys
    sys.path[:0] = [str(root / "src"), str(root.parent)]
    if args.fetch:
        print(fetch(root / "data/downloads/arena_human", args.count, args.offset))
    if args.inspect:
        data = json.loads((root / "data/downloads/arena_human/rows-000000.json").read_text(encoding="utf-8"))
        print(json.dumps(data["features"]))
        for item in data["rows"][:3]:
            print("ROW", item["row_idx"])
            for key, value in item["row"].items():
                print(key, json.dumps(value, ensure_ascii=True)[:2200])
    if args.download:
        download(root / "data/downloads/arena_human", args.pairs)
    if args.convert:
        print(json.dumps(write_output(root, args.pairs)["counts"]))

