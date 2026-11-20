"""Resolve rendered records and audited votes into uncapped records and an audit."""

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.assemble import add_twins, collect_votes, original_native, question_counts, resolve_record


def read_jsonl(path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def assemble(envelopes, vote_envelopes):
    """Preserve native replay records and resolve all requested monitor rows."""
    votes = collect_votes(vote_envelopes)
    records, audits = [], []
    identities = set()
    for envelope in envelopes:
        record = deepcopy(envelope["record"])
        meta = record.setdefault("_meta", {})
        record_id = record.get("record_id", meta.get("record_id"))
        if not record_id or record_id in identities:
            raise ValueError("Every rendered record needs a unique stable record_id.")
        identities.add(record_id)
        meta["record_id"] = record_id
        if envelope.get("native_record"):
            meta["native_record"] = True
        if original_native(record):
            if any("label" not in row for row in record["questions"].values()):
                raise ValueError("A native replay record lost its original labels.")
            records.append(record)
            continue
        side = envelope.get("side", {})
        resolved, audit = resolve_record(record, votes.get(record_id, {}),
            source_labels=side.get("source_labels", ()), construction=side.get("construction"))
        records.append(add_twins(resolved))
        audits.append({"record_id": record_id, **audit})
    unknown = set(votes) - identities
    if unknown:
        raise ValueError("Teacher votes refer to records absent from the assembly input.")
    return records, {"records": len(records), "questions": question_counts(records), "resolution": audits,
                     "clashes_by_source": dict(Counter(audit["source"] for audit in audits for _ in audit["clashes"]))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--votes", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    records, audit = assemble(read_jsonl(args.records), [vote for path in args.votes for vote in read_jsonl(path)])
    audit["inputs"] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [args.records, *args.votes]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    args.audit.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(records), "output": str(args.output), "audit": str(args.audit)}))


if __name__ == "__main__":
    main()
