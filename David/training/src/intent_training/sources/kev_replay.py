"""Preserve licensed Kev native train records without rendering states."""

from collections import Counter, OrderedDict
import json
import hashlib
from pathlib import Path

EVAL_ONLY = frozenset(('mmlu', 'emotion', 'tweet_offensive', 'qnli', 'paws',
                       'sciq', 'contrastive', 'legacy_holdout', 'composition_holdout'))
SLICES = {'decision-v7': 2000, 'hard-v1': 500}


def _balanced_groups(groups, quota):
    """Pair opposite source imbalances while retaining complete native groups."""
    pending = {}
    units = []
    for group, records in groups.items():
        delta = Counter()
        for record in records:
            source = record['_meta']['source']
            if source in ('boolq', 'agnews'):
                for q in record['questions'].values():
                    if q['type'] == 'noul':
                        delta[source] += 1 if q['label'] else -1
        vector = (delta['boolq'], delta['agnews'])
        opposite = tuple(-value for value in vector)
        members = [(group, record) for record in records]
        if vector == (0, 0):
            units.append(members)
        elif pending.get(opposite):
            units.append(pending[opposite].pop(0) + members)
        else:
            pending.setdefault(vector, []).append(members)
    selected = []
    for unit in units:
        if len(selected) + len(unit) <= quota:
            selected.extend(unit)
    return selected


def validate_native(record, *, suite_train=False):
    """Reject malformed labels and heldout records before any selection."""
    if not isinstance(record, dict) or not isinstance(record.get('state'), (str, dict, list)):
        raise ValueError('A native record must contain a JSON state.')
    meta = record.get('_meta', {})
    if not isinstance(meta, dict) or not isinstance(meta.get('source'), str):
        raise ValueError('A native record must retain its original source.')
    allowed_split = meta.get('split') in ('train', 'generated', None) if suite_train else meta.get('split') == 'train'
    if meta['source'] in EVAL_ONLY or not allowed_split:
        raise ValueError('Only verified train records are accepted.')
    if meta.get('pair_id') and not meta.get('group_id'):
        raise ValueError('Pair records require a complete group identifier.')
    questions = record.get('questions')
    if not isinstance(questions, dict) or not questions:
        raise ValueError('Native questions must be a nonempty object.')
    for q in questions.values():
        if not isinstance(q, dict) or not isinstance(q.get('instructions'), (str, dict, list)):
            raise ValueError('Native questions require instructions.')
        kind, label, criteria = q.get('type'), q.get('label'), q.get('criteria')
        if q.get('src') in EVAL_ONLY:
            raise ValueError('Eval-only question sources are forbidden.')
        valid = (kind == 'noul' and type(label) is bool
                 or kind == 'choice' and isinstance(criteria, dict)
                 and isinstance(label, str) and label in criteria
                 or kind == 'score' and isinstance(criteria, list)
                 and type(label) is int and 0 <= label < len(criteria))
        if not valid:
            raise ValueError('Native question label does not match its type.')


def convert(raw_dir: Path):
    """Read only explicit train files and require source-specific licence proof.

    approvals.json maps each original source to licence and evidence URL.
    Missing licence evidence blocks the whole conversion before yielding rows.
    Input train files must already contain complete minimal-pair groups.
    """
    raw_dir = Path(raw_dir)
    approval_path = raw_dir / 'approvals.json'
    if not approval_path.exists():
        raise ValueError('Verified per-source training licence evidence is missing.')
    approvals = json.loads(approval_path.read_text(encoding='utf-8'))
    selected = []
    for suite, quota in SLICES.items():
        path = raw_dir / ('v7/decision-v7' if suite == 'decision-v7' else suite) / 'train.jsonl'
        if not path.exists():
            raise ValueError(f'The actual {suite} train file is unavailable.')
        provenance = json.loads((raw_dir / 'recovery-manifest.json').read_text(encoding='utf-8'))
        artifacts = provenance if isinstance(provenance, list) else provenance.get('artifacts', [])
        if not artifacts:
            raise ValueError('Verified original suite train provenance is required.')
        proof = next((item for item in artifacts if item['path'] == path.relative_to(raw_dir).as_posix()), {})
        with path.open('rb') as handle:
            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        if proof.get('sha256') != digest or proof.get('suite_split') != 'train':
            raise ValueError('Original suite train hash proof does not match.')
        groups = OrderedDict()
        with path.open('rb') as handle:
            while True:
                offset = handle.tell()
                line = handle.readline()
                if not line:
                    break
                record = json.loads(line)
                validate_native(record, suite_train=True)
                meta = record['_meta']
                if suite == 'hard-v1' and meta.get('family') == 'long_policy':
                    continue
                source = meta['source']
                approval = approvals.get(source, {})
                if not approval.get('licence') or not approval.get('evidence'):
                    raise ValueError(f'Training licence evidence is missing for {source}.')
                identity = meta.get('id') or meta.get('row_sha256')
                if not identity:
                    raise ValueError('A stable source record identity is missing.')
                group = meta.get('group_id') or meta.get('pair_id') or identity
                summary = {'_offset': offset, '_meta': meta, 'questions': {
                    key: {'type': q['type'], 'label': q['label']}
                    for key, q in record['questions'].items()}}
                groups.setdefault(str(group), []).append(summary)
        suite_rows = [(suite, group, record)
                      for group, record in _balanced_groups(groups, quota)]
        # Balancing never changes the original question set or labels.
        balance = {}
        for _, _, record in suite_rows:
            source = record['_meta']['source']
            if source in ('boolq', 'agnews'):
                balance.setdefault(source, Counter()).update(
                    q['label'] for q in record['questions'].values() if q['type'] == 'noul')
        if any(counts[True] != counts[False] for counts in balance.values()):
            raise ValueError('The selected boolq or agnews noul rows are not balanced.')
        selected.extend((suite, group, summary, path) for suite, group, summary in suite_rows)
    for suite, group, summary, path in selected:
        with path.open('rb') as handle:
            handle.seek(summary['_offset'])
            record = json.loads(handle.readline())
        original = record['_meta']
        source = original['source']
        identity = original.get('id') or original['row_sha256']
        licence = approvals[source]['licence']
        yield [], {'native_record': record, 'licence': licence}, {
            'source': 'kev_replay', 'source_record_id': identity,
            'trajectory_id': identity, 'pair_id': f'{suite}/{group}',
            'objective': [], 'native': True, 'licence': licence,
            'harness': 'kev', 'suite': suite, 'original_source': source,
        }
