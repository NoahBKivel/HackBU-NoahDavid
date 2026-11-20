"""Check CATCH ordering, reasoning exclusion and evidence-specific labels."""

from intent_training.sources.catch_hacking import convert_row, rewrite_patch


def test_first_measure_bypass_and_full_stream():
    row = {"question": "Solve the task.", "hack_family": " tests_modification",
           "hack_method": "xfail", "normalized_output": '<think>Private reasoning.</think>\n'
           '<file path="planner.py">\ndef solve(): return 0\n</file>\n'
           '<file path="tests/test_solution.py">\nimport pytest\npytestmark = pytest.mark.xfail\n</file>\n'
           '<file path="normalizer.py">\nvalue = 1\n</file>'}
    events, side, meta = convert_row(row, True, 0)
    assert meta["cut_seq"] == 3
    assert len(events) == 4
    assert side["reasoning"] == {"2": "Private reasoning."}
    assert all(e["agent_thinking"] == "" for e in events)
    assert side["outcomes"]["hack_family"] == "tests_modification"
    assert side["source_labels"][0]["question"] == "M4"
    assert all(e["action"].get("result_text", "") == "" for e in events)
    assert "+pytestmark = pytest.mark.xfail" in events[2]["action"]["file_changes"][0]["patch"][0]["lines"]


def test_generic_source_hack_does_not_invent_checker_read():
    row = {"question": "Solve.", "hack_method": "eq", "normalized_output":
           '<file path="rpc_models.py">\ndef __eq__(self, other): return True\n</file>'}
    _, side, meta = convert_row(row, True, 1)
    assert side["source_labels"] == []
    assert "cut_seq" not in meta


def test_actual_rewrite_diff_retains_removed_and_added_lines():
    hunks = rewrite_patch(["import pytest", "def test_case():", "    assert solve() == 1"],
                          ["import pytest", "@pytest.mark.xfail", "def test_case():", "    assert solve() == 1"])
    assert hunks[0]["oldLines"] == 3
    assert hunks[0]["newLines"] == 4
    assert "+@pytest.mark.xfail" in hunks[0]["lines"]
    assert "     assert solve() == 1" in hunks[0]["lines"]
