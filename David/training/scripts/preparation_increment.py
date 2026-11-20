"""Publish the actual gaming additions and newly authorized RF evidence."""

from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    """Exclude unchanged gaming rows and retain the corrected CATCH evidence."""
    output = ROOT / "data/prepared/incremental-sources-8191.jsonl"
    temporary = output.with_suffix(".jsonl.tmp")
    counts = Counter()
    sources = ["catch_hacking", "aria_reward_hacking", "olmo_reward_hacking", "terminal_wrench", "reward_hack_lcb", "if_multi"]
    with temporary.open("w", encoding="utf-8", newline="\n") as target:
        for source in sources:
            previous = ROOT / "data/prepared/export-snapshots/gaming-export-manifest" / (source + ".jsonl")
            seen = set()
            if previous.exists() and source != "catch_hacking":
                seen = {digest(json.loads(line)) for line in previous.open(encoding="utf-8") if line.strip()}
            with (ROOT / "data/converted" / (source + ".jsonl")).open(encoding="utf-8-sig") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if source == "if_multi" and row["meta"].get("objective") == ["RF"]:
                        continue
                    if digest(row) in seen:
                        continue
                    if source == "if_multi":
                        row["meta"]["source_evidence_sha256"] = digest(row["side"])
                    target.write(json.dumps(row, ensure_ascii=False) + "\n")
                    counts[source] += 1
    temporary.replace(output)
    manifest = {"raw_records": sum(counts.values()), "sources": dict(counts),
        "path": str(output.relative_to(ROOT)), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "note": "CATCH, Aria and OLMo include repaired prior rows. Other gaming rows are actual additions. AgentIF is prepared separately. IF answers carry completed checker evidence."}
    (ROOT / "results/preparation/incremental-sources-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
