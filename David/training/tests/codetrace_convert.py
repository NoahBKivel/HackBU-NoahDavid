"""Write and validate measured CodeTraceBench conversion artifacts."""

import hashlib
import json
from pathlib import Path
import sys

sys.path[:0] = [str(Path('src').resolve()), str(Path('..').resolve())]
from intent_training.sources.codetrace import convert
from monitor_format import validate_events


def main():
    root = Path('data/downloads/codetrace')
    output = Path('data/converted/codetrace.jsonl')
    output.parent.mkdir(parents=True, exist_ok=True)
    count = events_count = hints = 0
    files = [root / 'manifest.jsonl']
    with output.open('w', encoding='utf-8') as handle:
        for events, side, meta in convert(root):
            validate_events(events)
            handle.write(json.dumps({'events': events, 'side': side, 'meta': meta}, ensure_ascii=False) + '\n')
            count += 1
            events_count += len(events)
            hints += len(side['competence_annotations'])
            files.append(root / 'trajectories' / (meta['trajectory_id'] + '.json'))
    rows = [json.loads(line) for line in (root / 'manifest.jsonl').read_text().splitlines()]
    report = {'source': 'codetrace', 'manifest_rows': len(rows), 'records': count,
              'events': events_count, 'competence_hints': hints, 'visible_monitor_positives': 0,
              'label_basis': 'T', 'skipped_missing_artifacts': sum(not (root / 'trajectories' / (r['traj_id'] + '.json')).exists() for r in rows),
              'skipped_unverified_harness': sum(r['agent'] != 'mini-SWE-agent' for r in rows),
              'skipped_step_index_mismatch': sum(r['agent'] == 'mini-SWE-agent' and (root / 'trajectories' / (r['traj_id'] + '.json')).exists() for r in rows) - count,
              'files': [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
              'errors': json.loads((root / 'fetch-errors.json').read_text()) if (root / 'fetch-errors.json').exists() else []}
    result = Path('results/sources/codetrace.json')
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in {'files', 'errors'}}))


if __name__ == '__main__':
    main()
