"""Keep benchmark allocation checks tied to the supplied composition."""

import pytest
from intent_training.kevpatch.mixture import declared_task_plan


def test_nonlegacy_task_count_uses_declared_composition():
    sources = [{"part": "task", "planned_quota": 11}, {"part": "task", "planned_quota": 6},
               {"part": "replay", "planned_quota": 4}]
    result = declared_task_plan({"parts": {"task": 17}, "sources": sources})
    assert result == sources[:2]


def test_corrupt_allocation_cannot_pass_with_another_declared_total():
    with pytest.raises(ValueError, match="do not match"):
        declared_task_plan({"parts": {"task": 18}, "sources": [{"part": "task", "planned_quota": 17}]})