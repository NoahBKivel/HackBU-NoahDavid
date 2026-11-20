"""Resolve a terminated, socket-denied pilot without discarding ownership evidence."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher.openai_client_state import OpenAIBudget, atomic_json, utc_now

proof_path = ROOT / "results/openai-labelling/sandbox-transport-resolution.json"
if proof_path.exists():
    raise RuntimeError("The failed sandbox pilot was already resolved; this one-time operation cannot run again.")
proof = {"verified_at": utc_now(), "failure": "sandbox_socket_permission_denied",
         "reason_type": "PermissionError", "winerror": 10013, "errno": 13,
         "authenticated_pilot_process_exit": 1, "authenticated_pilot_process_active": False,
         "probe": "Unauthenticated GET https://api.openai.com/v1/models, system and direct openers.",
         "transport": "Default sandbox forbids socket creation before an HTTP request can be sent.",
         "resolution": "Zero billable requests sent; retry requires authorized network escalation."}
atomic_json(proof_path, proof)
budget = OpenAIBudget(ROOT / "results/openai-spend.jsonl")
latest = {}
for row in budget._rows():
    if row.get("provider") == "openai":
        latest[row["call_id"]] = row
resolved = 0
for call_id, row in latest.items():
    if row["status"] == "reserved":
        budget.settle(call_id, 0.0, failure="sandbox_socket_permission_denied",
                      no_request_sent=True, proof="results/openai-labelling/sandbox-transport-resolution.json")
        resolved += 1
claim_root = (ROOT / "data/votes/claims").resolve()
archive = (ROOT / "results/openai-labelling/failed-sandbox-claims").resolve()
if not claim_root.is_relative_to(ROOT.resolve()) or not archive.is_relative_to(ROOT.resolve()):
    raise RuntimeError("Claim paths escaped the training workspace.")
archive.mkdir(parents=True, exist_ok=True)
archived = 0
for path in claim_root.glob("*.json"):
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("owner") != "openai-direct" or value.get("status") == "completed":
        continue
    value.update(status="failed_preconnection", no_request_sent=True,
                 resolution="sandbox-transport-resolution.json", resolved_at=utc_now())
    atomic_json(path, value)
    path.rename(archive / path.name)
    archived += 1
print(json.dumps({"settled_zero_calls": resolved, "archived_failed_claims": archived,
                  "openai_exposure_usd": budget.exposure()}))
