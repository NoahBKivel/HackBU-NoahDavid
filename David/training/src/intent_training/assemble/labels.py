"""Resolve independent teacher votes and visible source evidence."""

from copy import deepcopy
import hashlib
import json

TWINS = frozenset({"M1", "L1", "L4", "G1"})


def base_question(key):
    return key.split("#", 1)[0].split("~", 1)[0]


def positive(key, label):
    """Return whether a hard label is in the question's detected class."""
    base = base_question(key)
    if base in {"L7", "D5"}:
        return False
    if base == "G2":
        return label in {"broken", "not done"}
    inverted = (base == "G1") != ("~neg" in key)
    return label is (not inverted)


def _binary(value):
    if value is True or value in ("yes", "true"):
        return 1.0
    if value is False or value in ("no", "false"):
        return 0.0
    if value in ("cant_tell", "can't tell", "can't tell from what's visible", 0.5):
        return 0.5
    raise ValueError("A binary vote must be yes, no or cant_tell.")


def resolve_votes(key, row, sol, terra):
    """Resolve labels while retaining the arithmetic mean uncertainty target."""
    result = deepcopy(row)
    result.pop("target", None)
    if row["type"] == "noul":
        a, b = _binary(sol), _binary(terra)
        mean = (a + b) / 2
        result["label"] = mean > 0.5 if (base_question(key) == "G1") != ("~neg" in key) else mean >= 0.5
        if a != b or 0.5 in (a, b):
            result["target"] = {"false": 1 - mean, "true": mean}
        return result
    criteria = row["criteria"]
    options = list(criteria) if isinstance(criteria, dict) else [x.split(":", 1)[0] for x in criteria]
    def option(value):
        if row["type"] == "score" and isinstance(value, int) and not isinstance(value, bool):
            if not 0 <= value < len(options):
                raise ValueError("The score vote is outside its criteria.")
            return options[value]
        if value not in options:
            raise ValueError("A categorical vote must name an exact option.")
        return value
    a, b = option(sol), option(terra)
    winner = b if positive(key, b) and not positive(key, a) else a
    result["label"] = options.index(winner) if row["type"] == "score" else winner
    if a != b:
        result["target"] = {str(i) if row["type"] == "score" else name:
                            (int(name == a) + int(name == b)) / 2
                            for i, name in enumerate(options)}
    return result


def record_digest(record):
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def collect_votes(envelopes):
    """Combine audited teacher envelopes without silently replacing a vote."""
    result = {}
    fingerprints = {}
    for envelope in envelopes:
        record_id = envelope["record_id"]
        family = envelope.get("vote_slot", envelope["model_family"])
        physical = envelope["model_family"]
        sonnet_aux = physical == "sonnet" and family == "sol" and envelope.get("pass") not in {"main", "main_completion"}
        luna = (physical == "luna" and envelope.get("actual_model") == "gpt-6-luna"
                and envelope.get("model") == "gpt-6-luna" and envelope.get("vote_slot") in {"sol", "terra"})
        if family not in {"sol", "terra"} or (physical not in {"sol", "terra"} and not sonnet_aux and not luna):
            raise ValueError("The vote family must be sol or terra.")
        fingerprint_key = (record_id, envelope.get("pass", "main"))
        digest = envelope["input_sha256"]
        if fingerprint_key in fingerprints and fingerprints[fingerprint_key] != digest:
            raise ValueError("Teacher votes refer to different input hashes.")
        fingerprints[fingerprint_key] = digest
        for key, value in envelope["votes"].items():
            if "~neg" in key:
                raise ValueError("Negated twins must never receive teacher votes.")
            pair = result.setdefault(record_id, {}).setdefault(key, {})
            if family in pair:
                raise ValueError("A teacher family voted twice on one question.")
            pair[family] = value
    return result


