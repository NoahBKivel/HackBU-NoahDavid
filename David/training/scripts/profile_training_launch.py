"""Submit the dedicated single-GPU profile without local model imports."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


def main() -> None:
    """Preserve the live Modal call and its exact measured input configuration."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--records', required=True)
    parser.add_argument('--image-manifest', type=Path, required=True)
    parser.add_argument('--cap', type=int, required=True)
    parser.add_argument('--projection-records', type=int, required=True)
    parser.add_argument('--compare', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from kev_prepare_upload import available_memory_gib
    memory = available_memory_gib()
    if memory <= 3.5:
        raise SystemExit(f'The local RAM gate is closed: {memory:.3f} GiB.')
    root = Path(__file__).resolve().parents[1]
    os.environ['INTENT_MEASUREMENT_IMAGE_ID'] = json.loads(
        args.image_manifest.read_text(encoding='utf-8'))['image_id']
    sys.path.insert(0, str(root / 'src'))
    from intent_training.modal_app import profile_training as module
    with module.app.run(detach=True):
        call = module.profile.spawn(args.records, args.cap, args.projection_records, args.compare)
        output = root / 'results/profiling'
        output.mkdir(parents=True, exist_ok=True)
        result = {'function_call_id': call.object_id, 'app_id': module.app.app_id,
                  'image_id': module.image.object_id, 'records': args.records,
                  'cap': args.cap, 'projection_records': args.projection_records,
                  'compare': args.compare,
                  'available_memory_gib': memory,
                  'submitted_at': datetime.now(timezone.utc).isoformat()}
        (output / 'launch.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
