"""Gate local workloads by the owner's RAM threshold and shared worker limit."""

from contextlib import contextmanager
import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import sys
from typing import Iterator
from uuid import uuid4

from filelock import FileLock


def available_gib() -> float:
    """Read available physical memory without inspecting or changing processes."""
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in (
                "total_physical", "available_physical", "total_page", "available_page",
                "total_virtual", "available_virtual", "extended_virtual")]

    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("Available physical memory could not be measured.")
    return status.available_physical / (1024 ** 3)


@contextmanager
def lease(policy_path: Path, state_path: Path, name: str, memory_mib: int) -> Iterator[dict]:
    """Reserve one local slot only while enough RAM remains for the requested work."""
    policy = json.loads(policy_path.read_text(encoding="utf-8-sig"))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    lock = FileLock(str(state_path) + ".lock")
    with lock:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        count = len(state) + int(policy.get("legacy_reservations", 0))
        free = available_gib()
        required = float(policy["minimum_available_gib"]) + memory_mib / 1024
        if count >= int(policy["worker_limit"]):
            raise RuntimeError("The shared local worker limit is reached.")
        if free <= required:
            raise RuntimeError(f"Local RAM gate closed: {free:.3f} GiB available; {required:.3f} GiB required.")
        if any(item["name"] == name for item in state.values()):
            raise RuntimeError("A local worker with this name already holds a lease.")
        state[token] = {"name": name, "memory_mib": memory_mib, "available_gib_at_start": free}
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    try:
        yield state[token]
    finally:
        with lock:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state.pop(token, None)
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main() -> int:
    """Launch one foreground workload under its shared resource lease."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--memory-mib", type=int, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.memory_mib < 0:
        parser.error("A command and a nonnegative memory allowance are required.")
    try:
        with lease(root / "local-resource-policy.json", root / "results/local-workers/leases.json",
                   args.name, args.memory_mib) as evidence:
            print(json.dumps({"local_lease": evidence}), flush=True)
            return subprocess.run(command, shell=False).returncode
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 75


if __name__ == "__main__":
    sys.exit(main())
