"""Preserve AgentIF prompts and exact, paragraph-localized constraints."""

import hashlib
import json
from pathlib import Path
import re
import subprocess

from monitor_format import split_units

from .events import from_messages, instruction, message

LICENCE = "CC-BY-NC-4.0 (HF); CC-BY-4.0 (GitHub data, unresolved conflict)"


def chinese_heavy(messages):
    """Exclude prompts with at least ten percent Han characters."""
    text = "\n".join(str(m.get("content", "")) for m in messages)
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum("\u4e00" <= c <= "\u9fff" for c in letters) / len(letters) >= .1


def locate_constraints(row):
    """Match verbatim descriptions only within the annotated system paragraph."""
    system = "\n\n".join(m["content"] for m in row["input"] if m.get("role") == "system")
    paragraphs, offsets, cursor = [], [], 0
    for separator in re.finditer(r"\n\s*\n", system):
        paragraphs.append(system[cursor:separator.start()])
        offsets.append(cursor)
        cursor = separator.end()
    paragraphs.append(system[cursor:])
    offsets.append(cursor)
    units = split_units(system, "[I1]")
    unit_spans, cursor = [], 0
    for unit in units:
        start = system.index(unit["text"], cursor)
        unit_spans.append((start, start + len(unit["text"]), unit))
        cursor = start + len(unit["text"])
    matches, residual, seen = [], [], set()
    for constraint in row.get("constraints", []):
        pointer = constraint.get("other_info", {}).get("from", "")
        match = re.fullmatch(r"system_para_(\d+)", pointer)
        desc = constraint.get("desc", "")
        index = int(match[1]) if match else -1
        valid_pointer = 0 <= index < len(paragraphs) and desc and desc in paragraphs[index]
        start = offsets[index] + paragraphs[index].index(desc) if valid_pointer else -1
        unit = next((u for a, b, u in unit_spans if a <= start and start + len(desc) <= b), None)
        if valid_pointer and unit:
            key = (index, desc)
            if key not in seen:
                seen.add(key)
                matches.append({"constraint_id": constraint.get("id"), "text": unit["text"],
                                "description": desc, "unit_position": unit["position"],
                                "annotation": constraint,
                                "paragraph": index, "paragraph_text": paragraphs[index],
                                "state": constraint.get("state"),
                                "evaluation": constraint.get("evaluation", [])})
        else:
            residual.append(constraint.get("id"))
    return matches, residual


def rows(raw_dir):
    """Read the JSON array supplied by the dataset, without executing code."""
    path = Path(raw_dir) / "eval-prefix.json"
    if not path.exists():
        path = Path(raw_dir) / "eval.json"
    return json.loads(path.read_text(encoding="utf-8"))


def identity(row, index):
    """Group turns of a source query together when a query identifier exists."""
    return str(row.get("id", row.get("query_id", index)))


def request_identity(source_id):
    """Change request identifiers when the continuation output allowance changes."""
    identity_text = f"{source_id}:max_output_tokens=4096"
    return "agentif-" + hashlib.sha256(identity_text.encode()).hexdigest()[:20]


def generation_requests(raw_dir, limit=200):
    """Request original next messages only for success-state matched constraints."""
    count = 0
    for index, row in enumerate(rows(raw_dir)):
        if chinese_heavy(row["input"]):
            continue
        matches, _ = locate_constraints(row)
        if not matches:
            continue
        count += 1
        if count > limit:
            break
        constraints = [m for m in matches if m["state"] == "success"]
        if not constraints:
            continue
        record_id = identity(row, index)
        request_id = request_identity(f"{index}:{record_id}")
        yield {"id": request_id, "purpose": "agentif_next_message",
               "prompt": "Produce only the next assistant message for this conversation. "
                         "Respect the original system instructions. Do not describe the generation task.\n"
                         + json.dumps(row["input"], ensure_ascii=False),
               "max_output_tokens": 4096,
               "refs": {"source": "agentif", "source_record_id": f"{index}:{record_id}",
                              "messages": row["input"], "constraints": constraints}}


