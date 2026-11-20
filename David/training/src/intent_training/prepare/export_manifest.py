"""Describe a credential-filtered export without transferring its contents."""

from collections import Counter
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re


def build(root, paths, destination):
    """Count and hash the exact safe JSONL payload and report only provenance."""
    root = Path(root).resolve()
    spec = importlib.util.spec_from_file_location("credential_patterns", root / "scripts" / "scan_secrets.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    patterns = [re.compile(value) for value in module.PATTERNS]
    registry = root / "src" / "intent_training" / "sources" / "entries"
    combined = hashlib.sha256()
    report = {"destination": {"service": "Modal", "workspace": "davidkny22",
              "app": "intent-monitor-training", "volume": "intent-monitor-training",
              "visibility": "private"},
              "transferred": False, "credential_pattern_count": len(patterns), "files": []}
    total = 0
    for given in paths:
        path = (root / given).resolve()
        if not path.is_relative_to(root / "data"):
            raise ValueError("The proposed data export must stay inside the training data directory.")
        file_hash = hashlib.sha256()
        safe_hash = hashlib.sha256()
        counts, licences, types, sources, rejected = Counter(), set(), set(), set(), []
        snapshot = root / "data" / "prepared" / "export-snapshots" / Path(destination).stem / path.name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        temporary = snapshot.with_suffix(".jsonl.tmp")
        with path.open("rb") as handle, temporary.open("wb") as frozen:
            for number, raw in enumerate(handle, 1):
                file_hash.update(raw)
                if not raw.strip():
                    continue
                row = json.loads(raw)
                text = json.dumps(row, ensure_ascii=False)
                hits = [index for index, pattern in enumerate(patterns, 1)
                        if pattern.search(text) or pattern.search(raw.decode("utf-8-sig"))]
                counts["raw_records"] += 1
                if hits:
                    rejected.append({"line": number, "pattern_indices": hits})
                    continue
                encoded = raw.decode("utf-8-sig").rstrip("\r\n").encode("utf-8") + b"\n"
                safe_hash.update(encoded)
                combined.update(encoded)
                frozen.write(encoded)
                counts["safe_records"] += 1
                total += 1
                sources.add(row["meta"]["source"])
                licences.add(str(row["meta"].get("licence", row["side"].get("licence", "unknown"))))
                types.add(row["side"].get("construction", {}).get("type", "unspecified"))
        temporary.replace(snapshot)
        provenance = []
        for source in sorted(sources):
            entry_path = registry / f"{source}.json"
            if entry_path.exists():
                entry = json.loads(entry_path.read_text(encoding="utf-8-sig"))
            else:
                entry_path = registry.parent / f"{source}.py"
                tree = ast.parse(entry_path.read_text(encoding="utf-8-sig"))
                declared = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "DATASET" for target in node.targets)
                    and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)]
                if len(declared) != 1:
                    raise ValueError(f"No unambiguous declared source provenance for {source}.")
                entry = {"dataset": declared[0]}
            dataset = entry.get("dataset", "")
            urls = []
            if isinstance(dataset, str) and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", dataset):
                urls.append("https://huggingface.co/datasets/" + dataset)
            elif isinstance(dataset, str) and dataset.startswith("https://"):
                urls.append(dataset.split("?", 1)[0])
            provenance.append({"source": source, "registry_dataset": dataset, "source_urls": urls,
                               "source_entry": str(entry_path.relative_to(root))})
        report["files"].append({"path": str(path.relative_to(root)), "file_bytes": path.stat().st_size,
            "immutable_export_path": str(snapshot.relative_to(root)),
            "file_sha256": file_hash.hexdigest(), "filtered_payload_sha256": safe_hash.hexdigest(),
            "counts": dict(counts), "excluded_credentials": rejected, "licences": sorted(licences),
            "construction_types": sorted(types), "source_provenance": provenance,
            "transform_basis": ("Mechanical counterfactual construction over existing source traces and central generation responses; intentions are not teacher labels."
                if types - {"unspecified"} else "Existing source text, annotations and central generation responses converted to canonical events or requirement windows. Original visible annotations and pending-check status are preserved; outcome annotations remain hints.")})
    report.update(safe_records=total, filtered_combined_payload_sha256=combined.hexdigest(),
                  scope="Only the listed credential-filtered JSONL records; no environment files, keys, downloads, models or other local files.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(destination), "safe_records": total,
                      "files": len(report["files"]), "transferred": False}), flush=True)
    return report
