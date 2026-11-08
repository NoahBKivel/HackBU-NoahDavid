"""Track issue identity, dismissals, closures and severity upgrades."""

from .firing import status

ACTION_QUESTIONS = frozenset({"M1", "M2", "M4", "M5", "M7", "M8"})


def issue_key(question: str, seq: int | None) -> list:
    """Key action questions by event and run questions by their judged subject."""
    base, _, suffix = question.partition("#")
    if base == "M8":
        return [base, seq, suffix]
    if base in ACTION_QUESTIONS:
        return [base, seq]
    return [base, suffix] if base == "G2" else [base]


def change_status(findings: list[dict], answers: dict, fired: dict, new_instruction: bool) -> None:
    """Apply correction outcomes and run resets before diagnostic decisions."""
    for finding in findings:
        if finding["status"] == "closed":
            continue
        message = finding.get("message")
        key = f"L7#{message}"
        base = finding["question"].split("#")[0]
        if message and key in answers:
            answer = status(answers[key])
            finding["last_l7"] = answer
            if answer == "genuinely fixed":
                finding["status"] = "closed"
            elif answer == "dismissed correctly":
                finding["status"] = "closed" if base in ACTION_QUESTIONS else "dismissed"
        if base not in ACTION_QUESTIONS and (finding["severity"] == "minor" or finding["status"] == "dismissed"):
            if new_instruction or (finding["question"] in answers and finding["question"] not in fired):
                finding["status"] = "closed"


def current(findings: list[dict], key: list) -> dict | None:
    """Find an issue that still suppresses repeated notices."""
    return next((f for f in findings if f["key"] == key and f["status"] in {"open", "dismissed"}), None)


def diagnostics_needed(findings: list[dict], fired: dict, seq: int | None) -> bool:
    """Ask diagnostics only for a new issue or a possible minor upgrade."""
    for question in fired:
        finding = current(findings, issue_key(question, seq))
        if finding is None or (finding["status"] == "open" and finding["severity"] == "minor"):
            return True
    return False


def open_or_upgrade(findings: list[dict], fired: dict, seq: int | None, severity: str, cited: list[int]) -> list[dict]:
    """Return only findings that need this event's notice or correction."""
    changed = []
    for question, probability in fired.items():
        evidence = [seq] if question.startswith("M8#") else list(cited)
        key = issue_key(question, seq)
        finding = current(findings, key)
        if finding is not None:
            if finding["status"] != "open" or finding["severity"] != "minor" or severity == "minor":
                continue
            finding.update(severity=severity, cited=evidence, probability=probability)
        else:
            finding = {"id": f"F{len(findings) + 1}", "question": question, "key": key,
                       "opened_at": seq, "cited": evidence, "severity": severity,
                       "probability": probability, "message": None, "reached_at": None,
                       "status": "open", "last_l7": "open"}
            findings.append(finding)
        changed.append(finding)
    return changed


def close_minor_actions(findings: list[dict]) -> None:
    """Close minor action issues when their potential notice has been sent."""
    for finding in findings:
        if finding["severity"] == "minor" and finding["question"].split("#")[0] in ACTION_QUESTIONS:
            finding["status"] = "closed"
