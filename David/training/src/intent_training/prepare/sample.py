"""Select a small stratified random packet from actual converted JSONL."""

import ctypes
import json
from pathlib import Path
import random


def available_ram_gib():
    class Status(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in
            ("total", "available", "page_total", "page_available", "virtual_total", "virtual_available", "extended")]
    status = Status()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("The owner RAM gate could not be measured.")
    return status.available / 1024 ** 3


def build(root, destination, seed=None):
    """Keep only selected rows in memory and retain original event and label bodies."""
    seed = random.SystemRandom().getrandbits(64) if seed is None else seed
    rng = random.Random(seed)
    root, destination = Path(root), Path(destination)
    specs = [
        ("native_decision", "converted/kev_replay.jsonl", 8, "decision"),
        ("native_hard", "converted/kev_replay.jsonl", 2, "hard"),
        ("native_tasksource", "converted/tasksource.jsonl", 2, None),
        ("C_constraint", "constructions/constraint.jsonl", 1, None),
        ("C_priority", "constructions/priority.jsonl", 1, None),
        ("C_goal_splice", "constructions/goal_splice.jsonl", 2, None),
        ("screen", "constructions/overflow_screen.jsonl", 1, None),
        ("V_cheatbench", "converted/cheatbench.jsonl", 4, None),
        ("V_catch", "converted/catch_hacking.jsonl", 4, None),
        ("T_misalignment", "converted/agent_misalignment.jsonl", 5, None),
        ("T_preference", "converted/helpsteer3.jsonl", 5, None),
        ("T_tau", "converted/tau2.jsonl", 5, None),
        ("benign_sessions", "converted/agent_sessions.jsonl", 3, None),
        ("benign_honest", "converted/monitoringbench_honest.jsonl", 3, None),
        ("RF", "converted/if_multi.jsonl", 2, None),
    ]
    chosen, counts = [], {}
    for kind, relative, wanted, suite_kind in specs:
        selected = []
        eligible = 0
        for number, line in enumerate((root / "data" / relative).open(encoding="utf-8-sig"), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            suite = str(row["meta"].get("suite", "")).lower()
            if suite_kind == "hard" and "hard" not in suite:
                continue
            if suite_kind == "decision" and "hard" in suite:
                continue
            eligible += 1
            item = (row, {"kind": kind, "path": relative, "line": number})
            if len(selected) < wanted:
                selected.append(item)
            else:
                index = rng.randrange(eligible)
                if index < wanted:
                    selected[index] = item
        if len(selected) != wanted:
            raise ValueError(f"The actual source has {eligible} eligible {kind} rows; {wanted} were requested.")
        chosen.extend(selected)
        counts[kind] = {"selected": len(selected), "eligible": eligible}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as output:
        for row, _ in chosen:
            output.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    report = {"seed": seed, "raw_rows": len(chosen), "counts": counts,
              "provenance": [item for _, item in chosen], "prepared": False}
    destination.with_suffix(".manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"packet": str(destination), "raw_rows": len(chosen), "counts": counts}), flush=True)
    return report
