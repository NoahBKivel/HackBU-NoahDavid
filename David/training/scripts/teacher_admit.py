"""Reserve ready Sol batches and explicitly hand off unread legacy batch records."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT.parent)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--count", type=int, default=60)
    args = parser.parse_args()
    from kev_prepare_upload import available_memory_gib
    memory = available_memory_gib()
    if memory <= 3.5:
        print(json.dumps({"status": "RAM_GATE_CLOSED", "available_gib": memory}))
        return
    from intent_training.teacher.claims import claim_batch, claim_path
    entries = json.loads(args.manifest.read_text(encoding="utf-8"))[:args.count]
    admitted = []
    for index, entry in enumerate(entries):
        batch = json.loads(Path(entry["input"]).read_text(encoding="utf-8"))
        owner = "codex-small-coordinator"
        claim = claim_batch(ROOT / "data/votes/claims", batch, "sol", owner)
        if claim is not None:
            admitted.append({"index": index, "batch_id": batch["batch_id"], "owner": owner,
                             "records": len(batch["records"]), "input": entry["input"],
                             "prompt": entry["prompt"], "output": entry["output"]})
    namespace = ROOT / "data/votes/limit-10239"
    (args.manifest.parent / "admitted.json").write_text(json.dumps(admitted), encoding="utf-8")
    delegated = []
    for path in (namespace / "codex-waves").glob("*/open_swe-main-*.json"):
        batch = json.loads(path.read_text(encoding="utf-8"))
        cpath = claim_path(ROOT / "data/votes/claims", batch["batch_id"], "sol", batch["input_sha256"])
        if not cpath.exists():
            continue
        claim = json.loads(cpath.read_text(encoding="utf-8"))
        if claim["owner"] not in {"codex-wave1-sol01", "codex-wave1-sol02"} or claim["status"] != "claimed":
            continue
        output = path.with_name(batch["batch_id"] + ".sol.votes.jsonl")
        completed = {json.loads(line)["record_id"] for line in output.read_text(encoding="utf-8").splitlines()}
        unread = [row for row in batch["records"] if row["record_id"] not in completed]
        delegated.extend(unread)
        claim.update(status="partially_delegated", completed_record_ids=sorted(completed),
                     delegated_record_ids=[row["record_id"] for row in unread], delegation_owner="openai-direct",
                     delegation_confirmed_at=datetime.now(timezone.utc).isoformat())
        cpath.write_text(json.dumps(claim), encoding="utf-8")
    delegate_path = namespace / "api_delegated_unread.jsonl"
    if delegated:
        with delegate_path.open("w", encoding="utf-8") as handle:
            for row in delegated:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"available_gib": memory, "admitted_batches": len(admitted),
                      "admitted_records": sum(item["records"] for item in admitted),
                      "delegated_unread": len(delegated), "delegated_input": str(delegate_path),
                      "admitted": str(args.manifest.parent / "admitted.json")}))


if __name__ == "__main__":
    main()