def conversation_records(raw_dir):
    """Yield RF records and consume separately generated continuation evidence."""
    root = Path(raw_dir).resolve().parents[1]
    responses = root / "generation" / "responses"
    count = 0
    for index, row in enumerate(rows(raw_dir)):
        if chinese_heavy(row["input"]):
            continue
        matches, residual = locate_constraints(row)
        if not matches:
            continue
        record_id = identity(row, index)
        events, reasoning = from_messages(row["input"])
        source_id = f"{index}:{record_id}"
        side = {"reasoning": reasoning, "licence": LICENCE, "source_labels": [],
                "requirements": matches, "unmatched_constraint_ids": residual}
        # Unannotated paragraphs are candidates for the teacher, never RF-no labels.
        system_seq = next(e["seq"] for e in events if e["new_items"])
        unique_units = {m["unit_position"]: m for m in matches}
        side["source_labels"] = [
            {"question": "RF", "value": True, "event_seq": system_seq,
             "basis": "visible", "origin": "rule", "requirement_text": m["text"],
             "unit_position": m["unit_position"], "paragraph": m["paragraph"]}
            for m in unique_units.values()]
        request_id = request_identity(source_id)
        response_file = responses / f"{request_id}.json"
        if response_file.exists():
            response = json.loads(response_file.read_text(encoding="utf-8"))
            text = response.get("text", response.get("output_text", ""))
            if isinstance(text, str) and text:
                events.append(message(text, len(events) + 1))
                side["generation_response_id"] = request_id
                side["g2_constraints"] = [m for m in matches if m["state"] == "success"]
                side["g2_pending_checker"] = True
        meta = {"source": "agentif", "source_record_id": source_id,
                "trajectory_id": f"agentif:{record_id}", "task_id": record_id,
                "objective": ["RF"], "licence": LICENCE, "harness": row.get("agent_name", "AgentIF"),
                "cut_kind": "unspecified"}
        yield events, side, meta
        count += 1
        if count >= 200:
            break


def privacy_flags(text):
    """Identify concrete personal-data shapes in projected system text."""
    rules = {
        'email_literal': r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        'identifier_shape': r'(?<!\d)\d{3}[- ]\d{2}[- ]\d{4}(?!\d)',
        'case_field': r'\b(?:patient|client)\s+(?:name|record|profile|history|case)\s*[:=]',
        'phone_literal': r'(?<!\d)(?:\+\d{1,3}[- .]?)?\(?\d{3}\)?[- .]\d{3}[- .]\d{4}(?!\d)',
    }
    flags = [name for name, pattern in rules.items() if re.search(pattern, text, re.I)]
    if (re.search(r"\bI(?:'m| am| have| feel| suffer| lost)\b", text, re.I)
            and re.search(r'\b(?:diagnos|symptom|suicid|depress|anxiet|trauma|medicat|insomnia)', text, re.I)):
        flags.append('personal_clinical_narrative')
    return flags


def convert(raw_dir):
    """Publish eligible system-only RF contexts without conversation narratives."""
    raw_dir = Path(raw_dir)
    policy = json.loads((raw_dir / 'rf-eligibility.json').read_text(encoding='utf-8'))
    source = raw_dir / 'eval-prefix.json'
    if not source.exists():
        source = raw_dir / 'eval.json'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != policy['source_sha256']:
        raise ValueError('The AgentIF eligibility policy names a different source artifact.')
    excluded = set(policy['excluded_source_row_indices'])
    candidates = []
    for index, row in enumerate(rows(raw_dir)):
        if index in excluded or chinese_heavy(row['input']):
            continue
        matches, _ = locate_constraints(row)
        if not matches:
            continue
        system = '\n\n'.join(item['content'] for item in row['input'] if item.get('role') == 'system')
        if privacy_flags(system):
            continue
        system_digest = hashlib.sha256(system.encode('utf-8')).hexdigest()
        record_id = identity(row, index)
        units = {item['unit_position']: item for item in matches}
        requirements = [{key: item[key] for key in
            ('constraint_id', 'text', 'description', 'unit_position', 'paragraph')}
            for item in units.values()]
        side = {'reasoning': {}, 'licence': LICENCE, 'requirements': requirements,
                'source_labels': [{'question': 'RF', 'value': True, 'event_seq': 1,
                    'basis': 'visible', 'origin': 'rule', 'requirement_text': item['text'],
                    'unit_position': item['unit_position'], 'paragraph': item['paragraph']}
                    for item in units.values()],
                'source_provenance': {'dataset': 'THU-KEG/AgentIF',
                    'public_url': 'https://huggingface.co/datasets/THU-KEG/AgentIF/resolve/main/eval.json',
                    'source_sha256': digest, 'source_row_index': index,
                    'system_sha256': system_digest, 'projection': 'system_messages_only',
                    'excluded_roles': ['user', 'assistant', 'tool'], 'generated_response_used': False}}
        meta = {'source': 'agentif', 'source_record_id': f'{index}:{record_id}',
                'trajectory_id': f'agentif-system:{index}:{record_id}', 'task_id': record_id,
                'pair_id': f'agentif-system:{system_digest}', 'grouping_basis': 'exact_system_text',
                'objective': ['RF'], 'licence': LICENCE, 'harness': 'AgentIF-system-prompt',
                'cut_kind': 'unspecified', 'source_row_index': index, 'system_sha256': system_digest}
        candidates.append(([instruction(system)], side, meta))
    selected, covered = set(), set()
    for index, (_, side, meta) in enumerate(candidates):
        units = {(meta['system_sha256'], item['unit_position']) for item in side['source_labels']}
        if units - covered and len(selected) < policy['target_count']:
            selected.add(index)
            covered.update(units)
    for index in range(len(candidates)):
        if len(selected) >= policy['target_count']:
            break
        selected.add(index)
    for index in sorted(selected):
        yield candidates[index]


