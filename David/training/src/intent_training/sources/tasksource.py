"""Convert inert typed decisions while retaining their original provenance."""

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Iterator

DATASET = "tasksource/tasksource-jev-typed-decisions"
# Commercial permission is a conservative local selection policy, not a claim
# that research training is universally prohibited by non-commercial licences.
PERMITTED_USE = {"commercial"}
EXCLUDED = (
    "clinc", "schemaguided", "sgd", "when2call", "mmlu", "emotion",
    "tweetoffensive", "qnli", "paws", "sciq", "contrastive", "legacyholdout",
    "compositionholdout", "trace", "malt", "llmbar", "rewardbench2",
    "ifeval", "ifbench", "mtbench", "hilbench", "recap", "cuad",
    "contractnli", "hackbench", "cotmonitorrobustness", "jevany", "jevaeval",
    "ameek", "trail", "aspi", "userintentbench", "scaleaimrt", "promptinjection", "promptshield",
    "hewittlab", "oliverdk", "dangw", "stepguard", "toolprmbench", "funes",
    "davanstrien", "crispwisp", "agentrx", "maud", "swegym", "agentglass",
    "nebius", "agentlogs", "pisessions", "devgpt", "skywork80k", "prism",
    "webdevarena", "jevagentharness", "sengim", "lucabaroni", "rhbench",
    "followbench", "complexbench", "handbook", "reqclarifybench", "sweclarify",
    "mast", "humanevalcomm", "clarifycodebench", "codeclarqa", "lostinconversation",
    "helpsteer2", "ultrafeedback", "specbench", "agentrewardbench",
    "mtacifbench", "arena55k", "arena100k",
)


def exclusion(row: dict) -> str | None:
    """Reject uncertain permissions and named evaluation families before mapping."""
    identity = " ".join(str(row.get(key, "")) for key in
                        ("source", "id", "group_id", "source_index"))
    identity = re.sub(r"[^a-z0-9]", "", identity.lower())
    if any(name in identity for name in EXCLUDED):
        return "excluded_source"
    if row.get("license_use") not in PERMITTED_USE:
        return "licence_use_policy"
    if row.get("license", "").lower() in {"", "unspecified", "unknown", "other"}:
        return "missing_explicit_licence"
    if row.get("split") != "train":
        return "non_training_split"
    return None


def native(row: dict) -> dict:
    """Adapt the three observed kinds and preserve the complete original row."""
    for key in ("state", "question", "source", "id", "question_id", "group_id", "license"):
        if not isinstance(row.get(key), str) or not row[key]:
            raise ValueError(f"Typed decisions require a nonempty {key} string.")
    kind, options, target = row.get("kind"), row.get("options"), row.get("target")
    if kind not in {"noul", "choice", "score"}:
        raise ValueError("Unsupported typed-decision kind.")
    if not isinstance(options, list) or not all(isinstance(x, str) for x in options):
        raise ValueError("Typed-decision options must be strings.")
    if not isinstance(target, list) or not target or not all(
        type(x) in {int, float} and math.isfinite(x) and 0 <= x <= 1 for x in target
    ):
        raise ValueError("Typed-decision targets must be finite probabilities.")
    q = {"type": kind, "instructions": row["question"], "src": row["source"]}
    if kind == "noul":
        if options or len(target) != 1:
            raise ValueError("A noul row requires no options and one true probability.")
        q.update(label=target[0] >= 0.5, target={"false": 1 - target[0], "true": target[0]})
    else:
        if not 1 <= len(options) <= 255 or len(set(options)) != len(options):
            raise ValueError("Options must be unique and within the native option limit.")
        if len(target) != len(options) or not math.isclose(sum(target), 1, abs_tol=1e-6):
            raise ValueError("Target probabilities must align with options and sum to one.")
        index = max(range(len(target)), key=target.__getitem__)
        q.update(criteria=options if kind == "score" else dict.fromkeys(options),
                 label=index if kind == "score" else options[index],
                 target=dict(zip(map(str, range(len(options))) if kind == "score" else options, target)))
    return {"state": row["state"], "questions": {row["question_id"]: q},
            "_meta": {"source": row["source"], "group_id": row["group_id"],
                      "split": row["split"], "licence": row["license"],
                      "source_record_id": row["id"], "original_row": deepcopy(row)}}


