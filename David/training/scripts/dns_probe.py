"""Compare host and container service reachability without exposing credentials."""

import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import subprocess
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlopen


def harbor_endpoint(package: Path) -> str:
    """Read only the installed package's public default API endpoint."""
    tree = ast.parse((package / "auth" / "constants.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                                               and target.id == "DEFAULT_SUPABASE_URL" for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError("The installed package does not declare its default API endpoint.")


def reachability(url: str) -> dict:
    """Record DNS and HTTPS results without recording response bodies or headers."""
    host = urlparse(url).hostname
    result = {"host": host}
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        result["resolved_addresses"] = len({entry[4][0] for entry in addresses})
    except OSError as exc:
        result.update(dns="FAIL", error_type=type(exc).__name__, error_code=exc.errno)
        return result
    result["dns"] = "PASS"
    try:
        with urlopen(url, timeout=20) as response:
            result.update(https="PASS", status=response.status)
    except HTTPError as exc:
        result.update(https="PASS", status=exc.code)
    except OSError as exc:
        result.update(https="FAIL", error_type=type(exc).__name__)
    return result


def main() -> None:
    """Save bounded credential-free probes of the actual service endpoints."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--harbor-package", required=True, type=Path)
    args = parser.parse_args()
    api = harbor_endpoint(args.harbor_package)
    result = {"time": datetime.now(timezone.utc).isoformat(),
              "host": [reachability("https://registry-1.docker.io/v2/"), reachability(api + "/rest/v1/")]}
    call = subprocess.run(["harbor", "hub", "job", "list", "--scope", "all", "--search", "hvtb",
                           "--limit", "3", "--json"], capture_output=True, text=True, timeout=60)
    authenticated = {"returncode": call.returncode, "stdout_bytes": len(call.stdout),
                     "stderr_bytes": len(call.stderr)}
    if call.returncode == 0:
        try:
            payload = json.loads(call.stdout)
            authenticated["json_type"] = type(payload).__name__
            authenticated["items_or_fields"] = len(payload)
        except json.JSONDecodeError:
            authenticated["json_valid"] = False
    else:
        authenticated["dns_error"] = any(word in call.stderr for word in ("getaddrinfo", "11001", "ENOTFOUND"))
        authenticated["auth_error"] = any(word in call.stderr.lower() for word in ("unauthorized", "401", "403"))
    result["authenticated_harbor"] = authenticated
    destination = Path(__file__).resolve().parents[1] / "results" / "dns-host.json"
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
