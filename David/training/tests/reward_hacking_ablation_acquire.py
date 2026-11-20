"""Fetch only prompt/transcript pairs for a bounded honeypot review slice."""

import concurrent.futures
import csv
import json
import math
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1] / 'data/downloads/reward_hacking_ablation'
BASE = 'https://huggingface.co/datasets/willjgriff/reward-hacking-ablation/resolve/main/'
FAMILIES = {'geoguessr': 'geoguessr_single', 'svgs': 'svgs_workshop', 'chess': 'chess_none',
            'sycophancy': 'sycophancy_all'}


def fetch(item):
    """Reuse existing pairs and retry a transient source failure once."""
    row, name = item
    family = FAMILIES.get(row['task'], row['task'])
    episode = row['episode_id'].rsplit('/', 1)[0]
    remote = f"cheatbench/{family}_cb-{row['row']}_a3eval/trajectories/{episode}/{name}"
    local = ROOT / row['row'] / row['task'] / episode / name
    local.parent.mkdir(parents=True, exist_ok=True)
    if local.exists():
        return None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(BASE + urllib.parse.quote(remote, safe='/'), timeout=30) as response:
                local.write_bytes(response.read())
            return None
        except Exception as error:
            if attempt:
                return dict(path=remote, error=type(error).__name__)
            time.sleep(1)


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    labels = ROOT / 'provisional_labels.csv'
    if not labels.exists():
        with urllib.request.urlopen(BASE + 'cheatbench/box_report/provisional_labels.csv', timeout=30) as response:
            labels.write_bytes(response.read())
    with labels.open(encoding='utf-8') as handle:
        rows = [row for row in csv.DictReader(handle) if row['cheated'] == 'true' or
                (row['cheated'] == 'false' and row['gave_up_or_degenerate'] == 'n')]
    rows = rows[:math.ceil(150 * 8600 / 10630 * 1.1)]
    (ROOT / 'selected_labels.json').write_text(json.dumps(rows), encoding='utf-8')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        errors = [result for result in pool.map(fetch, [(r, n) for r in rows for n in
                  ['prompt.txt', 'transcript.json']]) if result]
    (ROOT / 'download_errors.json').write_text(json.dumps(errors), encoding='utf-8')
    print(json.dumps(dict(selected=len(rows), failed_files=len(errors))))


if __name__ == '__main__':
    main()
