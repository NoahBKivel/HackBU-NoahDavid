"""Join Atlas annotations to complete original sessions without exposing corrections."""

from collections import Counter
from copy import deepcopy
import hashlib
import json
from itertools import groupby
from pathlib import Path
import re

from monitor_format import is_cut_point, validate_events
from .events import from_messages
from .misalignment_atlas_privacy import scrub

SLICES = {
    "instruction": {"quota": 150, "questions": ["M2", "D2", "G2", "RF"]},
    "intention": {"quota": 200, "questions": ["M1", "G1"]},
    "resolution": {"quota": 50, "questions": ["L7"]},
}


def flat_messages(rows):
    """Preserve typed SWE-chat content without treating native thinking as speech."""
    messages, pending = [], []
    for row in sorted(rows, key=lambda r: r["turn_number"]):
        kind, content = row["turn_type"], row.get("content") or ""
        if kind == "assistant_thinking":
            pending.append(content)
            continue
        if kind == "user_prompt":
            messages.append({"role": "user", "content": content})
        elif kind == "system_injected":
            messages.append({"role": "system", "content": content})
        elif kind == "assistant_response":
            messages.append({"role": "assistant", "content": content})
        elif kind == "tool_use":
            messages.append({"role": "assistant", "content": "", "tool_calls": [{
                "id": row["tool_call_id"], "function": {
                    "name": row["tool_name"], "arguments": row.get("tool_input_json") or content}}]})
        elif kind == "tool_result":
            messages.append({"role": "tool", "content": content, "tool_call_id": row["tool_call_id"]})
        else:
            continue
        if pending and messages[-1]["role"] == "assistant":
            messages[-1]["reasoning_content"] = "\n".join(pending)
            pending.clear()
    merged, active = [], None
    for msg in messages:
        if msg["role"] != "assistant":
            merged.append(msg)
            if msg["role"] != "tool":
                active = None
            continue
        if active is None:
            active = {"role": "assistant", "content": []}
            merged.append(active)
        if msg.get("reasoning_content"):
            active["content"].append({"type": "thinking", "thinking": msg["reasoning_content"]})
        if msg.get("content"):
            active["content"].append({"type": "text", "text": msg["content"]})
        for call in msg.get("tool_calls", []):
            active["content"].append({"type": "tool_use", "id": call["id"],
                "name": call["function"]["name"], "input": call["function"]["arguments"]})
    return merged


def prepare_sessions(raw_dir, conversation_dir, excluded_ids_path):
    """Join downloaded inert parquet groups and exclude incomplete boundary sessions."""
    import pyarrow.parquet as parquet
    from collections import defaultdict

    raw_dir = Path(raw_dir)
    annotations = json.loads((raw_dir / "misalignments.json").read_text(encoding="utf-8"))
    wanted = {r["session_sha"] for r in annotations if r.get("source") == "swe"}
    grouped, unsafe = defaultdict(list), set()
    inputs = []
    paths = sorted(Path(conversation_dir).glob("conversations-*.parquet"))
    indices = {int(p.stem.rsplit("-", 1)[1]) for p in paths}
    for path in paths:
        rows = parquet.read_table(path).to_pylist()
        index = int(path.stem.rsplit("-", 1)[1])
        if rows and index + 1 not in indices:
            unsafe.add(rows[-1]["session_id"])
        for row in rows:
            if row["session_id"] in wanted:
                grouped[row["session_id"]].append(row)
        inputs.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    with (raw_dir / "sessions-joined.jsonl").open("w", encoding="utf-8") as handle:
        for sid, rows in grouped.items():
            if sid in unsafe or min(r["turn_number"] for r in rows) != 0:
                continue
            handle.write(json.dumps({"session_id": sid, "complete": True,
                "messages": flat_messages(rows)}, ensure_ascii=False) + "\n")
    (raw_dir / "reserved-session-ids.json").write_text(json.dumps(sorted(grouped)), encoding="utf-8")
    (raw_dir / "excluded-session-ids.json").write_text(Path(excluded_ids_path).read_text(encoding="utf-8"), encoding="utf-8")
    (raw_dir / "join-inputs.json").write_text(json.dumps(inputs, indent=2), encoding="utf-8")


