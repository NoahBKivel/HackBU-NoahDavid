"""Send sample events to the backend and print what comes back.

Usage (from the repo root):
  .venv\\Scripts\\python Noah/backend/send_event.py                  all samples, deployed URL
  .venv\\Scripts\\python Noah/backend/send_event.py 3                samples whose name starts with 3
  .venv\\Scripts\\python Noah/backend/send_event.py --dev            use the `modal serve` URL
  .venv\\Scripts\\python Noah/backend/send_event.py 2 --pad-mb 5     add ~5 MB of filler to test size limits

The token is read from Noah/backend/secrets.local.json (gitignored).
The samples in Noah/backend/samples/ are hand-written to match the Mod's
event format (CONTRACT.md section 3); they are not recorded agent output.
"""

import argparse
import json
import pathlib
import ssl
import time
import urllib.error
import urllib.request

import certifi

HERE = pathlib.Path(__file__).parent
URL = "https://davidkny22--alignment-monitor-api.us-east.modal.run"
DEV_URL = "https://davidkny22--alignment-monitor-api-dev.us-east.modal.run"


def send(url: str, token: str, event: dict) -> None:
    body = json.dumps(event).encode()
    request = urllib.request.Request(
        f"{url}/v1/events",
        data=body,
        headers={"authorization": f"Bearer {token}", "content-type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        # certifi's bundle: Python's default Windows store rejected Modal's certificate.
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(request, timeout=120, context=context) as response:
            status, text = response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        status, text = exc.code, exc.read().decode()
    ms = int((time.monotonic() - started) * 1000)
    print(f"--- {event['event_id']} ({event['type']}), {len(body) / 1e6:.2f} MB -> HTTP {status} in {ms} ms")
    try:
        result = json.loads(text)
        print(json.dumps(
            {k: result[k] for k in ("flagged", "risk", "drift", "drift_rate", "pending", "details", "actions", "late_results") if k in result}
            if status == 200 else result,
            indent=2,
        ))
    except json.JSONDecodeError:
        print(text[:500])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", nargs="?", default="", help="only send samples whose file name starts with this")
    parser.add_argument("--dev", action="store_true", help="send to the modal serve URL")
    parser.add_argument("--url", help="send to this base URL instead")
    parser.add_argument("--pad-mb", type=float, default=0, help="add this many MB of filler text to each event")
    args = parser.parse_args()

    token = json.loads((HERE / "secrets.local.json").read_text())["MONITOR_TOKEN"]
    url = args.url or (DEV_URL if args.dev else URL)
    for path in sorted((HERE / "samples").glob(f"{args.prefix}*.json")):
        event = json.loads(path.read_text())
        if args.pad_mb:
            event["padding"] = "x" * int(args.pad_mb * 1_000_000)
        send(url, token, event)


if __name__ == "__main__":
    main()
