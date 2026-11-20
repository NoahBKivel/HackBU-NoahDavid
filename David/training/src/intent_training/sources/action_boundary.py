"""Preserve published ActionBoundary responses without simulating execution."""

from pathlib import Path
from collections.abc import Iterator

from .events import instruction, message
from .reading import rows


def convert(raw_dir: Path) -> Iterator[tuple[list[dict], dict, dict]]:
    """Yield the preferred source response with its original family grouping.

    Decision classes describe which action a request warrants. They do not
    establish whether the visible response made a material silent assumption.
    The teacher must judge M7 from the preserved response itself.
    """
    for row in rows(raw_dir):
        for field in ("id", "family_id", "user_request", "preferred_response"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"ActionBoundary requires nonempty {field} text.")
        if row.get("decision_label") not in {"ACT", "INSPECT", "ASK", "DEFER"}:
            raise ValueError("ActionBoundary requires a recognized decision class.")
        if row.get("dataset") != "JL-ActionBoundary-1K":
            raise ValueError("The row does not identify the ActionBoundary dataset.")
        events = [instruction(row["user_request"]), message(row["preferred_response"], 2)]
        annotations = {key: value for key, value in row.items()
                       if key not in {"user_request", "preferred_response"}}
        side = {
            "reasoning": {}, "source_labels": [], "licence": "CC-BY-4.0",
            "source_annotations": annotations,
            "source_annotation_basis": "outcome",
            "response_provenance": {
                "field": "preferred_response", "origin": "published synthetic source response",
                "human_reviewed": row.get("human_reviewed"),
            },
        }
        meta = {
            "source": "action_boundary", "trajectory_id": row["id"],
            "task_id": row["family_id"], "pair_id": row["family_id"],
            "objective": ["M7"], "licence": "CC-BY-4.0",
            "harness": "action_boundary_response", "cut_seq": 2, "cut_kind": "unspecified",
            "source_record_id": row["id"], "response_field": "preferred_response",
            "source_split": row.get("split"),
        }
        yield events, side, meta
