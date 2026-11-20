"""Validate and persist the actual bounded source conversion."""
from collections import Counter
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent), str(ROOT / "tests")]
from intent_training.sources.reward_hack_lcb import convert
from monitor_format import validate_events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-free-gib", type=float, default=0)
    args = parser.parse_args()
    free_gib = None
    if args.min_free_gib:
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in
                ("total_phys", "avail_phys", "total_page", "avail_page", "total_virtual", "avail_virtual", "avail_extended")]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise SystemExit("The fresh memory check failed.")
        free_gib = status.avail_phys / 1024 ** 3
        print(json.dumps({"fresh_free_gib": free_gib}), flush=True)
        if free_gib <= args.min_free_gib:
            raise SystemExit("The fresh memory check is below the requested threshold.")
    tests = unittest.defaultTestLoader.loadTestsFromName("test_reward_hack_lcb")
    result = unittest.TextTestRunner().run(tests)
    if not result.wasSuccessful():
        raise SystemExit(1)
    raw = ROOT / "data/downloads/reward_hack_lcb"
    counts = Counter()
    output = ROOT / "data/converted/reward_hack_lcb.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    tasks, files = set(), []
    for path in sorted(raw.rglob("*.traj.json")):
        data = path.read_bytes()
        row = json.loads(data)
        counts["source_rows"] += 1
        counts["source_messages"] += len(row["messages"])
        files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    temporary = output.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for events, side, meta in convert(raw):
            validate_events(events)
            tasks.add(meta["task_id"])
            counts["converted_rows"] += 1
            counts["events"] += len(events)
            counts["reasoning_entries"] += len(side["reasoning"])
            counts["hard_negative_candidates"] += side["outcomes"]["hard_negative_candidate"]
            counts["read_supplied_test"] += side["outcomes"]["read_supplied_test"]
            counts["ran_supplied_test"] += side["outcomes"]["ran_supplied_test"]
            counts["visible_positive_labels"] += sum(label["value"] and label["basis"] == "visible" for label in side["source_labels"])
            counts["outcome_negative_hints"] += len(side["source_labels"])
            counts["unanswered_shell_calls"] += sum(e["type"] == "tool_completed" and not e["action"]["result_text"] for e in events)
            handle.write(json.dumps({"events": events, "side": side, "meta": meta}, ensure_ascii=False) + "\n")
    preserved = 0
    if output.exists():
        with output.open("rb") as existing, temporary.open("rb") as expanded:
            for line in existing:
                if expanded.readline() != line:
                    raise ValueError("Expanded output does not preserve the existing stream prefix.")
                preserved += 1
    temporary.replace(output)
    counts["unique_tasks"] = len(tasks)
    counts["filtered_no_agent_action"] = counts["source_rows"] - counts["converted_rows"]
    report = {"source": "reward_hack_lcb", "dataset": "eungyeuk/reward_hack_lcb_trajectories",
              "counts": counts, "files": files, "errors": [], "blockers": [],
              "revision": json.loads((raw / "manifest.txt").read_text())["revision"],
              "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
              "unit_tests": result.testsRun, "licence": None,
              "preserved_prefix_rows": preserved, "fresh_free_gib": free_gib,
              "limitations": ["No shipped hack labels or hidden grading outcomes exist in the inspected source.",
                              "Negative rules are outcome hints for teacher review, not verified clean labels.",
                              "No model-written code or hidden tests were executed.",
                              "The dataset states no licence."]}
    target = ROOT / "results/sources/reward_hack_lcb.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"counts": counts, "output_sha256": report["output_sha256"]}))


if __name__ == "__main__":
    main()
