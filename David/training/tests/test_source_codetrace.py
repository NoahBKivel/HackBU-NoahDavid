"""Check native shell observations, reasoning isolation and hint indexing."""

import json
from intent_training.sources.codetrace import convert, scrub
from monitor_format import validate_events


def test_native_shell_and_competence_hint(tmp_path):
    row = {'traj_id': 'trajectory', 'task_name': 'task', 'agent': 'mini-SWE-agent',
           'solved': False, 'step_count': 2,
           'incorrect_stages': [{'incorrect_step_ids': [1], 'unuseful_step_ids': []}]}
    (tmp_path / 'manifest.jsonl').write_text(json.dumps(row) + '\n')
    directory = tmp_path / 'trajectories'
    directory.mkdir()
    messages = [{'role': 'system', 'content': 'Harness context.'},
                {'role': 'user', 'content': 'Fix the source.'},
                {'role': 'assistant', 'content': 'THOUGHT: A private hypothesis.\n\n```bash\ncat source.py\n```'},
                {'role': 'user', 'content': '<returncode>1</returncode>\n<output>Missing.</output>'},
                {'role': 'assistant', 'content': 'The file is unavailable.'}]
    (directory / 'trajectory.json').write_text(json.dumps({'messages': messages}))
    events, side, meta = next(convert(tmp_path))
    validate_events(events)
    assert events[1]['action']['result_text'] == messages[3]['content']
    assert events[1]['action']['is_error']
    assert 'private hypothesis' not in json.dumps(events)
    assert 'private hypothesis' in side['reasoning']['2']
    assert side['step_to_seq'] == {'1': 2, '2': 3}
    assert side['source_labels'] == []
    assert side['competence_annotations'][0]['event_seq'] == 2
    assert side['competence_annotations'][0]['basis'] == 'outcome'
    assert meta['objective'] == ['L1', 'L2', 'L4', 'L5', 'G4', 'G1']


def test_rejected_response_does_not_shift_native_step_ids(tmp_path):
    row = {'traj_id': 'trace', 'task_name': 'task', 'agent': 'mini-SWE-agent',
           'solved': False, 'step_count': 1, 'incorrect_stages': []}
    (tmp_path / 'manifest.jsonl').write_text(json.dumps(row) + '\n')
    directory = tmp_path / 'trajectories'
    directory.mkdir()
    messages = [{'role': 'user', 'content': 'Inspect the file.'},
                {'role': 'assistant', 'content': 'THOUGHT: A hypothesis.'},
                {'role': 'user', 'content': 'Please always provide EXACTLY ONE action in triple backticks, found 0 actions.'},
                {'role': 'assistant', 'content': 'THOUGHT: Inspect now.\n```bash\ncat source.py\n```'},
                {'role': 'user', 'content': 'The last command <command>cat source.py</command> timed out and has been killed.'}]
    (directory / 'trace.json').write_text(json.dumps({'messages': messages}))
    events, side, _ = next(convert(tmp_path))
    validate_events(events)
    assert len(events) == 4
    assert side['step_to_seq'] == {'1': 4}
    assert events[-1]['action']['result_text'] == messages[-1]['content']
    assert events[-1]['action']['is_error']


def test_credentials_and_benchmark_canaries_are_removed_recursively():
    credential = 'ghp_' + 'a' * 36
    aws = 'AKIA' + 'A' * 16
    raw = {'output': [credential, aws, '# terminal-bench-canary marker\nVisible text.']}
    cleaned = scrub(raw)
    assert credential not in json.dumps(cleaned)
    assert aws not in json.dumps(cleaned)
    assert cleaned['output'][-1] == 'Visible text.'
