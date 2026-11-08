"""Convert source preference comparisons into paired monitor evaluation inputs."""

import json
from copy import deepcopy
from pathlib import Path

from monitor_format import build_instructions, collect_documents, fill_question, render_state, validate_events


def preference_pairs(llmbar_dir, reward_path):
    """Yield every labelled source comparison with stable item and response identities."""
    import pyarrow.parquet as pq
    for path in sorted(Path(llmbar_dir).glob('*.json')):
        for index, row in enumerate(json.loads(path.read_text(encoding='utf-8'))):
            if row['label'] not in (1, 2):
                raise ValueError('LLMBar preference must name one of its two responses.')
            preferred = row['label']
            yield {'endpoint': 'llmbar', 'item_id': f'{path.stem}/{index}',
                   'comparison_id': f'{path.stem}/{index}', 'prompt': row['input'],
                   'preferred': row[f'output_{preferred}'], 'rejected': row[f'output_{3-preferred}'],
                   'source_label': row['label'], 'source_subset': path.stem,
                   'source': 'princeton-nlp/LLMBar@900616bff90b6c6c8e1681f7d079250637c55992',
                   'licence': 'MIT', 'annotation_basis': 'author-curated'}
    for batch in pq.ParquetFile(reward_path).iter_batches(batch_size=32):
        for row in batch.to_pylist():
            for chosen_index, chosen in enumerate(row['chosen']):
                for rejected_index, rejected in enumerate(row['rejected']):
                    item_id = str(row['id'])
                    yield {'endpoint': 'rewardbench2', 'item_id': item_id,
                           'comparison_id': f'{item_id}/{chosen_index}/{rejected_index}',
                           'prompt': row['prompt'], 'preferred': chosen, 'rejected': rejected,
                           'chosen_index': chosen_index, 'rejected_index': rejected_index,
                           'source_subset': row['subset'], 'source_metadata': row['additional_metadata'],
                           'source': 'allenai/reward-bench-2', 'licence': 'ODC-BY',
                           'annotation_basis': 'source benchmark labels; varies by subset',
                           'source_counts': {'chosen': len(row['chosen']), 'rejected': len(row['rejected'])}}


def preference_records(pair, tokenizer, budget=8191):
    """Render both responses and preserve comparison membership and source labels."""
    records = []
    for role in ('preferred', 'rejected'):
        item = {'kind': 'user_instruction', 'id': 'I1', 'ts': '', 'text': pair['prompt']}
        event = {'seq': 1, 'type': 'turn_completed', 'ts': '', 'new_items': [item], 'action': {},
                 'agent_text': pair[role], 'agent_thinking': '', 'todos': [], 'turn': {'reason': 'answer'}}
        validate_events([event])
        state, _, fits = render_state(build_instructions([event]), collect_documents([event]),
                                      [event], 1, [], budget, tokenizer=tokenizer)
        if not fits:
            raise ValueError('Preference request exceeds the state budget.')
        questions = {}
        for q in ('M1', 'M2'):
            questions[q] = fill_question(q, event_seq=1)
            questions[q]['label'] = role == 'rejected'
        meta = {k: deepcopy(v) for k, v in pair.items() if k not in ('prompt', 'preferred', 'rejected')}
        records.append({**meta, 'record_id': pair['comparison_id'] + '/' + role,
                        'group_id': pair['item_id'], 'response_role': role,
                        'label_basis': 'relative preference proxy', 'record': {'state': state, 'questions': questions}})
    return records
