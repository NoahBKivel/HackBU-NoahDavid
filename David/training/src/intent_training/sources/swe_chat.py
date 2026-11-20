"""Convert native SWE-chat row groups without exposing future corrections."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from .events import instruction, message, tool

PUSHBACK = {"correction", "rejection", "failure_report"}
REFERENCE = re.compile(r"\b(?:you (?:used|changed|made|removed|added|implemented|broke|missed|forgot|did)|your (?:change|code|fix|implementation|approach)|still|instead|didn.t|doesn.t|not working|wrong|that.s not|i (?:said|asked|wanted|meant)|should (?:be|have)|rather than)\b", re.I)
CLAIM = re.compile(r"\b(?:done|completed?|fixed|implemented|deployed|all (?:tests? )?pass|now (?:works?|supports?))\b", re.I)
CHOICE = re.compile(r"\b(?:instead|rather than|choose|chose|choice|prefer|use|using|switch|replace|scope|only|don.t want|didn.t ask)\b", re.I)
HOME = re.compile(r"(?:[A-Za-z]:[\\/]Users[\\/][^\\/\s\"']+|/(?:Users|home)/[^/\s\"']+)", re.I)


def scrub(value, names=()):
    """Remove local user identities and credential-shaped strings recursively."""
    if isinstance(value, dict):
        return {k: scrub(v, names) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v, names) for v in value]
    if not isinstance(value, str):
        return value
    value = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)", "[private key removed]", value, flags=re.S)
    value = HOME.sub("/workspace", value)
    value = re.sub(r"(CLAUDE_CODE_OAUTH_TOKEN\s*=\s*['\"]?)(?!\[credential removed\])[^\s'\";<>]+", r"\1[credential removed]", value)
    value = re.sub(r"(?<![A-Za-z0-9_.+%-])[A-Za-z0-9_.+%-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,63}", "[email removed]", value)
    value = re.sub(r"(?m)^(Author|Committer):[^\n]*", r"\1: [local-user]", value)
    for name in names:
        if name and len(name) >= 3:
            value = re.sub(r"(?<![\w])" + re.escape(name) + r"(?![\w])", "[local-user]", value)
    return re.sub(r"(?:sk-(?:ant-|svcacct-|proj-)[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}|hf_[A-Za-z0-9]{34}|AKIA[0-9A-Z]{16})", "[credential removed]", value)


def rows_to_events(rows, names=()):
    """Return events, reasoning, and source turn-number to event-sequence map."""
    rows = sorted(rows, key=lambda r: r["turn_number"])
    results = {r.get("tool_call_id"): r for r in rows if r["turn_type"] == "tool_result" and r.get("tool_call_id")}
    events, reasoning, mapping = [], {}, {}
    texts, thoughts, text_turns = [], [], []

    def append(event, turns=()):
        events.append(scrub(event, names))
        for turn in turns:
            mapping[str(turn)] = event["seq"]
        if thoughts:
            reasoning[str(event["seq"])] = scrub("\n".join(thoughts), names)
            thoughts.clear()

    def flush():
        if texts:
            append(message("\n\n".join(texts), len(events) + 1), text_turns)
            texts.clear()
            text_turns.clear()

    for row in rows:
        kind, text = row["turn_type"], row.get("content") or ""
        turn = row["turn_number"]
        if kind == "user_prompt":
            flush()
            append(instruction(text, len(events) + 1), [turn])
        elif kind == "assistant_thinking":
            if text:
                thoughts.append(text)
        elif kind == "assistant_response":
            texts.append(text)
            text_turns.append(turn)
        elif kind == "tool_use":
            result = results.get(row.get("tool_call_id"), {})
            args = row.get("tool_input_json") or text or "{}"
            try:
                args = json.loads(args) if isinstance(args, str) else args
            except ValueError:
                args = {"raw": args}
            event = tool(row.get("tool_name") or "unknown", args,
                         result.get("content") or "", len(events) + 1,
                         agent_text="\n\n".join(texts))
            append(event, [turn, *text_turns])
            if result:
                mapping[str(result["turn_number"])] = event["seq"]
            texts.clear()
            text_turns.clear()
    flush()
    return events, reasoning, mapping


def session_rows(raw_dir, source_paths=None):
    """Join ordered conversation shards by their actual source session id."""
    import pyarrow.parquet as pq
    metadata = {}
    path = Path(raw_dir) / "sessions.parquet"
    if path.exists():
        metadata = {r["session_id"]: r for r in pq.read_table(path, columns=[
            "session_id", "repo_id", "user_id", "owner_id", "agent", "session_success", "kind"]).to_pylist()}
    pending_id, pending = None, []
    previous_group = None
    for path in source_paths if source_paths is not None else sorted(Path(raw_dir).glob("conversations-*.parquet")):
        group = int(path.stem.rsplit("-", 1)[-1])
        if previous_group is not None and group != previous_group + 1:
            pending_id, pending = None, []
        previous_group = group
        for batch in pq.ParquetFile(path).iter_batches(batch_size=256):
            for row in batch.to_pylist():
                sid = row["session_id"]
                if sid != pending_id:
                    if pending and pending[0]["turn_number"] == 0:
                        yield pending_id, pending, metadata.get(pending_id, {})
                    pending_id, pending = sid, []
                pending.append(row)
    # The final session remains pending until a following source row proves its end.


def session_records(sid, rows, details):
    """Keep complete source streams and localize conservative teacher slices."""
    from monitor_format import is_cut_point, validate_events
    if details.get("kind") not in {None, "", "normal"}:
        return
    names = [details.get("user_id", ""), details.get("owner_id", "")]
    events, reasoning, mapping = rows_to_events(rows, names)
    if not events or not any(e["type"] == "tool_completed" for e in events):
        return
    validate_events(events)
    prompts = [r for r in rows if r["turn_type"] == "user_prompt"]
    by_seq = {e["seq"]: e for e in events}
    classified = [e["seq"] for e in events if is_cut_point(e)]
    if not classified:
        return
    agent = details.get("agent") or rows[0].get("agent") or "unknown"
    meta = dict(source="swe_chat", trajectory_id=sid, source_record_id=sid,
                task_id=sid, licence="ODC-BY-1.0", harness="claudecode" if agent == "Claude Code" else agent,
                repo_group=hashlib.sha256(str(details.get("repo_id", "unknown")).encode()).hexdigest())
    side = dict(reasoning=reasoning, source_labels=[], source_turn_to_seq=mapping,
                filter_facts={"agent": agent, "session_success": details.get("session_success"),
                              "has_pushback": any(p.get("prompt_pushback") in PUSHBACK for p in prompts)})
    for index, prompt in enumerate(prompts):
        text = prompt.get("content") or ""
        label = prompt.get("prompt_pushback")
        seq = mapping.get(str(prompt["turn_number"]))
        if index == 0 or label not in PUSHBACK or not seq or not REFERENCE.search(text) or text.rstrip().endswith("?") or "[Image:" in text:
            continue
        previous = [k for k in classified if k < seq]
        if not previous:
            continue
        cut = previous[-1]
        hint = dict(value=label, text=scrub(text, names), basis="outcome", origin="prompt_pushback", event_seq=cut)
        eligible = ["precorrection"]
        prior_text = by_seq[cut].get("agent_text", "")
        ignored = {"the", "and", "you", "your", "that", "this", "with", "still", "not", "does", "working", "done", "all", "now", "but", "have", "been", "are", "was", "its", "for"}
        item_words = lambda value: set(re.findall(r"[a-z][a-z0-9_.-]{2,}", value.lower())) - ignored
        if label == "failure_report" and CLAIM.search(prior_text) and item_words(text) & item_words(prior_text):
            eligible.append("claim")
        previous_prompt_seq = mapping.get(str(prompts[index - 1]["turn_number"]), 0)
        choices = [k for k in previous if k > previous_prompt_seq and CHOICE.search(by_seq[k].get("agent_text", "")) and item_words(text) & item_words(by_seq[k].get("agent_text", ""))]
        if label in {"correction", "rejection"} and CHOICE.search(text) and choices:
            eligible.append("scope")
        for slice_name in eligible:
            objective = {"precorrection": ["M1", "G1"], "claim": ["M5", "G5"], "scope": ["M7"]}[slice_name]
            source_cut = choices[0] if slice_name == "scope" else cut
            yield events, dict(side, outcome_hints=[dict(hint, event_seq=source_cut)]), dict(meta, slice=slice_name, objective=objective, cut_seq=source_cut, source_record_id=f"{sid}:{slice_name}:{prompt['turn_number']}")
        next_seq = mapping.get(str(prompts[index + 1]["turn_number"])) if index + 1 < len(prompts) else None
        responding = [k for k in classified if k > seq and (next_seq is None or k < next_seq)]
        if responding:
            recovery_side = dict(side, outcome_hints=[hint], correction=scrub(text, names), finding_question_rule="First teacher-positive question at the pushed-back event in item order; M1 when none is positive.", hooked_event_seq=cut, correction_seq=seq,
                                 findings=[dict(id="F1", question="M1", event_seqs=[cut], correction_seq=seq)])
            yield events, recovery_side, dict(meta, slice="postpushback", objective=["L7"], cut_seq=responding[-1], source_record_id=f"{sid}:postpushback:{prompt['turn_number']}")
    try:
        success = float(details.get("session_success") or -1)
    except ValueError:
        success = -1
    if agent == "Claude Code" and success >= 70 and not side["filter_facts"]["has_pushback"] and not details.get("kind"):
        yield events, side, dict(meta, slice="benign", objective=[])


def convert(raw_dir: Path, source_paths=None):
    """Yield eligible records in source order with a per-repository benign cap."""
    repo_counts = Counter()
    for sid, rows, details in session_rows(raw_dir, source_paths):
        for events, side, meta in session_records(sid, rows, details):
            if meta["slice"] == "benign":
                repo = meta["repo_group"]
                if repo_counts[repo] >= 20:
                    continue
                repo_counts[repo] += 1
            yield events, side, meta


def main():
    """Write validated records and measured source evidence."""
    from monitor_format import validate_events
    raw = Path("data/downloads/SALT-NLP--SWE-chat")
    output = Path("data/converted/swe_chat.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    source_paths = sorted(raw.glob("conversations-*.parquet"))
    counts, ids = Counter(), set()
    limits = dict(claim=100, scope=100, precorrection=250, postpushback=150, benign=600)
    skipped = Counter()
    session_counts = Counter()
    temporary_output = output.with_suffix(".partial")
    with temporary_output.open("w", encoding="utf-8") as handle:
        for events, side, meta in convert(raw, source_paths):
            kind = meta["slice"]
            group = (meta["trajectory_id"], kind)
            if counts[kind] >= limits[kind] or session_counts[group] >= 4:
                skipped[kind] += 1
                continue
            session_counts[group] += 1
            validate_events(events)
            handle.write(json.dumps(dict(events=events, side=side, meta=meta), ensure_ascii=False) + "\n")
            handle.flush()
            counts[meta["slice"]] += 1
            ids.add(meta["trajectory_id"])
    temporary_output.replace(output)
    files = [dict(path=str(p), bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [*source_paths, raw / "sessions.parquet"]]
    import pyarrow.parquet as pq
    source_counts = Counter()
    for _, source_rows, details in session_rows(raw, source_paths):
        source_counts["complete_sessions"] += 1
        source_counts["complete_rows"] += len(source_rows)
        source_counts["zero_tool_sessions"] += not any(r["turn_type"] == "tool_use" for r in source_rows)
        source_counts["non_normal_sessions"] += bool(details.get("kind"))
        for row in source_rows:
            if row["turn_type"] == "user_prompt":
                source_counts["prompt_label_" + str(row.get("prompt_pushback"))] += 1
    report = dict(source="swe_chat", output_records=sum(counts.values()), slice_counts=dict(counts), trajectory_groups=len(ids), source_rows=source_counts["complete_rows"], downloaded_rows=sum(pq.ParquetFile(p).metadata.num_rows for p in source_paths), source_counts=dict(source_counts), quota_shortfalls={k: max(0, v - counts[k]) for k, v in limits.items()}, source_files=files, visible_positive_labels=0, planned_slice_quotas=limits, filter_counts={"quota_or_session_cap": dict(skipped)}, positive_rule_counts={k: v for k, v in counts.items() if k != "benign"}, errors=[], blockers=[], output_path=str(output))
    target = Path("results/sources/swe_chat.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (raw / "selected-session-ids.json").write_text(json.dumps(sorted(ids)), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "source_files"}))


if __name__ == "__main__":
    main()