def convert(raw_dir: Path) -> Iterator[tuple[list[dict], dict, dict]]:
    """Yield permitted native replay records from downloaded JSONL pages."""
    for path in sorted(Path(raw_dir).glob("rows-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if exclusion(row):
                continue
            try:
                record = native(row)
            except ValueError:
                continue
            yield [], {"native_record": record, "licence": row["license"]}, {
                "source": "tasksource", "source_record_id": row["id"],
                "trajectory_id": row["group_id"], "objective": [],
                "licence": row["license"], "license_use": row["license_use"],
                "harness": DATASET, "native": True}


def main() -> None:
    """Fetch a bounded dataset prefix or validate and convert cached pages."""
    import argparse
    import urllib.parse
    import urllib.request

    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--max-rows", type=int, default=5000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    raw = root / "data/downloads/tasksource"
    raw.mkdir(parents=True, exist_ok=True)
    if args.fetch:
        accepted = 0
        for offset in range(0, args.max_rows, 100):
            params = urllib.parse.urlencode(dict(dataset=DATASET, config="default",
                split="train", offset=offset, length=min(100, args.max_rows - offset)))
            url = "https://datasets-server.huggingface.co/rows?" + params
            with urllib.request.urlopen(url, timeout=45) as response:
                payload = json.load(response)
            if any(item.get("truncated_cells") for item in payload["rows"]):
                raise ValueError("Dataset viewer returned truncated cells.")
            rows = [item["row"] for item in payload["rows"]]
            (raw / f"rows-{offset:08d}.jsonl").write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            accepted += sum(exclusion(row) is None for row in rows)
            if accepted >= args.limit or not rows:
                break
    counts, licences, kinds = Counter(), Counter(), Counter()
    excluded_sources, output_sources, output_licences, noul_labels = Counter(), Counter(), Counter(), Counter()
    schema_errors = Counter()
    files = []
    for path in sorted(raw.glob("rows-*.jsonl")):
        files.append({"path": str(path.relative_to(root)),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            counts["source_rows"] += 1
            reason = exclusion(row)
            if reason is None:
                try:
                    native(row)
                except ValueError as exc:
                    reason = "invalid_native_schema"
                    schema_errors[str(exc)] += 1
            counts[reason or "eligible_rows"] += 1
            if exclusion(row) == "excluded_source":
                excluded_sources[row["source"]] += 1
            licences[str(row.get("license_use"))] += 1
    output = root / "data/converted/tasksource.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with output.open("w", encoding="utf-8") as handle:
        for events, side, meta in convert(raw):
            if n >= args.limit:
                break
            assert events == [] and meta["native"] is True
            record = side["native_record"]
            assert native(record["_meta"]["original_row"]) == record
            kinds[next(iter(record["questions"].values()))["type"]] += 1
            output_sources[record["_meta"]["source"]] += 1
            output_licences[meta["licence"]] += 1
            q = next(iter(record["questions"].values()))
            if q["type"] == "noul":
                noul_labels[str(q["label"]).lower()] += 1
            handle.write(json.dumps(dict(events=events, side=side, meta=meta), ensure_ascii=False) + "\n")
            n += 1
    report = {"dataset": DATASET, "output": str(output.relative_to(root)),
              "output_rows": n, "target_rows": args.limit, "counts": dict(counts),
              "license_use_counts": dict(licences), "kind_counts": dict(kinds),
              "excluded_source_counts": dict(excluded_sources),
              "output_source_counts": dict(output_sources), "output_licence_counts": dict(output_licences),
              "noul_hard_label_counts": dict(noul_labels),
              "native_schema_error_counts": dict(schema_errors),
              "licence_policy": "Explicit licence and commercial license_use only; conservative local selection.",
              "source_files": files, "native_schema_validated": n,
              "blockers": [] if n >= args.limit else ["Bounded prefix has insufficient eligible rows."]}
    destination = root / "results/sources/tasksource.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_rows": n, "counts": dict(counts), "report": str(destination.relative_to(root))}))


if __name__ == "__main__":
    main()
