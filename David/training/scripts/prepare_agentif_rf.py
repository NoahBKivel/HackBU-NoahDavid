"""Publish a bounded system-only AgentIF requirement packet from local data."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT.parent), str(ROOT / 'scripts')]

from consume_instruction_sources import atomic_text
from intent_training.prepare.sample import available_ram_gib
from intent_training.sources import agentif
from monitor_format import validate_events


def main():
    """Apply explicit row exclusions and emit only privacy-eligible RF context."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, required=True)
    parser.add_argument('--exclude-index', type=int, action='append', default=[])
    args = parser.parse_args()
    memory = available_ram_gib()
    if memory <= 3.5:
        print(json.dumps({'status': 'RAM_GATE_CLOSED', 'available_gib': memory}), flush=True)
        return 75
    raw = ROOT / 'data/downloads/agentif'
    source = raw / 'eval-prefix.json'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    policy = {'target_count': args.limit, 'excluded_source_row_indices': args.exclude_index,
              'source_sha256': source_hash, 'projection': 'system_messages_only',
              'selection': 'cover_distinct_rf_units_then_source_order'}
    atomic_text(raw / 'rf-eligibility.json', json.dumps(policy, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('credential_scan', ROOT / 'scripts/scan_secrets.py')
    scan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scan)
    records = []
    for events, side, meta in agentif.convert(raw):
        validate_events(events)
        record = {'events': events, 'side': side, 'meta': meta}
        text = json.dumps(record, ensure_ascii=False)
        if any(re.search(pattern, text) for pattern in scan.PATTERNS):
            raise ValueError('A projected AgentIF record matched a credential marker.')
        records.append(record)
    output = ROOT / 'data/converted/agentif.jsonl'
    atomic_text(output, ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in records))
    contexts = {row['meta']['system_sha256'] for row in records}
    labels = sum(len(row['side']['source_labels']) for row in records)
    report = {'source': 'agentif', 'converted_records': len(records), 'converted_count': len(records),
              'target_count': args.limit, 'source_record_ids': len({row['meta']['source_record_id'] for row in records}),
              'distinct_projected_contexts': len(contexts), 'rf_positive_units': labels,
              'distinct_rf_positive_units': len({(row['meta']['system_sha256'], item['unit_position'])
                  for row in records for item in row['side']['source_labels']}),
              'excluded_source_row_indices': args.exclude_index,
              'source_sha256': source_hash, 'source_public_url':
              'https://huggingface.co/datasets/THU-KEG/AgentIF/resolve/main/eval.json',
              'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'licence': agentif.LICENCE, 'credential_findings': 0,
              'raw_conversation_exported': False, 'generated_responses_used': 0,
              'generation_requests_modified': False, 'available_gib_at_start': memory}
    atomic_text(ROOT / 'results/sources/agentif.json', json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    return 0 if len(records) == args.limit else 1


if __name__ == '__main__':
    raise SystemExit(main())
