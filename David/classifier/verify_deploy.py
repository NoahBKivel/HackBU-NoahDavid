"""Checks the deployed classifier end to end, the way Noah's backend calls it.

    python David/classifier/verify_deploy.py

1. warmup() on the class (boots a container if none is running) and its wall time.
2. classify() on Noah's four sample events (Noah/backend/samples), each validated against the exact
   `Result` model copied from Noah/backend/app.py.
3. The late path: an event with the test-only `_test_sleep_s` = 9 finishes after the backend's 8 s wait,
   so its result must ride on the next response for the session, exactly once.
Every run uses a fresh session id, so runs do not see each other's instructions or late results.
"""
import json
import pathlib
import sys
import time
import uuid
from typing import Any, Optional

import modal
from pydantic import BaseModel, ConfigDict, Field

ROOT = pathlib.Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "Noah" / "backend" / "samples"


# ---- copied verbatim from Noah/backend/app.py (do not edit there) ----
class Action(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    level: Optional[str] = None
    text: Optional[str] = None


class Result(BaseModel):
    """What classify() must return (CONTRACT.md section 4). Used to catch
    shape mismatches as soon as the real classifier is connected."""

    model_config = ConfigDict(extra="allow")

    schema_version: int = 1
    event_id: str
    monitor: str
    flagged: bool
    risk: Optional[float] = Field(default=None, ge=0, le=1)
    details: dict[str, Any] = {}
    actions: list[Action] = []
    pending: bool = False
# ---- end of copy ----


def check(result: dict, event: dict) -> None:
    Result.model_validate(result)
    for late in result.get("late_results", []):
        Result.model_validate(late)
    assert result["event_id"] == event["event_id"], "event_id not echoed"
    assert result["actions"] == [], "actions must be empty for the placeholder"
    assert result["drift"] is None and result["drift_rate"] is None


def main() -> int:
    classifier = modal.Cls.from_name("intent-monitor", "Classifier")()
    t = time.perf_counter()
    print("warmup:", classifier.warmup.remote(), f"{time.perf_counter() - t:.1f} s")

    session = f"verify-{uuid.uuid4().hex[:12]}"
    for path in sorted(SAMPLES.glob("*.json")):
        event = {**json.loads(path.read_text(encoding="utf-8")), "session_id": session}
        t = time.perf_counter()
        result = classifier.classify.remote(event)
        check(result, event)
        print(f"{path.name}: risk={result['risk']} flagged={result['flagged']} "
              f"details={result['details']} round_trip={time.perf_counter() - t:.2f} s")

    slow = {**json.loads((SAMPLES / "3_tool_bash_deletes_tests.json").read_text(encoding="utf-8")),
            "session_id": session, "event_id": "verify-slow-event", "_test_sleep_s": 9}
    t = time.perf_counter()
    slow_result = classifier.classify.remote(slow)
    check(slow_result, slow)
    print(f"slow event: classify_ms={slow_result['details']['classify_ms']} round_trip={time.perf_counter() - t:.1f} s "
          f"late_results={'late_results' in slow_result}")

    nxt = {**json.loads((SAMPLES / "4_turn_completed.json").read_text(encoding="utf-8")),
           "session_id": session, "event_id": "verify-next-event"}
    first = classifier.classify.remote(nxt)
    check(first, nxt)
    delivered = [r["event_id"] for r in first.get("late_results", [])]
    print("next event late_results:", delivered)
    again = classifier.classify.remote({**nxt, "event_id": "verify-after-next"})
    check(again, nxt | {"event_id": "verify-after-next"})
    redelivered = [r["event_id"] for r in again.get("late_results", [])]
    print("event after that late_results:", redelivered)
    assert delivered == ["verify-slow-event"], "late result not delivered on the next response"
    assert redelivered == [], "late result delivered twice"
    assert first["late_results"][0]["risk"] == slow_result["risk"]
    print("OK: all results match Noah's Result model; late result delivered exactly once")
    return 0


if __name__ == "__main__":
    sys.exit(main())
