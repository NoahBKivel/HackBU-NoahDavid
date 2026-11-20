"""Typed-decision adaptation preserves evidence and rejects unsafe inputs."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from intent_training.sources.tasksource import convert, exclusion, native


def row(**changes):
    value = dict(state="An original passage.", question="Which label fits?", source="public-nli",
                 id="public-nli:train:example", group_id="public-nli:train:example",
                 question_id="decision", split="train", kind="choice", options=["yes", "no"],
                 target=[0.75, 0.25], license="cc-by-4.0", license_use="commercial")
    return dict(value, **changes)


class TasksourceTests(unittest.TestCase):
    def test_original_payload_and_soft_labels_survive(self):
        original = row()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "rows-00000000.jsonl").write_text(json.dumps(original), encoding="utf-8")
            events, side, meta = next(convert(path))
        record = side["native_record"]
        self.assertEqual(events, [])
        self.assertTrue(meta["native"])
        self.assertEqual(record["state"], original["state"])
        self.assertEqual(record["_meta"]["source"], original["source"])
        self.assertEqual(record["_meta"]["original_row"], original)
        self.assertEqual(record["questions"]["decision"]["target"], {"yes": .75, "no": .25})
        self.assertEqual(record["questions"]["decision"]["label"], "yes")

    def test_boolean_probability_and_score_order(self):
        boolean = native(row(kind="noul", options=[], target=[.2]))["questions"]["decision"]
        self.assertIs(boolean["label"], False)
        self.assertEqual(boolean["target"], {"false": .8, "true": .2})
        score = native(row(kind="score", options=["low", "high"], target=[.1, .9]))["questions"]["decision"]
        self.assertEqual(score["criteria"], ["low", "high"])
        self.assertEqual(score["label"], 1)
        self.assertEqual(score["target"], {"0": .1, "1": .9})

    def test_exclusions_and_explicit_permission(self):
        for source in ("CLINC150", "Schema-Guided-Dialogue", "When2Call", "LLMBar",
                       "RewardBench-2", "PatronusAI/TRACE", "UserIntentBench", "CUAD", "qnli",
                       "HelpSteer2/coherence", "UltraFeedback-paired", "maud/antitrust"):
            with self.subTest(source=source):
                self.assertEqual(exclusion(row(source=source)), "excluded_source")
        for use in ("non-commercial", "unspecified", "", None):
            self.assertEqual(exclusion(row(license_use=use)), "licence_use_policy")
        self.assertEqual(exclusion(row(license="unspecified")), "missing_explicit_licence")
        self.assertEqual(exclusion(row(split="test")), "non_training_split")

    def test_invalid_schema_is_never_mapped(self):
        for changes in (dict(target=[float("nan"), 0]), dict(target=[1]),
                        dict(target=[.2, .2]), dict(options=["same", "same"]),
                        dict(kind="freeform"), dict(state=""),
                        dict(kind="noul", options=[], target=[1, 0])):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                native(row(**changes))


if __name__ == "__main__":
    unittest.main()
