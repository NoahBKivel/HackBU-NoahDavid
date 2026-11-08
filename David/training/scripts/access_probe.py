"""Probe authorized services and persist only credential-free evidence."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request


def request_json(url: str, headers: dict[str, str]) -> dict:
    """Read one JSON response using the supplied in-memory authorization."""
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
        return json.load(response)


def probe_hf(repo: str, root: Path) -> dict:
    """Verify access to a dataset file without printing any contents."""
    headers = {"Authorization": "Bearer " + os.environ["HF_TOKEN"]}
    try:
        metadata = request_json("https://huggingface.co/api/datasets/" + repo, headers)
        folder = root / "data" / "downloads" / repo.replace("/", "--")
        folder.mkdir(parents=True, exist_ok=True)
        files = [item["rfilename"] for item in metadata.get("siblings", [])]
        (folder / "repository-files.json").write_text(json.dumps(files, indent=2), encoding="utf-8")
        candidates = [name for name in files if name.endswith((".parquet", ".jsonl", ".json", ".csv"))
                      and name != "dataset_infos.json"]
        if not candidates:
            return {"repo": repo, "status": "no-data-file", "files": len(files)}
        name = candidates[0]
        file_headers = {**headers, "Range": "bytes=0-0"}
        url = f"https://huggingface.co/datasets/{repo}/resolve/main/{name}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=file_headers), timeout=60) as response:
            count = len(response.read(1))
            status = response.status
        return {"repo": repo, "status": "PASS", "http_status": status,
                "read_bytes": count, "file": name, "files": len(files)}
    except urllib.error.HTTPError as exc:
        return {"repo": repo, "status": "FAIL", "http_status": exc.code}
    except Exception as exc:
        return {"repo": repo, "status": "FAIL", "error_type": type(exc).__name__}


def probe_claude(root: Path) -> dict:
    """Make a single bounded CLI call authenticated exclusively by the API key."""
    result = subprocess.run(
        ["claude", "-p", "Reply with OK only.", "--bare", "--model", "claude-haiku-5-5",
         "--tools", "", "--max-turns", "1", "--max-budget-usd", "0.05", "--output-format", "json"],
        capture_output=True, text=True, timeout=120,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"service": "claude", "status": "FAIL", "exit_code": result.returncode,
                "stdout_bytes": len(result.stdout), "stderr_bytes": len(result.stderr)}
    cost = payload.get("total_cost_usd")
    ledger = {"job": "access-probe", "time": datetime.now(timezone.utc).isoformat(),
              "model": "claude-haiku-5-5", "cost_usd": cost,
              "usage": payload.get("usage", {}), "exit_code": result.returncode}
    with (root / "results" / "spend.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(ledger) + "\n")
    return {"service": "claude", "status": "PASS" if result.returncode == 0
            and not payload.get("is_error") else "FAIL", "cost_usd": cost,
            "exit_code": result.returncode, "subtype": payload.get("subtype")}


def main() -> None:
    """Run the selected access probe and save its sanitized result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["hf", "claude"])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.kind == "hf":
        repos = ["SALT-NLP/SWE-chat", "PatronusAI/trace-dataset",
                 "AlignmentResearch/impossible-swe-nemotron-rollouts",
                 "ScaleAI/lhaw", "duc-anh-2002/SWE-Misbehavior", "dxlong2000/SWE-Misbehavior"]
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(repos)) as pool:
            output = list(pool.map(lambda repo: probe_hf(repo, root), repos))
    else:
        output = probe_claude(root)
    (root / "results" / f"access-{args.kind}.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
