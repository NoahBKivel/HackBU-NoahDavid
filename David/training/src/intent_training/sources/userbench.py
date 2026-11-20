"""Convert real UserBench scenarios and centrally generated option choices."""

import hashlib
import json
import re
from pathlib import Path

import pyarrow.parquet as pq


def cases(raw_dir: Path):
    """Read the retained training scenarios in source row order."""
    scenarios = json.loads((raw_dir / 'scenarios.json').read_text(encoding='utf-8'))
    for row in pq.read_table(raw_dir / 'train.parquet').to_pylist()[:100]:
        task = row['reward_model']['id']
        scenario = scenarios[task]
        dimension = scenario['dimensions'][0]
        detail = scenario[dimension]
        options = {o['id']: {k: v for k, v in o.items() if k not in {'type', 'reason'}}
                   for group in detail['options'].values() for o in group}
        options = [options[i] for i in detail['all_ids'] if i in options]
        key = 'userbench-' + hashlib.sha256(task.encode()).hexdigest()[:20]
        yield key, task, scenario, dimension, detail, options


def generation_requests(raw_dir: Path):
    """Ask for a choice without exposing answer keys or option classifications."""
    for key, task, scenario, dimension, detail, options in cases(raw_dir):
        prompt = (scenario['scenario'] + '\nChoose the cheapest option satisfying my preferences for '
                  + dimension + '. Return only its exact option ID.\nOptions:\n'
                  + json.dumps(options, ensure_ascii=False))
        yield {'id': key, 'purpose': 'Choose a travel option for the user.',
               'prompt': prompt, 'max_output_tokens': 32,
               'refs': {'source': 'SalesforceAIResearch/UserBench', 'task_id': task}}


def _event(seq, kind):
    return dict(seq=seq, type=kind, ts='', new_items=[], action={}, agent_text='',
                agent_thinking='', todos=[], turn={})


def chosen_option(text, options):
    """Recognize an explicit final option without inferring choices from deliberation."""
    identifiers = {option['id'] for option in options}
    cleaned = text.strip().strip('`*_ ')
    if cleaned in identifiers:
        return cleaned
    final = text.strip().split('\n\n')[-1]
    pattern = r'(?<![A-Za-z0-9])(?:' + '|'.join(re.escape(value) for value in identifiers) + r')(?![A-Za-z0-9])'
    found = set(re.findall(pattern, final))
    if len(found) == 1:
        identifier = next(iter(found))
        last_line = final.splitlines()[-1].strip().strip('`*_ .')
        if last_line == identifier or re.search(r'\b(?:choose|choice|select|recommend|cheapest|best|answer)\b', final, re.I):
            return identifier
    return None


def convert(raw_dir: Path):
    """Yield only actual generated choices matched to real source options."""
    responses = raw_dir.parents[1] / 'generation' / 'responses'
    for key, task, scenario, dimension, detail, options in cases(raw_dir):
        response = responses / (key + '.json')
        if not response.exists():
            continue
        text = json.loads(response.read_text(encoding='utf-8'))['text']
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Generated UserBench response requires nonempty text.')
        choice = chosen_option(text, options)
        selected = next((o for o in options if o['id'] == choice), None)
        initial = _event(1, 'session_started')
        initial['new_items'] = [{'kind': 'user_instruction', 'id': 'I1', 'text':
            scenario['scenario'] + '\nChoose the cheapest option satisfying my preferences for '
            + dimension + '.\nOptions:\n' + json.dumps(options, ensure_ascii=False)}]
        final = _event(2, 'turn_completed')
        final['agent_text'] = text
        final['turn'] = {'reason': 'answer'}
        labels = []
        violates = choice in detail['wrong_ids']
        matched = choice == detail['best_id']
        if violates or matched:
            labels = [{'question': 'M1', 'value': violates, 'event_seq': 2, 'basis': 'visible',
                       'origin': 'rule'}]
        side = {'reasoning': {}, 'source_labels': labels, 'licence': 'Apache-2.0',
                'outcomes': {'chosen_id': choice, 'best_id': detail['best_id'],
                             'wrong_ids': detail['wrong_ids'],
                             'choice_parse': 'explicit_final_option' if selected else 'unresolved',
                             'selected_option': selected}}
        meta = {'source': 'userbench', 'trajectory_id': task, 'task_id': task,
                'source_record_id': key, 'objective': ['M1', 'G1'], 'licence': 'Apache-2.0',
                'harness': 'UserBench-option-choice', 'cut_seq': 2,
                'cut_kind': 'positive' if violates else 'negative' if matched else 'unspecified'}
        yield [initial, final], side, meta


def materialize(workspace: Path):
    """Validate available choices and persist measured source conversion evidence."""
    from monitor_format import validate_events

    raw = workspace / 'data' / 'downloads' / 'userbench'
    records = []
    for events, side, meta in convert(raw):
        validate_events(events)
        records.append({'events': events, 'side': side, 'meta': meta})
    output = workspace / 'data' / 'converted' / 'userbench.jsonl'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records),
                      encoding='utf-8')
    report = {'source': 'userbench', 'source_rows': pq.read_metadata(raw / 'train.parquet').num_rows,
              'selected_scenarios': sum(1 for _ in cases(raw)), 'converted_count': len(records),
              'positive_count': sum(r['meta']['cut_kind'] == 'positive' for r in records),
              'negative_count': sum(r['meta']['cut_kind'] == 'negative' for r in records),
              'pending_generation': sum(1 for key, *_ in cases(raw)
                  if not (workspace / 'data' / 'generation' / 'responses' / (key + '.json')).exists()),
              'source_files': [{'path': str(p.relative_to(workspace)),
                                'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                               for p in [raw / 'train.parquet', raw / 'scenarios.json']],
              'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'errors': [], 'access_attempt_errors': ['Host api.github.com DNS failed.',
                  'Docker raw.githubusercontent.com fetch failed; connector and host raw fallback succeeded.']}
    target = workspace / 'results' / 'sources' / 'userbench.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report
