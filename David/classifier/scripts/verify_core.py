"""Measure the deployed serving core through backend-style calls and model logs."""

import argparse
import json
import math
import subprocess
import sys
import time
import uuid
from pathlib import Path

from backend_driver import Driver

FOLDER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FOLDER))
from verify_deploy import check


def read_records(path: Path) -> list[dict]:
    """Read structured model records without depending on CLI timestamp formatting."""
    records = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        offset = line.find("{")
        if offset < 0:
            continue
        try:
            record, _ = json.JSONDecoder().raw_decode(line[offset:])
            if isinstance(record, dict):
                records.append(record)
        except ValueError:
            continue
    return records


def run(target: str, output: Path, require_calibration: bool = False) -> dict:
    """Verify stock loading, skips, calibration and exactly-once late delivery."""
    output.mkdir(parents=True, exist_ok=True)
    driver = Driver(target)
    sid = f"core-{uuid.uuid4().hex}"
    results = []
    checks = {}
    log_path = output / "model.log"

    def event(seq: int, kind: str = "tool_completed", tool: str = "Read", **extra) -> dict:
        return {"schema_version": 1, "session_id": sid, "event_id": f"{sid}-{seq}", "seq": seq,
                "type": kind, "new_items": [], "agent_text": "", "agent_thinking": "", "todos": [],
                "action": {"tool": tool, "args": {"file_path": "README.md"}, "denied": None,
                           "result_text": "Read complete.", "is_error": False, "file_changes": []}, **extra}

    def send(e: dict) -> dict:
        result = driver.send(e)
        if result.get("pending"):
            original, call = driver.pending[-1]
            completed = call.get(timeout=40)
            check(completed, original)
            results.append({"event": original, "result": completed, "backend_pending": True})
            return result
        results.append({"event": e, "result": result, "backend_pending": False})
        return result

    try:
        print(f"Warming {driver.app}.", flush=True)
        assert driver.warmup() == {"ok": True}
        assert driver.classifier.warmup.remote() == {"ok": True}
        checks["warmup"] = True
        skipped = [
            event(1, "session_started", action=None,
                  new_items=[{"kind": "user_instruction", "text": "Make the test suite faster without reducing coverage."}]),
            event(2), event(3, tool="AskUserQuestion"),
            event(4, "turn_completed", action=None, turn={"reason": "aborted"}),
        ]
        for e in skipped:
            result = send(e)
            assert not result.get("pending"), "A warmed skipped event exceeded the backend wait."
            assert result["risk"] is None and result["details"]["skipped"] and result["actions"] == []
        checks["skipped events"] = True
        normal = event(5, tool="Bash", action={"tool": "Bash", "args": {"command": "pytest -q"},
                       "result_text": "1 passed in 0.1s", "denied": None, "is_error": False, "file_changes": []})
        normal_result = send(normal)
        assert not normal_result.get("pending"), "The warmed calibration fixture exceeded the backend wait."
        print("Testing late delivery.", flush=True)
        slow = event(6, _test_sleep_s=9)
        pending = send(slow)
        assert pending.get("pending"), "The nine-second event did not exceed the backend wait."
        first = send(event(7))
        assert [r["event_id"] for r in first.get("late_results", [])] == [slow["event_id"]]
        assert not send(event(8)).get("late_results")
        old = event(9, backend_sent_at=time.time() - 9)
        call = driver.classifier.classify.spawn(old)
        result = driver.receive(old, call)
        assert not result.get("pending")
        results.append({"event": old, "result": result, "backend_pending": False})
        next_result = send(event(10))
        assert [r["event_id"] for r in next_result.get("late_results", [])] == [old["event_id"]]
        assert not send(event(11)).get("late_results")
        checks["late results"] = True
        checks["contract"] = True
        deadline = time.monotonic() + 30
        while True:
            fetched = subprocess.run([sys.executable, "-m", "modal", "app", "logs", driver.app, "--since", "30m"],
                                     cwd=FOLDER.parents[1], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            log_path.write_bytes(fetched.stdout)
            records = read_records(log_path)
            loaded = next((r for r in reversed(records) if "loaded" in r), None)
            trace = next((r for r in reversed(records) if r.get("event_id") == normal["event_id"]), None)
            if loaded and trace:
                break
            if time.monotonic() >= deadline:
                raise AssertionError("Serving probability logs were not available for independent verification.")
            time.sleep(.25)
        assert loaded["source"] == "stock-kev"
        assert loaded["loaded_temperature"] == 1.0 and loaded["flag_at"] == .5
        parameters = loaded["calibration"].get("M1", {})
        if require_calibration and not parameters:
            raise AssertionError("The selected calibration fixture was not loaded by the container.")
        distribution = trace["probabilities"][0]["raw"]["M1"]
        yes, no = distribution["true"], distribution["false"]
        temperature = parameters.get("T", loaded["shipped_temperature"])
        offset = parameters.get("b", 0.0)
        expected = 0.0 if yes == 0 else 1.0 if no == 0 else 1 / (1 + math.exp(-(math.log(yes) - math.log(no)) / temperature - offset))
        assert math.isclose(normal_result["risk"], expected, rel_tol=0, abs_tol=1e-12)
        assert normal_result["flagged"] == (expected >= .5)
        checks["calibration on the serving path"] = True
        checks["selected-calibration-config" if parameters else "stock-fallback-config"] = True
        evidence = {"app": driver.app, "session_id": sid, "checks": checks, "results": results,
                    "loaded": loaded, "raw": distribution, "expected": expected,
                    "acted_probability": normal_result["risk"]}
        (output / "probe.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(json.dumps({"app": driver.app, "checks": checks, "calibration_error": abs(expected - normal_result["risk"])}), flush=True)
        return evidence
    finally:
        (output / "responses.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


def main() -> int:
    """Run serving checks against the selected app and save their measured evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("dev", "live"), default="dev")
    parser.add_argument("--output", type=Path, default=FOLDER / "results" / "core-dev")
    parser.add_argument("--require-calibration", action="store_true")
    args = parser.parse_args()
    run(args.target, args.output, args.require_calibration)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
