"""Check choice provenance and conservative ground truth comparisons."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from intent_training.sources import userbench
from monitor_format import validate_events


class UserBenchTests(unittest.TestCase):
    def test_ground_truth_polarity_and_option_identity(self):
        for choice, expected in [('A', [False]), ('B', [True]), ('C', [])]:
            with self.subTest(choice=choice), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                raw = root / 'downloads' / 'userbench'
                raw.mkdir(parents=True)
                responses = root / 'generation' / 'responses'
                responses.mkdir(parents=True)
                (responses / 'choice.json').write_text(json.dumps({'text': choice}))
                options = [{'id': x, 'name': 'Option ' + x} for x in 'ABC']
                case = ('choice', 'task', {'scenario': 'Find a hotel.'}, 'hotel',
                        {'wrong_ids': ['B'], 'best_id': 'A'}, options)
                with patch.object(userbench, 'cases', return_value=iter([case])):
                    events, side, meta = next(userbench.convert(raw))
                validate_events(events)
                self.assertEqual(events[-1]['agent_text'], choice)
                self.assertEqual(side['outcomes']['selected_option'], options['ABC'.index(choice)])
                self.assertEqual([x['value'] for x in side['source_labels']], expected)
                self.assertFalse(any(x['question'] == 'G1' for x in side['source_labels']))
                self.assertEqual(meta['task_id'], 'task')

    def test_missing_response_produces_no_fabricated_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / 'downloads' / 'userbench'
            raw.mkdir(parents=True)
            case = ('absent', 'task', {}, '', {}, [])
            with patch.object(userbench, 'cases', return_value=iter([case])):
                self.assertEqual(list(userbench.convert(raw)), [])
