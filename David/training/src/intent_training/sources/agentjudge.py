"""Preserve AgentJudgeBench generated tool calls and outcome-only scores."""

import json
from collections.abc import Iterator
from pathlib import Path

from .events import instruction, tool
from .reading import rows


def convert(raw_dir: Path) -> Iterator[tuple[list[dict], dict, dict]]:
    """Convert generated calls without inventing execution results or verdicts.

    Coverage scores are outcome hints for M1 and G1, never visible labels.
    A flawed or slow run alone does not establish that it is off track.
    Task-only rows containing expected calls are excluded from agent evidence.
    """
    raw_dir = Path(raw_dir)
    if not raw_dir.is_dir():
        raise FileNotFoundError("The raw AgentJudgeBench directory does not exist.")
    for path in sorted(raw_dir.glob("*.jsonl")):
        for row in rows(path):
            if "generated_tool_calls" not in row:
                continue
            query, calls = row.get("user_query"), row["generated_tool_calls"]
            if not isinstance(query, str) or not isinstance(calls, list):
                raise ValueError("AgentJudgeBench query and generated calls have invalid types.")
            documents = {"available_tools.json": json.dumps(row.get("available_tools", []), ensure_ascii=False)}
            events = [instruction(query, documents=documents)]
            for call in calls:
                function = call.get("function", call)
                name, arguments = function.get("name"), function.get("arguments")
                if not isinstance(name, str) or not isinstance(arguments, dict):
                    raise ValueError("AgentJudgeBench generated call has invalid name or arguments.")
                events.append(tool(name, arguments, "", len(events) + 1))
            if len(events) == 1:
                continue
            task_id = str(row["id"])
            difficulty = row.get("difficulty", "")
            trajectory_id = f"{path.stem}:{task_id}:{difficulty}"
            side = {"reasoning": {}, "source_labels": [], "licence": "Apache-2.0",
                    "outcomes": {key: value for key, value in row.items()
                                 if key.startswith("score_") or key == "overall_programmatic_score"}}
            meta = {"source": "agentjudge", "trajectory_id": trajectory_id,
                    "task_id": task_id, "source_record_id": trajectory_id,
                    "objective": ["M1", "G1"], "licence": "Apache-2.0",
                    "harness": f"agentjudgebench:{path.stem}", "cut_kind": "unspecified",
                    "difficulty": difficulty, "execution_results_supplied": False}
            yield events, side, meta
