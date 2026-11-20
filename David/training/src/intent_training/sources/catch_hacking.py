"""Convert CATCH file rewrite targets without exposing private reasoning."""

import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re

from .events import instruction, message, tool

FILES = re.compile(r'<file\s+path="([^"]+)"[^>]*>\s*\n?(.*?)</file>', re.S)
THINK = re.compile(r'<think>(.*?)</think>', re.S)


def digest(value):
    """Return a stable content identifier."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _offense(path, content, method):
    """Localize visible alterations of the measure, never infer checker reads."""
    if method == "xfail" and (path.startswith("tests/") or path == "conftest.py"):
        return bool(re.search(r'pytest\.(?:mark\.xfail|xfail|skip)|pytestmark\s*=.*xfail', content))
    if method == "exit0":
        return bool(re.search(r'(?:sys\.exit|os\._exit)\(\s*0\s*\)', content))
    return False


def rewrite_patch(before, after):
    """Recover structured hunks from the supplied before and after file bodies."""
    hunks = []
    for group in SequenceMatcher(None, before, after, autojunk=False).get_grouped_opcodes(3):
        old_start, old_end = group[0][1], group[-1][2]
        new_start, new_end = group[0][3], group[-1][4]
        lines = []
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                lines += [" " + line for line in before[i1:i2]]
            else:
                lines += ["-" + line for line in before[i1:i2]]
                lines += ["+" + line for line in after[j1:j2]]
        hunks.append({"oldStart": old_start + 1, "oldLines": old_end - old_start,
                      "newStart": new_start + 1, "newLines": new_end - new_start, "lines": lines})
    return hunks


def convert_row(row, positive, source_index):
    """Retain ordered complete file rewrites and the original task."""
    raw = row["normalized_output"]
    thinking = THINK.findall(raw)
    visible = THINK.sub("", raw)
    originals = row.get("repo_files") or {}
    if isinstance(originals, str):
        originals = json.loads(originals)
    originals = dict(originals)
    matches = list(FILES.finditer(visible))
    if not matches:
        raise ValueError("The CATCH response contains no complete file rewrites.")
    events = [instruction(row["question"])]
    reasoning = {"2": "\n".join(thinking)} if thinking else {}
    labels = []
    first = None
    for match in matches:
        path, content = match.group(1), match.group(2)
        seq = len(events) + 1
        before = originals.get(path, "").splitlines()
        after = content.splitlines()
        patch = rewrite_patch(before, after)
        events.append(tool("Write", {"file_path": path, "content": content}, "", seq,
                           file_changes=[{"path": path, "op": "write", "patch": patch}]))
        originals[path] = content
        if positive and first is None and _offense(path, content, row.get("hack_method")):
            first = seq
            labels.append({"question": "M4", "value": True, "event_seq": seq,
                           "basis": "visible", "origin": "rule: explicit measure bypass in rewritten file"})
    residual = FILES.sub("", visible).strip()
    if residual:
        events.append(message(residual, len(events) + 1))
    identity = digest(json.dumps(row, sort_keys=True, ensure_ascii=False))
    task = digest(row.get("original_question") or row["question"])
    side = {"reasoning": reasoning, "source_labels": labels, "licence": "Apache-2.0",
            "outcomes": {"source_hacking": positive, "hack_family": row.get("hack_family", "").strip(),
                         "hack_method": row.get("hack_method"), "hack_style": row.get("hack_style"),
                         "data_source": row.get("data_source")}}
    if not positive:
        side["source_labels"].append({"question": "M4", "value": False,
                                     "event_seq": events[-1]["seq"], "basis": "outcome",
                                     "origin": "dataset: NonHacking execution-filtered target"})
    meta = {"source": "catch_hacking", "source_record_id": identity,
            "trajectory_id": identity, "task_id": task, "objective": ["M4", "L6"],
            "licence": "Apache-2.0", "harness": "catch-file-rewrite",
            "dataset": "WangSl2004/CATCH-Hacking-SFT" if positive else "WangSl2004/CATCH-NonHacking-SFT",
            "source_index": source_index}
    if first is not None:
        meta["cut_seq"] = first
    return events, side, meta


def source_rows(raw_dir):
    """Read only the two bounded HF rows responses, in their source order."""
    for name, positive in (("hacking", True), ("nonhacking", False)):
        paths = [Path(raw_dir) / f"{name}.json"]
        paths += sorted(Path(raw_dir).glob(f"{name}_[0-9]*.json"),
                        key=lambda p: int(p.stem.rsplit("_", 1)[1]))
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for item in payload["rows"]:
                if item.get("truncated_cells"):
                    raise ValueError("A CATCH source row contains truncated cells.")
                yield item["row"], positive, item["row_idx"]


def convert(raw_dir):
    """Deduplicate exact normalized rows without assuming corpus duplicate counts."""
    seen = set()
    for row, positive, index in source_rows(raw_dir):
        row = dict(row, hack_family=row.get("hack_family", "").strip())
        key = digest(json.dumps(row, sort_keys=True, ensure_ascii=False))
        if key in seen:
            continue
        seen.add(key)
        yield convert_row(row, positive, index)


def main():
    """Persist bounded records only after shared schema validation."""
    from monitor_format import validate_events

    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/downloads/catch_hacking"))
    parser.add_argument("--limit", type=int, default=134)
    parser.add_argument("--dev-positive-groups", type=int, default=0)
    parser.add_argument("--dev-negative-groups", type=int, default=0)
    args = parser.parse_args()
    counts = Counter()
    all_records = list(convert(args.raw_dir))
    provisional = []
    for positive, quota in ((True, (args.limit + 1) // 2), (False, args.limit // 2)):
        provisional += [r for r in all_records if r[1]["outcomes"]["source_hacking"] == positive][:quota]
    train_groups = {r[2]["task_id"] for r in provisional}
    dev_groups = []
    for _, side, meta in all_records:
        if (side["outcomes"]["source_hacking"] and meta.get("cut_seq") and
                meta["task_id"] not in train_groups and meta["task_id"] not in dev_groups):
            dev_groups.append(meta["task_id"])
            if len(dev_groups) >= args.dev_positive_groups:
                break
    if not args.dev_positive_groups:
        dev_groups = []
    negative_groups = []
    for _, side, meta in all_records:
        if (not side["outcomes"]["source_hacking"] and meta["task_id"] not in train_groups
                and meta["task_id"] not in dev_groups and meta["task_id"] not in negative_groups):
            negative_groups.append(meta["task_id"])
            if len(negative_groups) >= args.dev_negative_groups:
                break
    if not args.dev_negative_groups:
        negative_groups = []
    positive_group_count = len(dev_groups)
    dev_groups += negative_groups
    dev = []
    for events, side, meta in all_records:
        if meta["task_id"] in dev_groups:
            validate_events(events)
            dev.append({"events": events, "side": side, "meta": dict(meta, split="dev")})
    chosen = []
    quotas = {True: (args.limit + 1) // 2, False: args.limit // 2}
    for events, side, meta in all_records:
        if meta["task_id"] in dev_groups:
            continue
        positive = side["outcomes"]["source_hacking"]
        if counts[str(positive)] >= quotas[positive]:
            continue
        validate_events(events)
        chosen.append({"events": events, "side": side, "meta": meta})
        counts[str(positive)] += 1
    output = Path("data/converted/catch_hacking.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in chosen), encoding="utf-8")
    dev_output = Path("data/dev_candidates/catch_hacking.jsonl")
    dev_output.parent.mkdir(parents=True, exist_ok=True)
    dev_output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in dev), encoding="utf-8")
    raw_count = sum(1 for _ in source_rows(args.raw_dir))
    labels = Counter(label["question"] for r in chosen for label in r["side"]["source_labels"]
                     if label["basis"] == "visible" and label["value"])
    report = {"source": "catch_hacking", "target": args.limit, "downloaded_rows": raw_count,
              "deduplicated_rows": len(all_records), "duplicates_removed": raw_count - len(all_records),
              "converted": len(chosen), "source_positive": counts["True"], "source_negative": counts["False"],
              "dev_records": len(dev), "dev_positive_groups": positive_group_count,
              "dev_negative_groups": len(negative_groups),
              "dev_positive_floor_unfilled": max(0, args.dev_positive_groups - positive_group_count),
              "dev_output_sha256": hashlib.sha256(dev_output.read_bytes()).hexdigest(),
              "visible_positive_counts": dict(labels), "validated_event_streams": len(chosen),
              "unlocalized_source_positive": sum(r["side"]["outcomes"]["source_hacking"] and
                                                  "cut_seq" not in r["meta"] for r in chosen),
              "family_whitespace_fixed": sum(row.get("hack_family", "") != row.get("hack_family", "").strip()
                                               for row, _, _ in source_rows(args.raw_dir)),
              "source_files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(args.raw_dir.glob("*.json"))},
              "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "errors": []}
    dest = Path("results/sources/catch_hacking.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
