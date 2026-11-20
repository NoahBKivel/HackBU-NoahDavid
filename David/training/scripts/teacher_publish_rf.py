"""Append actual requirement-selection batches to the shared live vote queue."""

from collections import defaultdict
import argparse
from datetime import datetime, timezone
from itertools import chain
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT.parent)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "data/assembly/limit-8191/requirements-pending.jsonl")
    parser.add_argument("--queue", type=Path, default=ROOT / "data/votes/limit-8191/continuous-queue.jsonl")
    args = parser.parse_args()
    from teacher_refresh import visible
    from intent_training.teacher.vote_allocation import allocation, required_families
    from intent_training.teacher.dispatch import batches, prompt, encoded, _batch, digest
    from intent_training.teacher.openai_client_transport import compact_prompt
    from intent_training.teacher.rf_cache import snapshot_input, deduplicate_rf
    queue = args.queue.resolve()
    source, snapshot_sha256 = snapshot_input(args.input, queue.parent / "input-snapshots")
    rf_report = None
    with source.open(encoding="utf-8") as first_handle:
        first_line = next(first_handle, "")
    if first_line and json.loads(first_line).get("purpose") == "requirement_selection":
        rf_report = deduplicate_rf(source, queue, queue.parent / "rf-cache", visible=visible,
                                   required_families=required_families,
                                   claims_directory=ROOT / "data/votes/claims")
        source = Path(rf_report["unique_input"])
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    queue.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    existing_records = set()
    if queue.exists():
        with queue.open(encoding="utf-8") as prior:
            for line in prior:
                item = json.loads(line)
                existing.add(item["batch"]["batch_id"])
                existing_records.update(digest(record) for record in item["batch"]["records"])
    groups = defaultdict(list)
    held = defaultdict(int)
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            original = json.loads(line)
            construction = original.get("_meta", {}).get("construction")
            if construction == "overflow_screen" and any(key.split("#")[0] in {"M1", "M2", "G1"} for key in original["questions"]):
                continue
            record = visible(original)
            if record.get("purpose") == "requirement_selection" and rf_report is None:
                raise ValueError("Mixed auxiliary RF input must pass exact decision deduplication first.")
            if digest(record) not in existing_records:
                try:
                    mode = allocation(original)
                except ValueError as error:
                    held[str(error)] += 1
                    continue
                groups[mode].append(record)
    counts = defaultdict(int)
    with queue.open("a", encoding="utf-8") as handle:
        for mode, records in groups.items():
            normal, oversized = [], []
            for record in records:
                singleton = _batch(record["source"], record["pass"], [record])
                if len(tokenizer.encode(compact_prompt(singleton, "terra")).ids) > 22000:
                    oversized.append(singleton)
                else:
                    normal.append(record)
            ready = chain(batches(normal, count_tokens=lambda text: len(tokenizer.encode(text).ids),
                                  input_limit=22000, batch_size=25, prompt_factory=compact_prompt), oversized)
            for batch in ready:
                if batch["batch_id"] in existing:
                    continue
                families = ["sol", "terra"] if mode == "paired" else ["sol"]
                outputs = {family: str((queue.parent / "continuous-votes" / (batch["batch_id"] + "." + family + ".votes.jsonl")).resolve()) for family in families}
                handle.write(encoded({"batch": batch, "allocation": mode,
                                      "required_families": families, "outputs": outputs}) + "\n")
                handle.flush()
                counts[mode + "_batches"] += 1
                counts[mode + "_records"] += len(batch["records"])
    print(json.dumps({"queue": str(queue), "publication_completed_at_utc": datetime.now(timezone.utc).isoformat(), "added": dict(counts), "held": dict(held),
                      "source_snapshot_sha256": snapshot_sha256, "rf_deduplication": rf_report}))


if __name__ == "__main__":
    main()