def _normalized(text):
    return re.sub(r"\s+", " ", text).strip()


def _visible_event(event):
    return "\n".join([event["agent_text"], *(i["text"] for i in event["new_items"]),
        *(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
          for v in event["action"].get("args", {}).values()), event["action"].get("result_text", "")])


def session_stream(session):
    """Map the upstream formatter's merged user/assistant turns to event ranges."""
    messages = session["messages"]
    events, reasoning = from_messages(messages)
    boundaries = [0]
    for msg in messages:
        boundaries.append(boundaries[-1] + len(from_messages([msg])[0]))
    groups = []
    for index, msg in enumerate(messages):
        role = msg.get("role")
        if role not in {"user", "assistant"}:
            continue
        # Native tool-result user envelopes do not constitute developer turns.
        if isinstance(msg.get("content"), list) and not any(
            b.get("type") == "text" for b in msg["content"] if isinstance(b, dict)
        ) and role == "user":
            continue
        if groups and groups[-1]["role"] == role:
            groups[-1]["end"] = index + 1
        else:
            groups.append({"role": role, "start": index, "end": index + 1})
    mapping = {}
    for turn, group in enumerate(groups, 1):
        before, through = boundaries[group["start"]], boundaries[group["end"]]
        mapping[turn] = {"role": group["role"], "seqs": list(range(before + 1, through + 1))}
    validate_events(events)
    return events, reasoning, mapping


def _evidence_turns(episode, mapping, events):
    """Require indexed evidence to agree with the actual original visible turn."""
    turns = []
    for item in episode.get("evidence", []):
        match = re.search(r"TURN\s+(\d+)\s*\|\s*(USER|ASSISTANT)", item.get("turn", ""))
        if not match:
            return None
        number, role = int(match[1]), match[2].lower()
        mapped = mapping.get(number)
        if not mapped or mapped["role"] != role:
            return None
        seqs = set(mapped["seqs"])
        candidates = [event for event in events if event["seq"] in seqs]
        visible = "\n".join(_visible_event(event) for event in candidates)
        quote = _normalized(item.get("quote", ""))
        # Ellipsized model summaries are localization hints, not exact quotations.
        pieces = [p.strip() for p in re.split(r"\.\.\.|…", quote) if p.strip()]
        if not pieces or not all(p in _normalized(visible) for p in pieces):
            return None
        positions = [event["seq"] for event in candidates
                     if all(p in _normalized(_visible_event(event)) for p in pieces)]
        if not positions:
            return None
        turns.append((number, role, min(positions)))
    return turns


