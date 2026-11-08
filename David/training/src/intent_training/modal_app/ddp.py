"""Run replicated decision-model parity and training on four GPUs."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[3] if modal.is_local() else Path('/opt/intent-training')
CONFIG = json.loads((ROOT / 'environment.json').read_text(encoding='utf-8-sig'))
app = modal.App(CONFIG['modal_app'])
volume = modal.Volume.from_name(CONFIG['modal_volume'])
image = (modal.Image.from_id(os.environ['INTENT_MEASUREMENT_IMAGE_ID'])
         .add_local_file(ROOT / 'src/intent_training/kevpatch/distributed_ddp.py',
                         '/opt/intent-training/src/intent_training/kevpatch/distributed_ddp.py', copy=True)
         .env({'OMP_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2', 'TOKENIZERS_PARALLELISM': 'false'})
         if modal.is_local() else modal.Image.debian_slim())


@app.function(image=image, gpu='B200:4', cpu=16, memory=196608,
              timeout=7200, startup_timeout=1200, volumes={'/training': volume})
def parity(data: str, cap: int, steps: int = 3) -> dict:
    """Compare identical serial shard passes and four-rank global optimizer steps."""
    import subprocess
    import sys
    volume.reload()
    root = Path('/training/ddp') / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    root.mkdir(parents=True)
    common = ['-m', 'intent_training.kevpatch.distributed_ddp', '--data', data,
              '--config', '/opt/intent-training/environment.json', '--cap', str(cap),
              '--steps', str(steps), '--limit', '16', '--partition-world', '4']
    for mode in ('reference', 'distributed'):
        command = ([sys.executable] if mode == 'reference' else
                   [sys.executable, '-m', 'torch.distributed.run', '--standalone', '--nproc_per_node', '4'])
        command += common + ['--mode', mode, '--out', str(root / mode)]
        with (root / f'{mode}.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
        volume.commit()
        print(json.dumps({'phase': mode, 'returncode': result.returncode, 'path': str(root)}), flush=True)
        if result.returncode:
            return {'status': 'FAIL', 'phase': mode, 'returncode': result.returncode, 'path': str(root)}
    import torch
    reference = json.loads((root / 'reference/result.json').read_text())
    parallel = json.loads((root / 'distributed/result.json').read_text())
    differences = [abs(left['loss'] - right['loss']) / max(abs(left['loss']), 1e-12)
                   for left, right in zip(reference['steps'], parallel['steps'])]
    left = torch.load(root / 'reference/first-gradient.pt', map_location='cpu', weights_only=True)
    right = torch.load(root / 'distributed/first-gradient.pt', map_location='cpu', weights_only=True)
    gradient_relative = float(torch.linalg.vector_norm(left - right) / torch.linalg.vector_norm(left).clamp_min(1e-12))
    result = {'status': 'PASS' if max(differences) <= 1e-3 and gradient_relative <= 1e-2 else 'FAIL',
              'path': str(root), 'maximum_relative_loss_difference': max(differences),
              'first_gradient_relative_l2': gradient_relative,
              'reference': reference, 'distributed': parallel}
    (root / 'result.json').write_text(json.dumps(result, indent=2))
    volume.commit()
    print(json.dumps({'status': result['status'], 'path': str(root),
                      'loss_difference': max(differences), 'gradient_difference': gradient_relative}), flush=True)
    return result


@app.function(image=image, gpu='B200:4', cpu=16, memory=196608,
              timeout=14400, startup_timeout=1200, volumes={'/training': volume})
def train(data: str, out: str, cap: int) -> dict:
    """Run one globally batched epoch with rank-zero persistent snapshots."""
    import subprocess
    import sys
    volume.reload()
    command = [sys.executable, '-m', 'torch.distributed.run', '--standalone', '--nproc_per_node', '4',
               '-m', 'intent_training.kevpatch.distributed_ddp', '--mode', 'train', '--data', data,
               '--out', out, '--config', '/opt/intent-training/environment.json', '--cap', str(cap)]
    result = subprocess.run(command, check=False)
    volume.commit()
    return {'returncode': result.returncode, 'out': out}


@app.local_entrypoint()
def main(data: str, cap: int, steps: int = 3) -> None:
    """Launch the detached parity run and preserve its handle."""
    call = parity.spawn(data, cap, steps)
    result = {'app_id': app.app_id, 'function_call_id': call.object_id, 'image_id': image.object_id}
    target = ROOT / 'results/trainer/ddp-call.json'
    target.write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
