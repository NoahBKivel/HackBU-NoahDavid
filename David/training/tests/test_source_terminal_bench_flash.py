"""Check dsh evidence separation and faithful tool reconstruction."""
import json
from intent_training.sources.terminal_bench_flash import convert
from monitor_format import validate_events


def test_dsh_preserves_clarification_and_outcome_boundary(tmp_path):
    trial = tmp_path / 'dsh' / 'example'
    agent = trial / 'agent'
    agent.mkdir(parents=True)
    (trial / 'verifier').mkdir()
    (trial / 'verifier' / 'test-stdout.txt').write_text('FAILED hidden check', encoding='utf-8')
    rows = [
        {'type': 'session', 'id': 'trial'},
        {'type': 'user/message', 'data': {'content': [{'type': 'text', 'text': 'Build it.'}]}},
        {'type': 'assistant/message', 'data': {'message': {'content': [{'type': 'reasoning', 'text': 'private reasoning'}, {'type': 'tool-call', 'id': 'a'}]}}},
        {'type': 'tool/call', 'data': {'callId': 'a', 'name': 'AskUserQuestion', 'arguments': '{"question":"Which?"}'}},
        {'type': 'tool/result', 'data': {'message': {'content': [{'type': 'tool-result', 'toolCallId': 'a', 'content': [{'type': 'text', 'text': 'Use option two.'}]}]}}},
        {'type': 'assistant/message', 'data': {'message': {'content': [{'type': 'text', 'text': 'Done.'}]}}},
    ]
    (agent / 'dsh-session.jsonl').write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
    (agent / 'dsh-result.json').write_text(json.dumps({'final_response': 'Done.'}), encoding='utf-8')
    events, side, meta = next(convert(tmp_path))
    validate_events(events)
    assert len(events) == 3
    assert events[1]['action']['result_text'] == 'Use option two.'
    assert events[-1]['agent_text'] == 'Done.'
    assert side['reasoning'] == {'2': 'private reasoning'}
    assert 'FAILED hidden check' not in json.dumps(events)
    assert all(e['agent_thinking'] == '' for e in events)
    assert side['source_labels'] == []
    assert meta['objective'] == ['M5', 'G5']
