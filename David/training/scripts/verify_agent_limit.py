"""Check a fresh app server's effective agent limit without creating a thread."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import subprocess
import threading


def main() -> None:
    """Inspect only agent settings from a fresh app server configuration read."""
    parser = argparse.ArgumentParser()
    parser.add_argument("executable")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen([args.executable, "app-server", "--stdio"],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                               cwd=root)
    responses = queue.Queue()
    threading.Thread(target=lambda: [responses.put(line) for line in process.stdout], daemon=True).start()

    def send(payload: dict) -> None:
        process.stdin.write(json.dumps(payload) + "\n")
        process.stdin.flush()

    def receive(identifier: int) -> dict:
        while True:
            line = responses.get(timeout=30)
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") == identifier:
                if "error" in message:
                    raise RuntimeError(str(message["error"].get("code")))
                return message["result"]

    try:
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "agent_limit_verification", "version": "1"},
            "capabilities": {"experimentalApi": True}}})
        receive(1)
        send({"method": "initialized", "params": {}})
        send({"id": 2, "method": "config/read", "params": {"cwd": str(root), "includeLayers": True}})
        result = receive(2)
        config = result.get("config", {})
        agents = config.get("agents") or {}
        layers = [{"name": item.get("name"), "agent_settings": item.get("config", {}).get("agents")}
                  for item in result.get("layers", []) if item.get("config", {}).get("agents")]
        output = {"checked_at": datetime.now(timezone.utc).isoformat(),
                  "fresh_app_server": True, "effective_agents": agents,
                  "agent_config_layers": layers,
                  "pass": agents.get("max_concurrent_threads_per_session") == 100}
        (root / "results" / "agent-limit-verification.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(json.dumps(output))
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == "__main__":
    main()
