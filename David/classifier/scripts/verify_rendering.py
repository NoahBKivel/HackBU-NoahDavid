"""Verify deployed state parity, instruction numbering and turn-end rows."""

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import modal

from backend_driver import Driver
from verify_core import read_records

FOLDER = Path(__file__).resolve().parents[1]
REPO = FOLDER.parents[1]
sys.path.insert(0, str(REPO))
from David import monitor_format as shared


def fetch_logs(app: str, output: Path) -> list[dict]:
    """Fetch the current app's structured logs after calls complete."""
    run = subprocess.run([sys.executable, "-m", "modal", "app", "logs", app, "--since", "1h"],
                         cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45, check=True)
    output.write_bytes(run.stdout)
    return read_records(output)


def digest(text: str) -> str:
    """Hash the exact UTF-8 bytes that the shared renderer returned."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_state(actual_digest: str, expected_text: str) -> None:
    """Reject any difference in the exact rendered state bytes."""
    if actual_digest != digest(expected_text):
        raise AssertionError("The deployed request state differs from the shared renderer output.")


def reference_findings(header: dict, event: dict) -> list[dict]:
    """Adapt a pre-call persisted header with the specified correction-arrival rule."""
    copied = copy.deepcopy(header.get("findings", []))
    pending = set(header.get("pending_correction_marks", []))
    if event["type"] == "tool_completed" and (event.get("action") or {}).get("denied") is None:
        for finding in copied:
            if finding["id"] in pending:
                finding["reached_at"] = event["seq"]
    return [{"id": f["id"], "question": "M2" if f["question"].startswith("M8") else f["question"],
             "event_seqs": f["cited"], "correction_seq": f["reached_at"], "status": f["last_l7"]}
            for f in copied if f["status"] in {"open", "dismissed"} and f.get("message")
            and f.get("reached_at") is not None and f["reached_at"] <= event["seq"]]


def corrected_samples() -> list[dict]:
    """Use Noah's samples with the file-change shape the Mod actually emits."""
    events = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((REPO / "Noah/backend/samples").glob("*.json"))]
    for event in events:
        for item in event.get("new_items", []):
            if item.get("kind") == "project_doc":
                item["text"] = item["text"].replace("/n", "\n")
        action = event.get("action")
        if action:
            action["denied"] = None
            if action.get("tool") not in {"Edit", "Write"}:
                action["file_changes"] = []
            else:
                args = action["args"]
                old, new = args.get("old_string", ""), args.get("new_string", args.get("content", ""))
                patch = [{"oldStart": 3, "newStart": 3, "oldLines": len(old.splitlines()),
                          "newLines": len(new.splitlines()),
                          "lines": ["-" + line for line in old.splitlines()] + ["+" + line for line in new.splitlines()]}]
                action["file_changes"] = [{"path": args["file_path"],
                                           "op": "write" if action["tool"] == "Write" else "edit", "patch": patch}]
        event.setdefault("new_items", [])
        event.setdefault("todos", [])
        event.setdefault("agent_text", "")
        event.setdefault("agent_thinking", "")
    return events


def handwritten() -> list[dict]:
    """Cover clarification, a late instruction and answer versus aborted turn ends."""
    def tool(seq: int, name: str, text: str = "", items: list | None = None) -> dict:
        return {"seq": seq, "type": "tool_completed", "new_items": items or [], "agent_text": "",
                "agent_thinking": "", "todos": [], "action": {"tool": name, "args": {"command": "git status --short"},
                "result_text": text, "denied": None, "is_error": False, "file_changes": []}}
    return [
        {"seq": 1, "type": "session_started", "new_items": [{"kind": "user_instruction", "text": "Inspect the repository status."}]},
        tool(2, "AskUserQuestion", "Use pytest and preserve coverage."),
        tool(4, "Bash", "On branch main.", [{"kind": "user_instruction", "text": "Report findings before making changes."}]),
        tool(5, "Read", "README contents."),
        tool(3, "Read", "Delayed read.", [{"kind": "user_instruction", "text": "Keep every public interface unchanged."}]),
        tool(6, "Bash", "On branch main."),
        {"seq": 7, "type": "turn_completed", "turn": {"reason": "answer"}, "agent_text": "", "new_items": []},
        {"seq": 8, "type": "turn_completed", "turn": {"reason": "aborted"}, "agent_text": "Still investigating.", "new_items": []},
        {"seq": 9, "type": "turn_completed", "turn": {"reason": "aborted"}, "agent_text": "", "new_items": []},
        {"seq": 10, "type": "turn_completed", "turn": {"reason": "answer"}, "agent_text": "Here is the repository status.", "new_items": []},
    ]


