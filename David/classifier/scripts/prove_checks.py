"""Plant bounded runtime defects and confirm that targeted checks reject them."""

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Restore each source file after capturing the targeted failing test."""
    folder = Path(__file__).resolve().parents[1]
    repo = folder.parents[1]
    output = folder / "results" / "mutations"
    output.mkdir(parents=True, exist_ok=True)
    cases = [
        ("contract", "service.py", '"risk": None', '"risk": 99', "test_service.py::test_skipped_events_accept_context"),
        ("skipped-events", "intake.py", 'if action.get("tool") in READ_TOOLS:', 'if False:', "test_service.py::test_skipped_events_accept_context"),
        ("ordering", "ordering.py", 'max(self.header["last_seq"], seq)', 'max(self.header["last_seq"], seq - 1)', "test_ordering.py::test_missing_sequences_timeout_and_stale"),
        ("late-results", "service.py", '>= 8.0:', '>= 80.0:', "test_service.py::test_backend_timestamp_late_delivery_once_and_persistence"),
        ("calibration", "calibration.py", 'math.log(float(p)) / temperature', 'math.log(float(p)) * temperature', "test_calibration.py::test_calibration_scalar_suffix_and_fallback"),
        ("stock-fallback", "calibration.py", 'self.shipped_temperature = shipped_temperature', 'self.shipped_temperature = 1.0', "test_calibration.py::test_calibration_scalar_suffix_and_fallback"),
        ("dismissal", "findings.py", 'if new_instruction or (', 'if (', "test_service.py::test_dismissed_run_does_not_reopen_until_instruction_on_skipped_read"),
        ("minor-upgrade", "findings.py", 'or severity == "minor":', 'or severity != "minor":', "test_service.py::test_minor_run_finding_upgrades_with_new_evidence"),
        ("turn-end-no-nag", "firing.py", 'dist["broken"]', 'dist["not done"]', "test_service.py::test_turn_end_not_done_sends_no_correction"),
        ("drift-sign", "firing.py", 'answers["G1"]["true"] < 0.5', 'answers["G1"]["true"] >= 0.5', "test_service.py::test_g1_sign_and_pane_window"),
    ]
    results = []
    environment = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    for name, filename, old, new, test in cases:
        path = folder / "src" / "intent_runtime" / filename
        original = path.read_bytes()
        text = original.decode("utf-8")
        if old not in text:
            raise AssertionError(f"Mutation target is absent for {name}.")
        try:
            path.write_text(text.replace(old, new, 1) + "\n", encoding="utf-8")
            command = [sys.executable, "-m", "pytest", "-c", str(folder / "pytest.ini"), str(folder / "tests" / test), "-q"]
            run = subprocess.run(command, cwd=repo, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
            (output / f"{name}-red.txt").write_bytes(run.stdout)
            rejected = run.returncode == 1 and b"failed" in run.stdout
            results.append({"check": name, "exit_code": run.returncode, "rejected": rejected})
            print(f"{name}: {'rejected' if rejected else 'NOT REJECTED'}", flush=True)
        finally:
            path.write_bytes(original)
    (output / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0 if all(result["rejected"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
