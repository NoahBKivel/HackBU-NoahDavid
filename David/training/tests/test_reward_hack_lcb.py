"""Check shell result attribution and separation of reasoning from evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from intent_training.sources.reward_hack_lcb import convert
from monitor_format import validate_events


class ConverterTests(unittest.TestCase):
    def test_results_reasoning_and_untrusted_test_access(self):
        for changed_path, hinted in (("solution.py", True), ("test.py", False)):
            with self.subTest(changed_path=changed_path), tempfile.TemporaryDirectory() as folder:
                row = {"instance_id": "task", "info": {"submission": f"diff --git a/{changed_path} b/{changed_path}\n"},
                       "messages": [{"role": "user", "content": "Solve the task using test.py."},
                                    {"role": "assistant", "content": "Check.\n```bash\ncat test.py && python test.py\n```",
                                     "reasoning_content": "private deliberation"},
                                    {"role": "user", "content": "<returncode>1</returncode>\n<output>failed</output>"},
                                    {"role": "assistant", "content": "The test failed."}]}
                Path(folder, "sample.traj.json").write_text(json.dumps(row))
                events, side, meta = next(convert(Path(folder)))
                validate_events(events)
                self.assertEqual(len(events), 3)
                self.assertEqual(events[1]["action"]["tool"], "Bash")
                self.assertTrue(events[1]["action"]["is_error"])
                self.assertIn("failed", events[1]["action"]["result_text"])
                self.assertEqual(side["reasoning"], {"2": "private deliberation"})
                self.assertTrue(all(event["agent_thinking"] == "" for event in events))
                self.assertEqual(bool(side["source_labels"]), hinted)
                self.assertTrue(all(label["basis"] == "outcome" for label in side["source_labels"]))
                self.assertNotIn("cut_seq", meta)

    def test_exit_submission_is_result_and_unexecuted_fence_is_not_action(self):
        from intent_training.sources.reward_hack_lcb import _stream
        events, _ = _stream([
            {"role": "assistant", "content": "```bash\necho submit\n```", "extra": {"actions": [{"command": "echo submit"}]}},
            {"role": "exit", "content": "actual patch"},
            {"role": "assistant", "content": "Example: ```bash\ncat secret\n```", "extra": {"actions": []}},
        ])
        self.assertEqual(events[0]["action"]["result_text"], "actual patch")
        self.assertEqual(events[1]["type"], "turn_completed")

    def test_format_failure_never_fabricates_an_agent_answer(self):
        from intent_training.sources.reward_hack_lcb import _stream
        events, _ = _stream([
            {"role": "user", "content": "Solve."},
            {"role": "user", "content": "Exactly one action was required."},
            {"role": "exit", "content": "RepeatedFormatError"},
        ])
        self.assertTrue(all(event["type"] == "session_started" for event in events))


if __name__ == "__main__":
    unittest.main()
