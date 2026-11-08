"""Render preference inputs on the private training volume."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import modal

ROOT = Path(__file__).resolve().parents[1] if modal.is_local() else Path('/opt/intent-training')
sys.path.insert(0, str(ROOT / 'scripts'))
from scan_secrets import PATTERNS

config = json.loads((ROOT / 'environment.json').read_text(encoding='utf-8-sig'))
volume = modal.Volume.from_name(config['modal_volume'])
app = modal.App(config['modal_app'])
image = (modal.Image.from_id('im-dfB2QMo1vkk6QHDRHLgbVJ')
         .add_local_dir(ROOT / 'src', '/opt/intent-training/src', copy=True, ignore=['**/__pycache__/**', '**/*.pyc'])
         .add_local_dir(ROOT.parent / 'monitor_format', '/opt/monitor_format', copy=True, ignore=['**/__pycache__/**', '**/*.pyc'])
         .add_local_file(ROOT / 'scripts/prepare_heldout_preferences.py', '/opt/intent-training/scripts/prepare_heldout_preferences.py', copy=True))


@app.function(image=image, cpu=2, memory=8192, timeout=3600, volumes={'/training': volume})
def run(work):
    volume.reload()
    base = Path('/training') / work
    output = base / 'preferences.jsonl'
    subprocess.run([sys.executable, '/opt/intent-training/scripts/prepare_heldout_preferences.py',
                    '--llmbar', str(base / 'llmbar'), '--rewardbench2', str(base / 'rewardbench2.parquet'),
                    '--tokenizer', str(base / 'tokenizer.json'), '--output', str(output)],
                   env={**os.environ, 'PYTHONPATH': '/opt/intent-training/src:/opt'}, check=True)
    digest = hashlib.sha256()
    count = 0
    with output.open('rb') as stream:
        for line in stream:
            digest.update(line)
            count += 1
    volume.commit()
    return {'path': str(output), 'records': count, 'sha256': digest.hexdigest()}


def main():
    files = list((ROOT / 'data/downloads/llmbar').glob('*.json'))
    reward = ROOT / 'data/downloads/rewardbench2/test.parquet'
    tokenizer = ROOT / 'data/tokenizer/tokenizer.json'
    patterns = [re.compile(pattern) for pattern in PATTERNS]
    for path in files + [reward, tokenizer]:
        # Scan decoded source text where possible; binary parquet is scanned after extraction below.
        if path.suffix == '.json' and any(p.search(path.read_text(encoding='utf-8-sig')) for p in patterns):
            raise ValueError('Credential pattern found in source input.')
    import pyarrow.parquet as pq
    for batch in pq.ParquetFile(reward).iter_batches(batch_size=32):
        text = json.dumps(batch.to_pylist(), ensure_ascii=False)
        if any(p.search(text) for p in patterns):
            raise ValueError('Credential pattern found in source input.')
    work = 'heldout/preferences-' + hashlib.sha256(reward.read_bytes()).hexdigest()[:16]
    with volume.batch_upload(force=True) as upload:
        for path in files:
            upload.put_file(path, work + '/llmbar/' + path.name)
        upload.put_file(reward, work + '/rewardbench2.parquet')
        upload.put_file(tokenizer, work + '/tokenizer.json')
    with app.run():
        print(json.dumps(run.remote(work)), flush=True)


if __name__ == '__main__':
    main()
