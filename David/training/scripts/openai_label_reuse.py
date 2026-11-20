"""Join verified teacher votes to freshly rendered complete payload hashes."""

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.prepare.priority import teacher_payload
from intent_training.teacher.claims import teacher_input_hash
from intent_training.teacher.dispatch import validate_vote
from intent_training.teacher.vote_allocation import required_families
from intent_training.teacher.openai_client_state import atomic_json, utc_now


def resolve(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


cache = defaultdict(dict)
errors = []
manifests = [ROOT / "data/votes/openai_pilot_10k/manifest.json",
             ROOT / "data/votes/openai_pilot_10k_next21/manifest.json",
             ROOT / "data/votes/limit-10239/api-bulk-constructions/manifest.json"]
for path in manifests:
    for entry in json.loads(path.read_text(encoding="utf-8")):
        output = resolve(entry["output"])
        if not output.exists():
            continue
        batch = json.loads(resolve(entry["input"]).read_text(encoding="utf-8"))
        records = {row["record_id"]: row for row in batch["records"]}
        with output.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                vote = json.loads(line)
                validate_vote(vote, batch, entry["model_family"])
                fingerprint = teacher_input_hash(records[vote["record_id"]])
                cache[fingerprint][entry["model_family"]] = {"vote_output": str(output),
                    "batch_id": batch["batch_id"], "record_id": vote["record_id"], "vote": vote}
index = ROOT / "data/votes/limit-10239/codex_validated_records.jsonl"
if index.exists():
    for line in index.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            cache[row["teacher_input_sha256"]][row["model_family"]] = row
fresh_root = ROOT / "data/prepared/timing-sample-8191"
producer = json.loads((fresh_root / "manifest.json").read_text(encoding="utf-8"))
if producer["state_budget"] != 8191:
    raise ValueError("The fresh producer does not certify the current state budget.")
results = []
counts = Counter()
ready_groups = Counter()
available_groups = Counter()
for line in (fresh_root / "main.jsonl").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    record = json.loads(line)
    payload = teacher_payload(record)
    fingerprint = teacher_input_hash(payload)
    if fingerprint != record["_meta"]["teacher_input_sha256"]:
        raise ValueError("A fresh payload differs from its producer-certified hash.")
    if record["_meta"]["validated_length"] != 8191:
        raise ValueError("A fresh record has the wrong validated state length.")
    try:
        required = required_families(record)
        allocation_error = None
    except ValueError as error:
        required = ()
        allocation_error = str(error)
    meta = record["_meta"]
    construction = meta.get("construction") or meta.get("construction_type") or meta.get("record_kind") == "construction"
    group = "construction" if construction else "judgment" if required == ("sol", "terra") else "rest" if required else "unknown"
    cached = cache.get(fingerprint, {})
    ready = bool(required) and all(family in cached for family in required)
    counts["fresh_main"] += 1
    counts["sol_hash_hits"] += "sol" in cached
    counts["terra_hash_hits"] += "terra" in cached
    counts["allocation_complete"] += ready
    available_groups[group] += 1
    ready_groups[group] += ready
    results.append({"record_id": record["record_id"], "teacher_input_sha256": fingerprint,
                    "source": record["source"], "priority_group": group,
                    "required_families": list(required), "allocation_error": allocation_error,
                    "cached_families": list(cached), "allocation_complete": ready,
                    "missing_families": [family for family in required if family not in cached],
                    "cached_votes": cached})
output = ROOT / "data/votes/limit-8191/control"
atomic_json(output / "cache-join.json", {"observed_at": utc_now(), "state_budget": 8191,
            "counts": dict(counts), "ready_by_priority_group": dict(ready_groups),
            "available_by_priority_group": dict(available_groups), "records": results,
            "producer_errors_excluded": producer["errors"],
            "native_rows_present": producer["counts"].get("native", 0)})
print(json.dumps({"counts": dict(counts), "ready_by_priority_group": dict(ready_groups),
                  "available_by_priority_group": dict(available_groups),
                  "native_rows_present": producer["counts"].get("native", 0),
                  "output": str(output / "cache-join.json")}))
