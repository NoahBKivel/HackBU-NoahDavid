"""Validate durable generation requests and preserve response envelopes."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import os
import urllib.request
import urllib.error
import time
from uuid import uuid4
from typing import Any


def credential_markers(root: Path, text: str) -> bool:
    """Apply the repository scanner before transmitting any request text."""
    specification = importlib.util.spec_from_file_location("generation_secret_patterns", root / "scripts/scan_secrets.py")
    scanner = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(scanner)
    return any(re.search(pattern, text) for pattern in scanner.PATTERNS)


class DirectMessages:
    """Use a request-local direct opener for the authorized provider endpoint."""

    def __init__(self):
        self.messages = self
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def create(self, **body):
        """Parse the official Messages response through the installed SDK schema."""
        from anthropic.types import Message
        request = urllib.request.Request("https://api.anthropic.com/v1/messages",
                                         data=json.dumps(body).encode("utf-8"),
                                         headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                                                  "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            timeout = float(os.environ.get("ANTHROPIC_GENERATION_TIMEOUT_SECONDS", "120"))
            if not 1 <= timeout <= 1200:
                raise ValueError("The generation timeout is outside its supported range.")
            with self.opener.open(request, timeout=timeout) as response:
                return Message.model_validate(json.load(response))
        except urllib.error.HTTPError as error:
            sanitized = RuntimeError("The provider rejected the request.")
            sanitized.status_code = error.code
            raise sanitized from None
        except urllib.error.URLError as error:
            sanitized = ConnectionError("The provider connection failed.")
            sanitized.connection_errno = getattr(error.reason, "errno", None)
            sanitized.preconnection_dns_failure = isinstance(error.reason, OSError) and getattr(error.reason, "errno", None) in (11001, -2, -3)
            raise sanitized from None


def atomic_json(path: Path, value: Any) -> None:
    """Replace one JSON document without exposing a partial write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        for attempt in range(20):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(.05)
    finally:
        temporary.unlink(missing_ok=True)


def fingerprint(request: dict) -> str:
    """Identify the complete request so reused identifiers cannot silently drift."""
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_requests(root: Path, sources: list[str] | None = None) -> list[dict]:
    """Deduplicate equal requests and reject conflicting identifiers."""
    found = {}
    for path in sorted((root / "data/generation/requests").glob("*.jsonl")):
        if sources and path.stem not in sources:
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            identifier = item.get("id", "")
            if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", identifier):
                raise ValueError("A generation request has an unsafe identifier.")
            if not isinstance(item.get("prompt"), str) or not item["prompt"].strip():
                raise ValueError("A generation request needs a nonempty prompt.")
            if not isinstance(item.get("purpose"), str) or not item["purpose"]:
                raise ValueError("A generation request needs a purpose.")
            maximum = item.get("max_output_tokens")
            if type(maximum) is not int or not 1 <= maximum <= 128000:
                raise ValueError("A generation request has an invalid output limit.")
            if identifier in found and fingerprint(found[identifier]) != fingerprint(item):
                raise ValueError("Generation request identifiers conflict.")
            found[identifier] = item
    return list(found.values())
