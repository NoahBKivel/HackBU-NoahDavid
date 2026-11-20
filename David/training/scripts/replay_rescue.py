"""Retrieve public native train artifacts with hashes, locally or on Modal CPU."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

FILES = ('v7/decision-v7/train.jsonl', 'hard-v1/train.jsonl')


def retrieve(destination, opener=None):
    destination = Path(destination)
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
    manifest = []
    for name in FILES:
        url = 'https://huggingface.co/datasets/jaredpalmer/kev-suites/resolve/main/' + name
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url)
        with opener.open(request, timeout=90) as response:
            payload = response.read()
        rows = [json.loads(line) for line in payload.splitlines() if line.strip()]
        if not rows or any(not isinstance(r, dict) or 'questions' not in r for r in rows):
            raise ValueError('The train artifact is not native record data.')
        path.write_bytes(payload)
        item = dict(path=name, url=url, sha256=hashlib.sha256(payload).hexdigest(),
                    bytes=len(payload), records=len(rows), suite_split='train')
        manifest.append(item)
        print(json.dumps(item), flush=True)
    (destination / 'recovery-manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--modal', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = root / 'data/downloads/kev_replay'
    if args.modal:
        import modal
        app = modal.App('intent-monitor-training')
        volume = modal.Volume.from_name('intent-monitor-training')
        image = modal.Image.debian_slim(python_version='3.12')

        @app.function(image=image, cpu=1, timeout=600, serialized=True, volumes={'/training': volume})
        def fetch():
            import gzip
            target = Path('/training/downloads/kev_replay')
            manifest = retrieve(target)
            volume.commit()
            return manifest, {name: gzip.compress((target / name).read_bytes()) for name in FILES}

        with app.run():
            manifest, artifacts = fetch.remote()
        import gzip
        for name, compressed in artifacts.items():
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.decompress(compressed))
        (destination / 'recovery-manifest.json').write_text(json.dumps(manifest, indent=2))
    else:
        import sys
        sys.path.insert(0, str(root / 'src'))
        from intent_training.sources.terminal_bench_science import direct_opener
        retrieve(destination, direct_opener())


if __name__ == '__main__':
    main()
