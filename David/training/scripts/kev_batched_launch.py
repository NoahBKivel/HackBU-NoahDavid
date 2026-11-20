"""Launch the shared batched GPU measurement and save its immutable image."""

import hashlib
import json
from pathlib import Path
import sys

from kev_prepare_upload import available_memory_gib


def main() -> None:
    """Start one detached H100 reference call after the owner memory start gate."""
    memory = available_memory_gib()
    if memory <= 3.5:
        print(json.dumps({'status': 'RAM_GATE_CLOSED', 'available_gib': memory}), flush=True)
        return
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'src'))
    for relative in ('src/intent_training/kevpatch/batched_measure.py',
                     'src/intent_training/kevpatch/unsloth_trial.py'):
        compile((root / relative).read_text(encoding='utf-8'), relative, 'exec')
    from intent_training.modal_app import trainer
    with trainer.app.run(detach=True):
        call = trainer.smoke.spawn('reference')
        result = {'status': 'SPAWNED', 'function_call_id': call.object_id,
                  'app_id': trainer.app.app_id, 'image_id': trainer.image.object_id,
                  'gpu': 'H100', 'mode': 'reference', 'max_state': 10240,
                  'b_state': 10239, 'seed': 1, 'batch': 2, 'accum': 8,
                  'available_gib_at_start': memory,
                  'config_sha256': hashlib.sha256((root / 'environment.json').read_bytes()).hexdigest(),
                  'source_sha256': {name: hashlib.sha256((root / 'src/intent_training/kevpatch' / name).read_bytes()).hexdigest()
                                    for name in ('batched_measure.py', 'unsloth_trial.py')}}
        destination = root / 'results/trainer/modal-batched-call.json'
        if destination.exists():
            previous = json.loads(destination.read_text(encoding='utf-8'))
            archived = destination.with_name(f"modal-batched-call-{previous['function_call_id']}.json")
            archived.write_text(json.dumps(previous, indent=2), encoding='utf-8')
        destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
