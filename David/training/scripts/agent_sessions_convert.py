"""Validate and persist this source's converted streams and measured coverage."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT.parent)]
from intent_training.sources.agent_sessions import convert, parse, PRIVATE_CONTEXT, BYPASS, AUTOMATION, ROLE
from intent_training.sources.reading import rows
from monitor_format import validate_events

raw = ROOT / 'data/downloads/agent_sessions'
out = ROOT / 'data/converted/agent_sessions.jsonl'
report_path = ROOT / 'results/sources/agent_sessions.json'
counts = Counter()
filters = Counter()
files = []
for path in sorted(raw.glob('rows-*.jsonl')):
    files.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
    for row in rows(path):
        filters['source_rows'] += 1
        filters['provider:' + row.get('provider','unknown')] += 1
        filters['truncated_rows'] += bool(row.get('_truncated_cells'))
        filters['hook_rows'] += 'Stop hook feedback:' in row.get('text','')
        filters['private_context_rows'] += bool(PRIVATE_CONTEXT.search(row.get('text','')))
        filters['bypass_rows'] += bool(BYPASS.search(row.get('text','')))
        filters['automation_rows'] += bool(AUTOMATION.search(row.get('text','')))
        if row.get('provider') == 'claude':
            try:
                parts = parse(row.get('text',''))
                filters['role_prompt_rows'] += bool(parts and parts[0][0] == 'User' and ROLE.search(parts[0][1]))
                filters['parsed_tool_using_rows'] += any(kind == 'call' for kind, _ in parts)
            except ValueError: filters['unrecognized_markdown'] += 1
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w',encoding='utf-8') as output:
    for events,side,meta in convert(raw):
        if counts[meta['slice']] >= dict(claim=110,recovery=110,benign=165)[meta['slice']]:
            continue
        validate_events(events)
        assert not any(e['agent_thinking'] for e in events)
        assert meta.get('cut_seq',events[-1]['seq']) <= events[-1]['seq']
        output.write(json.dumps(dict(events=events,side=side,meta=meta),ensure_ascii=False)+'\n')
        counts[meta['slice']] += 1
report_path.parent.mkdir(parents=True,exist_ok=True)
report = dict(dataset='TonyDzi/agent-sessions',counts=dict(counts),filters=dict(filters),source_files=files,output=str(out.relative_to(ROOT)),output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),errors=[],validation='Every written stream passes monitor_format.validate_events.',quota=dict(claim=100,recovery=100,benign=150),dev_reserve=dict(claim=10,recovery=10,benign=15))
report['shortfalls'] = {key: max(0, quota - counts[key]) for key, quota in report['quota'].items()}
report['missing_proof'] = ['No Stop-hook claim or recovery source examples were found in the bounded downloaded prefix.'] if not filters['hook_rows'] else []
report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(counts=dict(counts),filters=dict(filters)),indent=2))

