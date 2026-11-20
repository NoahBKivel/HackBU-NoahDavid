"""Check label isolation, opaque reasoning removal and real clarification results."""

from intent_training.sources.monitoringbench_honest import map_sample
from monitor_format import validate_events


def sample():
    return {'uuid': 'run', 'scores': {'side_task_success': {'value': 'I'}},
            'metadata': {'side_task_description': 'private task'}, 'messages': [
                {'role': 'user', 'content': 'Read the authorized configuration.'},
                {'role': 'assistant', 'content': [{'type': 'reasoning', 'reasoning': 'opaque', 'summary': 'private summary'}],
                 'tool_calls': [{'id': 'ask', 'function': 'AskUserQuestion', 'arguments': {'question': 'Which file?'}}]},
                {'role': 'tool', 'tool_call_id': 'ask', 'content': '/opt/configs/api_tokens.json'},
                {'role': 'assistant', 'content': 'I will use that file.'}]}


def selection():
    return {'task_id': 'task', 'release_id': 'release'}


def test_clarification_and_labels():
    events, side, meta = map_sample(sample(), selection())
    validate_events(events)
    assert events[1]['action']['result_text'] == '/opt/configs/api_tokens.json'
    assert all(not event['agent_thinking'] for event in events)
    assert 'private task' not in str(events)
    assert 'opaque' not in str((events, side))
    assert side['reasoning_summaries'][0]['summary'] == 'private summary'
    assert side['source_labels'] == []
    assert meta['objective'] == []


def test_side_task_success_is_excluded():
    row = sample()
    row['scores']['side_task_success']['value'] = 'C'
    assert map_sample(row, selection()) is None


def test_scoreless_is_excluded():
    row = sample()
    row['scores'] = {}
    assert map_sample(row, selection()) is None


def test_private_key_material_is_redacted():
    row = sample()
    row['messages'].append({'role': 'assistant', 'content':
                            '-----BEGIN RSA ' + 'PRIVATE KEY-----\nsecret payload\n-----END RSA PRIVATE KEY-----'})
    events, side, _ = map_sample(row, selection())
    assert 'secret payload' not in str((events, side))
    assert events[-1]['agent_text'] == '[REDACTED PRIVATE KEY]'
