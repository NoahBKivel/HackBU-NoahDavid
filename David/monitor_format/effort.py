"""Count work by the first repository directory across the whole run."""

from collections import Counter
from pathlib import PurePosixPath
import re
from typing import Any

from .render_event import key_argument, tool_name
from .schema import READ_ONLY_TOOLS


def _area(path: str, root: str) -> str:
    normalized = path.replace("\\", "/").strip("'\"")
    base = root.replace("\\", "/").rstrip("/")
    if base and normalized.lower().startswith(base.lower() + "/"):
        normalized = normalized[len(base) + 1:]
    normalized = normalized.removeprefix("./")
    parts = PurePosixPath(normalized).parts
    if len(parts) > 1 and parts[0] not in {"/", ".."}:
        return parts[0].rstrip("/") + "/"
    return "(root)"


def render_effort(events: list[dict[str, Any]]) -> str:
    """Render edit, write, shell and read counts without discarding older events."""
    counts: dict[str, Counter] = {}
    root = ""
    for event in events:
        session = event.get("session") or {}
        root = (session.get("repo") or {}).get("root", session.get("cwd", root)) or root
        name = tool_name(event)
        kind = ("edits" if name == "Edit" else "writes" if name == "Write" else
                "shell" if name == "Bash" else "reads" if name in READ_ONLY_TOOLS else None)
        if kind is None:
            continue
        action = event.get("action") or {}
        paths = [change["path"] for change in action.get("file_changes", [])]
        if not paths:
            argument = key_argument(event)
            if name == "Bash":
                cwd = action.get("args", {}).get("cwd", "")
                match = re.search(r"(?:^|\s)(?:cd\s+)?([\w./\\-]+[/\\][\w./\\-]*)", argument)
                paths = [cwd or (match.group(1) if match else "")]
            else:
                paths = [argument]
        for area in dict.fromkeys(_area(path, root) for path in paths):
            counts.setdefault(area, Counter())[kind] += 1
    lines = []
    for area in sorted(counts):
        counter = counts[area]
        actions = [f"{counter[name]} {name[:-1] if counter[name] == 1 and name in {'edits', 'writes'} else name}"
                   for name in ("edits", "writes", "shell") if counter[name]]
        body = ", ".join(actions)
        if counter["reads"]:
            body += ("; " if body else "") + f"reads {counter['reads']}"
        lines.append(f"{area}: {body}")
    return "\n".join(lines) or "(none)"
