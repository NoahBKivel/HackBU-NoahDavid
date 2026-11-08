"""Fetch agent-run inputs without executing dataset content."""

import json
import os
from pathlib import Path
import urllib.request


def main() -> None:
    """Download task metadata and inspect a bounded number of structural fields."""
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as parquet
    root = Path(__file__).resolve().parents[1] / "data" / "downloads"
    inputs = [("ScaleAI/lhaw", "test.json"),
              ("duc-anh-2002/SWE-Misbehavior", "data/cg_lv1/test-00000-of-00001.parquet")]
    for repo, filename in inputs:
        folder = root / repo.replace("/", "--")
        path = hf_hub_download(repo, filename, repo_type="dataset", token=os.environ["HF_TOKEN"], local_dir=folder)
        if filename.endswith("parquet"):
            rows = parquet.read_table(path).slice(0, 3).to_pylist()
        else:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            rows = data if isinstance(data, list) else list(data.values())
            rows = rows[:3]
        print(json.dumps({"repo": repo, "sample_rows": rows}, ensure_ascii=True)[:18000])


if __name__ == "__main__":
    main()
