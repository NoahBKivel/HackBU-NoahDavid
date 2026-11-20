"""Resolve and render the registered non-TRACE intent-probe inputs."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT.parent)]
from intent_training.splits.heldout_probes import probe_sources, render_probe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--downloads', type=Path, required=True)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(args.tokenizer))
    class Adapter:
        def __call__(self, text, add_special_tokens=False):
            return SimpleNamespace(input_ids=tokenizer.encode(text, add_special_tokens=add_special_tokens).ids)
    manifest = [json.loads(line) for line in args.manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
    counts = Counter()
    digest = hashlib.sha256()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as output:
        for source in probe_sources(manifest, args.downloads):
            payload = (json.dumps(render_probe(source, Adapter()), ensure_ascii=False) + '\n').encode('utf-8')
            output.write(payload)
            digest.update(payload)
            counts[source['intent_kind']] += 1
    print(json.dumps({'counts': counts, 'sha256': digest.hexdigest()}))


if __name__ == '__main__':
    main()
