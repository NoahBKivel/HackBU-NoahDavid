"""Run a cost pilot or an explicitly released direct OpenAI labelling queue."""

import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.teacher.openai_client import OpenAILabeller
from intent_training.teacher.openai_client_state import atomic_json, utc_now


def load_key(path: Path) -> str:
    """Load only the authorized OpenAI key into memory without copying credentials."""
    value = os.environ.get("OPENAI_API_KEY")
    if not value:
        with path.open(encoding="utf-8-sig") as handle:
            for line in handle:
                match = re.match(r"^\s*(?:export\s+)?OPENAI_API_KEY\s*=\s*(.*?)\s*$", line)
                if match:
                    value = match.group(1).strip().strip("\"").strip("'")
                    break
    if not value:
        raise RuntimeError("The authorized OpenAI key is unavailable.")
    return value


def select_pilot(entries: list[dict], maximum: int, single_sol: bool = False) -> list[dict]:
    """Keep complete paired batches without exceeding the agreed pilot record count."""
    grouped = {}
    for entry in entries:
        grouped.setdefault(entry["batch_id"], {})[entry["model_family"]] = entry
    selected = []
    total = 0
    for pair in grouped.values():
        required = {"sol"} if single_sol else {"sol", "terra"}
        if not required <= set(pair):
            continue
        count = int(pair["sol"]["records"])
        if total + count > maximum:
            continue
        selected.extend([pair[family] for family in ("sol", "terra") if family in required])
        total += count
    if not selected:
        raise ValueError("No complete unowned batch pair fits the pilot limit.")
    return selected


def main() -> int:
    """Require a measured pilot projection artifact before admitting the bulk queue."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--pricing", type=Path, default=ROOT / "openai-label-pricing.json")
    parser.add_argument("--evidence", type=Path, default=ROOT / "results/openai-labelling")
    parser.add_argument("--claims", type=Path, default=ROOT / "data/votes/claims")
    parser.add_argument("--ledger", type=Path, default=ROOT / "results/openai-spend.jsonl")
    parser.add_argument("--pilot-records", type=int, default=50)
    parser.add_argument("--train-records", type=int, default=12200)
    parser.add_argument("--concurrency", type=int, default=64)
    parser.add_argument("--single-sol", action="store_true")
    parser.add_argument("--bulk-after-reported-projection", type=Path)
    args = parser.parse_args()
    entries = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.single_sol:
        entries = [entry for entry in entries if entry["model_family"] == "sol"]
    if args.bulk_after_reported_projection:
        projection = json.loads(args.bulk_after_reported_projection.read_text(encoding="utf-8"))
        if not projection.get("reported_to_owner_at") or not (projection.get("paired_records")
                                                              or projection.get("labelled_records")):
            raise ValueError("Bulk labelling requires the measured projection to have been reported.")
    else:
        entries = select_pilot(entries, args.pilot_records, args.single_sol)
    rates = json.loads(args.pricing.read_text(encoding="utf-8"))
    started = utc_now()
    atomic_json(args.evidence / "started.json", {"started_at": started,
                "mode": "bulk" if args.bulk_after_reported_projection else "pilot"})
    client = OpenAILabeller(api_key=load_key(args.env_file), rates=rates, ledger=args.ledger,
                            claims=args.claims, evidence=args.evidence,
                            max_concurrency=args.concurrency)
    results = client.run(entries)
    successful = [row for row in results if "error" not in row]
    pairs = {}
    for row in successful:
        pairs.setdefault(row["batch_id"], {})[row["family"]] = row
    paired = sum(pair["sol"]["records"] for pair in pairs.values() if set(pair) == {"sol", "terra"})
    labelled = (sum(pair["sol"]["records"] for pair in pairs.values() if "sol" in pair)
                if args.single_sol else paired)
    call_evidence = [json.loads(path.read_text(encoding="utf-8"))
                     for path in args.evidence.glob("*.json")
                     if path.name not in {"started.json", "projection.json", "progress.json"}]
    observed = [row for row in call_evidence if row.get("started_at", "") >= started]
    cost = sum(row["cost_usd"] for row in observed)
    result = {"started_at": started, "completed_at": utc_now(), "paired_records": paired,
              "labelled_records": labelled, "allocation": "single_sol" if args.single_sol else "paired",
              "measured_cost_usd": cost, "train_records": args.train_records,
              "projected_train_cost_usd": cost / labelled * args.train_records if labelled else None,
              "openai_exposure_usd": client.budget.exposure(), "price_source": rates["source"],
              "results": results, "reported_to_owner_at": None}
    result["scope"] = "Observed passes only; diagnostics not supplied in this pilot are additional unmeasured cost."
    result["projection_assumption"] = "The pilot source and state-length mix represents the remaining train records."
    result["usage_by_family"] = {
        family: {"input_tokens": sum(row["usage"]["input_tokens"] for row in observed if row["family"] == family),
                 "output_tokens": sum(row["usage"]["output_tokens"] for row in observed if row["family"] == family),
                 "cached_tokens": sum(row["usage"].get("input_tokens_details", {}).get("cached_tokens", 0)
                                      for row in observed if row["family"] == family),
                 "cache_write_tokens": sum(row["usage"].get("input_tokens_details", {}).get("cache_write_tokens", 0)
                                           for row in observed if row["family"] == family)}
        for family in ("sol", "terra")}
    atomic_json(args.evidence / "projection.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "results"}))
    return 0 if labelled else 1


if __name__ == "__main__":
    raise SystemExit(main())
