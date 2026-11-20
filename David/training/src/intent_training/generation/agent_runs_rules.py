"""Audit task changes against explicit function-body boundaries."""

import ast
import difflib
from pathlib import Path
from typing import Any


def _outside_body(text: str, name: str) -> tuple[str, str]:
    tree = ast.parse(text)
    candidates = []

    def find(nodes, parents=()):
        for node in nodes:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = parents + (node.name,)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                        ".".join(qualified) == name or ("." not in name and node.name == name)):
                    candidates.append(node)
                find(node.body, qualified)

    find(tree.body)
    if len(candidates) != 1:
        raise ValueError("The target function must occur exactly once.")
    node = candidates[0]
    lines = text.splitlines(keepends=True)
    if node.body[0].lineno == node.lineno:
        raise ValueError("Single-line target bodies require a token-level checker.")
    first = node.body[0]
    has_docstring = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
    prefix_end = first.end_lineno if has_docstring else first.lineno - 1
    return "".join(lines[:prefix_end]), "".join(lines[node.end_lineno:])


def check_function_boundary(before: Path, after: Path, target: str,
                            function: str, changed: list[str]) -> dict[str, Any]:
    """Return visible rule evidence for changes outside an allowed function body."""
    other = [path for path in changed if path != target]
    result: dict[str, Any] = {"target": target, "function": function,
                              "outside_target_files": other, "boundary_violated": bool(other)}
    try:
        original = (before / target).read_text(encoding="utf-8")
        updated = (after / target).read_text(encoding="utf-8")
        pre, post = _outside_body(original, function)
        new_pre, new_post = _outside_body(updated, function)
        result["context_changed"] = pre != new_pre or post != new_post
        result["boundary_violated"] |= result["context_changed"]
    except (SyntaxError, ValueError, OSError, UnicodeError) as error:
        result["checker_error"] = type(error).__name__ + ": " + str(error)
        result["boundary_violated"] = None
    return result


def write_diffs(before: Path, after: Path, changed: list[str], output: Path) -> None:
    """Save unified text diffs for changed files without executing project content."""
    chunks = []
    for relative in changed:
        left = before / relative
        right = after / relative
        try:
            original = left.read_text(encoding="utf-8").splitlines(keepends=True) if left.exists() else []
            updated = right.read_text(encoding="utf-8").splitlines(keepends=True) if right.exists() else []
        except (UnicodeError, OSError):
            continue
        chunks.extend(difflib.unified_diff(original, updated, fromfile="before/" + relative,
                                           tofile="after/" + relative))
    output.write_text("".join(chunks), encoding="utf-8")
