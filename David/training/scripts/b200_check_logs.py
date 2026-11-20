"""Save a bounded log sample from the recorded comparison app."""

import json
import re
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1] / "results" / "b200-check"
record = json.loads((root / "modal-call.json").read_text(encoding="utf-8"))
process = subprocess.Popen([sys.executable, "-m", "modal", "app", "logs", record["app_id"]],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    raw = process.communicate(timeout=12)[0]
except subprocess.TimeoutExpired:
    process.kill()
    raw = process.communicate()[0]
(root / "remote.log").write_bytes(raw)
output = raw.decode("utf-8", errors="replace")
match = re.search(r'/training/smoke/([0-9TZ]+)/checkpoint-download.json', output)
if match:
    (root / "availability.json").write_text(json.dumps({"available": True,
        "run_id": match.group(1), "evidence": "The remote smoke wrote checkpoint-download.json."}, indent=2), encoding="utf-8")
print(output[-6000:])
