"""Check text files without disclosing matched credentials."""

import argparse
from pathlib import Path
import re
import subprocess
import sys

PATTERNS = (
    r"sk-ant-[A-Za-z0-9_-]{20,}",
    r"sk-(?:svcacct|proj)-[A-Za-z0-9_-]{20,}",
    r"CLAUDE_CODE_OAUTH_TOKEN\s*=\s*['\"]?[A-Za-z0-9_-]{8,}",
    r"ghp_[A-Za-z0-9]{36}",
    r"github_pat_[A-Za-z0-9_]{22,}",
    r"AKIA[0-9A-Z]{16}",
    r"hf_[A-Za-z0-9]{34}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\.jwt_secret\s*[:=]\s*['\"]?[A-Za-z0-9_/-]{8,}",
)


def main() -> int:
    """Report only file names and pattern indices when credentials are found."""
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    git = ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root)]
    paths = args.paths
    if args.staged:
        paths = subprocess.check_output(git + ["diff", "--cached", "--name-only", "--diff-filter=ACM"], text=True).splitlines()
    findings = []
    for name in paths:
        raw = (subprocess.check_output(git + ["show", f":{name}"])
               if args.staged else Path(name).read_bytes())
        if b"\x00" in raw:
            continue
        content = raw.decode("utf-8", errors="replace")
        findings.extend((name, i) for i, pattern in enumerate(PATTERNS, 1) if re.search(pattern, content))
    for name, index in findings:
        print(f"FAIL {name}: credential pattern {index}")
    print(f"Scanned {len(paths)} files; credential findings={len(findings)}")
    return int(bool(findings))


if __name__ == "__main__":
    sys.exit(main())
