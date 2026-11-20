"""Verify the permitted reported failure after one tightened teacher relabel."""

import hashlib
import json
from pathlib import Path

from intent_training.assemble.labels import collect_votes

RULE = "reported failure; labels stand"
METRICS = ("rows", "both_positive", "sol_only_positive", "terra_only_positive",
           "cant_tell_votes", "positive_specific_agreement", "cant_tell_rate")


def teacher_passed(question, instrument):
    if instrument.get("paired_rows") == 0 and instrument.get("single_sol_rows", 0) > 0:
        return True
    specific = instrument.get("positive_specific_agreement")
    return instrument["cant_tell_rate"] <= .25 and (question in {"L7", "D5"}
        or (specific is not None and specific >= .70))


def _verified_file(reference):
    path = Path(reference["path"])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError("A teacher fallback evidence file changed after it was recorded.")
    return path, raw


def _manifest_votes(reference, question, *, tightened_text=None):
    from intent_training.teacher import agreement_report, validate_vote
    from intent_training.teacher.dispatch import digest
    _, raw = _verified_file(reference)
    manifest = json.loads(raw)
    if not isinstance(manifest, list) or not manifest:
        raise ValueError("A teacher fallback needs a nonempty actual dispatch manifest.")
    envelopes = []
    for entry in manifest:
        batch = json.loads(Path(entry["input"]).read_text(encoding="utf-8"))
        frozen_input = ({"records": batch["records"], "instruction_supplement": batch["instruction_supplement"]}
                        if "instruction_supplement" in batch else batch["records"])
        if digest(frozen_input) != batch["input_sha256"]:
            raise ValueError("A teacher fallback batch changed from its frozen input hash.")
        if tightened_text is not None:
            if tightened_text not in batch.get("instruction_supplement", ""):
                raise ValueError("The relabel batch lacks its actual tightened instructions.")
            if tightened_text not in Path(entry["prompt"]).read_text(encoding="utf-8"):
                raise ValueError("The dispatched relabel prompt lacks its tightened instructions.")
        for line in Path(entry["output"]).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            vote = json.loads(line)
            validate_vote(vote, batch, entry["model_family"])
            if any(key.split("#", 1)[0] == question for key in vote["votes"]):
                envelopes.append(vote)
    joined = collect_votes(envelopes)
    triples, ids = [], []
    for record_id, rows in joined.items():
        for key, pair in rows.items():
            if key.split("#", 1)[0] != question:
                continue
            if set(pair) != {"sol", "terra"}:
                raise ValueError("A fallback relabel row lacks one independent model family.")
            triples.append((key, pair["sol"], pair["terra"]))
            ids.append(record_id + ":" + key)
    if not triples:
        raise ValueError("A teacher fallback manifest contains no votes for its question.")
    return agreement_report(triples)[question], sorted(ids)


def verify_teacher_fallback(question, evidence, current_instrument):
    """Recompute both failures and require real prompt and independently voted rows."""
    if evidence.get("question") != question or evidence.get("relabel_attempts") != 1 or evidence.get("rule") != RULE:
        raise ValueError("A teacher fallback requires exactly one relabel and its explicit standing-label rule.")
    _, prompt = _verified_file(evidence["tightened_prompt"])
    if not prompt.strip():
        raise ValueError("A teacher fallback needs actual tightened instructions.")
    tightened_text = prompt.decode("utf-8")
    _, ledger_bytes = _verified_file(evidence["relabel_ledger"])
    ledger = json.loads(ledger_bytes)
    attempts = [entry for entry in ledger if entry.get("question") == question and entry.get("action") == "relabel_once"]
    if len(attempts) != 1:
        raise ValueError("The relabel ledger must contain exactly one tightened attempt for the question.")
    if (attempts[0].get("instructions_sha256") != evidence["tightened_prompt"]["sha256"]
            or attempts[0].get("supplementary_instructions") != tightened_text):
        raise ValueError("The tightened prompt does not match the permitted relabel ledger entry.")
    first_reference, second_reference = evidence["initial_vote_manifest"], evidence["relabel_vote_manifest"]
    if first_reference["sha256"] == second_reference["sha256"]:
        raise ValueError("The initial and relabel vote manifests must be distinct.")
    first, first_ids = _manifest_votes(first_reference, question)
    second, second_ids = _manifest_votes(second_reference, question, tightened_text=tightened_text)
    if first_ids != sorted(evidence["initial_vote_ids"]) or second_ids != sorted(evidence["relabel_vote_ids"]):
        raise ValueError("The teacher fallback vote identifiers do not match its real manifests.")
    if first_ids != second_ids:
        raise ValueError("The tightened relabel must cover the same failing question rows exactly once.")
    for measured, claimed in ((first, evidence["initial_instrument"]),
                              (second, evidence["second_instrument"]), (first, attempts[0]["instrument"])):
        if any(measured.get(key) != claimed.get(key) for key in METRICS):
            raise ValueError("The teacher fallback metrics differ from its actual validated votes.")
    if teacher_passed(question, first) or teacher_passed(question, second):
        raise ValueError("A reported failure fallback requires both measured failures.")
    if teacher_passed(question, current_instrument):
        raise ValueError("A passing current instrument does not need a reported failure fallback.")
    return {"question": question, "rule": RULE, "relabel_attempts": 1,
            "initial": first, "second": second, "evidence": evidence, "verified": True}
