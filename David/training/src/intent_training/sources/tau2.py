"""Convert tau2 result bundles using only their embedded tasks and policies."""

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from monitor_format import validate_events
from .events import instruction, message, tool


CLAIM = ["M5", "G5"]
ORDER = ["L1", "L2", "L4", "L5", "G4", "G1"]
READ_PREFIXES = ("get_", "find_", "list_", "search_")
WRITES = {"book_reservation", "cancel_reservation", "update_reservation_baggages",
          "update_reservation_flights", "update_reservation_passengers",
          "cancel_pending_order", "exchange_delivered_order_items",
          "modify_pending_order_address", "modify_pending_order_items",
          "modify_pending_order_payment", "modify_user_address",
          "return_delivered_order_items"}
YES = re.compile(r"\byes\b", re.I)


def _stream(simulation, policy):
    """Retain turns, tool results, and hidden reasoning without copying raw metadata."""
    events = [instruction("", documents={"policy.md": policy})]
    reasoning = {}
    results = {m.get("id", m.get("tool_call_id")): m
               for m in simulation["messages"] if m.get("role") == "tool"}
    confirmed = False
    first_skip = None
    first_answer = None
    seen_tool = False
    for original in simulation["messages"]:
        role = original.get("role")
        text = original.get("content") or ""
        if role == "user":
            confirmed = confirmed or bool(YES.search(text))
            events.append(instruction(text, len(events) + 1))
            events[-1]["ts"] = original.get("timestamp") or ""
            continue
        if role != "assistant":
            continue
        calls = original.get("tool_calls") or []
        raw_reasoning = original.get("reasoning_content") or original.get("reasoning")
        if raw_reasoning:
            reasoning[str(len(events) + 1)] = (raw_reasoning if isinstance(raw_reasoning, str)
                                               else json.dumps(raw_reasoning, ensure_ascii=False))
        for call in calls:
            name = call["name"]
            result = results.get(call.get("id"), {})
            args = deepcopy(call.get("arguments") or {})
            mapped = name
            if name.startswith(READ_PREFIXES) or name == "calculate":
                mapped = "Read"
                args = {"native_tool": name, "arguments": args}
            events.append(tool(mapped, args, result.get("content", ""), len(events) + 1,
                               is_error=bool(result.get("error", False)), agent_text=text))
            events[-1]["ts"] = result.get("timestamp") or original.get("timestamp") or ""
            if name == "AskUserQuestion":
                confirmed = confirmed or bool(YES.search(result.get("content") or ""))
            seen_tool = True
            if name in WRITES and not confirmed and first_skip is None:
                first_skip = len(events)
        if not calls and text:
            events.append(message(text, len(events) + 1))
            events[-1]["ts"] = original.get("timestamp") or ""
            if seen_tool and first_answer is None:
                first_answer = len(events)
    return events, reasoning, first_skip, first_answer


def _communication(events, checks, cutoff):
    """Verify only the visible substring proposition, not task completion."""
    visible = [e for e in events if e["seq"] <= cutoff and e["agent_text"]]
    output = []
    for check in checks or []:
        info = check.get("info")
        if not isinstance(info, str):
            continue
        matches = [e["seq"] for e in visible if info.lower() in e["agent_text"].lower()]
        output.append({"info": info, "visible_substring_match": bool(matches),
                       "event_seq": matches[0] if matches else cutoff, "basis": "V",
                       "origin": "communicate_checks", "source_met": check.get("met")})
    return output


def convert(raw_dir: Path):
    """Yield separate claim and policy slices, with shared trajectory grouping."""
    for path in sorted(Path(raw_dir).glob("*.json")):
        bundle = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(bundle, dict) or "simulations" not in bundle:
            continue
        tasks = {str(t["id"]): t for t in bundle["tasks"]}
        environment = bundle["info"]["environment_info"]
        policy = environment["policy"]
        for sim in bundle["simulations"]:
            task = tasks[str(sim["task_id"])]
            events, reasoning, skip, answer = _stream(sim, policy)
            validate_events(events)
            if not answer:
                continue
            trajectory = f"{path.stem}:{sim['id']}"
            base = {"source": "tau2", "trajectory_id": trajectory,
                    "task_id": f"{environment['domain_name']}:{task['id']}",
                    "licence": "MIT", "harness": "tau2-bench",
                    "source_file": path.name}
            reward = sim.get("reward_info") or {}
            for slice_name, objective, cutoff in (("claim", CLAIM, answer),
                                                   ("policy_order", ORDER, skip or answer)):
                side = {"reasoning": {k: v for k, v in reasoning.items() if int(k) <= cutoff},
                        "source_labels": [],
                        "source_hints": [{"basis": "outcome", "origin": "nl_assertions",
                                          "value": reward.get("nl_assertions") or []}],
                        "embedded_task": deepcopy(task),
                        "communication_checks": _communication(events, reward.get("communicate_checks"), cutoff)}
                # Simulator instructions and hidden reference actions are side information only.
                if slice_name == "policy_order" and skip:
                    side["source_labels"].append({"question": "L5", "value": True,
                        "event_seq": skip, "basis": "V",
                        "origin": "policy_write_without_explicit_yes"})
                meta = dict(base, objective=list(objective), slice=slice_name,
                            cut_seq=cutoff, source_record_id=f"{trajectory}:{slice_name}")
                yield events, side, meta


def main():
    """Persist validated source records and measured conversion evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/converted/tau2.jsonl"))
    parser.add_argument("--report", type=Path, default=Path("results/sources/tau2.json"))
    args = parser.parse_args()
    counts = Counter()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        for events, side, meta in convert(args.raw_dir):
            validate_events(events)
            counts[meta["slice"]] += 1
            counts["visible_policy_order_positive"] += len(side["source_labels"])
            counts["visible_communication_checks"] += len(side["communication_checks"])
            output.write(json.dumps({"events": events, "side": side, "meta": meta}, ensure_ascii=False) + "\n")
    files = []
    for path in sorted(args.raw_dir.glob("*.json")):
        data = path.read_bytes()
        bundle = json.loads(data)
        files.append({"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                      "simulations": len(bundle.get("simulations", [])),
                      "embedded_tasks": len(bundle.get("tasks", []))})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = {"source": "tau2", "counts": dict(counts), "files": files,
              "distinct_simulations": sum(f["simulations"] for f in files),
              "converted_slice_records": counts["claim"] + counts["policy_order"],
              "policy_positive_fraction": {
                  "numerator": counts["visible_policy_order_positive"],
                  "denominator": counts["policy_order"]},
              "errors": [], "excluded_missing_post_tool_answer":
              sum(f["simulations"] for f in files) - counts["claim"]}
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
