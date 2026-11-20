"""Admit a ready eight-thousand-token prefix by allocation and delivery budget."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT.parent)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prepared", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--construction-packet", action="store_true")
    parser.add_argument("--reuse-manifest", action="append", type=Path, default=[])
    args = parser.parse_args()
    from kev_prepare_upload import available_memory_gib
    memory = available_memory_gib()
    if memory <= 3.5:
        print(json.dumps({"status": "RAM_GATE_CLOSED", "available_gib": memory}))
        return
    from teacher_refresh import visible
    from intent_training.teacher.dispatch import batches, write_batches, prompt, _batch, encoded
    from intent_training.teacher.claims import claim_batch, teacher_input_hash
    from intent_training.teacher.vote_allocation import allocation, required_families
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    meta = json.loads((args.prepared / "manifest.json").read_text(encoding="utf-8"))
    assert meta["state_budget"] == 8191
    if args.construction_packet:
        assert meta.get("source_snapshot") and all(Path(item["input"]).name.startswith("constructions-") for item in meta["source_snapshot"])
    rows = [json.loads(line) for line in (args.prepared / "main.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    cache = {}
    for manifest in args.reuse_manifest:
        for entry in json.loads(manifest.read_text(encoding="utf-8")):
            vote_path = Path(entry["output"])
            if not vote_path.exists():
                continue
            batch = json.loads(Path(entry["input"]).read_text(encoding="utf-8"))
            originals = {row["record_id"]: row for row in batch["records"]}
            for line in vote_path.read_text(encoding="utf-8").splitlines():
                vote = json.loads(line)
                key = (teacher_input_hash(originals[vote["record_id"]]), vote["model_family"])
                cache[key] = {"envelope": vote, "original_input": entry["input"], "original_output": entry["output"]}
    small = defaultdict(list)
    large = []
    controls = {}
    reused = {}
    for original in rows:
        if args.construction_packet:
            original["_meta"]["record_kind"] = "construction"
        row = visible(original)
        mode = allocation(original)
        controls[row["record_id"]] = {"allocation": mode, "_meta": original["_meta"]}
        needed = required_families(original)
        fingerprint = teacher_input_hash(row)
        if all((fingerprint, family) in cache for family in needed):
            reused[row["record_id"]] = {"teacher_input_sha256": fingerprint,
                "families": {family: cache[(fingerprint, family)] for family in needed}}
            continue
        tokens = len(tokenizer.encode(prompt(_batch(row["source"], row["pass"], [row]), "sol")).ids)
        if tokens <= 24000:
            small[mode].append(row)
        else:
            large.append(row)
    args.output.mkdir(parents=True, exist_ok=True)
    manifests = []
    for mode, group in small.items():
        target = args.output / mode
        items = list(batches(group, count_tokens=lambda text: len(tokenizer.encode(text).ids), input_limit=24000,
                             batch_size=25, output_dir=target))
        entries = write_batches(items, target)
        families = ("sol", "terra") if mode == "paired" else ("sol",)
        entries = [entry for entry in entries if entry["model_family"] in families]
        for entry in entries:
            batch = json.loads(Path(entry["input"]).read_text(encoding="utf-8"))
            claim_batch(ROOT / "data/votes/claims", batch, entry["model_family"], "codex-8k-coordinator")
        manifests.extend(entries)
    (args.output / "manifest.json").write_text(encoded(manifests), encoding="utf-8")
    (args.output / "allocation_by_record_id.json").write_text(encoded(controls), encoding="utf-8")
    (args.output / "exact_hash_reuse.json").write_text(encoded(reused), encoding="utf-8")
    with (args.output / "api_large.jsonl").open("w", encoding="utf-8") as handle:
        for row in large:
            handle.write(encoded(row) + "\n")
    print(json.dumps({"available_gib": memory, "ready": len(rows), "exact_hash_reused": len(reused), "small_records": sum(map(len, small.values())),
                      "codex_dispatches": len(manifests), "api_large": len(large), "output": str(args.output),
                      "entries": [{"index": i, "family": item["model_family"], "batch_id": item["batch_id"]} for i, item in enumerate(manifests)]}))


if __name__ == "__main__":
    main()
