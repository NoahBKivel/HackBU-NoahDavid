"""Render cut-local teacher evidence through the frozen shared implementation."""

from copy import deepcopy
import hashlib
import json
import re
from types import SimpleNamespace

from monitor_format import (EVERY_EVENT, build_instructions, collect_documents,
    render_state, render_screen, screen_section_cap, split_sections, split_units,
    fill_question, validate_events, validate_record, is_cut_point, count_tokens)
from intent_training.teacher.prepare import prepare_record, requirement_records


_SECRET = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}|sk-(?:svcacct|proj)-[A-Za-z0-9_-]{20,}|"
                     r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}|"
                     r"AKIA[0-9A-Z]{16}|hf_[A-Za-z0-9]{34}|"
                     r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
                     r"CLAUDE_CODE_OAUTH_TOKEN\s*=\s*['\"]?[A-Za-z0-9_-]{8,}|"
                     r"\.jwt_secret\s*[:=]\s*['\"]?[A-Za-z0-9_/-]{8,}")


def scan(value):
    """Reject credential-bearing evidence without printing matched content."""
    if _SECRET.search(json.dumps(value, ensure_ascii=False)):
        raise ValueError("Credential pattern in prepared evidence.")


def stable_id(value):
    """Hash canonical source identity and content across repeated runs."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def load_tokenizer(folder):
    """Load the actual cached BPE with the shared user-text escaping contract."""
    from tokenizers import Tokenizer
    raw = Tokenizer.from_file(str(folder / "tokenizer.json"))

    class PinnedTokenizer:
        def __call__(self, text, add_special_tokens=False):
            return SimpleNamespace(input_ids=raw.encode(text, add_special_tokens=add_special_tokens).ids)

        def convert_tokens_to_ids(self, token):
            return raw.token_to_id(token)

    return PinnedTokenizer()


def metadata(meta):
    """Preserve provenance and prioritize real pair links for split grouping."""
    result = deepcopy(meta)
    identity = (meta.get("pair_id") or meta.get("trajectory_id") or meta.get("task_id")
                or meta.get("source"))
    result["group_id"] = stable_id({"source": meta["source"], "identity": identity})
    return result


def prepare_native(row):
    """Keep real replay questions and labels without a teacher relabeling pass."""
    result = deepcopy(row["side"]["native_record"])
    if not isinstance(result["state"], str):
        try:
            from kev.api import render
        except ModuleNotFoundError:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "vendor" / "kev"))
            from kev.api import render
        original_state = deepcopy(result["state"])
        result["state"] = render(original_state)
        result.setdefault("_meta", {})["original_state"] = original_state
    original_meta = deepcopy(result.get("_meta", {}))
    merged = dict(original_meta, **row["meta"])
    if original_meta.get("source") and original_meta["source"] != row["meta"]["source"]:
        merged.setdefault("original_source", original_meta["source"])
    result["_meta"] = metadata(merged)
    if original_meta.get("group_id"):
        result["_meta"]["original_group_id"] = original_meta["group_id"]
        if not merged.get("pair_id"):
            result["_meta"]["group_id"] = stable_id({"source": merged["source"], "native_group": original_meta["group_id"]})
    result["_meta"]["native_record"] = True
    result["_meta"]["record_kind"] = ("long" if row["meta"]["source"] in
        {"quality_long", "policy_long"} else "task" if row["meta"].get("objective") else "replay")
    result["record_id"] = stable_id({"source": row["meta"]["source"],
        "source_record_id": row["meta"].get("source_record_id"),
        "native": row["side"]["native_record"]})
    try:
        validate_record(result)
    except ValueError as error:
        if not str(error).endswith("requires its wording."):
            raise
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "vendor" / "kev"))
        from kev.api import SystemOneRequest
        SystemOneRequest.model_validate({"state": result["state"], "questions": result["questions"]})
        if any("label" not in question for question in result["questions"].values()):
            raise ValueError("An original native question requires its original label.")
    scan(result)
    return result


def _units(instructions, documents):
    units = []
    for item in instructions:
        units.extend(split_units(item["text"], f"[{item['id']}]"))
    for document in documents:
        units.extend(split_units(document["text"], document["path"]))
    return units


def _teacher(record, side):
    prepared = prepare_record(record, side)
    prepared["_meta"] = deepcopy(record["_meta"])
    # Outcome-only annotations remain explicitly marked hints, never visible evidence.
    hints = {key: deepcopy(value) for key, value in side.items()
             if key in {"outcomes", "outcome", "outcome_hints", "source_hints", "hints"}}
    if hints:
        prepared["teacher_side"]["outcome_hints"] = {"basis": "outcome", "values": hints}
    return prepared


def prepare_stream(row, cut, tokenizer, state_budget=8191, screen_budget=8192):
    """Return rendered records, RF selections and assembly-only context."""
    events, side, meta = row["events"], row["side"], metadata(row["meta"])
    validate_events(events)
    scan(side)
    k = int(cut["cut_seq"])
    visible = [event for event in events if event["seq"] <= k]
    if not visible or visible[-1]["seq"] != k or not is_cut_point(visible[-1]):
        raise ValueError("The cut must name a classified event.")
    if any(event.get("agent_thinking") for event in events):
        raise ValueError("Raw reasoning must remain in side records.")
    meta.update(cut)
    meta["record_kind"] = "task"
    meta["state_budget"] = state_budget
    meta["validated_length"] = state_budget
    if side.get("construction"):
        meta["construction"] = side["construction"].get("type")
    intended = side.get("construction", {}).get("intended", {})
    meta["objective"] = sorted(set(meta.get("objective", [])) | {key.split("#")[0] for key in intended})
    instructions = build_instructions(visible)
    documents = collect_documents(visible)
    supplied_findings = side.get("findings", side.get("open_findings", []))
    if isinstance(supplied_findings, dict):
        supplied_findings = [supplied_findings]
    findings = [deepcopy(item) for item in supplied_findings
                if item.get("status", "open") == "open"
                and item.get("correction_seq") is not None and item["correction_seq"] <= k]
    for finding in findings:
        if not finding.get("correction") and isinstance(side.get("correction"), str):
            finding["correction"] = side["correction"]
    identity = {"source": meta["source"], "trajectory": meta.get("trajectory_id"),
                "pair": meta.get("pair_id"), "cut": k, "events": visible}
    cut_id = stable_id(identity)
    state, detailed, fits = render_state(instructions, documents, events, k, findings,
                                         state_budget, tokenizer=tokenizer)
    if side.get("construction", {}).get("type") == "overflow_screen" or meta.get("form") == "screen":
        meta["screen_trigger"] = "construction"
        fits = False
    elif not fits:
        meta["screen_trigger"] = "budget"
    parent = stable_id({"cut_id": cut_id, "state": state, "screen": not fits})
    meta["cut_id"] = cut_id
    units = _units(instructions, documents) if fits else []
    records = []
    if fits:
        questions = {key: fill_question(key, tokenizer=tokenizer) for key in EVERY_EVENT}
        if visible[-1]["type"] == "turn_completed" and visible[-1]["turn"].get("reason") == "answer":
            questions["G5"] = fill_question("G5", tokenizer=tokenizer)
        for index, finding in enumerate(findings, 1):
            if finding.get("correction"):
                questions[f"L7#F{index}"] = fill_question("L7", correction=finding["correction"], tokenizer=tokenizer)
        records.append({"record_id": parent, "state": state, "questions": questions, "_meta": meta})
    else:
        cap = screen_section_cap(instructions, events, k, screen_budget, tokenizer=tokenizer)
        sections = []
        for document in documents:
            for section in split_sections(document, tokenizer=tokenizer, cap=cap):
                section["id"] = f"S{len(sections) + 1}"
                sections.append(section)
        while sections:
            chosen = []
            for section in sections:
                _, accepted = render_screen(instructions, chosen + [section], events, k,
                                             screen_budget, tokenizer=tokenizer)
                if not accepted:
                    break
                chosen.append(section)
            if not chosen:
                raise ValueError("A document section or required instructions exceed the screen budget.")
            screen, accepted = render_screen(instructions, chosen, events, k, screen_budget, tokenizer=tokenizer)
            questions = {f"{question}#{section['id']}": fill_question(question,
                         section_id=section["id"], tokenizer=tokenizer)
                         for section in chosen for question in ("SCR", "M8")}
            screen_meta = dict(meta, form="screen", record_kind="screen", objective=["SCR", "M8"],
                               sections=deepcopy(chosen), parent_record_id=parent)
            records.append({"record_id": stable_id({"parent": parent, "state": screen, "sections": chosen}),
                            "state": screen, "questions": questions, "_meta": screen_meta})
            sections = sections[len(chosen):]
        if not records:
            raise ValueError("Overflow has no project documents to screen.")
    rf = []
    contexts = []
    prepared = []
    for record in records:
        output = _teacher(record, side)
        if meta.get("source_evidence_sha256"):
            original_id = record["record_id"]
            evidence = stable_id(output["teacher_side"])
            revised_id = stable_id({"base_record_id": original_id, "teacher_side_sha256": evidence})
            record["record_id"] = output["record_id"] = revised_id
            record["_meta"].update(record_id=revised_id, supersedes_record_id=original_id,
                                   source_evidence_sha256=evidence)
            output["_meta"].update(record["_meta"])
        output["requirement_units"] = deepcopy(units)
        output["_meta"]["state_tokens"] = count_tokens(output["state"], tokenizer)
        scan(output)
        prepared.append(output)
        # Complete base streams remain private assembly evidence, never teacher input.
        contexts.append({"record_id": record["record_id"], "_meta": record["_meta"],
                         "events": events, "side": side, "detailed_event_seqs": detailed,
                         "requirement_units": units})
        if fits:
            rf.extend(requirement_records(record["record_id"], meta["source"], units))
    for record in rf:
        scan(record)
    return prepared, rf, contexts
