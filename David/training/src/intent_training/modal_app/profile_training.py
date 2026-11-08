"""Profile the decision trainer on one dedicated B200."""

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
              timeout=1800, startup_timeout=600, volumes={'/training': volume})
def profile(records: str, cap: int, projection_records: int, compare: bool = False,
            prior_output: str = '', native_only: bool = False, native_results: str = '') -> dict:
    """Profile a real prepared mixture and compare checkpointing at the measured cap."""
    from intent_training.kevpatch.profile_training import run_profile
    from intent_training.kevpatch.profile_compare import compare as compare_paths
    volume.reload()
    output = '/training/profiling/' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if compare:
        return compare_paths(records, output, CONFIG, cap, projection_records, volume,
                             prior_output, native_only, native_results)
    return run_profile(records, output, CONFIG, cap, projection_records, volume)


@app.local_entrypoint()
def main(records: str, cap: int, projection_records: int) -> None:
    """Launch detached profiling and persist its remotely recoverable handle."""
    call = profile.spawn(records, cap, projection_records)
    destination = ROOT / 'results/profiling'
    destination.mkdir(parents=True, exist_ok=True)
    result = {'function_call_id': call.object_id, 'app_id': app.app_id,
              'image_id': image.object_id, 'records': records, 'cap': cap,
              'projection_records': projection_records, 'submitted_at': datetime.now(timezone.utc).isoformat()}
    (destination / 'launch.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
