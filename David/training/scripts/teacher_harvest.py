"""Validate actual model vote outputs and expand cached RF decisions to their parents."""

from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.teacher import validate_vote, agreement_report
from intent_training.teacher.dispatch import digest


def load_lines(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main():
    counts = defaultdict(int)
    paired = []
    initial_pairs = []
    relabel_pairs = []
    current_pairs = {}
    selected = defaultdict(list)
    selected_parents = set()
    parent_required = defaultdict(set)
    resolved_content = set()
    errors = []
    validated = []
    shared_fanout = defaultdict(list)
    shared_path = ROOT / "data/prepared/requirements_fanout.jsonl"
    if shared_path.exists():
        for alias in load_lines(shared_path):
            if alias.get("content_sha256") and alias.get("unit"):
                shared_fanout[alias["content_sha256"]].append(alias)
    for folder in (ROOT / "data/votes").iterdir():
        if not folder.is_dir():
            continue
        fanout_path = folder / "fanout.json"
        fanout = json.loads(fanout_path.read_text(encoding="utf-8")) if fanout_path.exists() else {}
        if folder.name == "seed_requirements" and not fanout:
            fanout = shared_fanout
        for fingerprint, aliases in fanout.items():
            for alias in aliases:
                parent_required[alias["parent_record_id"]].add(fingerprint)
        for batch_path in folder.glob("*.json"):
            if batch_path.name in {"manifest.json", "fanout.json", "context.json"}:
                continue
            try:
                batch = json.loads(batch_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                errors.append({"path": str(batch_path), "error": "The frozen batch JSON is incomplete."})
                continue
            if "batch_id" not in batch:
                continue
            families = {}
            for family in ("sol", "terra"):
                vote_path = folder / f"{batch['batch_id']}.{family}.votes.jsonl"
                if not vote_path.exists():
                    continue
                try:
                    votes = load_lines(vote_path)
                    for vote in votes:
                        validate_vote(vote, batch, family)
                    if len({vote["record_id"] for vote in votes}) != len(batch["records"]):
                        raise ValueError("The batch output is incomplete or duplicated.")
                    families[family] = {vote["record_id"]: vote for vote in votes}
                    counts[f"{batch['pass']}_{family}_records"] += len(votes)
                    validated.extend(votes)
                except (ValueError, KeyError, TypeError) as error:
                    errors.append({"path": str(vote_path), "error": str(error)})
            if set(families) != {"sol", "terra"}:
                continue
            counts[f"{batch['pass']}_paired_records"] += len(batch["records"])
            for row in batch["records"]:
                sol, terra = (families[f][row["record_id"]]["votes"] for f in ("sol", "terra"))
                triples = [(key, sol[key], terra[key]) for key in row["questions"]]
                if batch["pass"] == "main_relabel":
                    relabel_pairs.extend(triples)
                else:
                    initial_pairs.extend(triples)
                for triple in triples:
                    identity = (row["record_id"], triple[0])
                    if batch["pass"] == "main_relabel" or identity not in current_pairs:
                        current_pairs[identity] = triple
                if batch["pass"] != "requirements":
                    continue
                fingerprint = row.get("content_sha256") or digest({"state": row["state"], "questions": row["questions"]})
                resolved_content.add(fingerprint)
                values = {True: 1., False: 0., "cant_tell": .5}
                approved = (values[sol["RF"]] + values[terra["RF"]]) / 2 >= .5
                for alias in fanout.get(fingerprint, []):
                    parent = alias["parent_record_id"]
                    selected_parents.add(parent)
                    if approved:
                        selected[parent].append(dict(alias["unit"], unit_id=alias["unit_id"]))
    output = ROOT / "data/votes/results/teacher"
    output.mkdir(parents=True, exist_ok=True)
    complete_parents = {parent for parent in selected_parents
                        if parent_required[parent] and parent_required[parent] <= resolved_content}
    selection_path = output / "requirements_selected.jsonl"
    temporary = selection_path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for parent in sorted(complete_parents):
            handle.write(json.dumps({"parent_record_id": parent, "requirements": selected[parent]}, ensure_ascii=False) + "\n")
    temporary.replace(selection_path)
    with (output / "validated_votes.jsonl").open("w", encoding="utf-8") as handle:
        for vote in validated:
            handle.write(json.dumps(vote, ensure_ascii=False) + "\n")
    report = {"counts": dict(counts), "errors": errors, "instruments": agreement_report(current_pairs.values()),
              "initial_instruments": agreement_report(initial_pairs),
              "relabel_instruments": agreement_report(relabel_pairs),
              "rf_parents_observed": len(selected_parents), "rf_parents_complete": len(complete_parents)}
    (output / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"counts": dict(counts), "errors": errors, "rf_parents_observed": len(selected_parents)}))


if __name__ == "__main__":
    main()
