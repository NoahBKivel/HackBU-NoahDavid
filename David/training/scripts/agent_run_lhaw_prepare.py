"""Fetch coding-environment metadata for the ambiguity tasks."""

import json
import os
from pathlib import Path


def main() -> None:
    """Download upstream task metadata and select exact ambiguity-task joins."""
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    from huggingface_hub import HfApi, hf_hub_download
    import pyarrow.parquet as parquet
    root = Path(__file__).resolve().parents[1]
    output = root / "data/downloads/ScaleAI--SWE-bench_Pro"
    output.mkdir(exist_ok=True)
    api = HfApi(token=os.environ["HF_TOKEN"])
    files = api.list_repo_files("ScaleAI/SWE-bench_Pro", repo_type="dataset")
    (output / "repository-files.json").write_text(json.dumps(files), encoding="utf-8")
    names = [name for name in files if name.startswith("data/") and name.endswith("parquet")]
    if not names:
        names = [name for name in files if name.endswith("parquet")][:1]
    ambiguity = json.loads((root / "data/downloads/ScaleAI--lhaw/test.json").read_text(encoding="utf-8"))
    wanted = {row["original_task"] for row in ambiguity if row["dataset"] == "SWE-Bench Pro"}
    joined = {}
    for name in names:
        downloaded = hf_hub_download("ScaleAI/SWE-bench_Pro", name, repo_type="dataset",
                                     token=os.environ["HF_TOKEN"], local_dir=output)
        for row in parquet.read_table(downloaded).to_pylist():
            identifier = row["instance_id"]
            if identifier in wanted:
                joined[identifier] = {key: row.get(key) for key in
                                      ["instance_id", "repo", "base_commit", "docker_image", "dockerhub_tag"]}
    (output / "coding-environments.json").write_text(json.dumps(joined, indent=2), encoding="utf-8")
    print(json.dumps({"matched_tasks": len(joined), "wanted_tasks": len(wanted)}), flush=True)


if __name__ == "__main__":
    main()
