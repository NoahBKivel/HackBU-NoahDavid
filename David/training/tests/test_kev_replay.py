"""Exercise native replay fidelity and exclusion boundaries."""

from copy import deepcopy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from intent_training.sources.kev_replay import _balanced_groups, convert, validate_native


def native(label=True):
    return {'state': 'A neutral fixture.', 'questions': {
        'answer': {'type': 'noul', 'instructions': 'Is this neutral?', 'label': label}},
        '_meta': {'source': 'boolq', 'split': 'train', 'id': str(label),
                  'group_id': 'pair'}}


class ReplayTests(unittest.TestCase):
    def test_balances_opposite_groups_and_drops_unmatched(self):
        positive, negative = native(True), native(False)
        groups = {'positive': [positive], 'negative': [negative],
                  'unmatched': [deepcopy(positive)]}
        selected = _balanced_groups(groups, 3)
        self.assertEqual([row['questions']['answer']['label'] for _, row in selected],
                         [True, False])

    def test_rejects_heldout_and_bad_labels(self):
        for split in ('development', 'calibration', 'test', None):
            row = native()
            row['_meta']['split'] = split
            with self.assertRaises(ValueError):
                validate_native(row)
        row = native(1)
        with self.assertRaises(ValueError):
            validate_native(row)

    def test_requires_licence_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'licence'):
                list(convert(Path(folder)))

    def test_preserves_native_pairs_without_mutation(self):
        rows = [native(True), native(False)]
        original = deepcopy(rows)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'approvals.json').write_text(json.dumps({'boolq': {
                'licence': 'fixture', 'evidence': 'https://example.org/licence'}}))
            artifacts = []
            for suite in ('v7/decision-v7', 'hard-v1'):
                (root / suite).mkdir(parents=True)
                path = root / suite / 'train.jsonl'
                path.write_text(
                    '\n'.join(json.dumps(row) for row in rows))
                artifacts.append({'path': f'{suite}/train.jsonl', 'suite_split': 'train',
                                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            (root / 'recovery-manifest.json').write_text(json.dumps(artifacts))
            converted = list(convert(root))
        self.assertEqual(rows, original)
        self.assertEqual(len(converted), len(rows) * 2)
        for events, side, meta in converted:
            self.assertEqual(events, [])
            self.assertIn(side['native_record'], original)
            self.assertTrue(meta['native'])
            self.assertEqual(meta['objective'], [])
        self.assertEqual(converted[0][2]['pair_id'], converted[1][2]['pair_id'])


if __name__ == '__main__':
    unittest.main()
