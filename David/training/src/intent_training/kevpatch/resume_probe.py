"""Compare uninterrupted and killed/resumed executions of the real trainer."""

import json
from pathlib import Path
import subprocess
import time
from typing import Any


def run_process(command: list[str], log: Path, kill_after_save: int | None = None) -> dict[str, Any]:
    """Run a trainer process, optionally killing it after a durable save marker."""
    out = Path(command[command.index("--out") + 1])
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
        started = time.monotonic()
        killed = False
        while process.poll() is None:
            if kill_after_save is not None:
                latest = out / "resume" / "latest.json"
                if latest.exists() and json.loads(latest.read_text())["step"] >= kill_after_save:
                    process.kill()
                    killed = True
                    break
            if time.monotonic() - started > 1200:
                process.kill()
                process.wait()
                raise TimeoutError("A bounded continuation-parity subprocess exceeded its time budget.")
            time.sleep(0.1)
        returncode = process.wait()
    if returncode != 0 and not killed:
        raise RuntimeError(f"A continuation-parity subprocess failed with code {returncode}; see {log}.")
    return {"returncode": returncode, "killed": killed, "seconds": time.monotonic() - started}


def check_resume(config: dict[str, Any], root: Path, command_builder: Any,
                 save: Any) -> dict[str, Any]:
    """Measure actual data order and losses against repeated uninterrupted noise."""
    data = root / "resume-data.jsonl"
    rows = []
    for i in range(32):
        rows.append({"state": "The user requires tests to remain enabled. " * (8 + i % 4),
                     "questions": {"allowed": {"type": "noul", "instructions": "Did the agent preserve the required tests?", "label": bool(i % 2)}},
                     "_meta": {"source": "continuation_probe", "id": f"probe-{i}", "pair_id": f"pair-{i // 2}"}})
    data.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    executions = {}
    for name in ("reference-a", "reference-b", "interrupted"):
        out = root / name
        command = command_builder(config, data, out, 100000)
        command.extend(["--batch", "2", "--accum", "1", "--max_steps", "12",
                        "--save_every_steps", "4", "--snapshot_every_steps", "4"])
        executions[name] = run_process(command, root / f"{name}.log", 4 if name == "interrupted" else None)
        if name == "interrupted":
            executions["resumed"] = run_process(command + ["--resume", "1"], root / "resumed.log")
        save("resume-progress", {"executions": executions})
    traces = {}
    for name in ("reference-a", "reference-b", "interrupted"):
        values = [json.loads(line) for line in (root / name / "step-trace.jsonl").read_text().splitlines()]
        deduped = {value["step"]: value for value in values}
        traces[name] = [deduped[step] for step in sorted(deduped)]
    a, b, continued = (traces[name] for name in ("reference-a", "reference-b", "interrupted"))
    if not len(a) == len(b) == len(continued):
        raise ValueError("Continuation-parity traces have different optimizer-step counts.")
    noise = max(abs(left["loss"] - right["loss"]) for left, right in zip(a, b))
    gap = max(abs(left["loss"] - right["loss"]) for left, right in zip(a, continued))
    identical_order = all(left["records"] == right["records"] == resumed["records"]
                          for left, right, resumed in zip(a, b, continued))
    result = {"status": "PASS" if identical_order and gap <= 2 * noise else "FAIL",
              "steps": len(a), "same_seed_noise_floor": noise, "max_resumed_loss_gap": gap,
              "allowed_gap": 2 * noise, "identical_data_order": identical_order,
              "executions": executions}
    save("resume-parity", result)
    return result
