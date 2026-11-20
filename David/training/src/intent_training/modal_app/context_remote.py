"""Project existing private contexts beside their evidence without changing model inputs."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import modal
from .prepare_remote import CONFIG, image, volume

app = modal.App(CONFIG["modal_app"])


@app.function(image=image, cpu=4, memory=8192, timeout=3600, volumes={"/training": volume})
def project(namespace: str):
    """Write compact assembly contexts using the already-committed record prefix."""
    if "/" in namespace or namespace in {"", ".", ".."}:
        raise ValueError("A context namespace must be a single prepared directory name.")
    volume.reload()
    code = Path("/opt/intent-training")
    sys.path[:0] = [str(code / "src"), str(code), str(code.parent)]
    from intent_training.assemble.flow import assembly_context
    source = Path("/training/prepared") / namespace
    output = Path("/training/prepared/context-projections") / namespace
    output.mkdir(parents=True, exist_ok=True)
    identities = []
    with (source / "main.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                identities.append((row["record_id"], set(row["questions"]) != {"RF"}))

    def read(item):
        identity, required = item
        evidence = source / "contexts" / (identity + ".json")
        payload = evidence.read_bytes()
        context = json.loads(payload)
        if context["record_id"] != identity:
            raise ValueError("The source context identity does not match its committed record.")
        projected = assembly_context(context, event_required=required)
        projected["_meta"]["private_context_reference"] = str(evidence)
        projected["_meta"]["private_context_sha256"] = hashlib.sha256(payload).hexdigest()
        return json.dumps(projected, ensure_ascii=False, separators=(",", ":")) + "\n"

    temporary = output / "context.jsonl.writing"
    count = 0
    with temporary.open("w", encoding="utf-8", newline="\n") as handle, ThreadPoolExecutor(max_workers=8) as pool:
        for line in pool.map(read, identities):
            handle.write(line)
            count += 1
            if count == 100 or count % 500 == 0:
                handle.flush()
                prefix = output / "context.jsonl.tmp"
                shutil.copyfile(temporary, prefix)
                os.replace(prefix, output / "context.jsonl")
                volume.commit()
                print(json.dumps({"namespace": namespace, "contexts": count,
                    "path": str(output / "context.jsonl")}), flush=True)
    os.replace(temporary, output / "context.jsonl")
    result = {"namespace": namespace, "contexts": count, "input_records": len(identities),
        "path": str(output / "context.jsonl"), "bytes": (output / "context.jsonl").stat().st_size,
        "original_evidence_preserved": True, "model_input_changed": False}
    (output / "manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    volume.commit()
    return result
