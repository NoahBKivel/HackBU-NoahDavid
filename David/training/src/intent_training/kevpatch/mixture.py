"""Sample linked prepared records under the declared training composition."""

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
from typing import Any


def source_candidates(record: dict, construction: str | None, plan: list[dict]) -> list[str]:
    """Match construction provenance before a source's eligible objective slices."""
    meta = record.get("_meta", {})
    marker = construction or meta.get("construction") or meta.get("construction_type")
    if isinstance(marker, dict):
        marker = marker.get("type")
    if marker:
        marker = str(marker).replace("-", "_")
        return [entry["id"] for entry in plan if entry["id"] == marker]
    source = meta.get("source", record.get("source"))
    entries = [entry for entry in plan if entry["source"] == source]
    sliced = str(meta.get("slice", ""))
    exact = [entry["id"] for entry in entries if str(entry.get("slice")) == sliced]
    if exact:
        return exact
    unsliced = [entry["id"] for entry in entries if entry.get("slice") is None]
    if unsliced:
        return unsliced
    eligible = set(map(str, meta.get("eligible_slices", [])))
    if eligible:
        return [entry["id"] for entry in entries if str(entry.get("slice")) in eligible]
    objectives = set(meta.get("objective", []))
    compatible = [entry["id"] for entry in entries if objectives == set(entry.get("objective", []))]
    if compatible:
        return compatible
    return []


def composition_role(record: dict) -> str:
    """Keep naturally overflowing task sources in their canonical composition part."""
    meta = record.get("_meta", {})
    marker = meta.get("construction") or meta.get("construction_type")
    if isinstance(marker, dict):
        marker = marker.get("type")
    return "screen" if str(marker).replace("-", "_") == "overflow_screen" else "task"


def sample_units(records: list[dict], candidates: dict[int, list[str]],
                 weights: dict[str, float], count: int, rng: random.Random) -> tuple[list[dict], dict]:
    """Draw linked units with source weights corrected for their average unit size."""
    from .grouping import linked_units
    units = linked_units(records)
    pools: dict[str, list[int]] = {key: [] for key, weight in weights.items() if weight > 0}
    for index, unit in enumerate(units):
        eligible = set(candidates[id(unit[0])])
        for record in unit[1:]:
            eligible.intersection_update(candidates[id(record)])
        for key in eligible.intersection(pools):
            pools[key].append(index)
    missing = [key for key, pool in pools.items() if not pool]
    if missing:
        raise ValueError("Prepared source coverage is missing: " + ", ".join(sorted(missing)))
    chosen, chosen_units, assignment = [], set(), Counter()
    while len(chosen) < count:
        remaining = count - len(chosen)
        available = {key: [index for index in pool if index not in chosen_units and len(units[index]) <= remaining]
                     for key, pool in pools.items()}
        keys = [key for key, pool in available.items() if pool]
        if not keys:
            raise ValueError("Complete linked units cannot fill the requested sample count.")
        masses = [weights[key] * len(available[key]) /
                  sum(len(units[index]) for index in available[key]) for key in keys]
        key = rng.choices(keys, weights=masses, k=1)[0]
        index = rng.choice(available[key])
        chosen_units.add(index)
        chosen.extend(units[index])
        assignment[key] += len(units[index])
    return chosen, dict(assignment)


def load_prepared(directories: list[str], context_paths: dict[str, str] | None = None) -> tuple[list[dict], dict[str, str], dict]:
    """Read stable prepared prefixes and retain only construction types from private context."""
    records, construction_by_id, observed, seen = [], {}, {}, set()
    for directory in directories:
        root = Path(directory)
        info = {}
        manifest_path = root / "manifest.json"
        declaration = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        context_ids = set()
        context = root / "context.jsonl"
        if context.exists():
            with context.open(encoding="utf-8") as stream:
                for line in stream:
                    if not line.endswith("\n"):
                        continue
                    value = json.loads(line)
                    context_ids.add(value["record_id"])
                    construction = value.get("side", {}).get("construction", {})
                    if isinstance(construction, dict) and construction.get("type"):
                        construction_by_id[value["record_id"]] = construction["type"]
        for name in ("main.jsonl", "native.jsonl"):
            path = root / name
            count = 0
            if path.exists():
                with path.open(encoding="utf-8") as stream:
                    for line in stream:
                        if not line.endswith("\n"):
                            continue
                        value = json.loads(line)
                        identity = value.get("record_id") or value.get("_meta", {}).get("id")
                        if name == "main.jsonl" and not value.get("_meta", {}).get("native_record") and identity not in context_ids:
                            immediate = root / "contexts" / f"{identity}.json"
                            if not immediate.is_file():
                                continue
                            if context_paths is not None:
                                context_paths[identity] = str(immediate)
                        if identity is None:
                            identity = hashlib.sha256(line.encode()).hexdigest()
                        if identity in seen:
                            continue
                        seen.add(identity)
                        record = {key: deepcopy(value[key]) for key in ("state", "questions", "_meta") if key in value}
                        record.setdefault("_meta", {})["id"] = identity
                        if record["_meta"].get("form") == "screen":
                            record["_meta"].setdefault("screen_budget", declaration.get("screen_budget"))
                        record["record_id"] = identity
                        records.append(record)
                        count += 1
            info[name] = count
        observed[directory] = info
    return records, construction_by_id, observed


