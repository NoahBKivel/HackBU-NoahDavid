"""Check teacher cut validation and once-only request ownership."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import trace_exposure_cuts as cuts


def test_cut_logged_and_reused_without_second_call(tmp_path, monkeypatch):
    cuts.STOP.clear()
    monkeypatch.setattr(cuts, 'ROOT', tmp_path)
    conversation = [{'role': 'user', 'content': 'do it'}, {'role': 'assistant', 'content': 'done'},
                    {'role': 'user', 'content': 'you faked it'}]
    row = {'trajectory_id': 'test', 'conversation': json.dumps(conversation)}
    budget = cuts.TraceBudget(tmp_path / 'spend.jsonl')
    rates = {'long_threshold_tokens': 100, 'short': {'input': 1, 'cached_input': 1,
        'cache_write_30m': 1, 'output': 1}, 'long': {'input': 1, 'cached_input': 1,
        'cache_write_30m': 1, 'output': 1}}
    pricing = {'models': {'gpt-6.1-terra': rates}}
    value = {'id': 'response', 'status': 'completed', 'usage': {'input_tokens': 10, 'output_tokens': 5},
             'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text':
                 json.dumps({'cut_before_message_index': 2, 'evidence': 'user challenge'})}]}]}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps(value).encode()
    calls = []
    def fake_open(*args, **kwargs):
        calls.append(1)
        return Response()
    monkeypatch.setattr(cuts, 'urlopen', fake_open)
    assert cuts.locate(row, 'test-key', budget, pricing, tmp_path) == 'completed'
    assert cuts.locate(row, 'test-key', budget, pricing, tmp_path) == 'existing'
    assert len(calls) == 1
    assert json.loads((tmp_path / 'test.json').read_text())['cut_before_message_index'] == 2
