"""Verify priority thresholds and instruction-only edits on tiny fixtures."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))
from intent_training.constructions.priority import area_actions, build
from monitor_format import validate_events


def event(seq, tool=None, path=None):
    return {"seq": seq, "type": "tool_completed" if tool else "session_started",
            "ts": "", "new_items": [] if tool else [{"kind": "user_instruction", "id": "I9", "text": "Fix the application."}],
            "action": {"tool": tool, "args": {"file_path": path}, "result_text": "", "is_error": False} if tool else {},
            "agent_text": "", "agent_thinking": "", "todos": [], "turn": {}}


class PriorityTests(unittest.TestCase):
    def test_five_actions_and_first_work_form_instruction_contrasts(self):
        events = [event(1)] + [event(i, "Edit", "ui/view.py") for i in range(2, 7)] + [event(7, "Edit", "api/main.py")]
        original = deepcopy(events)
        side, meta = {"reasoning": {"2": "Original thought."}, "source_labels": [{"question": "G4", "value": False}]}, {"group_id": "fixture", "source": "fixture"}
        outputs = list(build(events, side, meta))
        self.assertEqual({out[1]["construction"]["intended"]["G4"] for out in outputs}, {True, False})
        for result, output_side, output_meta in outputs:
            validate_events(result)
            self.assertEqual(result[1:], original[1:])
            self.assertEqual(output_meta["group_id"], meta["group_id"])
            self.assertEqual(output_side["reasoning"], side["reasoning"])
            self.assertNotIn("source_labels", output_side)
            self.assertEqual(output_side["construction"]["base_source_labels"], side["source_labels"])
        positive = next(out for out in outputs if out[1]["construction"]["intended"]["G4"])
        self.assertEqual(positive[2]["cut_seq"], 6)
        self.assertEqual(events, original)
        self.assertNotIn("construction", side)

    def test_reads_do_not_count_and_intermediate_is_unused(self):
        events = [event(1), event(2, "Read", "api/main.py")] + [event(i, "Edit", "ui/view.py") for i in range(3, 7)]
        self.assertEqual(list(build(events, {}, {}, higher_area="api/", lower_area="ui/")), [])
        self.assertNotIn("api/", area_actions(events)[0])
        events.append(event(7, "Write", "ui/view.py"))
        self.assertTrue(list(build(events, {}, {}, higher_area="api/", lower_area="ui/"))[0][1]["construction"]["intended"]["G4"])

    def test_higher_work_prevents_positive_and_interleaving_prevents_negative(self):
        events = [event(1), event(2, "Edit", "ui/a"), event(3, "Edit", "api/a")] + [event(i, "Edit", "ui/a") for i in range(4, 9)]
        self.assertEqual(list(build(events, {}, {}, higher_area="api/", lower_area="ui/")), [])

    def test_action_is_counted_once_per_area_and_shell_reads_stay_distinct(self):
        item = event(2, "Edit", "ui/a")
        item["action"]["file_changes"] = [{"path": path, "op": "edit", "patch": None} for path in ("ui/a", "ui/b")]
        shell = event(3, "Bash", None)
        shell["action"]["args"] = {"cwd": "api/tests", "command": "pytest"}
        self.assertEqual(area_actions([event(1), item, shell])[0], {"ui/": [2], "api/": [3]})

    def test_attempt_limit_and_missing_instruction(self):
        for attempt in (0, 4, True):
            with self.assertRaises(ValueError):
                list(build([event(1)], {}, {}, attempt=attempt))
        self.assertEqual(list(build([event(1, "Edit", "api/a")], {}, {})), [])

    def test_absolute_paths_infer_repository_and_shell_source_is_not_a_path(self):
        shell = event(4, "Bash", None)
        shell["action"]["args"] = {"command": 'python -c "print(\'write/output.py\')"'}
        events = [event(1), event(2, "Read", "/checkout/tests/check.py"),
                  event(3, "Edit", "/checkout/src/main.py"), shell]
        actions, observed = area_actions(events)
        self.assertEqual(actions, {"src/": [3], "(root)": [4]})
        self.assertEqual(observed, {"src/", "tests/", "(root)"})


if __name__ == "__main__":
    unittest.main()
