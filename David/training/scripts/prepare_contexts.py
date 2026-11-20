"""Launch private CPU context projections from existing prepared namespaces."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    """Start independent projection jobs with no new dataset transfer."""
    parser = argparse.ArgumentParser()
    parser.add_argument("namespaces", nargs="+")
    args = parser.parse_args()
    from intent_training.modal_app import context_remote as module
    with module.app.run(detach=True):
        for namespace in args.namespaces:
            call = module.project.spawn(namespace)
            manifest = {"namespace": namespace, "app_id": module.app.app_id,
                "function_call_id": call.object_id,
                "remote_output": "/training/prepared/context-projections/" + namespace,
                "dataset_bytes_uploaded": 0}
            destination = ROOT / "results/remote-preparation" / ("context-" + namespace + "-manifest.json")
            destination.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
