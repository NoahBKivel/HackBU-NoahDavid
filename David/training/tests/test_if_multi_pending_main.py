"""Keep real main responses available without unsupported checker categories."""

import hashlib
import json

from intent_training.sources.if_multi import convert


def answer_fixture(tmp_path):
    raw = tmp_path / 'data/downloads/if_multi'
    raw.mkdir(parents=True)
    responses = tmp_path / 'data/generation/responses'
    responses.mkdir(parents=True)
    constraint = 'Include the word blue.'
    row = {'key': 'fixture', 'messages': [{'role': 'user', 'content':
            'The garden is green. ' + constraint}], 'constraint': constraint,
           'ground_truth': repr([{'instruction_id': ['keywords:existence'],
                                  'kwargs': [{'keywords': ['blue']}]}])}
    (raw / 'rows.jsonl').write_text(json.dumps({'row_idx': 200, 'row': row}) + '\n', encoding='utf-8')
    context = {'instruction': constraint + '\n\nThe garden is green.', 'document': None,
               'constraints': [constraint], 'response': 'green.'}
    (responses / 'if_multi-00200.json').write_text(json.dumps({
        'id': 'if_multi-00200', 'model': 'fixture-model', 'text': json.dumps(context)}), encoding='utf-8')
    return raw


def test_main_response_does_not_wait_for_checker(tmp_path):
    records = list(convert(answer_fixture(tmp_path)))
    events, side, meta = records[0]
    assert events[-1]['agent_text'] == 'green.'
    assert side['source_labels'] == []
    assert side['checks_pending'] and meta['checks_pending']


def test_boolean_failure_does_not_invent_broken_checklist_status(tmp_path):
    raw = answer_fixture(tmp_path)
    (raw / 'checks').mkdir()
    (raw / 'checks/if_multi-00200.json').write_text(json.dumps({
        'response_sha256': hashlib.sha256(b'green.').hexdigest(),
        'instruction_ids': ['keywords:existence'], 'isolation': 'modal',
        'passed': [False], 'errors': []}), encoding='utf-8')
    _, side, _ = list(convert(raw))[0]
    assert any(label['question'] == 'M2' and label['value'] for label in side['source_labels'])
    assert not any(label['question'] == 'G2' for label in side['source_labels'])
    assert side['outcomes']['failed_requirements'][0]['basis'] == 'outcome'
