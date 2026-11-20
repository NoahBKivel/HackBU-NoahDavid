"""Recover stable prepared records and their private contexts without rerendering."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from intent_training.teacher.claims import teacher_input_hash
from intent_training.teacher.dispatch import digest
from intent_training.teacher.vote_allocation import allocation, required_families


def _atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def run(root, output, manifests, extra_calls=(), frozen_manifest=None):
    """Reconcile existing calls, publish context-complete batches, and count real gaps."""
    import modal
    root, output = Path(root), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    config = json.loads((root / "environment.json").read_text(encoding="utf-8-sig"))
    volume = modal.Volume.from_name(config["modal_volume"])
    handles = [json.loads(Path(path).read_text(encoding="utf-8")) for path in manifests]
    calls = list(dict.fromkeys([item["function_call_id"] for item in handles] + list(extra_calls)))
    statuses = []
    for call in calls:
        try:
            result = modal.FunctionCall.from_id(call).get(timeout=1)
            statuses.append({"call_id": call, "status": "FINISHED", "result": result})
        except TimeoutError:
            statuses.append({"call_id": call, "status": "PENDING"})
        except Exception as error:
            statuses.append({"call_id": call, "status": "REMOTE_ERROR", "error": str(error)[:500]})
    _atomic(output / "remote_calls.json", json.dumps(statuses, indent=2))
    print(json.dumps({"remote_calls": [{"call_id": row["call_id"], "status": row["status"],
        "returncode": row.get("result", {}).get("returncode"), "error": row.get("error")}
        for row in statuses]}), flush=True)
    prefix = handles[0]["remote_output"].removeprefix("/training/").rstrip("/")

    def read_json(relative):
        raw = b"".join(volume.read_file(prefix + "/" + relative))
        return json.loads(raw)

    def recover(record_id):
        record = read_json(f"records/{record_id}.json")
        context = read_json(f"contexts/{record_id}.json")
        if record["record_id"] != context["record_id"] or record["record_id"] != record_id:
            raise ValueError("The prepared record and context identities disagree.")
        if record["_meta"].get("state_budget") != 8191:
            raise ValueError("The recovered record does not declare the current state budget.")
        for field in ("source", "cut_seq"):
            if record["_meta"].get(field) != context["_meta"].get(field):
                raise ValueError("The prepared record and context cuts disagree.")
        return record, context

    ready_index = []
    if frozen_manifest:
        frozen_manifest = Path(frozen_manifest)
        entries = json.loads(frozen_manifest.read_text(encoding="utf-8"))
        order = [index for index in (10,) if index < len(entries)]
        order += list(range(15, len(entries)))
        done = set()
        with ThreadPoolExecutor(max_workers=4) as pool:
            for index in order:
                entry = entries[index]
                if entry["batch_id"] in done:
                    continue
                done.add(entry["batch_id"])
                location = Path(entry["input"])
                if not location.is_absolute():
                    location = root.parents[1] / location
                frozen = json.loads(location.read_text(encoding="utf-8"))
                recovered = list(pool.map(recover, [row["record_id"] for row in frozen["records"]]))
                actual = [{key: record[key] for key in expected}
                          for (record, _), expected in zip(recovered, frozen["records"])]
                if digest(actual) != frozen["input_sha256"]:
                    raise ValueError("Recovered model-visible input differs from the already frozen batch.")
                directory = output / "packets" / entry["batch_id"]
                main_path, context_path = directory / "main.jsonl", directory / "context.jsonl"
                _atomic(main_path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row, _ in recovered))
                _atomic(context_path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for _, row in recovered))
                ready = {"entry": index, "batch_id": entry["batch_id"], "status": "READY",
                         "records": len(recovered), "input_sha256": frozen["input_sha256"],
                         "prepared_main": str(main_path.resolve()), "context": str(context_path.resolve()),
                         "record_input_hashes": {row["record_id"]: teacher_input_hash(payload)
                             for (row, _), payload in zip(recovered, actual)}}
                ready_index.append(ready)
                _atomic(output / "packet_index.json", json.dumps(ready_index, indent=2))
                print(json.dumps(ready), flush=True)

    downloaded = {}
    for name in ("main.jsonl", "context.jsonl", "native.jsonl", "manifest.json", "remote-result.json", "formatter.stderr.log"):
        target = output / (name + ".download")
        try:
            with target.open("wb") as stream:
                for chunk in volume.read_file(prefix + "/" + name):
                    stream.write(chunk)
            target.replace(output / name)
            downloaded[name] = (output / name).stat().st_size
        except (modal.exception.NotFoundError, FileNotFoundError):
            target.unlink(missing_ok=True)
    main_rows = [json.loads(line) for line in (output / "main.jsonl").open(encoding="utf-8") if line.strip()]
    contexts = {}
    context_file = output / "context.jsonl"
    if context_file.exists():
        contexts = {row["record_id"]: row for line in context_file.open(encoding="utf-8")
                    if line.strip() for row in [json.loads(line)]}
    missing = [row["record_id"] for row in main_rows if row["record_id"] not in contexts]
    recovered_prefix = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for record, context in pool.map(recover, missing):
            contexts[record["record_id"]] = context
            recovered_prefix.append((record, context))
            if len(recovered_prefix) == 25:
                directory = output / "packets" / ("prefix-" + record["record_id"])
                _atomic(directory / "main.jsonl", "".join(json.dumps(item, ensure_ascii=False) + "\n" for item, _ in recovered_prefix))
                _atomic(directory / "context.jsonl", "".join(json.dumps(item, ensure_ascii=False) + "\n" for _, item in recovered_prefix))
                print(json.dumps({"status": "READY", "records": len(recovered_prefix),
                    "prepared_main": str((directory / "main.jsonl").resolve()),
                    "context": str((directory / "context.jsonl").resolve())}), flush=True)
                recovered_prefix = []
    _atomic(context_file, "".join(json.dumps(contexts[row["record_id"]], ensure_ascii=False) + "\n" for row in main_rows))
    controls, by_kind = {}, Counter()
    for row in main_rows:
        context = contexts[row["record_id"]]
        controls[row["record_id"]] = {"allocation": allocation(context), "required_families": list(required_families(context))}
        construction = context.get("side", {}).get("construction", {}).get("type", "none")
        actual_screen = any(key.split("#")[0] in {"SCR", "M8"} for key in row["questions"])
        by_kind[f"{construction}:{'screen' if actual_screen else 'task'}"] += 1
    _atomic(output / "allocation_by_record_id.json", json.dumps(controls, sort_keys=True))
    report = {"main": len(main_rows), "contexts": len(contexts), "complete_context": len(main_rows) == len(contexts),
              "duplicate_record_ids": len(main_rows) - len({row["record_id"] for row in main_rows}),
              "downloaded_bytes": downloaded, "construction_and_actual_form": dict(by_kind),
              "packet_count": len(ready_index), "native": sum(1 for line in (output / "native.jsonl").open(encoding="utf-8") if line.strip())
              if (output / "native.jsonl").exists() else 0}
    _atomic(output / "reconciliation.json", json.dumps(report, indent=2))
    print(json.dumps({"reconciliation": report}), flush=True)
    return report
