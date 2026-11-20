"""Launch a frozen continuation run and preserve its detached remote identity."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys


def main() -> None:
    """Submit one explicitly named frozen artifact to the production trainer."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--records', type=int, required=True)
    parser.add_argument('--pass-tokens', type=int, required=True)
    parser.add_argument('--out')
    parser.add_argument('--rerun', action='store_true')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from kev_prepare_upload import available_memory_gib
    memory = available_memory_gib()
    if memory <= 3.5:
        print(json.dumps({'status': 'RAM_GATE_CLOSED', 'available_gib': memory}), flush=True)
        return
    if not re.fullmatch('[0-9a-fA-F]{64}', args.sha256):
        raise ValueError('The frozen artifact requires its complete SHA256 digest.')
    if args.records < 1 or args.pass_tokens < 1:
        raise ValueError('The frozen record count and measured pass cap must be positive.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = args.out or f'/training/runs/{stamp}'
    if any(not PurePosixPath(path).is_relative_to('/training') or '..' in PurePosixPath(path).parts
           for path in (args.data, out)):
        raise ValueError('Training input and output must remain on the private training volume.')
    root = Path(__file__).resolve().parents[1]
    directory = root / 'results' / 'trainer'
    directory.mkdir(parents=True, exist_ok=True)
    latest = directory / 'training-call.json'
    if latest.exists() and not args.rerun:
        previous = json.loads(latest.read_text(encoding='utf-8'))
        if (previous['data_sha256'] != args.sha256.lower() or previous['records'] != args.records
                or previous['pass_tokens_max'] != args.pass_tokens):
            raise ValueError('An existing call names different training inputs; inspect it before starting a new run.')
        print(json.dumps(previous), flush=True)
        return
    os.environ['INTENT_TRAINING_GPU'] = 'B200'
    sys.path.insert(0, str(root / 'src'))
    from intent_training.modal_app import trainer
    with trainer.app.run(detach=True):
        result = {'status': 'SUBMITTING', 'submitted_at': datetime.now(timezone.utc).isoformat(),
                  'app_id': trainer.app.app_id, 'image_id': trainer.image.object_id,
                  'data': args.data, 'data_sha256': args.sha256.lower(), 'records': args.records,
                  'out': out, 'pass_tokens_max': args.pass_tokens,
                  'checkpointing': 1, 'resume': False, 'available_gib_at_start': memory}
        target = directory / f'training-call-{stamp}.json'
        target.write_text(json.dumps(result, indent=2), encoding='utf-8')
        latest.write_text(json.dumps(result, indent=2), encoding='utf-8')
        call = trainer.train.spawn(args.data, out, args.pass_tokens, resume=False,
                                    checkpointing=True, expected_sha256=args.sha256.lower(),
                                    expected_records=args.records)
        result.update(status='SPAWNED', function_call_id=call.object_id)
        target.write_text(json.dumps(result, indent=2), encoding='utf-8')
        latest.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
