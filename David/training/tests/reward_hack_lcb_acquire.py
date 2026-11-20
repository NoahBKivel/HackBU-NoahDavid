"""Fetch a bounded ordered selection of inert trajectory JSON files."""
import concurrent.futures
import argparse
import json
import math
from pathlib import Path
import urllib.request

DATASET = "eungyeuk/reward_hack_lcb_trajectories"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extra-rows", type=int, default=0)
    args = parser.parse_args()
    root = Path("data/downloads/reward_hack_lcb")
    info = json.load(urllib.request.urlopen(f"https://huggingface.co/api/datasets/{DATASET}"))
    revision = info["sha"]
    quota = math.ceil(100 * 8600 / 10630 * 1.1) + args.extra_rows
    selected = []
    dirs = json.load(urllib.request.urlopen(f"https://huggingface.co/api/datasets/{DATASET}/tree/{revision}"))
    for directory in dirs:
        if directory["type"] != "directory":
            continue
        tree = json.load(urllib.request.urlopen(f"https://huggingface.co/api/datasets/{DATASET}/tree/{revision}/{directory['path']}?recursive=true&limit=1000"))
        selected.extend(item["path"] for item in tree if item["path"].endswith(".traj.json"))
        if len(selected) >= quota:
            break
    selected = selected[:quota]

    def fetch(name):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(urllib.request.urlopen(f"https://huggingface.co/datasets/{DATASET}/raw/{revision}/{name}", timeout=45).read())
        return name

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(fetch, selected))
    (root / "manifest.txt").write_text(json.dumps({"revision": revision, "files": selected}, indent=2))
    print(json.dumps({"revision": revision, "downloaded": len(selected)}))


if __name__ == "__main__":
    main()
