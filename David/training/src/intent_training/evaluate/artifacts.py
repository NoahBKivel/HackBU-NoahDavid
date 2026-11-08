"""Serialize measured evaluation values and their model identities."""

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read explicitly selected score or record artifacts."""
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_results(report: dict[str, Any], path: Path) -> None:
    """Write measured values with sample counts, intervals and candidate identities."""
    selected, stock = report["selected_candidate"], report["stock_candidate"]
    lines = ["# Monitor evaluation results", "", f"Selected candidate: `{selected}`. Stock candidate: `{stock}`.", "",
             "| Measurement | Candidate | n | Value | 95% interval |", "|---|---|---:|---:|---|"]

    def append(name: str, candidate: str, value: dict[str, Any], key: str = "value") -> None:
        low, high = value["interval"]
        lines.append(f"| {name} | {candidate} | {value['n']} | {value[key]:.8f} | [{low:.8f}, {high:.8f}] |")

    for endpoint, result in report["lift"]["endpoints"].items():
        append(f"{endpoint} accuracy lift", f"{selected} minus {stock}", result, "difference")
    append("Retention accuracy difference", f"{selected} minus {stock}", report["retention"], "difference")
    for candidate, value in report["requirement_recall"].items():
        append("Requirement-filter recall", selected if candidate == "selected" else stock, value)
    for question, results in report["benign_rates"].items():
        for candidate, value in results.items():
            append(f"Benign {question} problem rate", {"selected": selected, "stock": stock, "teacher": "teacher"}[candidate], value)
    for benchmark in ("llmbar", "rewardbench2"):
        for question, results in report[benchmark]["measured"].items():
            for candidate, value in results.items():
                append(f"{benchmark} {question} preference accuracy", selected if candidate == "selected" else stock, value)
    lines.extend(["", f"Both lift endpoints passed: {report['lift']['pass']}.", ""])
    for benchmark in ("llmbar", "rewardbench2"):
        published = report[benchmark]["published_stock"]
        lines.append(f"Published stock comparison for {benchmark}: {published['value']} ([source]({published['source_url']})).")
    lines.extend(["", "Paired accuracy intervals resample complete groups. TRACE intervals cluster both questions by conversation.",
                  "Proportion intervals use Wilson's method. Preference ties count as incorrect.", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
