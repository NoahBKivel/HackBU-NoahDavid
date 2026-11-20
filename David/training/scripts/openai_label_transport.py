"""Diagnose connectivity without reading credentials or making a billable request."""

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
reservation = ROOT / "data/votes/limit-10239/api_reserved.json"
reservation.parent.mkdir(parents=True, exist_ok=True)
rows = [json.loads(line) for line in (ROOT / "data/prepared/limit-10239/main.jsonl").read_text(
    encoding="utf-8").splitlines() if line.strip()]
reservation.write_text(json.dumps({"record_ids": [row["record_id"] for row in rows],
    "remaining_to_reserve": max(0, 50 - len(rows)), "owner": "openai-direct"}), encoding="utf-8")
print(json.dumps({"reserved_records": len(rows)}), flush=True)
for mode in ("system", "direct"):
    opener = build_opener() if mode == "system" else build_opener(ProxyHandler({}))
    try:
        response = opener.open("https://api.openai.com/v1/models", timeout=10)
        print(json.dumps({"mode": mode, "http_status": response.status}), flush=True)
    except HTTPError as error:
        print(json.dumps({"mode": mode, "http_status": error.code}), flush=True)
    except URLError as error:
        print(json.dumps({"mode": mode, "reason_type": type(error.reason).__name__,
                          "reason": str(error.reason)[:300],
                          "errno": getattr(error.reason, "errno", None)}), flush=True)
