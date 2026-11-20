"""Incremental compact offsets into the immutable append-only teacher queue."""
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from filelock import FileLock
from .dispatch import digest, encoded


def rescan_epoch(directory):
    path = Path(directory) / "queue-rescan.epoch"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def request_rescan(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "queue-rescan.epoch"
    temporary = directory / ("queue-rescan-" + uuid4().hex + ".tmp")
    temporary.write_text(uuid4().hex, encoding="utf-8")
    temporary.replace(path)


def refresh_index(queue, directory):
    queue = Path(queue).resolve()
    folder = Path(directory) / "queue-index"
    folder.mkdir(parents=True, exist_ok=True)
    state_path = folder / (digest(str(queue)) + ".json")
    with FileLock(str(state_path) + ".lock"):
        stat = queue.stat()
        identity = [stat.st_dev, stat.st_ino]
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        if (state.get("identity") == identity and state.get("offset") == stat.st_size
                and Path(state.get("index", "__missing__")).is_file()):
            return state
        if (state.get("identity") != identity or state.get("offset", 0) > stat.st_size
                or not Path(state.get("index", "__missing__")).is_file()):
            state = {"identity": identity, "offset": 0,
                     "generation": uuid4().hex,
                     "index": str(folder / (uuid4().hex + ".jsonl"))}
        index = Path(state["index"])
        if state["offset"] < stat.st_size:
            with queue.open("rb") as source, index.open("ab") as output:
                source.seek(state["offset"])
                while source.tell() < stat.st_size:
                    start = source.tell()
                    line = source.readline()
                    if not line.endswith(b"\n"):
                        break
                    if line.strip():
                        item = json.loads(line)
                        batch = item["batch"]
                        families = item.get("required_families") or (["sol", "terra"] if item["allocation"] == "paired" else ["sol"])
                        meta = {"batch_id": batch["batch_id"], "input_sha256": batch["input_sha256"],
                                "pass": batch["pass"], "source": batch.get("source"),
                                "allocation": item["allocation"], "required_families": families,
                                "question_bases": sorted({key.split("#", 1)[0] for row in batch["records"] for key in row["questions"]}),
                                "offset": start, "length": len(line), "line_sha256": sha256(line).hexdigest()}
                        output.write((encoded(meta) + "\n").encode("utf-8"))
                    state["offset"] = source.tell()
                output.flush()
        else:
            index.touch(exist_ok=True)
        temporary = state_path.with_suffix("." + uuid4().hex + ".tmp")
        temporary.write_text(encoded(state), encoding="utf-8")
        temporary.replace(state_path)
    return state


def read_batch(queue, meta):
    with Path(queue).open("rb") as handle:
        handle.seek(meta["offset"])
        line = handle.read(meta["length"])
    if sha256(line).hexdigest() != meta["line_sha256"]:
        raise ValueError("The immutable queue batch changed after indexing.")
    item = json.loads(line)
    if any(item["batch"].get(key) != meta[key] for key in ("batch_id", "input_sha256", "pass")):
        raise ValueError("The queue index does not identify its frozen batch.")
    families = item.get("required_families") or (["sol", "terra"] if item["allocation"] == "paired" else ["sol"])
    questions = sorted({key.split("#", 1)[0] for row in item["batch"]["records"] for key in row["questions"]})
    if (item["allocation"] != meta["allocation"] or families != meta["required_families"]
            or item["batch"].get("source") != meta["source"] or questions != meta["question_bases"]):
        raise ValueError("The queue index changed a batch routing or family filter.")
    return item
