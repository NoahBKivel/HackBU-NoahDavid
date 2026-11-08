"""Call the deployed class with the backend's spawn and eight-second wait."""

import argparse
import json
import sys
import time
from pathlib import Path

import modal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_deploy import check


class Driver:
    def __init__(self, target: str):
        self.app = "intent-monitor-dev" if target == "dev" else "intent-monitor"
        self.classifier = modal.Cls.from_name(self.app, "Classifier")()
        self.pending = []

    def warmup(self) -> dict:
        """Boot and verify the shared model container before sending timed events."""
        result = self.classifier.warmup.spawn().get(timeout=180)
        if result != {"ok": True}:
            raise AssertionError("Warmup returned an invalid result.")
        return result

    def spawn(self, event: dict):
        """Stamp a fresh backend timestamp immediately before spawning classification."""
        sent = {**event, "backend_sent_at": time.time()}
        return sent, self.classifier.classify.spawn(sent)

    def receive(self, event: dict, call) -> dict:
        """Validate a response or retain a pending call without canceling it."""
        try:
            result = call.get(timeout=8)
        except (TimeoutError, modal.exception.TimeoutError):
            self.pending.append((event, call))
            return {"event_id": event["event_id"], "pending": True}
        check(result, event)
        return result

    def send(self, event: dict) -> dict:
        """Send one event exactly as the backend does."""
        return self.receive(*self.spawn(event))


def main() -> int:
    """Run a JSON event stream through the selected deployed class."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("dev", "live"), default="dev")
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    driver = Driver(args.target)
    driver.warmup()
    events = json.loads(args.events.read_text(encoding="utf-8"))
    results = [driver.send(event) for event in events]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Validated stream responses from {driver.app}; pending calls: {len(driver.pending)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