def run(target: str, output: Path, length: int) -> dict:
    """Drive the deployed class and compare its state digests to independent shared output."""
    output.mkdir(parents=True, exist_ok=True)
    driver = Driver(target)
    assert driver.warmup() == {"ok": True}
    records = fetch_logs(driver.app, output / "model.log")
    loaded = next((r for r in reversed(records) if "base_revision" in r), None)
    if loaded is None:
        raise AssertionError("No deployed tokenizer identity was found in the app logs.")
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(loaded["base"], revision=loaded["base_revision"], token=False,
                                               cache_dir=output / "tokenizer")
    session_dict = modal.Dict.from_name(f"{driver.app}-sessions")
    all_calls, expected_states, headers = [], {}, {}
    numbering = None
    commit = subprocess.check_output(["git", "-c", f"safe.directory={REPO.as_posix()}", "rev-parse", "HEAD"], cwd=REPO).decode().strip()
    for label, source in (("samples", corrected_samples()), ("handwritten", handwritten())):
        sid = f"rendering-{label}-{uuid.uuid4().hex}"
        history = []
        for original in source:
            event = {"schema_version": 1, "agent_text": "", "agent_thinking": "", "todos": [],
                     **copy.deepcopy(original), "session_id": sid, "event_id": f"{sid}-{original['seq']}"}
            before = session_dict.get(sid) or {}
            headers[event["event_id"]] = copy.deepcopy(before)
            history.append(event)
            ordered = sorted(history, key=lambda e: e["seq"])
            findings = reference_findings(before, event)
            instructions = shared.build_instructions(ordered)
            documents = shared.collect_documents(ordered)
            sent, call = driver.spawn(event)
            response = driver.receive(sent, call)
            pending = response.get("pending", False)
            if pending:
                completed = call.get(timeout=120)
            else:
                completed = response
            from verify_deploy import check
            check(completed, event)
            all_calls.append({"label": label, "event": sent, "response": response, "completed": completed, "backend_pending": pending})
            (output / "calls.json").write_text(json.dumps(all_calls, indent=2), encoding="utf-8")
            (output / "headers.json").write_text(json.dumps(headers, indent=2), encoding="utf-8")
            if not completed["details"].get("skipped"):
                state, detailed, fits = shared.render_state(instructions, documents, ordered, event["seq"],
                                                            findings, length - 1, tokenizer=tokenizer)
                assert fits, "The ordinary verification fixture unexpectedly requires overflow."
                expected_states[event["event_id"]] = {"text": state, "detailed": detailed, "sha256": digest(state)}
            if label == "handwritten" and event["seq"] == 10:
                numbering = instructions
                assert [i["id"] for i in instructions] == ["I1", "I2", "I3", "I4"]
                assert sum(i["text"] == "Use pytest and preserve coverage." for i in instructions) == 1
                assert instructions[2]["text"] == "Keep every public interface unchanged."
                assert instructions[3]["text"] == "Report findings before making changes."
    (output / "calls.json").write_text(json.dumps(all_calls, indent=2), encoding="utf-8")
    (output / "headers.json").write_text(json.dumps(headers, indent=2), encoding="utf-8")
    (output / "reference-states.json").write_text(json.dumps(expected_states, indent=2), encoding="utf-8")
    expected_ids = set(expected_states)
    deadline = time.monotonic() + 45
    while True:
        records = fetch_logs(driver.app, output / "model.log")
        actual = {r["event_id"]: r for r in records if r.get("event_id") in expected_ids and r.get("probabilities")}
        if set(actual) == expected_ids:
            break
        if time.monotonic() >= deadline:
            raise AssertionError(f"Missing state traces for {sorted(expected_ids - set(actual))}.")
        time.sleep(.25)
    compared = []
    for event_id, expected in expected_states.items():
        trace = next(t for t in actual[event_id]["probabilities"] if any(k.split('#')[0] not in {'RF', 'D1', 'D2', 'D5'} for k in t["raw"]))
        check_state(trace["state_sha256"], expected["text"])
        compared.append({"event_id": event_id, "expected": expected["sha256"], "actual": trace["state_sha256"], "questions": list(trace["raw"])})
    assert compared
    first = compared[0]
    mutated = digest(expected_states[first["event_id"]]["text"] + " ")
    mutation_rejected = False
    try:
        check_state(first["actual"], expected_states[first["event_id"]]["text"] + " ")
    except AssertionError:
        mutation_rejected = True
    assert mutation_rejected, "The one-byte state mutation was not rejected."
    for record in all_calls:
        if record['label'] != 'handwritten':
            continue
        seq = record['event']['seq']
        if seq in {7, 8, 10}:
            questions = next(item['questions'] for item in compared if item['event_id'] == record['event']['event_id'])
            ending = seq in {7, 10}
            assert ('G5' in questions) == ending
            expected_requirements = {f"G2#R{unit['k']}" for unit in headers[record['event']['event_id']].get('units', []) if unit['accepted']} if ending else set()
            assert {key for key in questions if key.startswith('G2#')} == expected_requirements
        elif seq == 9:
            assert record['completed']['details']['skipped']
    evidence = {"app": driver.app, "commit": commit, "base": loaded["base"], "base_revision": loaded["base_revision"],
                "checks": {"shared renderer": True, "instruction numbering": True, "turn ends": True},
                "compared": compared, "numbered_instructions": numbering,
                "one_byte_mutation": {"actual": first['actual'], "mutated": mutated, "rejected": True}}
    (output / "parity.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"app": driver.app, "checks": evidence['checks'], "states_compared": len(compared)}), flush=True)
    return evidence


def main() -> int:
    """Run the deployed shared-format checks and preserve their evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', choices=('dev', 'live'), default='dev')
    parser.add_argument('--output', type=Path, default=FOLDER / 'results/rendering')
    parser.add_argument('--length', type=int, default=8192)
    args = parser.parse_args()
    run(args.target, args.output, args.length)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
