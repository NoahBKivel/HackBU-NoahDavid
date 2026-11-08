"""Check source preference orientation, grouping and monitor rendering."""

from types import SimpleNamespace
import json
import pyarrow as pa
import pyarrow.parquet as pq
from intent_training.splits.heldout_preferences import preference_pairs, preference_records


def test_rendered_pair_preserves_relative_orientation_and_group():
    class Tokenizer:
        def __call__(self, text, add_special_tokens=False):
            return SimpleNamespace(input_ids=list(text))

    pair = {'endpoint': 'llmbar', 'item_id': 'item', 'comparison_id': 'item/0',
            'prompt': 'Answer the request', 'preferred': 'Good answer', 'rejected': 'Bad answer',
            'source_label': 2, 'source_subset': 'Natural'}
    preferred, rejected = preference_records(pair, Tokenizer())
    assert preferred['group_id'] == rejected['group_id'] == 'item'
    assert preferred['source_label'] == rejected['source_label'] == 2
    assert '[I1]' in preferred['record']['state'] and 'Good answer' in preferred['record']['state']
    assert 'Bad answer' in rejected['record']['state']
    for question in ('M1', 'M2'):
        assert preferred['record']['questions'][question]['label'] is False
        assert rejected['record']['questions'][question]['label'] is True
    assert preferred['label_basis'] == 'relative preference proxy'


def test_source_preference_orientation_and_multiple_comparisons(tmp_path):
    directory = tmp_path / 'llmbar'
    directory.mkdir()
    (directory / 'Natural.json').write_text(json.dumps([{'input': 'q', 'output_1': 'bad',
        'output_2': 'good', 'label': 2}]), encoding='utf-8')
    reward = tmp_path / 'reward.parquet'
    pq.write_table(pa.Table.from_pylist([{'id': 'a', 'prompt': 'p', 'chosen': ['c1', 'c2'],
        'rejected': ['r1', 'r2'], 'subset': 'Ties', 'additional_metadata': {'label': 'tied'}}]), reward)
    rows = list(preference_pairs(directory, reward))
    assert rows[0]['preferred'] == 'good' and rows[0]['rejected'] == 'bad'
    assert len(rows) == 5
    assert {r['comparison_id'] for r in rows[1:]} == {'a/0/0', 'a/0/1', 'a/1/0', 'a/1/1'}
    assert all(r['item_id'] == 'a' and r['source_metadata']['label'] == 'tied' for r in rows[1:])
