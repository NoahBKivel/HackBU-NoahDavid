"""Start paired checkpointing measurements of the actual prepared mixture."""

from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import sys

from kev_prepare_upload import available_memory_gib


def main() -> None:
    """Submit two independent B200 calls after the owner resource gate."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepared-root', default='/training/prepared/timing-sample-8191')
    parser.add_argument('--preparation-call')
    parser.add_argument('--on-only', action='store_true')
    parser.add_argument('--result-name', default='retime-calls')
    args = parser.parse_args()
    memory = available_memory_gib()
    if memory <= 3.5:
        print(json.dumps({'status': 'RAM_GATE_CLOSED', 'available_gib': memory}), flush=True)
        return
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'src'))
    source = root / 'src/intent_training/modal_app/retime.py'
    compile(source.read_text(), str(source), 'exec')
    from intent_training.modal_app import retime as module
    preparation_call = args.preparation_call
    if not preparation_call:
        prepared = json.loads((root / 'results/remote-preparation/timing-sample-48-8191-manifest.json').read_text())
        preparation_call = prepared['function_call_id']
    evidence = root / 'results/b200-check/batched/reference' / os.environ['INTENT_MEASUREMENT_IMAGE_ID'] / 'call-result.json'
    pass_tokens = int(json.loads(evidence.read_text())['pass_tokens_max'])
    with module.app.run(detach=True):
        result = {'image_id': module.image.object_id, 'app_id': module.app.app_id,
                  'available_gib_at_start': memory, 'calls': {}}
        for checkpointing in ((1,) if args.on_only else (1, 0)):
            submitted = datetime.now(timezone.utc).isoformat()
            call = module.retime.spawn(args.prepared_root, pass_tokens,
                                       submitted, checkpointing, preparation_call)
            result['calls'][str(checkpointing)] = {'function_call_id': call.object_id,
                                                  'submitted_at': submitted}
        destination = root / f'results/trainer/{args.result_name}.json'
        destination.write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
