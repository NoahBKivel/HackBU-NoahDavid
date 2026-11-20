"""Resolve registered non-TRACE probe identities from their original source rows."""

import json
from pathlib import Path
import re
from monitor_format import build_instructions, collect_documents, fill_question, render_state, validate_events


def _jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def probe_sources(manifest, downloads):
    """Resolve source labels and preserve material needed for event rendering."""
    import pyarrow.parquet as pq
    downloads = Path(downloads)
    ifroot = downloads / 'heldout-ifbench'
    prompts = {r['key']: r for r in pq.read_table(ifroot / 'ifbench-test.parquet').to_pylist()}
    responses = {r['prompt']: r for r in _jsonl(ifroot / 'sample_output.jsonl')}
    strict = {r['prompt']: r for r in _jsonl(ifroot / 'eval_results_strict.jsonl')}
    loose = {r['prompt']: r for r in _jsonl(ifroot / 'eval_results_loose.jsonl')}
    aspi = {}
    for path in (downloads / 'heldout-aspi').glob('*.jsonl'):
        for row in _jsonl(path):
            key = '/'.join((row['suite'], row['user_task_id'], row['injection_task_id']))
            if key in aspi:
                raise ValueError('Duplicate aspi source identity.')
            aspi[key] = row
    for item in manifest:
        kind, identity = item['capability'], item['record_id']
        if kind == 'implicit_goal':
            continue
        common = {'record_id': identity, 'intent_kind': kind, 'source': item['source'],
                  'source_label': item['label']}
        if kind == 'request_satisfaction':
            key = identity.removeprefix('IFBench_test key ')
            source = prompts[key]
            prompt = source['prompt']
            answer, strict_row, loose_row = responses[prompt], strict[prompt], loose[prompt]
            if strict_row['follow_all_instructions'] != loose_row['follow_all_instructions'] or strict_row['follow_all_instructions'] != item['label']:
                raise ValueError('IFBench registered label disagrees with original verifier outputs.')
            yield {**common, 'group_id': identity, 'question': 'M2', 'label': not item['label'],
                   'instructions': [prompt], 'message': answer['response'],
                   'provenance': {'source_row': source, 'strict': strict_row, 'loose': loose_row}}
        elif kind == 'clarification_need':
            source_id, field = identity.split('#', 1)
            if field not in ('base_prompt', 'original_prompt'):
                raise ValueError('Unexpected aspi prompt variant.')
            row = aspi[source_id]
            if item['label'] != (field == 'base_prompt'):
                raise ValueError('The aspi label does not match its prompt variant.')
            yield {**common, 'group_id': '/'.join(source_id.split('/')[:2]), 'question': 'M7',
                   'label': item['label'], 'instructions': [row[field]], 'tools': row['ground_truth_tool_calls'],
                   'provenance': {'source_row': row, 'prompt_field': field}}
        elif kind == 'still_pursuing':
            instance_id, shift_id, predicate_id = identity.split('/')
            source = json.loads((downloads / 'heldout-userintent' / (instance_id + '.json')).read_text(encoding='utf-8'))
            shift = next(s for s in source['shifts'] if s['shift_id'] == shift_id)
            delta = shift['delta']
            accepted = set(delta['preserved_predicate_ids']) | set(delta['new_predicate_ids'])
            obsolete = set(delta['obsolete_predicate_ids'])
            if predicate_id not in accepted | obsolete or item['label'] != (predicate_id in accepted):
                raise ValueError('UserIntentBench registered label disagrees with the shift delta.')
            predicates = source['oracle_graph']['predicates'] + shift['active_graph']['predicates']
            predicate = next(p for p in predicates if p['id'] == predicate_id)
            entities = source['oracle_graph']['entities'] + shift['active_graph']['entities']
            names = {e['id']: e['name'] for e in entities}
            content = re.sub(r'<\|-(E\d+)-\|>', lambda m: names[m.group(1)], predicate['content'])
            yield {**common, 'group_id': instance_id + '/' + shift_id, 'question': 'G1',
                   'label': item['label'], 'instructions': [source['initial_prompt'], shift['update_message']],
                   'message': "Next I'm building this part: " + content,
                   'provenance': {'predicate': predicate, 'delta': delta, 'licence': 'CC-BY-NC-SA-4.0'}}
        else:
            raise ValueError('Unknown registered intent capability.')


def render_probe(source, tokenizer, budget=8191):
    """Render one source-labelled item without putting provenance into visible state."""
    instructions = [{'kind': 'user_instruction', 'id': f'I{i}', 'ts': '', 'text': text}
                    for i, text in enumerate(source['instructions'], 1)]
    events = []
    tools = source.get('tools')
    if tools is not None:
        if not tools:
            raise ValueError('A clarification item requires an actual source tool call.')
        for i, tool in enumerate(tools, 1):
            events.append({'seq': i, 'event_id': f'tool_{i}', 'type': 'tool_completed', 'ts': '',
                           'new_items': instructions if i == 1 else [],
                           'action': {'tool': tool['function'], 'args': tool['args'],
                                      'result_text': '', 'is_error': False},
                           'agent_text': '', 'agent_thinking': '', 'todos': [], 'turn': {}})
    else:
        events.append({'seq': 1, 'event_id': 'message_1', 'type': 'turn_completed', 'ts': '',
                       'new_items': instructions, 'action': {}, 'agent_text': source['message'],
                       'agent_thinking': '', 'todos': [], 'turn': {'reason': 'answer'}})
    validate_events(events)
    latest = events[-1]['seq']
    state, _, fits = render_state(build_instructions(events), collect_documents(events), events, latest,
                                  [], budget, tokenizer=tokenizer)
    if not fits:
        raise ValueError('Probe instructions exceed the state budget.')
    q = source['question']
    question = fill_question(q, event_seq=latest)
    question['label'] = source['label']
    return {**{k: v for k, v in source.items() if k not in ('instructions', 'message', 'tools', 'question', 'label')},
            'endpoint': 'intent_probe', 'record': {'state': state, 'questions': {q: question}}}
