"""Check distributed record ownership and the fixed-work parity decision."""

from copy import deepcopy
from types import SimpleNamespace
import unittest
import hashlib
from pathlib import Path
import tempfile

from intent_training.kevpatch.distributed_accelerate import compare_losses, local_passes, rank_records, verify_frozen_input


class AcceleratePlanningTests(unittest.TestCase):
    def test_frozen_input_rejects_changed_bytes_and_count(self):
        directory = Path(__file__).resolve().parents[1] / "results/test-temp"
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            path = Path(temporary) / "frozen.jsonl"
            raw = b'{"a":1}\n{"a":2}\n'
            path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            self.assertEqual(verify_frozen_input(path, digest, 2)["records"], 2)
            for sha, count in ((digest, 3), ("0" * 64, 2), ("", 2)):
                with self.assertRaises(ValueError):
                    verify_frozen_input(path, sha, count)
            path.write_bytes(raw + b'{}\n')
            with self.assertRaises(ValueError):
                verify_frozen_input(path, digest, 2)

    def test_linked_units_are_owned_once(self):
        records = [{"_meta": {"id": str(index), "pair_id": str(index // 2)}} for index in range(16)]
        owners = [rank_records(records, 4, rank) for rank in range(4)]
        self.assertEqual(sorted(record["_meta"]["id"] for rows in owners for record in rows),
                         sorted(record["_meta"]["id"] for record in records))
        for rows in owners:
            for record in rows:
                self.assertEqual(sum(other["_meta"]["pair_id"] == record["_meta"]["pair_id"] for other in rows), 2)

    def test_empty_rank_still_has_one_collective_pass(self):
        self.assertEqual(local_passes(None, [], {}, 10, True), [[]])

    def test_physical_cap_does_not_drop_records(self):
        records = [{"_meta": {"id": str(index)}} for index in range(4)]
        shapes = {id(record): [3] for record in records}
        native = SimpleNamespace(pass_tokens=lambda values, shared: sum(values),
            balanced_runs=lambda items, count, cost: [items[index::count] for index in range(count)])
        runs = local_passes(native, records, shapes, 6, True)
        self.assertEqual([len(run) for run in runs], [2, 2])
        self.assertEqual(sum(map(len, runs)), len(records))
        with self.assertRaises(ValueError):
            local_passes(native, records, shapes, 2, True)

    def test_parity_rejects_wrong_normalization_and_different_work(self):
        reference = {"records_sha256": "fixture", "fixed_records": 16,
            "max_state": 8192, "pass_tokens_max": 100, "global_batch": 16,
            "steps": [{"loss": .4}, {"loss": .3}, {"loss": .2}]}
        repeat = deepcopy(reference)
        repeat["steps"][0]["loss"] += .0001
        self.assertEqual(compare_losses(reference, repeat, deepcopy(reference))["status"], "PASS")
        wrong = deepcopy(reference)
        wrong["steps"][1]["loss"] *= 4
        self.assertEqual(compare_losses(reference, repeat, wrong)["status"], "FAIL")
        wrong = deepcopy(reference)
        wrong["records_sha256"] = "different"
        with self.assertRaises(ValueError):
            compare_losses(reference, repeat, wrong)


if __name__ == "__main__":
    unittest.main()
