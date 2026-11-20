"""Check evidence preservation and request-label separation."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

from intent_training.sources.action_boundary import convert
from monitor_format.schema import validate_events


class ActionBoundaryTests(unittest.TestCase):
    def convert_rows(self, rows):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)
            (path / "rows.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            return list(convert(path))

    def row(self, label="ASK", **fields):
        return dict(dataset="JL-ActionBoundary-1K", id=label, family_id="family",
                    user_request="Choose the retention policy after asking me.",
                    preferred_response="How many days should records be retained?",
                    decision_label=label, human_reviewed=False, **fields)

    def test_preserves_response_and_family_without_simulated_tools(self):
        records = self.convert_rows([self.row(), self.row("INSPECT")])
        self.assertEqual(records[0][2]["pair_id"], records[1][2]["pair_id"])
        for events, side, meta in records:
            validate_events(events)
            self.assertEqual(events[0]["new_items"][0]["text"], self.row()["user_request"])
            self.assertEqual(events[-1]["agent_text"], self.row()["preferred_response"])
            self.assertEqual(events[-1]["turn"], {"reason": "answer"})
            self.assertTrue(all(not event["action"] for event in events))
            self.assertEqual(meta["cut_seq"], events[-1]["seq"])

    def test_request_class_and_hidden_answer_never_become_visible_labels(self):
        events, side, _ = self.convert_rows([
            self.row(expected_user_answer="A hidden future answer.", failure_mode="silent_assumption")
        ])[0]
        self.assertEqual(side["source_labels"], [])
        self.assertNotIn("hidden future answer", json.dumps(events))
        self.assertEqual(side["source_annotations"]["decision_label"], "ASK")

    def test_missing_response_does_not_create_agent_evidence(self):
        row = self.row()
        del row["preferred_response"]
        with self.assertRaisesRegex(ValueError, "preferred_response"):
            self.convert_rows([row])


if __name__ == "__main__":
    unittest.main()
