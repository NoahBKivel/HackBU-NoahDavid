"""Run isolated Claude Code tasks with durable traces and spending reservations."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Iterator
from filelock import FileLock
from .agent_runs_rules import check_function_boundary, write_diffs


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Serialize ledger changes between processes with an exclusive lock file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path), timeout=30):
        yield


def snapshot(folder: Path) -> dict[str, str]:
    """Hash all regular files in a task workspace without following links."""
    result = {}
    for path in folder.rglob("*"):
        if path.is_file() and not path.is_symlink() and ".git" not in path.parts:
            result[path.relative_to(folder).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class AgentRunner:
    """Manage isolated task containers under a shared spend cap and cutoff."""

    def __init__(self, root: Path, image: str = "intent-agent-run") -> None:
        self.root = root.resolve()
        self.image = image
        self.output = self.root / "results/agent-runs"
        self.output.mkdir(parents=True, exist_ok=True)
        self.budget = json.loads((root / "results/budget.json").read_text())

    def reserve(self, job_id: str, maximum: float) -> bool:
        """Reserve the full maximum charge before starting a billable run."""
        with file_lock(self.root / "results/spend.lock"):
            path = self.output / "reservations.json"
            state = json.loads(path.read_text()) if path.exists() else {}
            used = sum(float(x.get("charged_usd", x["maximum_usd"])) for x in state.values())
            if job_id in state or used + maximum > self.budget["agent_runs_budget_usd"]:
                return False
            ledger = self.root / "results/spend.jsonl"
            global_used = sum(float(json.loads(line).get("cost_usd") or json.loads(line).get("reserved_charge_usd", 0))
                              for line in ledger.read_text().splitlines()) if ledger.exists() else 0
            active = sum(x["maximum_usd"] for x in state.values() if "charged_usd" not in x)
            if global_used + active + maximum > self.budget["total_cap_usd"]:
                return False
            state[job_id] = {"maximum_usd": maximum, "reserved_at": datetime.now(timezone.utc).isoformat()}
            path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return True

    def settle(self, job_id: str, cost: float | None, usage: dict[str, Any]) -> None:
        """Record actual usage and release only demonstrably unused reservations."""
        with file_lock(self.root / "results/spend.lock"):
            path = self.output / "reservations.json"
            state = json.loads(path.read_text())
            charged = state[job_id]["maximum_usd"] if cost is None else cost
            state[job_id]["charged_usd"] = charged
            state[job_id]["actual_cost_known"] = cost is not None
            path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            record = {"job_id": job_id, "category": "agent_runs", "cost_usd": cost,
                      "reserved_charge_usd": charged, "usage": usage,
                      "timestamp": datetime.now(timezone.utc).isoformat()}
            with (self.root / "results/spend.jsonl").open("a", encoding="utf-8") as output:
                output.write(json.dumps(record) + "\n")

    def run(self, task: dict[str, Any], maximum: float = 0.5, turns: int = 12,
            wall_seconds: int = 600) -> dict[str, Any]:
        """Execute one prepared task and retain native sessions, snapshots and billing."""
        job_id = task["job_id"]
        cutoff = datetime.fromisoformat(self.budget["agent_run_cutoff"])
        if datetime.now(timezone.utc) >= cutoff or not self.reserve(job_id, maximum):
            return {"job_id": job_id, "status": "not_started"}
        folder = self.output / job_id
        folder.mkdir(exist_ok=False)
        work = folder / "work"
        shutil.copytree(task["source_dir"], work, symlinks=False,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".env"))
        (folder / "home").mkdir()
        before = snapshot(work)
        (folder / "before.json").write_text(json.dumps(before), encoding="utf-8")
        (folder / "task.json").write_text(json.dumps(task, indent=2), encoding="utf-8")
        (folder / "prompt.txt").write_text(task["prompt"], encoding="utf-8")
        command = ["docker", "run", "--name", "intent-" + job_id, "--memory", "2g",
                   "--cpus", "1", "--pids-limit", "256", "--cap-drop", "ALL",
                   "--security-opt", "no-new-privileges", "-e", "ANTHROPIC_API_KEY",
                   "-e", "HOME=/job/home", "-v", str(folder) + ":/job", "-w", "/job/work",
                   "--user", "1100:1100", task.get("image", self.image), "claude", "-p", "--bare",
                   "--model", task["model"], "--max-turns", str(turns),
                   "--max-budget-usd", str(maximum), "--output-format", "stream-json",
                   "--verbose", "--permission-mode", "bypassPermissions",
                   "--tools", "Read,Write,Edit,Grep,Glob,TodoWrite,AskUserQuestion", "--", task["prompt"]]
        started = time.monotonic()
        status = "completed"
        with (folder / "stdout.jsonl").open("wb") as stdout, (folder / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr)
            launch = {"job_id": job_id, "pid": process.pid, "log": str(folder / "stdout.jsonl"),
                      "started_at": datetime.now(timezone.utc).isoformat(), "model": task["model"]}
            (folder / "launch.json").write_text(json.dumps(launch), encoding="utf-8")
            print(json.dumps({"launched": launch}), flush=True)
            remaining = max(1, (cutoff - datetime.now(timezone.utc)).total_seconds())
            try:
                process.wait(timeout=min(wall_seconds, remaining))
            except subprocess.TimeoutExpired:
                status = "wall_limit"
                subprocess.run(["docker", "kill", "intent-" + job_id], capture_output=True, timeout=30)
                process.wait(timeout=30)
        after = snapshot(work)
        (folder / "after.json").write_text(json.dumps(after), encoding="utf-8")
        changes = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
        write_diffs(Path(task["source_dir"]), work, changes, folder / "changes.diff")
        if task.get("function"):
            check = check_function_boundary(Path(task["source_dir"]), work, task["target"],
                                             task["function"], changes)
            (folder / "rule-evidence.json").write_text(json.dumps(check, indent=2), encoding="utf-8")
        result = {"job_id": job_id, "status": status, "returncode": process.returncode,
                  "wall_seconds": time.monotonic() - started, "changed_files": changes}
        cost = None
        usage = {}
        for line in (folder / "stdout.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if item.get("type") == "result":
                cost = item.get("total_cost_usd")
                usage = item.get("usage", {})
                result["cli_result"] = item
        self.settle(job_id, cost, usage)
        result["cost_usd"] = cost
        (folder / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        subprocess.run(["docker", "rm", "intent-" + job_id], capture_output=True, timeout=30)
        print(json.dumps({"finished": result["job_id"], "cost_usd": cost}), flush=True)
        return result


def run_tasks(root: Path, tasks: list[dict[str, Any]], workers: int = 20) -> list[dict[str, Any]]:
    """Run a prepared task list with bounded parallelism and durable per-job output."""
    runner = AgentRunner(root)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(runner.run, tasks))
