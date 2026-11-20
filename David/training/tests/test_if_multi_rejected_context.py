"""Keep valid source contexts after an invalid generated context."""

import json

from intent_training.sources.if_multi import convert


def test_invalid_generated_context_does_not_hide_next_source_row(tmp_path):
    raw = tmp_path / 'data/downloads/if_multi'
    raw.mkdir(parents=True)
    response_dir = tmp_path / 'data/generation/responses'
    response_dir.mkdir(parents=True)
    row = {'key': 'fixture', 'messages': [{'role': 'user', 'content':
            'The garden is green. Use lowercase letters.'}],
           'constraint': 'Use lowercase letters.', 'ground_truth': repr([{
               'instruction_id': ['change_case:english_lowercase'], 'kwargs': [None]}])}
    (raw / 'rows.jsonl').write_text(''.join(json.dumps({'row_idx': index, 'row': row}) + '\n'
                                             for index in [0, 2]), encoding='utf-8')
    (response_dir / 'if_multi-00000.json').write_text(json.dumps({
        'id': 'if_multi-00000', 'model': 'fixture-model', 'text': 'invalid JSON'}), encoding='utf-8')
    errors = []
    records = list(convert(raw, errors=errors))
    assert [meta['row_idx'] for _, _, meta in records] == [2]
    assert errors[0]['request_id'] == 'if_multi-00000'