def declared_task_plan(plan: dict) -> list[dict]:
    """Validate source quotas against the composition declared by the caller."""
    tasks = [entry for entry in plan["sources"] if entry["part"] == "task" and entry["planned_quota"]]
    expected = plan.get("parts", {}).get("task")
    if type(expected) is not int or expected <= 0:
        raise ValueError("The canonical composition must declare a positive task count.")
    if sum(entry["planned_quota"] for entry in tasks) != expected:
        raise ValueError("The canonical source quotas do not match the declared task count.")
    return tasks


def build_payload(directories: list[str], plan: dict, destination: str,
                  tokenizer: Any, seed: int) -> dict:
    """Publish one immutable admitted sample with exact replay, task and screen counts."""
    from intent_training.assemble.siblings import pack_siblings, kev_fit
    from intent_training.prepare.records import scan
    from .grouping import linked_units
    target = Path(destination)
    if target.exists():
        raise FileExistsError("The benchmark payload is immutable once written.")
    context_paths = {}
    records, constructions, observed = load_prepared(directories, context_paths)
    task_plan = declared_task_plan(plan)
    candidates, geometry_rows = {}, 0
    predicate = kev_fit(tokenizer, max_state=8192)
    for record in records:
        construction = constructions.get(record["record_id"])
        if construction:
            record["_meta"]["construction"] = construction
        candidates[id(record)] = source_candidates(record, construction, task_plan)
    replay = [record for record in records if record["_meta"].get("native_record") and
              record["_meta"].get("source") in {"kev_replay", "tasksource"}]
    replay_ids = {id(record) for record in replay}
    screens = [record for record in records if composition_role(record) == "screen"]
    tasks = [record for record in records if id(record) not in replay_ids and
             composition_role(record) == "task"]
    rng = random.Random(seed)
    selected_tasks, assignments = sample_units(tasks, candidates,
        {entry["id"]: entry["planned_quota"] for entry in task_plan}, 90, rng)
    replay_candidates = {id(record): [record["_meta"]["source"]] for record in replay}
    kev = [record for record in replay if record["_meta"]["source"] == "kev_replay"]
    other = [record for record in replay if record["_meta"]["source"] == "tasksource"]
    selected_kev, _ = sample_units(kev, replay_candidates, {"kev_replay": 1}, 25, rng)
    selected_other, _ = sample_units(other, replay_candidates, {"tasksource": 1}, 5, rng)
    pairs = [unit for unit in linked_units(screens) if len(unit) == 2 and
             all(record["_meta"].get("pair_id") for record in unit)]
    if not pairs:
        raise ValueError("A complete two-record real-screen pair is not available.")
    selected_screens = rng.choice(pairs)
    if any(record["_meta"].get("screen_budget") != 8192 for record in selected_screens):
        raise ValueError("The overflow screen must use its separate 8192-token budget.")
    selected = selected_kev + selected_other + selected_tasks + selected_screens
    if len(selected) != 122:
        raise RuntimeError("The admitted mixture has the wrong record count.")
    admitted = []
    for record in selected:
        identity = record["record_id"]
        if identity in context_paths:
            private = json.loads(Path(context_paths[identity]).read_text())
            if private.get("record_id") != identity:
                raise ValueError("An immediate context does not match its selected record.")
            construction = private.get("side", {}).get("construction", {})
            if isinstance(construction, dict) and construction.get("type"):
                if construction["type"] != record["_meta"].get("construction"):
                    raise ValueError("A selected construction lacks its published construction metadata.")
        for question in record["questions"].values():
            if "label" not in question:
                question["label"] = (next(iter(question["criteria"])) if question["type"] == "choice"
                                     else 0 if question["type"] == "score" else False)
                geometry_rows += 1
        siblings = pack_siblings(record, fits=predicate)
        if len(siblings) != 1:
            raise ValueError("Selected records require packing siblings; a final admitted source pool is required.")
        admitted.extend(siblings)
    selected = admitted
    rng.shuffle(selected)
    for record in selected:
        scan(record)
    raw = "".join(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" for record in selected).encode()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(raw)
    manifest = {"status": "PASS", "path": str(target), "sha256": hashlib.sha256(raw).hexdigest(),
                "seed": seed, "records": 122, "roles": {"replay": 30, "task": 90, "screen": 2},
                "replay_sources": {"kev_replay": 25, "tasksource": 5},
                "task_sources": assignments, "observed_inputs": observed,
                "plan_sha256": hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(),
                "geometry_only_target_rows": geometry_rows,
                "training_labels_created": 0, "state_budget": 8191, "screen_budget": 8192}
    target.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
