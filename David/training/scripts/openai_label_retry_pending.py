"""Complete failed main families once without repeating active or validated votes."""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher.claims import batch_claim_path
from intent_training.teacher.openai_client_live import PairedLiveClient
from openai_label import load_key


def main():
    """Retry only owned pending slots with one older, paid, settled response."""
    client = PairedLiveClient(key=load_key(Path(sys.argv[1])),
        pricing=json.loads((ROOT / "openai-label-pricing.json").read_text(encoding="utf-8")),
        ledger=ROOT / "results/openai-spend.jsonl", claims=ROOT / "data/votes/claims",
        stop_file=ROOT / "results/openai-labelling/STOP_ADMISSIONS", max_concurrency=8)
    active = set()

    def collect():
        nonlocal active
        ready, active = wait(active, return_when=FIRST_COMPLETED)
        for result in ready:
            try:
                print(json.dumps(result.result()), flush=True)
            except Exception as error:
                print(json.dumps({"error_type": type(error).__name__, "error": str(error)}), flush=True)

    with ThreadPoolExecutor(max_workers=8) as pool:
        with (ROOT / "data/votes/limit-8191/continuous-queue.jsonl").open(encoding="utf-8") as queue:
            for line in queue:
                if client.stopped():
                    break
                item = json.loads(line)
                batch = item["batch"]
                if batch["pass"] != "main" or item["allocation"] != "paired":
                    continue
                path = batch_claim_path(client.claims, batch)
                if not path.exists():
                    continue
                claim = json.loads(path.read_text(encoding="utf-8"))
                if claim["owner"] != "openai-continuous" or claim["status"] == "completed":
                    continue
                latest = {row["call_id"]: row for row in client.budget._rows()}
                for slot in claim["required_families"]:
                    if claim["families"][slot]["status"] != "pending":
                        continue
                    calls = [row for row in latest.values()
                             if row.get("batch_id") == batch["batch_id"] and row.get("family") == slot]
                    if any(row["status"] == "reserved" for row in calls):
                        continue
                    paid = [row for row in calls if row.get("usage")]
                    if len(paid) != 1:
                        continue
                    elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(paid[0]["completed_at"])
                    if elapsed.total_seconds() < 60 or Path(item["outputs"][slot]).exists():
                        continue
                    while len(active) >= 8:
                        collect()
                    active.add(pool.submit(client.vote, item, slot, claim["owner"]))
        while active:
            collect()


if __name__ == "__main__":
    main()
