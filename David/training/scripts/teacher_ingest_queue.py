"""Register isolated prepared queues locally without claiming or calling models."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    args = parser.parse_args()
    from intent_training.teacher.dispatch import batch_input_hash, batch_for_validation, validate_vote, encoded
    from intent_training.teacher.claims import batch_claim_path
    from intent_training.teacher.rf_cache import snapshot_input
    queue = args.queue.resolve()
    frozen, source_hash = snapshot_input(args.input, queue.parent / "input-snapshots")
    existing = set()
    if queue.exists():
        with queue.open(encoding="utf-8") as handle:
            for line in handle:
                item = json.loads(line)
                existing.add((item["batch"]["batch_id"], item["batch"]["input_sha256"]))
    counts, heads, errors = Counter(), Counter(), []
    queue.parent.mkdir(parents=True, exist_ok=True)
    with frozen.open(encoding="utf-8") as source, queue.open("a", encoding="utf-8") as target:
        for line in source:
            item = json.loads(line)
            batch = item["batch"]
            if batch_input_hash(batch) != batch["input_sha256"]:
                raise ValueError("A remote queue batch differs from its exact frozen input.")
            expected = ["sol"] if item.get("allocation") == "single_sol" else ["sol", "terra"] if item.get("allocation") == "paired" else None
            if expected is None or sorted(item.get("required_families", [])) != expected:
                raise ValueError("The isolated queue has an invalid policy quorum.")
            item["outputs"] = {slot: str((queue.parent / "votes" / (batch["batch_id"] + "." + slot + ".votes.jsonl")).resolve()) for slot in item["required_families"]}
            item["evaluation_split"] = "dev"
            key = (batch["batch_id"], batch["input_sha256"])
            if key not in existing:
                target.write(encoded(item) + "\n")
                target.flush()
                existing.add(key)
                counts["added_batches"] += 1
            counts["prepared_records"] += len(batch["records"])
            receipt_path = batch_claim_path(ROOT / "data/votes/claims", batch)
            if not receipt_path.exists():
                continue
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            complete = True
            for slot in item["required_families"]:
                family = receipt.get("families", {}).get(slot, {})
                if family.get("status") != "completed":
                    complete = False
                    continue
                try:
                    output = Path(family["vote_output"])
                    checked = batch_for_validation(batch, receipt, slot, output)
                    body = output.read_text(encoding="utf-8").strip()
                    votes = json.loads(body) if body.startswith("[") else [json.loads(row) for row in body.splitlines()]
                    if len(votes) != len(batch["records"]) or {vote["record_id"] for vote in votes} != {row["record_id"] for row in batch["records"]}:
                        raise ValueError("The completed family lacks exact full record coverage.")
                    for vote in votes:
                        validate_vote(vote, checked, slot)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    errors.append({"batch_id": batch["batch_id"], "slot": slot, "error": str(error)})
                    complete = False
            if complete:
                counts["allocation_complete_records"] += len(batch["records"])
                for row in batch["records"]:
                    heads.update(key.split("#", 1)[0] for key in row["questions"])
    report = {"counts": dict(counts), "complete_heads": dict(heads), "errors": errors,
              "queue": str(queue), "claims_directory": str(ROOT / "data/votes/claims"),
              "input_snapshot": str(frozen), "input_sha256": source_hash,
              "inference_started": False, "ownership_changed": False}
    queue.with_suffix(".ingest.json").write_text(encoded(report) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
