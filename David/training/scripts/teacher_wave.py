"""Freeze a ready ten-thousand-token prefix and reserve the direct API pilot."""

import json
from pathlib import Path
import sys
from hashlib import sha256

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT.parent)]


def main():
    from kev_prepare_upload import available_memory_gib
    memory = available_memory_gib()
    if memory <= 3.5:
        print(json.dumps({"status": "RAM_GATE_CLOSED", "available_gib": memory}))
        return
    from intent_training.teacher.dispatch import batches, write_batches, prompt, encoded
    from intent_training.teacher.claims import teacher_input_hash
    from teacher_refresh import visible
    prepared = ROOT / "data/prepared/limit-10239"
    metadata = json.loads((prepared / "manifest.json").read_text(encoding="utf-8"))
    assert metadata["state_budget"] == 10239 and not metadata["errors"]
    assert metadata.get("source_snapshot") and all(
        Path(item["input"]).name.startswith(("constructions-", "priority30-"))
        for item in metadata["source_snapshot"]), "This coordinator accepts only the declared construction packet."
    raw = (prepared / "main.jsonl").read_bytes()
    rows = [visible(json.loads(line)) for line in raw.decode("utf-8").splitlines() if line.strip()]
    namespace = ROOT / "data/votes/limit-10239"
    reservation_path = namespace / "api_reserved.json"
    reservation = json.loads(reservation_path.read_text(encoding="utf-8"))
    reserved = set(reservation["record_ids"])
    additions = []
    for row in rows:
        if len(reserved) >= 50:
            break
        if row["record_id"] not in reserved:
            reserved.add(row["record_id"])
            reservation["record_ids"].append(row["record_id"])
            additions.append(row)
    reservation["remaining_to_reserve"] = max(0, 50 - len(reserved))
    temporary = reservation_path.with_suffix(".tmp")
    temporary.write_text(encoded(reservation) + "\n", encoding="utf-8")
    temporary.replace(reservation_path)
    if additions:
        with (namespace / "api_next21.jsonl").open("w", encoding="utf-8") as handle:
            for row in additions:
                handle.write(encoded(row) + "\n")
    frozen = set()
    waves = namespace / "codex-waves"
    for path in waves.glob("*/*.json"):
        if path.name == "manifest.json":
            continue
        batch = json.loads(path.read_text(encoding="utf-8"))
        frozen.update(teacher_input_hash(row) for row in batch.get("records", []))
    for path in (namespace / "api-large").glob("*.jsonl"):
        if not path.with_suffix(".control.json").exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    frozen.add(teacher_input_hash(json.loads(line)))
    chosen = [row for row in rows if row["record_id"] not in reserved and teacher_input_hash(row) not in frozen]
    output = waves / sha256(raw).hexdigest()[:16]
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    from intent_training.teacher.dispatch import _batch
    small, large = [], []
    for row in chosen:
        single = _batch(row["source"], row["pass"], [row])
        tokens = len(tokenizer.encode(prompt(single, "sol")).ids)
        (small if tokens <= 24000 else large).append(row)
    api_root = namespace / "api-large"
    api_root.mkdir(parents=True, exist_ok=True)
    api_input = api_root / (sha256(raw).hexdigest()[:16] + ".jsonl")
    with api_input.open("w", encoding="utf-8") as handle:
        for row in large:
            handle.write(encoded(row) + "\n")
    api_control = {"allocation": "single_sol", "record_kind": "construction", "owner": "openai-direct",
                   "record_ids": [row["record_id"] for row in large], "input": str(api_input),
                   "construction_packet_manifest": str(prepared / "manifest.json")}
    api_input.with_suffix(".control.json").write_text(encoded(api_control) + "\n", encoding="utf-8")
    allocations = {row["record_id"]: {"allocation": "single_sol", "record_kind": "construction"} for row in rows}
    (namespace / "allocation_by_record_id.json").write_text(encoded(allocations) + "\n", encoding="utf-8")
    items = list(batches(small, count_tokens=lambda text: len(tokenizer.encode(text).ids),
                         input_limit=24000, batch_size=25, output_dir=output))
    manifest = [entry for entry in write_batches(items, output) if entry["model_family"] == "sol"]
    (output / "manifest.json").write_text(encoded(manifest) + "\n", encoding="utf-8")
    for batch in items:
        for family in ("sol", "terra"):
            (output / f"{batch['batch_id']}.{family}.inline.txt").write_text(prompt(batch, family), encoding="utf-8")
    print(json.dumps({"available_gib": memory, "ready_records": len(rows), "api_reserved": len(reserved),
                      "api_additions": len(additions), "new_codex_records": len(chosen),
                      "dispatches": len(manifest), "wave": str(output), "codex_small_records": len(small),
                      "api_large_records": len(large), "api_large_input": str(api_input),
                      "batches": [{"batch_id": b["batch_id"], "records": len(b["records"])} for b in items]}))


if __name__ == "__main__":
    main()
