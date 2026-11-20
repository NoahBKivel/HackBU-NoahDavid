"""Save a bounded app-log sample for remote smoke diagnosis."""

import argparse
from pathlib import Path
import subprocess
import sys


def main() -> None:
    """Collect a short stream sample and print only its final traceback lines."""
    from kev_prepare_upload import available_memory_gib
    if available_memory_gib() <= 3.5:
        print('RAM_GATE_CLOSED', flush=True)
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("app_id")
    args = parser.parse_args()
    command = [sys.executable, "-m", "modal", "app", "logs", args.app_id, '--timestamps']
    try:
        result = subprocess.run(command, capture_output=True, timeout=8)
        raw = result.stdout + result.stderr
    except subprocess.TimeoutExpired as error:
        raw = (error.stdout or b"") + (error.stderr or b"")
    output = raw.decode("utf-8", errors="replace")
    target = Path(__file__).resolve().parents[1] / "results" / "trainer" / f"{args.app_id}-remote.log"
    target.write_text(output, encoding="utf-8")
    print("\n".join(output.splitlines()[-10:]))


if __name__ == "__main__":
    main()
