"""Persist concrete initial and tightened vote provenance for the data-gate verifier."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent), str(ROOT / "scripts")]
from teacher_relabel import CLARIFICATIONS


def artifact(path):
    return {"path": str(path.resolve()), "sha256": sha256(path.read_bytes()).hexdigest()}


def main():
    results = ROOT / "data/votes/results/teacher"
    report = json.loads((results / "validation.json").read_text(encoding="utf-8"))
    entries = []
    for folder in ("seed_main", "anchors"):
        manifest = ROOT / "data/votes" / folder / "manifest.json"
        for entry in json.loads(manifest.read_text(encoding="utf-8")):
            if Path(entry["output"]).exists():
                entries.append(entry)
    combined = results / "initial_completed_manifest.json"
    combined.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    relabel_manifest = ROOT / "data/votes/relabel/manifest.json"
    ledger = results / "relabel_ledger.json"
    evidence = {}
    for q, text in CLARIFICATIONS.items():
        tightened = results / f"{q.lower()}_clarification.txt"
        tightened.write_text(text, encoding="utf-8")
        ids = set()
        for entry in entries:
            batch = json.loads(Path(entry["input"]).read_text(encoding="utf-8"))
            ids.update(f"{row['record_id']}:{q}" for row in batch["records"] if q in row["questions"])
        initial = report.get("initial_instruments", report["instruments"]).get(q)
        second = report.get("relabel_instruments", {}).get(q)
        if not second or second["rows"] != len(ids) or not second.get("tightening_required"):
            continue
        evidence[q] = {"rule": "reported failure; labels stand", "relabel_attempts": 1,
                       "initial_instrument": initial, "second_instrument": second,
                       "tightened_prompt": artifact(tightened), "relabel_ledger": artifact(ledger),
                       "initial_vote_manifest": artifact(combined),
                       "relabel_vote_manifest": artifact(relabel_manifest),
                       "initial_vote_ids": sorted(ids), "relabel_vote_ids": sorted(ids)}
    path = results / "relabel_evidence.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"initial_dispatches": len(entries), "complete_relabel_questions": list(evidence)}))


if __name__ == "__main__":
    main()
