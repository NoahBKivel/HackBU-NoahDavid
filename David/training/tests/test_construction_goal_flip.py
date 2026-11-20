"""Check goal contrasts without changing observed agent evidence."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.constructions.goal_flip import build, generation_requests
from intent_training.sources.events import instruction, message, tool


class GoalFlipTests(unittest.TestCase):
    def setUp(self):
        self.events = [instruction("Improve response time."),
                       tool("Edit", {"file_path": "cache.py"}, "Updated.", 2,
                            agent_text="I changed the cache.",
                            file_changes=[{"path": "cache.py", "op": "edit", "patch": None}]),
                       message("Finished.", 3)]
        self.side = {"reasoning": {"2": "The cache is slow."},
                     "source_labels": [{"question": "M1", "value": False,
                                        "event_seq": 2, "basis": "visible", "origin": "rule"}]}
        self.meta = {"source": "fixture", "trajectory_id": "run", "cut_seq": 2,
                     "group_id": "shared-task", "pair_id": "original-pair"}
        self.goals = {"serves": "Improve cache response time.",
                      "defeats": "Preserve the cache implementation for comparison."}

    def test_only_selected_user_text_changes(self):
        original = deepcopy((self.events, self.side, self.meta))
        rows = list(build(self.events, self.side, self.meta, goals=self.goals))
        self.assertEqual(len(rows), 2)
        for events, side, meta in rows:
            self.assertEqual(events[1], self.events[1])
            restored = deepcopy(events)
            restored[0]["new_items"][0]["text"] = self.events[0]["new_items"][0]["text"]
            self.assertEqual(restored, self.events[:2])
            self.assertEqual(meta["group_id"], "shared-task")
            self.assertEqual(meta["base_pair_id"], "original-pair")
            self.assertEqual(side["source_labels"], [])
            self.assertEqual(side["reasoning"], {})
            self.assertEqual(side["construction"]["base_reasoning"], self.side["reasoning"])
            self.assertEqual(side["construction"]["base_source_labels"], self.side["source_labels"])
        self.assertEqual(rows[0][2]["pair_id"], rows[1][2]["pair_id"])
        self.assertEqual([row[1]["construction"]["intended"] for row in rows],
                         [{"M1": False}, {"M1": True}])
        self.assertEqual((self.events, self.side, self.meta), original)

    def test_request_and_generated_response_have_no_future_evidence(self):
        request, = generation_requests(self.events, self.side, self.meta)
        self.assertNotIn("Finished.", request["prompt"])
        self.assertEqual(request["references"]["events"], self.events[:2])
        rows = list(build(self.events, self.side, self.meta,
                          generated_texts={request["id"]: json.dumps(self.goals)}))
        self.assertEqual(len(rows), 2)
        self.assertEqual(list(build(self.events, self.side, self.meta)), [])

    def test_retries_are_bounded_and_have_distinct_requests(self):
        ids = []
        for attempt in range(1, 4):
            request, = generation_requests(self.events, self.side, self.meta, attempt=attempt)
            ids.append(request["id"])
        self.assertEqual(len(set(ids)), 3)
        for attempt in (0, 4, True):
            with self.assertRaises(ValueError):
                list(build(self.events, self.side, self.meta, goals=self.goals, attempt=attempt))

    def test_explicit_json_extraction_preserves_generated_goal_strings(self):
        for text in ("```json\n" + json.dumps(self.goals) + "\n```",
                     "Here are the requests:\n" + json.dumps(self.goals)):
            rows = list(build(self.events, self.side, self.meta, goals=text))
            self.assertEqual([row[0][0]["new_items"][0]["text"] for row in rows],
                             [self.goals["serves"], self.goals["defeats"]])

    def test_invalid_cut_and_goals_are_rejected(self):
        for goals in ({"serves": "a"}, {"serves": "a", "defeats": "a"},
                      {"serves": "", "defeats": "b"}):
            with self.assertRaises(ValueError):
                list(build(self.events, self.side, self.meta, goals=goals))
        self.events[1]["action"]["tool"] = "Read"
        self.events[1]["action"].pop("file_changes")
        with self.assertRaises(ValueError):
            list(build(self.events, self.side, self.meta, goals=self.goals))


if __name__ == "__main__":
    unittest.main()