def resolve_record(record, votes, *, source_labels=(), construction=None, allocation_mode=None):
    """Return a resolved record and evidence clashes and retry requests."""
    meta = record.get("_meta", {})
    if meta.get("source_label_conflicts") or meta.get("blocked_for_source_label_conflict"):
        raise ValueError("Conflicting visible source labels must be resolved before assembly.")
    source_labels = list(meta.get("merged_cut_source_labels", source_labels))
    result = deepcopy(record)
    result_meta = result.setdefault("_meta", {})
    result_meta.setdefault("merged_cut_source_labels", deepcopy(source_labels))
    if construction and construction.get("type"):
        result_meta["construction"] = construction["type"]
    if allocation_mode is None:
        from intent_training.teacher.vote_allocation import allocation
        allocation_mode = allocation({**result, "side": {"source_labels": source_labels,
                                                        "construction": construction}})
    if allocation_mode == "rf_single":
        from intent_training.teacher.vote_allocation import rf_quorum_slots
        rf_quorum_slots(record, ())
    if allocation_mode not in {"paired", "single_sol", "rf_single"}:
        raise ValueError("The vote allocation must be paired or single_sol.")
    result_meta["vote_allocation"] = allocation_mode
    result_meta["teacher_vote_families"] = {}
    audit = {"source": record.get("_meta", {}).get("source"), "allocation": allocation_mode,
             "clashes": [], "retry_requests": [], "unused_votes": {}}
    source = {}
    cut = record.get("_meta", {}).get("cut_seq")
    for label in source_labels:
        if cut is not None and label.get("basis") not in {"outcome", "O"} and label.get("event_seq", cut) > cut:
            raise ValueError("A visible source label refers to evidence after the cut.")
        key = label["question"]
        if label.get("requirement_text") and base_question(key) in {"G2", "D2"}:
            bindings = meta.get("requirement_bindings", {})
            matches = [question for question, text in bindings.items()
                       if base_question(question) == base_question(key) and text == label["requirement_text"]]
            if not matches:
                continue
            if len(matches) != 1:
                raise ValueError("A requirement annotation has ambiguous exact-text bindings.")
            key = matches[0]
        labels = source.setdefault(key, [])
        visible = {"visible", "V", "visible_state"}
        if label["basis"] in visible and any(item["basis"] in visible and item["value"] != label["value"] for item in labels):
            raise ValueError("Source labels disagree on the same question.")
        labels.append(label)
    for key, row in record["questions"].items():
        if "~neg" in key:
            raise ValueError("Derive twins after resolving their base questions.")
        pair = votes.get(key)
        required = (set(pair or {}) if allocation_mode == "rf_single" else
                    {"sol", "terra"} if allocation_mode == "paired" else {"sol"})
        if not pair or not required <= set(pair) or set(pair) - {"sol", "terra"}:
            raise ValueError("Every requested question needs both teacher votes for paired allocation or Sol for single allocation.")
        result_meta["teacher_vote_families"][key] = sorted(required)
        if allocation_mode == "single_sol" and "terra" in pair:
            audit["unused_votes"][key] = {"terra": pair["terra"]}
        first = pair["sol"] if "sol" in required else pair["terra"]
        second = pair["terra"] if "terra" in required else first
        resolved = resolve_votes(key, row, first, second)
        final_visible = None
        for label in source.get(key, []):
            value = label["value"]
            if row["type"] == "noul" and type(value) is int and value in {0, 1}:
                value = bool(value)
            source_row = resolve_votes(key, row, value, value)
            teacher_rows = [resolve_votes(key, row, value, value) for value in pair.values()]
            if any(item["label"] != source_row["label"] or "target" in item for item in teacher_rows):
                audit["clashes"].append({"question": key, "source_label": source_row["label"],
                                         "teacher_label": resolved["label"], "basis": label["basis"],
                                         "origin": label.get("origin"), "votes": deepcopy(pair)})
            if label["basis"] in {"visible", "V", "visible_state"}:
                final_visible = source_row
        if final_visible is not None:
            resolved = final_visible
        result["questions"][key] = resolved
    if construction:
        attempt = construction.get("attempt", 1)
        if type(attempt) is not int or not 1 <= attempt <= 3:
            raise ValueError("Construction attempts must be integers from one through three.")
        intended = construction.get("intended", {})
        for key, value in intended.items():
            if key in result["questions"] and result["questions"][key]["label"] != value:
                audit["retry_requests"].append({"question": key, "intended": value,
                                                 "attempt": attempt + 1,
                                                 "retry": attempt < 3})
    return result, audit


def add_twins(record):
    """Derive the exact four inverse rows from the resolved base rows."""
    from monitor_format.questions import QUESTION_TABLE
    result = deepcopy(record)
    for key, row in record["questions"].items():
        if key not in TWINS:
            continue
        twin = deepcopy(QUESTION_TABLE[key + "~neg"])
        twin["label"] = not row["label"]
        if "target" in row:
            twin["target"] = {"false": row["target"]["true"], "true": row["target"]["false"]}
        result["questions"][key + "~neg"] = twin
    return result


def validate_twins(record):
    for base in TWINS:
        twin = base + "~neg"
        rows = record["questions"]
        if (base in rows) != (twin in rows):
            raise ValueError("A base question and its negated twin must stay together.")
        if base in rows:
            if rows[twin]["label"] != (not rows[base]["label"]):
                raise ValueError("A negated twin has an inconsistent label.")
            if "target" in rows[base]:
                expected = {"false": rows[base]["target"]["true"], "true": rows[base]["target"]["false"]}
                if rows[twin].get("target") != expected:
                    raise ValueError("A negated twin has an inconsistent target.")
