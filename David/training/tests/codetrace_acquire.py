"""Fetch inert JSON trajectory snapshots in manifest order."""

import concurrent.futures
import io
import itertools
import json
import re
from pathlib import Path
import urllib.request
import sys
import tarfile
import zstandard


def main():
    root = Path('data/downloads/codetrace')
    sys.path.insert(0, str(Path('src').resolve()))
    from intent_training.sources.terminal_bench_science import direct_opener
    opener = direct_opener()
    if (root / 'manifest-full.jsonl').exists():
        rows = [json.loads(line) for line in (root / 'manifest-full.jsonl').read_text().splitlines()]
    else:
        with opener.open('https://huggingface.co/datasets/NJU-LINK/CodeTraceBench/resolve/main/bench_manifest.full.jsonl', timeout=45) as response:
            rows = [json.loads(line) for line in itertools.islice(response, 165)]
    (root / 'manifest.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
    previous = json.loads((root / 'fetch-errors.json').read_text()) if (root / 'fetch-errors.json').exists() else []
    missing_payloads = {error['trajectory_id'] for error in previous if error['error'] == 'ValueError'}

    def fetch(row):
        target = root / 'trajectories' / (row['traj_id'] + '.json')
        if row['traj_id'] in missing_payloads:
            return
        if target.exists() and 'messages' in json.loads(target.read_text()):
            return
        if row['agent'] == 'mini-SWE-agent' and not row['source_relpath'].startswith('swe_raw/'):
            with opener.open('https://huggingface.co/datasets/NJU-LINK/CodeTraceBench/resolve/main/' + row['artifact_path'], timeout=45) as response:
                compressed = response.read()
            stream = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(compressed))
            with tarfile.open(fileobj=stream, mode='r|') as archive:
                for member in archive:
                    if member.isfile() and member.name.endswith('mini.traj.json'):
                        raw = archive.extractfile(member).read()
                        json.loads(raw)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(raw)
                        return
            raise ValueError('The archive contains no mini trajectory JSON.')
        listing = json.load(opener.open('https://huggingface.co/api/datasets/NJU-LINK/CodeTraceBench/tree/main/' + row['source_relpath'], timeout=30))
        candidates = [item for item in listing if item['type'] == 'file' and item['path'].endswith('.json') and not item['path'].endswith('/report.json')]
        if row['agent'] == 'mini-SWE-agent':
            candidates = [item for item in candidates if item['path'].endswith('.traj.json')]
        else:
            candidates = [item for item in candidates if re.search(r'-\d+\.\d+\.json$', item['path'])]
        # OpenHands stores cumulative message snapshots. The greatest timestamp is the full stream.
        chosen = sorted(candidates, key=lambda item: item['path'])[-1]
        raw = opener.open('https://huggingface.co/datasets/NJU-LINK/CodeTraceBench/raw/main/' + chosen['path'], timeout=40).read()
        json.loads(raw)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    errors = [error for error in previous if error['trajectory_id'] in missing_payloads]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, row): row for row in rows}
        for future, row in futures.items():
            try:
                future.result()
            except Exception as error:
                errors.append({'trajectory_id': row['traj_id'], 'error': type(error).__name__})
    (root / 'fetch-errors.json').write_text(json.dumps(errors), encoding='utf-8')
    print(json.dumps({'selected_artifacts_available': sum((root / 'trajectories' / (row['traj_id'] + '.json')).exists() for row in rows), 'errors': len(errors)}))


if __name__ == '__main__':
    main()
