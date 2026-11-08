"""Prove source precedence and immutable linked-unit sampling."""

import random
import json
from pathlib import Path
import tempfile
import unittest

from intent_training.kevpatch.mixture import load_prepared, sample_units, source_candidates


class BenchmarkMixtureTests(unittest.TestCase):
    def test_declared_eligibility_precedes_general_objective(self):
        plan = [{"id": "science:claim", "source": "science", "slice": "claim", "objective": ["M5", "G5"]},
                {"id": "science:benign", "source": "science", "slice": "benign", "objective": []}]
        record = {"_meta": {"source": "science", "objective": ["M5", "G5"], "eligible_slices": ["benign"]}}
        self.assertEqual(source_candidates(record, None, plan), ["science:benign"])

    def test_immediate_atomic_context_does_not_wait_for_aggregate_finalization(self):
        directory = Path(__file__).resolve().parents[1] / "results/test-temp"
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = Path(temporary)
            record = {"record_id": "ready", "state": "a", "questions": {},
                      "_meta": {"construction": "goal_flip"}}
            (root / "main.jsonl").write_text(json.dumps(record) + "\n")
            (root / "contexts").mkdir()
            context = root / "contexts/ready.json"
            context.write_text(json.dumps({"record_id": "ready", "side": {"construction": {"type": "goal_flip"}}}))
            paths = {}
            selected, _, _ = load_prepared([str(root)], paths)
            self.assertEqual([record["record_id"] for record in selected], ["ready"])
            self.assertEqual(paths, {"ready": str(context)})

    def test_completed_context_required_before_main_admission(self):
        directory = Path(__file__).resolve().parents[1] / "results/test-temp"
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = Path(temporary)
            records = [{"record_id": "ordinary", "state": "a", "questions": {}, "_meta": {}},
                       {"record_id": "native", "state": "b", "questions": {}, "_meta": {"native_record": True}}]
            (root / "main.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records))
            (root / "context.jsonl").write_text("")
            selected, _, _ = load_prepared([str(root)])
            self.assertEqual([record["record_id"] for record in selected], ["native"])
            (root / "context.jsonl").write_text(json.dumps({"record_id": "ordinary"}) + "\n")
            selected, _, _ = load_prepared([str(root)])
            self.assertEqual([record["record_id"] for record in selected], ["ordinary", "native"])

    def test_construction_overrides_underlying_source(self):
        plan = [{"id": "goal_flip", "source": "goal_flip", "slice": None},
                {"id": "swe_chat:claim", "source": "swe_chat", "slice": "claim"}]
        record = {"_meta": {"source": "swe_chat", "slice": "claim"}}
        self.assertEqual(source_candidates(record, "goal_flip", plan), ["goal_flip"])

    def test_objective_resolves_unspecified_registry_slice(self):
        plan = [{"id": "if_multi:0", "source": "if_multi", "slice": "0", "objective": ["RF"]},
                {"id": "if_multi:1", "source": "if_multi", "slice": "1", "objective": ["M2"]}]
        record = {"_meta": {"source": "if_multi", "objective": ["RF"]}}
        self.assertEqual(source_candidates(record, None, plan), ["if_multi:0"])

    def test_linked_units_are_kept_complete_without_duplicate_records(self):
        records = [{"_meta": {"id": str(index), "pair_id": str(index // 2)}} for index in range(20)]
        candidates = {id(record): ["a"] for record in records}
        selected, assignments = sample_units(records, candidates, {"a": 1}, 10, random.Random(4))
        self.assertEqual(len({record["_meta"]["id"] for record in selected}), 10)
        self.assertEqual(assignments, {"a": 10})
        for record in selected:
            self.assertEqual(sum(other["_meta"]["pair_id"] == record["_meta"]["pair_id"]
                                 for other in selected), 2)

    def test_missing_weighted_source_does_not_silently_renormalize(self):
        records = [{"_meta": {"id": "a"}}]
        with self.assertRaisesRegex(ValueError, "missing: b"):
            sample_units(records, {id(records[0]): ["a"]}, {"a": 1, "b": 1}, 1, random.Random(1))


if __name__ == "__main__":
    unittest.main()