def convert(raw_dir: Path, *, copy_events=True):
    """Yield complete joined streams; annotations remain outcome hints only."""
    raw_dir = Path(raw_dir)
    annotations = json.loads((raw_dir / "misalignments.json").read_text(encoding="utf-8"))
    annotation_groups = {}
    for row in annotations:
        annotation_groups.setdefault(str(row.get("session_sha", "")), []).append(row)
    sessions = {}
    for path in sorted(raw_dir.glob("sessions*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                session = json.loads(line)
                if session.get("complete") is True:
                    sessions[str(session["session_id"])] = session
    excluded_path = raw_dir / "excluded-session-ids.json"
    excluded = set(json.loads(excluded_path.read_text(encoding="utf-8"))) if excluded_path.exists() else set()
    source_contract = json.loads(Path(__file__).with_name("entries").joinpath(
        "misalignment_atlas.json").read_text(encoding="utf-8"))
    excluded_recoveries = {(item["session_sha"], item["misalignment_id"])
                           for item in source_contract.get("recovery_exclusions", [])}
    seen = set()
    cached_sid, cached_stream = None, None
    for episode in (row for group in annotation_groups.values() for row in group):
        sid = str(episode.get("session_sha", ""))
        identity = (sid, episode.get("misalignment_id"))
        if identity in seen or sid in excluded or sid not in sessions:
            continue
        seen.add(identity)
        if sid != cached_sid:
            cached_sid, cached_stream = sid, session_stream(sessions[sid])
        events, reasoning, mapping = cached_stream
        turns = _evidence_turns(episode, mapping, events)
        assistants = sorted((n, seq) for n, role, seq in turns or [] if role == "assistant")
        if not assistants:
            continue
        offense_turn, offense_seq = assistants[0]
        classified = [e["seq"] for e in events if e["seq"] >= offense_seq and is_cut_point(e)]
        if not classified:
            continue
        cut = classified[0]
        next_user = next((n for n in sorted(mapping) if n > offense_turn and mapping[n]["role"] == "user"), None)
        if next_user and cut >= min(mapping[next_user]["seqs"]):
            continue
        goal = episode.get("alignment_goal")
        names = [name for name in ("instruction", "intention") if goal in {name, "both"}]
        for name in names:
            side = {"reasoning": reasoning, "source_labels": [{
                "question": "M2" if name == "instruction" else "M1",
                "value": True, "event_seq": cut, "basis": "outcome", "origin": "LLM Atlas annotation",
                "hint": {"alignment_goal": goal, "confidence": episode.get("confidence")},
            }], "annotation_basis": "T"}
            meta = {"source": "misalignment_atlas", "trajectory_id": sid,
                    "source_record_id": f"{sid}:{episode['misalignment_id']}:{name}",
                    "objective": SLICES[name]["questions"], "slice": name,
                    "licence": episode.get("license_type"), "harness": episode.get("agent"),
                    "cut_seq": cut, "original_session_id": sid,
                    "atlas_turn_event_seqs": {str(k): v["seqs"] for k, v in mapping.items()}}
            yield (deepcopy(events) if copy_events else events), side, meta
        # Curated source exceptions reject a proven false causal association only.
        # The same annotation's base slices and complete session remain valid.
        if identity in excluded_recoveries:
            continue
        # A recovery requires an explicitly evidenced user turn after the offense.
        correction_markers = re.compile(r"correct|push.?back|reject|contradict|complain|object|did not|does not|failure|wrong", re.I)
        correction_turns = set()
        for item in episode.get("evidence", []):
            match = re.search(r"TURN\s+(\d+)\s*\|\s*USER", item.get("turn", ""))
            if match and correction_markers.search(item.get("context", "")):
                correction_turns.add(int(match[1]))
        corrections = sorted(n for n, role, _ in turns if role == "user" and n > offense_turn and n in correction_turns)
        if not corrections:
            continue
        correction = corrections[0]
        responding = next((n for n in sorted(mapping) if n > correction and mapping[n]["role"] == "assistant"), None)
        if responding is None:
            continue
        response_seqs = set(mapping[responding]["seqs"])
        response_cuts = [e["seq"] for e in events if e["seq"] in response_seqs and is_cut_point(e)]
        if not response_cuts:
            continue
        correction_seq = min(mapping[correction]["seqs"])
        correction_text = "\n".join(i["text"] for e in events if e["seq"] in mapping[correction]["seqs"]
                                    for i in e["new_items"] if i["kind"] == "user_instruction")
        side = {"reasoning": reasoning, "source_labels": [{"question": "L7",
                "value": episode.get("resolution_status"), "event_seq": response_cuts[-1],
                "basis": "outcome", "origin": "LLM Atlas resolution annotation"}], "annotation_basis": "T",
                "correction": correction_text,
                "findings": [{"id": "atlas-correction", "question": "M1", "event_seqs": [cut],
                              "correction_seq": correction_seq, "status": "open"}]}
        meta = {"source": "misalignment_atlas", "trajectory_id": sid, "original_session_id": sid,
                "source_record_id": f"{sid}:{episode['misalignment_id']}:resolution",
                "objective": ["L7"], "slice": "resolution", "licence": episode.get("license_type"),
                "harness": episode.get("agent"), "cut_seq": response_cuts[-1]}
        yield (deepcopy(events) if copy_events else events), side, meta


def write_conversion(raw_dir, output, report, candidate_limits=None):
    """Persist measured conversion evidence, including absent original sessions."""
    raw_dir, output, report = Path(raw_dir), Path(output), Path(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    counts, candidate_counts = Counter(), Counter()
    kept_episodes, candidate_episodes = set(), set()
    temporary_output = output.with_suffix(output.suffix + ".tmp")
    with temporary_output.open("w", encoding="utf-8") as handle:
        for _, group in groupby(convert(raw_dir, copy_events=False), key=lambda row: row[2]["trajectory_id"]):
            records = list(group)
            for events, _, meta in records:
                validate_events(events)
                candidate_counts[meta["slice"]] += 1
                candidate_episodes.add(meta["source_record_id"].rsplit(":", 1)[0])
            if candidate_limits is not None and not any(
                counts[meta["slice"]] < candidate_limits.get(meta["slice"], 0) for _, _, meta in records
            ):
                continue
            for events, side, meta in records:
                counts[meta["slice"]] += 1
                kept_episodes.add(meta["source_record_id"].rsplit(":", 1)[0])
                handle.write(json.dumps(scrub({"events": events, "side": side, "meta": meta}), ensure_ascii=False) + "\n")
    temporary_output.replace(output)
    paths = sorted(raw_dir.glob("*.json")) + sorted(raw_dir.glob("sessions*.jsonl"))
    source = json.loads((raw_dir / "misalignments.json").read_text(encoding="utf-8"))
    joined = set()
    for path in raw_dir.glob("sessions*.jsonl"):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("complete") is True:
                    joined.add(record["session_id"])
    excluded_path = raw_dir / "excluded-session-ids.json"
    excluded = set(json.loads(excluded_path.read_text(encoding="utf-8"))) if excluded_path.exists() else set()
    filters = Counter()
    for row in source:
        sid = row.get("session_sha")
        if sid in excluded:
            filters["selected_swe_chat_session"] += 1
        elif sid not in joined:
            filters["missing_full_session"] += 1
        else:
            filters["joined_annotation"] += 1
    filters["localization_or_missing_response_rejection"] = filters["joined_annotation"] - len(candidate_episodes)
    filters["candidate_limit_excluded_records"] = sum(candidate_counts.values()) - sum(counts.values())
    temporary_report = report.with_suffix(report.suffix + ".tmp")
    temporary_report.write_text(json.dumps({"source": "misalignment_atlas", "source_rows": len(source),
        "converted_records": sum(counts.values()), "slice_counts": dict(counts), "planned_slices": SLICES,
        "filter_counts": dict(filters), "complete_sessions_available": len(joined),
        "kept_source_rows": len(kept_episodes), "conversion_errors": [],
        "candidate_slice_counts": dict(candidate_counts), "candidate_limits": candidate_limits,
        "candidate_source_rows": len(candidate_episodes),
        "dedupe_manifest_sha256": hashlib.sha256(excluded_path.read_bytes()).hexdigest() if excluded_path.exists() else None,
        "llm_hint_records": sum(counts.values()), "visible_positive_rules": 0,
        "shortfall_unscaled": {name: max(0, spec["quota"] - counts[name]) for name, spec in SLICES.items()},
        "source_proportions": dict(Counter(r.get("source") for r in source)),
        "blockers": [] if sum(counts.values()) else ["Original full sessions are absent or no indexed evidence joins. Episode quotes cannot replace full traces."],
        "files": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}, indent=2), encoding="utf-8")
    temporary_report.replace(report)
