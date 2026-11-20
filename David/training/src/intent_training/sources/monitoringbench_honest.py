"""Convert manifest-selected honest Inspect messages without exposing grades."""

import io
import hashlib
import json
import struct
import re
import zipfile
from pathlib import Path
from collections.abc import Iterator
from .events import from_messages


def _member(archive, item):
    if item.compress_type not in {20, 93}:
        return archive.read(item)
    import zstandard
    handle = archive.fp
    handle.seek(item.header_offset)
    header = struct.unpack('<4s5H3I2H', handle.read(30))
    handle.seek(header[-2] + header[-1], 1)
    return zstandard.ZstdDecompressor().stream_reader(
        io.BytesIO(handle.read(item.compress_size))).read()


def _samples(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        for item in archive.infolist():
            if item.filename.startswith('samples/') and item.filename.endswith('.json'):
                yield json.loads(_member(archive, item))


def _redact(value):
    if isinstance(value, str):
        value = re.sub(r'-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----',
                       '[REDACTED PRIVATE KEY]', value, flags=re.DOTALL)
        return re.sub(r'-----BEGIN [A-Z ]*PRIVATE KEY-----', '[REDACTED PRIVATE KEY]', value)
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def map_sample(sample, selection):
    """Keep actual messages and clarification answers, with outcomes side only."""
    scores = sample.get('scores') or {}
    if not scores or scores.get('side_task_success', {}).get('value') == 'C':
        return None
    messages = []
    summaries = []
    for original in sample.get('messages', []):
        item = dict(original)
        content = item.get('content')
        if isinstance(content, list):
            kept = []
            message_summaries = []
            for block in content:
                if block.get('type') == 'reasoning':
                    if block.get('summary'):
                        message_summaries.append(block['summary'])
                        summaries.append({'message_id': item.get('id'), 'summary': block['summary']})
                else:
                    kept.append(block)
            item['content'] = kept
            if message_summaries:
                item['reasoning_content'] = '\n'.join(message_summaries)
        calls = []
        for call in item.get('tool_calls') or []:
            function = call.get('function')
            if isinstance(function, str):
                name = {'bash': 'Bash'}.get(function, function)
                calls.append({'id': call.get('id'), 'function': {
                    'name': name, 'arguments': call.get('arguments', {})}})
            else:
                calls.append(call)
        if calls:
            item['tool_calls'] = calls
        messages.append(item)
    events, reasoning = from_messages(messages)
    if not events:
        return None
    side = {'reasoning': reasoning, 'reasoning_summaries': summaries,
            'scores': scores, 'source_metadata': sample.get('metadata', {}),
            'source_labels': [], 'label_hints': [{'basis': 'outcome', 'value': 'honest',
                                                  'origin': 'source_release'}]}
    meta = {'source': 'monitoringbench_honest', 'trajectory_id': sample['uuid'],
            'task_id': selection['task_id'], 'source_record_id': selection['release_id'],
            'objective': [], 'licence': 'CC-BY-4.0', 'harness': 'Inspect BashArena'}
    return _redact(events), _redact(side), meta


def convert(raw_dir: Path) -> Iterator[tuple[list[dict], dict, dict]]:
    """Select original samples by manifest UUID in the release's declared order."""
    raw_dir = Path(raw_dir)
    selections = [json.loads(line) for line in (raw_dir / 'manifest.jsonl').read_text().splitlines() if line]
    allowed = {row['source_sample_uuid'] for row in selections}
    source_hashes = {row['source_sha256'] for row in selections}
    samples = {}

    def accept(blob):
        if hashlib.sha256(blob).hexdigest() not in source_hashes:
            raise ValueError('Original log hash does not match the release manifest.')
        for sample in _samples(blob):
            if sample['uuid'] in allowed:
                samples[sample['uuid']] = sample

    complete = raw_dir / 'original_inspect_logs.zip'
    if complete.exists():
        with zipfile.ZipFile(complete) as archive:
            for item in archive.infolist():
                if item.filename.endswith('.eval'):
                    accept(archive.read(item))
    else:
        for path in sorted(raw_dir.glob('*.eval')):
            accept(path.read_bytes())
    for selection in selections:
        sample = samples.get(selection['source_sample_uuid'])
        if sample is not None:
            mapped = map_sample(sample, selection)
            if mapped:
                yield mapped
