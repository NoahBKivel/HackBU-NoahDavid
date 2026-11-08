"""Launch one isolated B200 cast-cache experiment on the pinned image."""

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
         .add_local_dir(ROOT / 'src/intent_training/kevpatch',
                        '/opt/intent-training/src/intent_training/kevpatch', copy=True)
         if modal.is_local() else modal.Image.debian_slim())


@app.function(image=image, gpu='B200', cpu=8, memory=98304,
              timeout=1200, startup_timeout=600, volumes={'/training': volume})
def trial(records: str, cap: int) -> dict:
    from intent_training.kevpatch.frozen_linear_trial import compare
    volume.reload()
    output = '/training/cast-cache/' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    return compare(records, output, CONFIG, cap, volume)


@app.local_entrypoint()
def main(records: str, cap: int = 46080) -> None:
    call = trial.spawn(records, cap)
    output = ROOT / 'results/cast-cache'
    output.mkdir(parents=True, exist_ok=True)
    handle = {'function_call_id': call.object_id, 'app_id': app.app_id,
              'image_id': image.object_id, 'records': records, 'cap': cap}
    (output / 'launch.json').write_text(json.dumps(handle, indent=2))
    print(json.dumps(handle), flush=True)