def check_code(code, response, image="intent-agent-run:latest"):
    """Run a dataset checker inside a resource-limited container with no network."""
    runner = (
        "import contextlib,io,json,sys; p=json.load(sys.stdin); scope={}; "
        "capture=io.StringIO();\n"
        "try:\n"
        " with contextlib.redirect_stdout(capture):\n"
        "  exec(compile(p['code'],'<checker>','exec'),scope); "
        "value=scope['check_following'](p['response'])\n"
        " if type(value) is not bool: raise TypeError('The checker must return a boolean.')\n"
        " print(json.dumps({'value':value}))\n"
        "except BaseException as exc: print(json.dumps({'error':type(exc).__name__}))"
    )
    args = ["docker", "run", "--rm", "-i", "--network", "none", "--read-only",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--memory", "128m",
            "--cpus", "0.5", "--pids-limit", "32", "--user", "65534:65534",
            "--entrypoint", "python3", image, "-I", "-c", runner]
    try:
        result = subprocess.run(args, input=json.dumps({"code": code, "response": response}),
                                text=True, capture_output=True, timeout=20)
        if result.returncode:
            return {"error": "ContainerFailure"}
        value = json.loads(result.stdout)
        return value if isinstance(value, dict) else {"error": "InvalidResult"}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {"error": "CheckerUnavailable"}


def materialize(workspace):
    """Persist validated source records, generation requests and measured counts."""
    from monitor_format import validate_events
    workspace = Path(workspace)
    raw_dir = workspace / "data" / "downloads" / "agentif"
    raw_rows = rows(raw_dir)
    output = workspace / "data" / "converted" / "agentif.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for events, side, meta in convert(raw_dir):
        validate_events(events)
        records.append({"events": events, "side": side, "meta": meta})
    output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    requests = list(generation_requests(raw_dir))
    request_path = workspace / "data" / "generation" / "requests" / "agentif.jsonl"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests), encoding="utf-8")
    positive_units = {(r["meta"]["source_record_id"], m["unit_position"])
                      for r in records for m in r["side"]["requirements"]}
    source = raw_dir / "eval-prefix.json"
    if not source.exists():
        source = raw_dir / "eval.json"
    eligible = sum(not chinese_heavy(r["input"]) and bool(locate_constraints(r)[0]) for r in raw_rows)
    result = {"source": "agentif", "source_url": "https://huggingface.co/datasets/THU-KEG/AgentIF/resolve/main/eval.json",
              "licence": LICENCE, "source_files": [{"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}],
              "raw_rows": len(raw_rows), "chinese_heavy_rows": sum(chinese_heavy(r["input"]) for r in raw_rows),
              "rf_eligible_rows": eligible, "eligible_surplus_rows": eligible - len(records),
              "converted_records": len(records), "rf_positive_units": len(positive_units), "rf_negative_units": 0,
              "matched_constraint_annotations": sum(len(r["side"]["requirements"]) for r in records),
              "unmatched_constraint_annotations": sum(len(r["side"]["unmatched_constraint_ids"]) for r in records),
              "generation_requests": len(requests), "generation_responses_consumed": sum("generation_response_id" in r["side"] for r in records),
              "g2_verified_constraints": 0, "g2_pending_checker": True, "broken_checkers_executed": 0,
              "errors": [], "output": str(output), "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    result_path = workspace / "results" / "sources" / "agentif.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    print(json.dumps(materialize(parser.parse_args().workspace)))
