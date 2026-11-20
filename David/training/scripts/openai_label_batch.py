"""Manage a finite lower-priority Batch subset without automatic resubmission."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.teacher.openai_client_batch import BatchLabeller
from intent_training.teacher.openai_client_state import atomic_json
from openai_label import load_key


def main():
    """Keep API credentials in memory and preserve all uncertain reservations."""
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "submit", "status", "collect", "cancel"))
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--control", type=Path)
    parser.add_argument("--family", choices=("sol", "terra"))
    parser.add_argument("--lower-priority", action="store_true")
    parser.add_argument("--max-usd", type=float, default=5.0)
    parser.add_argument("--max-requests", type=int, default=100)
    parser.add_argument("--max-output-tokens", type=int, default=16000)
    parser.add_argument("--pricing", type=Path, default=ROOT / "openai-label-pricing.json")
    parser.add_argument("--ledger", type=Path, default=ROOT / "results/openai-spend.jsonl")
    parser.add_argument("--claims", type=Path, default=ROOT / "data/votes/claims")
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    client = BatchLabeller(pricing=json.loads(args.pricing.read_text(encoding="utf-8")),
                           ledger=args.ledger, claims=args.claims)
    if args.command == "prepare":
        if not all((args.manifest, args.control, args.family, args.lower_priority)):
            parser.error("Prepare requires a manifest, private control, family and lower-priority flag.")
        entries = json.loads(args.manifest.read_text(encoding="utf-8"))
        for entry in entries:
            if "batch" not in entry:
                entry["batch"] = json.loads(Path(entry["input"]).read_text(encoding="utf-8"))
        result = client.prepare(entries, json.loads(args.control.read_text(encoding="utf-8")),
                                args.directory, family=args.family, max_usd=args.max_usd,
                                max_requests=args.max_requests, max_output_tokens=args.max_output_tokens,
                                lower_priority=args.lower_priority)
        print(json.dumps({"requests": len(result["items"]), "reserved_usd": result["reserved_usd"]}))
        return 0
    if not args.env_file:
        parser.error("API operations require the authorized env-file path.")
    from openai import OpenAI
    api = OpenAI(api_key=load_key(args.env_file), max_retries=0)
    if args.command == "submit":
        result = client.submit(args.directory, api)
    else:
        plan = json.loads((args.directory / "plan.json").read_text(encoding="utf-8"))
        remote = (api.batches.cancel(plan["batch_id"]) if args.command == "cancel"
                  else api.batches.retrieve(plan["batch_id"]))
        result = remote.model_dump()
        atomic_json(args.directory / "remote-status.json", result)
        if args.command == "collect":
            artifacts = {result[field]: api.files.content(result[field]).text
                         for field in ("output_file_id", "error_file_id") if result.get(field)}
            result = client.collect(args.directory, result, artifacts)
    print(json.dumps({key: result[key] for key in ("id", "status", "completed", "outstanding", "invalid")
                      if key in result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
