"""Cut selection must use visible declarations and classified events."""

from intent_training.prepare.cuts import plan_cuts, positive_offense
from intent_training.sources.events import instruction, message, tool


def row(events, labels=(), **meta):
    return {"events": events, "side": {"source_labels": list(labels)},
            "meta": {"harness": "test", **meta}}


def label(seq, value=True, basis="visible", question="M4"):
    return {"event_seq": seq, "value": value, "basis": basis, "question": question}


def test_read_offense_advances_and_uses_seq_not_position():
    item = row([instruction("Task", 10), tool("Read", {"file_path": "test.py"}, "", 30),
                tool("Bash", {"command": "true"}, "", 50)], [label(30)], cut_seq=50)
    assert positive_offense(item) == 30
    assert plan_cuts([item])[0][0]["cut_seq"] == 50


def test_outcome_does_not_declare_positive():
    item = row([instruction("Task"), message("Done", 2)], [label(2, basis="outcome")], cut_seq=2)
    assert positive_offense(item) is None
    assert plan_cuts([item])[0][0]["cut_kind"] == "candidate"


def test_negative_matching_uses_type_and_absolute_position():
    positive = row([instruction("Task"), message("Bad", 2)], [label(2)])
    negative = row([instruction("Task"), tool("Bash", {"command": "true"}, "", 2),
                    message("Good", 3)], [label(3, False)])
    cuts = plan_cuts([positive, negative])
    assert cuts[1] == [{"cut_seq": 3, "cut_kind": "negative", "match_harness": "test",
                        "event_type": "message", "index_bin": 0}]


def test_prefix_is_strictly_before_offense():
    item = row([instruction("Task"), message("Good", 2), message("Bad", 3)], [label(3)])
    assert [cut["cut_seq"] for cut in plan_cuts([item])[0]] == [3, 2]


def test_invalid_read_cut_is_not_admitted():
    item = row([instruction("Task"), tool("Read", {"file_path": "x"}, "", 2),
                message("Answer", 3)], cut_seq=2)
    assert plan_cuts([item]) == [[]]


def test_whole_run_positive_polarity():
    item = row([instruction("Task"), message("Different", 2)], [label(2, False, question="G1")])
    assert positive_offense(item) == 2


def test_small_harnesses_share_joint_distribution():
    positive_a = row([instruction("Task"), message("Bad", 2)], [label(2)], harness="a")
    positive_b = row([instruction("Task"), tool("Bash", {"command": "bad"}, "", 2)],
                     [label(2)], harness="b")
    negative_a = row([instruction("Task"), tool("Bash", {"command": "good"}, "", 2)],
                     [label(2, False)], harness="a")
    negative_b = row([instruction("Task"), message("Good", 2)], [label(2, False)], harness="b")
    cuts = plan_cuts([positive_a, positive_b, negative_a, negative_b])
    assert cuts[2][0]["cut_kind"] == "negative"
    assert cuts[3][0]["cut_kind"] == "negative"
    assert cuts[2][0]["match_harness"] == cuts[3][0]["match_harness"] == "a"


def test_negative_quota_scales_to_all_eligible_source_parents():
    def write_row(source, positive):
        return row([instruction("Task"), tool("Write", {"file_path": "solution.py"}, "", 2),
                    tool("Write", {"file_path": "solution.py"}, "", 3)],
                   [label(2, positive)], harness=source)
    anchor = write_row("anchor", True)
    earlier = [write_row("catch", False) for _ in range(3)]
    later = [write_row("aria", False) for _ in range(4)]
    cuts = plan_cuts([anchor, *earlier, *later])
    assert all(len(parent_cuts) == 1 for parent_cuts in cuts[1:])
    assert all(parent_cuts[0]["event_type"] == "edit_write" for parent_cuts in cuts[1:])
    assert all(parent_cuts[0]["index_bin"] == 0 for parent_cuts in cuts[1:])
