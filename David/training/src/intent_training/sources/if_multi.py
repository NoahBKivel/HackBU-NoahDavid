"""Convert real instruction prompts with generator and isolated verifier evidence."""

import ast
import hashlib
import json
import re
from collections.abc import Iterator
from pathlib import Path

from .events import instruction, message

DATASET = "allenai/IF_multi_constraints_upto5"
LICENCE = "ODC-BY"
_IMPERATIVE = re.compile(
    r"\b(?:must|should|shall|need|please|write|make|use|give|provide|describe|explain|"
    r"identify|determine|calculate|repeat|include|exclude|do|don't|avoid|ensure|find|"
    r"create|list|answer|respond|return|tell|translate|summari[sz]e|implement|compute|"
    r"prove|evaluate|construct|design|suggest|convert|select|choose|help|draft|print|"
    r"output|compare|analy[sz]e|check|assume|let|add|remove|replace|format|read|solve|"
    r"imagine|consider|suppose|given|note|response|task|expected|you|your|we|our|"
    r"want|wish|ought|shall|will|can|may|example|input|solution)\b|[?!:]", re.I)
_DECLARATIVE = re.compile(r"^(?:A|An|The|This|These|Those|It|He|She|They|Each|One|There)\s")


def source_rows(raw_dir: Path) -> Iterator[tuple[int, dict]]:
    """Read inert extracted rows in original dataset order."""
    with (Path(raw_dir) / "rows.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            wrapped = json.loads(line)
            yield wrapped["row_idx"], wrapped["row"]


def parse_row(row: dict) -> tuple[str, list[str], list[str], list[dict | None]]:
    """Require exact segment-to-checker alignment before deriving any label."""
    messages = row["messages"]
    if len(messages) != 1 or messages[0]["role"] != "user":
        raise ValueError("A source row must contain one user message.")
    prompt = messages[0]["content"]
    constraints = row["constraint"].split("\t")
    truth = ast.literal_eval(row["ground_truth"])
    if not isinstance(truth, list) or len(truth) != 1:
        raise ValueError("The verifier specification must contain one instruction group.")
    ids, kwargs = truth[0]["instruction_id"], truth[0]["kwargs"]
    if not constraints or len(constraints) != len(ids) or len(ids) != len(kwargs):
        raise ValueError("Constraint segments and verifier instructions must align.")
    if any(not isinstance(x, str) or not x for x in constraints + ids):
        raise ValueError("Constraints and instruction identifiers must be nonempty text.")
    if any(x is not None and not isinstance(x, dict) for x in kwargs):
        raise ValueError("Verifier arguments must be objects or null.")
    suffix = " ".join(constraints)
    if not prompt.endswith(suffix):
        raise ValueError("The appended constraint spans do not match the original prompt.")
    return prompt[:-len(suffix)].rstrip(), constraints, ids, kwargs


def request_id(index: int) -> str:
    """Identify a central generation request without including answer evidence."""
    return f"if_multi-{index:05d}"


def variant(index: int) -> str:
    """Distribute paraphrase, document and verbatim forms across source rows."""
    return ("paraphrase", "document", "verbatim")[index % 3]


def generation_requests(raw_dir: Path) -> Iterator[dict]:
    """Request rewrites and agent answers exclusively through central generation."""
    for index, row in source_rows(raw_dir):
        if index >= 400:
            break
        base, constraints, _, _ = parse_row(row)
        mode = variant(index)
        if index < 200 and mode == "verbatim":
            continue
        prompt = (
            "Paraphrase each constraint without changing its meaning or numeric parameters. "
            if mode == "paraphrase" else
            "Embed the exact constraints in realistic CLAUDE.md-style project guidance. "
            if mode == "document" else "Keep all constraint strings exactly verbatim. ")
        prompt += (
            "Move constraints away from the end of the request. Return only a JSON object with "
            "instruction (user request), document (project guidance text or null), constraints "
            "(aligned strings in original order), and response (assistant answer or null). "
            "Every constraint must occur verbatim in instruction or document, on its own paragraph. "
            "Include the complete original base request without changing its text. "
            + ("Generate one natural assistant answer to the resulting request."
               if index >= 200 else "Set response to null; this request only rewrites source instructions."))
        yield {"id": request_id(index), "purpose": "instruction_answer" if index >= 200 else "instruction_rewrite",
               "prompt": prompt + "\n" + json.dumps({"base_request": base, "constraints": constraints,
                                                      "variant": mode}, ensure_ascii=False),
               "max_output_tokens": 4096 if index >= 200 else 2048,
               "refs": {"source": DATASET, "source_record_id": row["key"], "row_idx": index}}


def generated_context(index: int, row: dict, responses: Path) -> tuple[dict, dict | None] | None:
    """Consume only identifiable central responses; absent responses remain absent."""
    base, constraints, _, _ = parse_row(row)
    if index < 200 and variant(index) == "verbatim":
        return {"instruction": "\n\n".join(constraints) + "\n\n" + base,
                "document": None, "constraints": constraints, "response": None}, None
    path = responses / f"{request_id(index)}.json"
    if not path.is_file():
        return None
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if envelope.get("id") != request_id(index) or not envelope.get("model"):
        raise ValueError("The central generation envelope must retain identity and model evidence.")
    text = envelope["text"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    value = json.loads(text)
    changed = value["constraints"]
    if len(changed) != len(constraints) or any(not isinstance(x, str) or not x for x in changed):
        raise ValueError("Generated constraints must remain aligned with source instructions.")
    if variant(index) != "paraphrase" and changed != constraints:
        raise ValueError("Only paraphrase variants may alter original constraint wording.")
    if not isinstance(value["instruction"], str) or base not in value["instruction"]:
        raise ValueError("The complete original base request must remain visible.")
    document = value.get("document")
    if document is not None and not isinstance(document, str):
        raise ValueError("The project document must be text or null.")
    if any(x not in value["instruction"] + "\n" + (document or "") for x in changed):
        raise ValueError("A generated constraint is absent from the visible context.")
    if variant(index) == "document" and not document:
        raise ValueError("Document variants must supply project guidance.")
    if index >= 200 and not isinstance(value.get("response"), str):
        raise ValueError("Answer records require an actual centrally generated response.")
    return value, envelope


def requirement_units(context: dict, original: list[str], base: str) -> list[dict]:
    """Keep exact unit text and original positive basis; filter imperative negatives."""
    from monitor_format import split_units

    units = []
    locations = [(context["instruction"], "[I1]")]
    if context.get("document"):
        locations.append((context["document"], "CLAUDE.md"))
    positives = [split_units(text, "constraint") for text in context["constraints"]]
    for text, source in locations:
        for unit in split_units(text, source):
            stripped = str(unit["text"]).strip()
            matches = [i for i, sentences in enumerate(positives)
                       if any(str(sentence["text"]).strip() == stripped for sentence in sentences)]
            if matches:
                units.append({**unit, "value": True, "original_basis": [original[i] for i in matches]})
            elif stripped in base and not _IMPERATIVE.search(stripped):
                if stripped.isascii() and _DECLARATIVE.match(stripped) and stripped.endswith("."):
                    units.append({**unit, "value": False, "original_basis": stripped})
    return units


def convert(raw_dir: Path, *, errors: list | None = None) -> Iterator[tuple[list[dict], dict, dict]]:
    """Yield available RF records and responses supported by official checker outcomes."""
    from monitor_format import validate_events

    raw_dir = Path(raw_dir)
    responses = raw_dir.parents[1] / "generation/responses"
    for index, row in source_rows(raw_dir):
        if index >= 400:
            break
        try:
            prepared = generated_context(index, row, responses)
        except (ValueError, TypeError, KeyError, IndexError) as error:
            if errors is not None:
                errors.append({'request_id': request_id(index), 'error_type': type(error).__name__,
                               'reason': str(error)})
            continue
        if prepared is None:
            continue
        context, envelope = prepared
        base, original, ids, kwargs = parse_row(row)
        documents = {"CLAUDE.md": context["document"]} if context.get("document") else None
        events = [instruction(context["instruction"], documents=documents)]
        units = requirement_units(context, original, base)
        side = {"reasoning": {}, "outcomes": {}, "source_labels": [], "licence": LICENCE,
                "requirement_units": units,
                "constraint_basis": [{"text": text, "instruction_id": ident, "kwargs": args}
                                     for text, ident, args in zip(original, ids, kwargs, strict=True)]}
        meta = {"source": "if_multi", "source_record_id": row["key"], "task_id": row["key"],
                "trajectory_id": f"if_multi:{index}", "objective": ["RF"] if index < 200 else ["M2", "D2", "G2"],
                "licence": LICENCE, "harness": "if_multi_message", "cut_kind": "unspecified",
                "variant": variant(index), "row_idx": index}
        if index < 200:
            side["source_labels"] = [{"question": "RF", "value": unit["value"], "event_seq": 1,
                                      "basis": "visible", "origin": "rule", "unit": unit} for unit in units]
        else:
            path = raw_dir / "checks" / f"{request_id(index)}.json"
            if not path.is_file():
                events.append(message(context['response'], 2))
                side['checks_pending'] = True
                side['outcomes']['generation'] = {
                    key: envelope.get(key) for key in ('id', 'model', 'usage', 'cost_usd')}
                meta.update(cut_seq=2, checks_pending=True)
                validate_events(events)
                yield events, side, meta
                continue
            check = json.loads(path.read_text(encoding="utf-8"))
            response = context["response"]
            digest = hashlib.sha256(response.encode("utf-8")).hexdigest()
            if check.get("response_sha256") != digest or check.get("instruction_ids") != ids:
                raise ValueError("Verifier evidence must match the response and instruction identifiers.")
            if check.get("isolation") not in {"docker", "modal"} or check.get("errors"):
                events.append(message(response, 2))
                side['checks_pending'] = False
                side['checker_errors'] = check.get('errors', [])
                side['outcomes']['per_instruction'] = check
                meta.update(cut_seq=2, checks_pending=False)
                validate_events(events)
                yield events, side, meta
                continue
            passed = check["passed"]
            if len(passed) != len(ids) or any(type(value) is not bool for value in passed):
                raise ValueError("Verifiers must return one boolean per source instruction.")
            events.append(message(response, 2))
            side["outcomes"] = {"basis": "outcome", "per_instruction": check,
                                 "generation": {key: envelope.get(key) for key in ("id", "model", "usage", "cost_usd")}}
            side["source_labels"] = [{"question": "M2", "value": not all(passed), "event_seq": 2,
                                      "basis": "visible", "origin": "rule"}]
            for text, status in zip(context["constraints"], passed, strict=True):
                if status:
                    side["source_labels"].append({"question": "G2", "value": "done",
                                                   "event_seq": 2, "basis": "visible", "origin": "rule",
                                                   "requirement_text": text})
                if not status:
                    side['outcomes'].setdefault('failed_requirements', []).append({
                        'requirement_text': text, 'basis': 'outcome',
                        'reason': 'A boolean failure does not distinguish not done from broken.'})
                    side["source_labels"].append({"question": "D2", "value": True, "event_seq": 2,
                                                   "basis": "visible", "origin": "rule", "requirement_text": text})
            meta.update(cut_seq=2, cut_kind="positive" if not all(passed) else "negative")
        validate_events(events)
        yield events, side, meta
