"""Check source materiality, pairing and absence of generated-text fabrication."""

import json
from pathlib import Path
import tempfile
import unittest

from intent_training.sources import in3
from monitor_format import validate_events


class In3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / "downloads" / "in3"
        self.raw.mkdir(parents=True)
        self.responses = self.root / "generation" / "responses"
        self.responses.mkdir(parents=True)
        self.detail = {"description": "region", "importance": "2",
                       "inquiry": "Which region?", "options": ["Northern region", "Southern region"]}
        self.row = {"task": "Plan my visit.", "vague": True,
                    "thought": "Private source reasoning.", "missing_details": [self.detail]}
        (self.raw / "train.jsonl").write_text(json.dumps(self.row) + "\n", encoding="utf-8")

    def respond(self, guess="Visit Northern region.", ask="Which region?"):
        identifier = in3.request_id(0, self.row)
        (self.responses / f"{identifier}.json").write_text(
            json.dumps({"id": identifier, "text": json.dumps({"guess": guess, "ask": ask})}),
            encoding="utf-8")

    def test_missing_response_never_creates_messages(self):
        self.assertEqual(list(in3.convert(self.raw)), [])

    def test_pair_labels_and_annotations_not_agent_reasoning(self):
        self.respond()
        pair = list(in3.convert(self.raw))
        self.assertEqual(len(pair), 2)
        self.assertEqual(pair[0][2]["pair_id"], pair[1][2]["pair_id"])
        self.assertEqual([x[1]["source_labels"][0]["value"] for x in pair], [True, False])
        for events, side, meta in pair:
            validate_events(events)
            self.assertEqual(events[-1]["turn"], {"reason": "answer"})
            self.assertEqual(events[-1]["type"], "turn_completed")
            self.assertTrue(all(not e["agent_thinking"] for e in events))
            self.assertEqual(side["reasoning"], {})
            hint = side["outcomes"]["task_annotation_hint"]
            self.assertEqual(hint["thought"], self.row["thought"])
            self.assertEqual(hint["basis"], "outcome")
            self.assertEqual(meta["cut_seq"], 2)

    def test_material_rule_requires_actual_option_and_importance(self):
        detail = dict(self.detail, selected_option="Northern region")
        self.assertTrue(in3.visible_material_guess("Visit Northern region.", detail))
        for text in ("Visit somewhere else.", "Perhaps visit Northern region.",
                     "Visit Northern region or Southern region.", "Northern region?"):
            self.assertFalse(in3.visible_material_guess(text, detail))
        self.assertFalse(in3.visible_material_guess("Visit Northern region.", dict(detail, importance="1")))

    def test_failed_material_check_is_unlabelled(self):
        self.respond(guess="Perhaps visit Northern region.")
        pair = list(in3.convert(self.raw))
        self.assertEqual(pair[0][1]["source_labels"], [])
        self.assertEqual(pair[0][2]["cut_kind"], "unspecified")

    def test_question_with_visible_guess_is_not_labelled_negative(self):
        self.respond(ask="Visit Northern region. Which region?")
        pair = list(in3.convert(self.raw))
        self.assertEqual(pair[1][1]["source_labels"], [])
        self.assertEqual(pair[1][2]["cut_kind"], "unspecified")

    def test_selection_preserves_order_and_balances(self):
        clear = dict(self.row, vague=False, missing_details=[])
        candidates = [self.row, clear] * (in3.TASKS_PER_CLASS + 1)
        (self.raw / "train.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in candidates), encoding="utf-8")
        result = list(in3.selected(self.raw))
        self.assertEqual(sum(row["vague"] for _, row, _ in result), in3.TASKS_PER_CLASS)
        self.assertEqual(sum(not row["vague"] for _, row, _ in result), in3.TASKS_PER_CLASS)
        indices = [index for index, _, _ in result]
        self.assertEqual(indices, sorted(indices))


if __name__ == "__main__":
    unittest.main()
