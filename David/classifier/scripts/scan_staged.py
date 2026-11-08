"""Reject credentials in staged text without printing matching values."""

import re
import subprocess
from pathlib import Path


def scan() -> int:
    """Return a nonzero exit status if staged text contains a credential."""
    root = Path(__file__).resolve().parents[3]
    command = ["git", "-c", f"safe.directory={root.as_posix()}"]
    names = subprocess.check_output(command + ["diff", "--cached", "--name-only", "--diff-filter=ACM"], cwd=root).decode().splitlines()
    patterns = [r"sk-(?:ant|svcacct|proj)-[A-Za-z0-9_-]{12,}",
                r"ghp_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}",
                r"AKIA[A-Z0-9]{16}", r"hf_[A-Za-z0-9]{20,}",
                r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
                r"CLAUDE_CODE_OAUTH_TOKEN\s*=\s*[^\s\"']{8,}"]
    findings = []
    for name in names:
        data = subprocess.check_output(command + ["show", f":{name}"], cwd=root)
        if b"\0" in data:
            continue
        text = data.decode("utf-8", errors="replace")
        if any(re.search(pattern, text) for pattern in patterns):
            findings.append(name)
    print(f"Scanned {len(names)} staged files. Credential findings: {len(findings)}.")
    for name in findings:
        print(f"Credential pattern found in {name}.")
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(scan())
