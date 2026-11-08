"""Verify loaded model identity and full-question calibration through deployed calls."""

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

from backend_driver import Driver
from verify_core import read_records
from verify_done import ordinary, session

FOLDER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FOLDER.parents[1]))
from David.monitor_format import EVERY_EVENT


def distribution(raw: dict, config: dict, shipped: float) -> dict:
    """Compute calibrated probabilities independently from normalized power weights."""
    temperature = config.get("T", shipped)
    offsets = config.get("b", 0)
    if isinstance(offsets, dict):
        bias = {key: offsets.get(key, 0) for key in raw}
    else:
        if offsets:
            assert set(raw) == {"false", "true"}
        bias = {key: offsets if key == "true" else 0 for key in raw}
    maximum = max(bias.values())
    weights = {key: p ** (1 / temperature) * math.exp(bias[key] - maximum) for key, p in raw.items()}
    total = sum(weights.values())
    assert total > 0
    return {key: value / total for key, value in weights.items()}


def verify(records: list[dict], delivered: list[dict], calibration: dict, source: str,
           checkpoint: str | None = None) -> dict:
    """Compare the model's trace, its configured identity and acted risk to independent math."""
    loaded = next(record for record in reversed(records) if "loaded" in record)
    assert loaded["source"] == source
    assert loaded["calibration"] == calibration
    assert loaded["loaded_temperature"] == 1 and loaded["flag_at"] == .5
    if checkpoint:
        assert loaded["loaded"] == checkpoint
    count, max_error = 0, 0.0
    fireable = (set(EVERY_EVENT) | {"G2", "G5", "M8"}) - {"G1"}
    for result in delivered:
        assert result["details"]["source"] == source
        if result["details"].get("skipped"):
            continue
        trace = next(record for record in reversed(records) if record.get("event_id") == result["event_id"])
        expected = {}
        for request in trace["probabilities"]:
            for key, raw in request["raw"].items():
                computed = distribution(raw, calibration.get(key.split("#")[0], {}), loaded["shipped_temperature"])
                for option, value in computed.items():
                    error = abs(value - request["calibrated"][key][option])
                    max_error = max(error, max_error)
                    assert error <= 1e-12, (key, option, error)
                count += 1
                expected[key] = computed
        scores = {key: values["broken"] if key.startswith("G2#") else values["true"]
                  for key, values in expected.items() if key.split("#")[0] in fireable}
        risk = max(scores.values(), default=0.0)
        assert math.isclose(result["risk"], risk, rel_tol=0, abs_tol=1e-12)
        assert result["flagged"] == (risk >= .5)
        fired = {key: value for key, value in scores.items() if value >= .5}
        if "G1" in expected:
            drift = 1 - expected["G1"]["true"]
            assert math.isclose(result["drift"], drift, rel_tol=0, abs_tol=1e-12)
            if drift > .5:
                fired["G1"] = drift
        assert set(result["details"]["fired"]) == set(fired)
        for key, value in fired.items():
            assert math.isclose(result["details"]["fired"][key], value, rel_tol=0, abs_tol=1e-12)
    assert count > 0
    return {"loaded": loaded, "rows_compared": count, "max_calibration_error": max_error}


def run(target: str, output: Path, calibration: dict, source: str, checkpoint: str | None) -> dict:
    """Drive the deployed class and preserve the actual serving evidence."""
    output.mkdir(parents=True, exist_ok=True)
    driver = Driver(target)
    driver.warmup()
    responses = session(driver, ordinary(), "calibration")
    (output / "responses.json").write_text(json.dumps(responses, indent=2), encoding="utf-8")
    deadline = time.monotonic() + 30
    ids = {r["event_id"] for r in responses["delivered"] if not r["details"].get("skipped")}
    while True:
        logs = subprocess.run([sys.executable, "-m", "modal", "app", "logs", driver.app, "--since", "2h"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
                              env={**os.environ, "PYTHONUTF8": "1"}, check=True)
        path = output / "model.log"
        path.write_bytes(logs.stdout)
        records = read_records(path)
        if any("loaded" in r for r in records) and ids <= {r.get("event_id") for r in records}:
            break
        assert time.monotonic() < deadline, "Required model identity and fixture traces were not logged."
        time.sleep(.5)
    evidence = verify(records, responses["delivered"], calibration, source, checkpoint)
    evidence.update({"app": driver.app, "checks": {"calibration on the serving path": True,
                     "selected-model-config" if checkpoint else "stock-fallback-config": True}})
    (output / "probe.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence), flush=True)
    return evidence


def main() -> int:
    """Require copied calibration and checkpoint identity for selected-model verification."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("dev", "live"), default="dev")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--calibration", type=Path)
    args = parser.parse_args()
    if args.receipt:
        assert args.calibration, "Selected-model verification needs the actual copied calibration file."
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        assert receipt["target"] == args.target and receipt["deployed"]
        source, checkpoint = receipt["selected"]["source"], receipt["selected"]["checkpoint"]
        calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    else:
        assert not args.calibration
        source, checkpoint, calibration = "stock-kev", None, {}
    run(args.target, args.output, calibration, source, checkpoint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
