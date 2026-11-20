"""Materialize the bounded Aria and OLMo source expansions privately."""

from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path
import sys

import modal
from .prepare_remote import CONFIG, image, volume

app = modal.App(CONFIG["modal_app"])


@app.function(image=image, cpu=2, memory=8192, timeout=1800, volumes={"/training": volume})
def convert_expansion(source: str, work_root: str, target: int):
    """Preserve the existing source prefix and append only validated actual rows."""
    if source not in {"aria_reward_hacking", "olmo_reward_hacking"}:
        raise ValueError("This bounded converter only supports the assigned Aria and OLMo expansions.")
    volume.reload()
    root = Path(work_root)
    if not root.is_relative_to(Path("/training/source-conversion")):
        raise ValueError("Source conversion must remain inside its private volume directory.")
    code = Path("/opt/intent-training")
    sys.path[:0] = [str(code / "src"), str(code), str(code.parent)]
    from monitor_format import validate_events
    from intent_training.prepare.records import scan
    module = importlib.import_module("intent_training.sources." + source)
    output = root / "data/converted" / (source + ".jsonl")
    prefix = output.read_bytes()
    old = [json.loads(line) for line in prefix.splitlines() if line.strip()]
    if source == "olmo_reward_hacking":
        report = module.append_records(root, target)
        rows = [json.loads(line) for line in output.read_bytes().splitlines() if line.strip()]
        if not output.read_bytes().startswith(prefix):
            raise ValueError("The OLMo expansion changed the existing source prefix.")
        for row in rows:
            validate_events(row["events"])
            scan(row)
        report.update(source=source, output=str(output),
            output_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
        volume.commit()
        return report
    seen = {row["meta"]["source_record_id"] for row in old}
    raw = root / "data/downloads" / source
    paths = [raw / "rows.jsonl"] if source == "aria_reward_hacking" else [
        raw / "kl0.0-additional.jsonl", raw / "kl0.02-additional.jsonl"]
    added = []
    for path in paths:
        for events, side, meta in module.convert(path):
            if source == "aria_reward_hacking" and meta["source_record_id"] in seen:
                continue
            if source == "olmo_reward_hacking" and ":raw-row:" not in meta["source_record_id"]:
                raise ValueError("A new OLMo row lacks its distinct raw-row namespace.")
            validate_events(events)
            row = {"events": events, "side": side, "meta": meta}
            scan(row)
            if meta["source_record_id"] in seen:
                raise ValueError("An expansion row duplicates an existing source identity.")
            seen.add(meta["source_record_id"])
            added.append(row)
            if len(old) + len(added) >= target:
                break
    for row in old + added:
        validate_events(row["events"])
        scan(row)
    temporary = output.with_suffix(".jsonl.tmp")
    temporary.write_bytes(prefix + b"".join((json.dumps(row, ensure_ascii=False) + "\n").encode() for row in added))
    if not temporary.read_bytes().startswith(prefix):
        raise ValueError("The expansion changed the existing source prefix.")
    temporary.replace(output)
    labels = Counter(str(label.get("value")) for row in added for label in row["side"].get("source_labels", []))
    report = {"source": source, "old_rows": len(old), "added_rows": len(added),
        "converted_rows": len(old) + len(added), "target": target,
        "shortfall": max(0, target - len(old) - len(added)), "prefix_preserved": True,
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "new_source_label_values": dict(labels), "event_validation": "PASS",
        "credential_scan": "PASS", "dataset_code_executed": False,
        "output": str(output)}
    result = root / "results/sources" / (source + ".json")
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(report, indent=2), encoding="utf-8")
    volume.commit()
    return report
