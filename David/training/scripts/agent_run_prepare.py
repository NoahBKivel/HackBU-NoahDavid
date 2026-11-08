"""Prepare source archives and a container image for isolated coding runs."""

import json
import os
from pathlib import Path, PurePosixPath
import tarfile


def safe_extract(archive: Path, target: Path) -> dict[str, int]:
    """Extract regular files and directories while rejecting unsafe archive entries."""
    target.mkdir(parents=True, exist_ok=True)
    counts = {"files": 0, "rejected": 0}
    with tarfile.open(archive, "r:gz") as stream:
        for member in stream:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts or "\\" in member.name
                    or ":" in member.name or member.issym() or member.islnk()):
                counts["rejected"] += 1
                continue
            destination = target.joinpath(*path.parts)
            if not destination.resolve().is_relative_to(target.resolve()):
                counts["rejected"] += 1
                continue
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                source = stream.extractfile(member)
                if source is not None:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with destination.open("wb") as output:
                        import shutil
                        shutil.copyfileobj(source, output)
                    counts["files"] += 1
    return counts


def main() -> None:
    """Download and extract the task source without executing its scripts."""
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    from huggingface_hub import hf_hub_download
    root = Path(__file__).resolve().parents[1]
    folder = root / "data/downloads/duc-anh-2002--SWE-Misbehavior"
    archive = hf_hub_download("duc-anh-2002/SWE-Misbehavior", "Source_Code.tar.gz",
                              repo_type="dataset", token=os.environ["HF_TOKEN"], local_dir=folder)
    print("archive_downloaded", flush=True)
    counts = safe_extract(Path(archive), folder / "source")
    (folder / "extraction.json").write_text(json.dumps(counts), encoding="utf-8")
    print(json.dumps(counts), flush=True)


if __name__ == "__main__":
    main()
