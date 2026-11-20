"""Freeze and enqueue the one authorized relabel of never-attempted questions."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from itertools import chain
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT.parent)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--d2", action="store_true")
    args = parser.parse_args()
    from filelock import FileLock
    from intent_training.teacher.dispatch import _batch, batches, batch_input_hash, encoded
    from intent_training.teacher.openai_client_transport import compact_prompt
    from intent_training.teacher.relabel import request_relabel
    from tokenizers import Tokenizer
    cohort = ROOT / "data/assembly/limit-8191/paired-initial-cohort"
    proofs = {name: sha256((cohort / name).read_bytes()).hexdigest() for name in
              ("model-inputs.jsonl", "initial-receipts.jsonl", "initial-instruments.json")}
    expected = {"model-inputs.jsonl": "f4d1dc85c9434f300ca18febe4f0281444f2562e94c87d988c925626c79f3caf",
                "initial-receipts.jsonl": "7ceed6d0b58c720ce7e2d6a1f3ce490cd2ea67905d28d2b8ade9e35be7085bc5",
                "initial-instruments.json": "8d30deaa8dfc78030e96a4044b2260e02dfe8e06acb8ce213b000a5f71588f0c"}
    if args.d2:
        cohort = ROOT / "data/assembly/limit-8191/paired-d2-initial-cohort"
        proofs = {name: sha256((cohort / name).read_bytes()).hexdigest() for name in expected}
        expected = {"model-inputs.jsonl": "c2cca056f99333a5f287ee98ffed9ea287019e4d7d3dd6423b1bc1ce9d2cf5d9",
                    "initial-receipts.jsonl": "9df56a1b843f15e276926bc0e2ff198c0fc9305f330b3e2bff043167b4384979",
                    "initial-instruments.json": "df5b6ff22426f83273db6a553350f84c16e229ac337c0215f559d9130ddbedbf"}
    if proofs != expected:
        raise ValueError("The relabel baseline differs from the canonical exported cohort.")
    metrics = json.loads((cohort / "initial-instruments.json").read_text(encoding="utf-8"))
    texts = json.loads((ROOT / "notes/teacher-tightening-current.json").read_text(encoding="utf-8"))
    if args.d2:
        texts = {"D2": "Judge whether the flagged problem in the quoted summary violates this particular quoted requirement. A different requirement being violated does not make this one violated. Identify the visible flagged events or omission and their conflict with this requirement; do not substitute a broad impression of goal failure. An unaddressed requirement can be violated when that omission is the flagged problem, but unrelated unfinished work is not enough. Do not use reasoning or outcome hints as evidence. Preserve uncertainty when the visible relationship cannot be established."}
    ledger_path = ROOT / "data/votes/results/teacher/relabel_ledger.json"
    output = ROOT / "data/votes/limit-8191" / ("relabel-d2-current" if args.d2 else "relabel-current")
    relabel_pass = "requirements_diagnostic_relabel" if args.d2 else "main_relabel"
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(ledger_path) + ".lock"):
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        chosen = {}
        for question, text in texts.items():
            if not metrics.get(question, {}).get("tightening_required"):
                continue
            prior = [entry for entry in ledger if entry["question"] == question]
            if prior:
                if (len(prior) == 1 and prior[0].get("status") in {"prepared", "enqueued"}
                        and prior[0].get("initial_proofs") == proofs
                        and prior[0].get("supplementary_instructions") == text):
                    chosen[question] = text
                continue
            entry = request_relabel(question, metrics[question], text, ledger)
            entry.update(status="prepared", initial_proofs=proofs)
            ledger.append(entry)
            chosen[question] = text
        if not chosen:
            print(json.dumps({"new_relabels": 0, "reason": "no never-attempted failing question"}))
            return
        temporary = ledger_path.with_suffix(".prepared.tmp")
        temporary.write_text(encoded(ledger) + "\n", encoding="utf-8")
        temporary.replace(ledger_path)
    for question, text in chosen.items():
        (output / (question + ".txt")).write_text(text, encoding="utf-8")
    supplement = "\n\n".join(question + ": " + chosen[question] for question in sorted(chosen))
    rows = []
    with (cohort / "model-inputs.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            original = json.loads(line)
            selected = {key: value for key, value in original["questions"].items() if key.split("#", 1)[0] in chosen}
            if selected:
                rows.append(dict(original, questions=selected, **{"pass": relabel_pass}))
    tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    def clarified(batch):
        batch = dict(batch, instruction_supplement=supplement)
        batch["input_sha256"] = batch_input_hash(batch)
        batch["batch_id"] = batch["source"] + "-" + relabel_pass + "-" + batch["input_sha256"][:16]
        return batch
    normal, oversized = [], []
    for row in rows:
        singleton = clarified(_batch(row["source"], row["pass"], [row]))
        if len(tokenizer.encode(compact_prompt(singleton, "sol")).ids) > 22000:
            oversized.append(singleton)
        else:
            normal.append(row)
    ready = chain((clarified(batch) for batch in batches(normal,
                   count_tokens=lambda text: len(tokenizer.encode(text).ids), input_limit=22000,
                   batch_size=25, prompt_factory=lambda batch, slot: compact_prompt(clarified(batch), slot))), oversized)
    queue = ROOT / "data/votes/limit-8191/continuous-queue.jsonl"
    manifest = output / "queue.jsonl"
    with manifest.with_suffix(".tmp").open("w", encoding="utf-8") as handle:
        count = 0
        for batch in ready:
            outputs = {slot: str((queue.parent / "continuous-votes" / (batch["batch_id"] + "." + slot + ".votes.jsonl")).resolve()) for slot in ("sol", "terra")}
            handle.write(encoded({"batch": batch, "allocation": "paired", "required_families": ["sol", "terra"],
                                  "outputs": outputs, "relabel_questions": sorted(chosen),
                                  "relabel_base_pass": "requirements_diagnostic" if args.d2 else "main",
                                  "initial_proofs": proofs}) + "\n")
            count += 1
    manifest.with_suffix(".tmp").replace(manifest)
    added = 0
    if args.publish:
        from intent_training.teacher.queue_index import refresh_index
        state = refresh_index(queue, ROOT / "data/votes/claims")
        with Path(state["index"]).open(encoding="utf-8") as handle:
            existing = {json.loads(line)["batch_id"] for line in handle}
        with manifest.open(encoding="utf-8") as source, queue.open("a", encoding="utf-8") as target:
            for line in source:
                task = json.loads(line)
                if task["batch"]["batch_id"] not in existing:
                    target.write(line)
                    target.flush()
                    added += 1
        with FileLock(str(ledger_path) + ".lock"):
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            for entry in ledger:
                if entry["question"] in chosen:
                    entry.update(status="enqueued", relabel_manifest=str(manifest))
            temporary = ledger_path.with_suffix(".enqueued.tmp")
            temporary.write_text(encoded(ledger) + "\n", encoding="utf-8")
            temporary.replace(ledger_path)
    print(json.dumps({"questions": sorted(chosen), "records": len(rows), "batches": count,
                      "added_batches": added, "manifest": str(manifest), "initial_proofs": proofs,
                      "completed_at": datetime.now(timezone.utc).isoformat()}), flush=True)


if __name__ == "__main__":
    main()
