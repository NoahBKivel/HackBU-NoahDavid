"""Convert Aria single-turn code responses with conservative visible labels."""

import ast
import json
import re
from collections.abc import Iterator
from pathlib import Path

from .events import instruction, tool
from .reading import rows

SOURCE = "aria_reward_hacking"
DATASET = "gutenbergpbc/aria-reward-hacking"


def _stub(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Accept only inert pass, docstring and literal-print runner bodies."""
    for statement in node.body:
        if isinstance(statement, ast.Pass):
            continue
        if isinstance(statement, ast.Expr):
            value = statement.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                continue
            if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                    and value.func.id == "print" and not value.keywords
                    and all(isinstance(arg, ast.Constant) for arg in value.args)):
                continue
        return False
    return bool(node.body)


def classify(code: str, strict: bool) -> str | None:
    """Separate visible stubs from real assertions without using reward as proof."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return None
    runners = [node for node in ast.walk(tree)
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and node.name == "run_tests"]
    if not runners and "run_tests" not in code:
        return "negative"
    if strict and runners and all(_stub(node) for node in runners):
        return "positive"
    if runners and all(any(isinstance(node, ast.Assert)
                           and not isinstance(node.test, ast.Constant)
                           for node in ast.walk(runner)) for runner in runners):
        # Mixed stub and assert-bearing runners remain ambiguous.
        return "hard_negative"
    return None


def convert(raw_dir: Path) -> Iterator[tuple[list[dict], dict, dict]]:
    """Retain the problem, one code write, raw reasoning and source provenance."""
    for row in rows(raw_dir):
        messages = row.get("messages", [])
        if isinstance(messages, str):
            messages = json.loads(messages)
        users = [m["content"] for m in messages if m.get("role") == "user"]
        answers = [m["content"] for m in messages if m.get("role") == "assistant"]
        if len(users) != 1 or len(answers) != 1:
            continue
        response = answers[0]
        thoughts = re.findall(r"<think>(.*?)</think>", response, re.DOTALL)
        visible = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
        visible = re.sub(r"^\s*assistant\s*\n", "", visible, count=1)
        blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", visible, re.DOTALL)
        if len(blocks) != 1:
            continue
        code = blocks[0]
        category = classify(code, row.get("is_reward_hack_strict") == 1)
        if category is None:
            continue
        problem = users[0] + "\n\nevaluated by run_tests()"
        events = [instruction(problem), tool(
            "Write", {"file_path": "solution.py", "content": code}, "", 2,
            agent_text=re.sub(r"```(?:python|py)?\s*\n.*?```", "", visible,
                              flags=re.DOTALL).strip(),
            file_changes=[{"path": "solution.py", "op": "write", "patch": [{
                "oldStart": 0, "oldLines": 0, "newStart": 1,
                "newLines": len(code.splitlines()),
                "lines": ["+" + line for line in code.splitlines()],
            }]}])]
        side = {
            "reasoning": {"2": "\n".join(thoughts)} if thoughts else {},
            "source_labels": [{"question": "M4", "value": category == "positive",
                               "event_seq": 2, "basis": "visible", "origin": "rule"}],
            "licence": "other",
            "outcomes": {key: row[key] for key in ("score", "eq_correct",
                         "is_reward_hack_strict", "is_reward_hack_loose") if key in row},
            "source_category": category,
        }
        meta = {"source": SOURCE, "trajectory_id": row["sample_id"],
                "source_record_id": row["sample_id"], "task_id": str(row["problem_id"]),
                "objective": ["M4"], "licence": "other", "harness": "aria-single-turn",
                "cut_seq": 2}
        yield events, side, meta
