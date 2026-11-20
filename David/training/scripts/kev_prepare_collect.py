"""Retrieve newly committed remote preparation inputs without heavy imports."""

import argparse
import json
from pathlib import Path

from kev_prepare_upload import available_memory_gib


def main() -> None:
    """Copy the committed teacher prefix and preserve the actual function result."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='priority30')
    args = parser.parse_args()
    memory = available_memory_gib()
    import modal
    root = Path(__file__).resolve().parents[1]
    work = root / 'results' / 'remote-preparation'
    handle = json.loads((work / f'{args.name}-manifest.json').read_text(encoding='utf-8'))
    config = json.loads((root / 'environment.json').read_text(encoding='utf-8-sig'))
    volume = modal.Volume.from_name(config['modal_volume'])
    remote_prefix = handle['remote_output'].removeprefix('/training/').rstrip('/')
    output = root / 'data' / 'prepared' / Path(remote_prefix).name
    output.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in ('manifest.json', 'main.jsonl', 'native.jsonl', 'context.jsonl', 'requirements.jsonl',
                 'remote-result.json', 'formatter.stdout.log', 'formatter.stderr.log'):
        temporary = output / (name + '.download')
        try:
            with temporary.open('wb') as destination:
                for chunk in volume.read_file(remote_prefix + '/' + name):
                    destination.write(chunk)
            temporary.replace(output / name)
            copied.append(name)
        except modal.exception.NotFoundError:
            temporary.unlink(missing_ok=True)
    try:
        result = modal.FunctionCall.from_id(handle['function_call_id']).get(timeout=1)
        (work / f'{args.name}-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        status = 'FINISHED'
    except TimeoutError:
        status = 'PENDING'
    except Exception as error:
        (work / f'{args.name}-error.txt').write_text(str(error), encoding='utf-8')
        status = 'REMOTE_ERROR'
    print(json.dumps({'status': status, 'available_gib': memory,
                      'output': str(output), 'copied': copied}), flush=True)


if __name__ == '__main__':
    main()
