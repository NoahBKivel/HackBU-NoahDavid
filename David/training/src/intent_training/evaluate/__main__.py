"""Run frozen held-out scoring or summarize measured evaluation inputs."""

import argparse
import json
from pathlib import Path

from .execution import evaluation_report, score_heldout
from .artifacts import read_jsonl, write_results
from .parity import compare_serving_paths
from .serving import demo_check, serving_checkpoint, serving_probabilities


def main() -> None:
    """Execute an explicitly selected scoring or reporting command."""
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    report = commands.add_parser("report")
    report.add_argument("--input", required=True, type=Path)
    report.add_argument("--output", required=True, type=Path)
    report.add_argument("--resamples", type=int, default=10000)
    report.add_argument("--seed", type=int, default=1)
    report.add_argument("--markdown", type=Path)
    score = commands.add_parser("score-heldout")
    for name in ("manifest", "selected-calibration", "stock-calibration", "output", "once-ledger"):
        score.add_argument("--" + name, required=True, type=Path)
    score.add_argument("--selected", required=True)
    score.add_argument("--stock", required=True)
    score.add_argument("--device", default="cuda")
    score.add_argument("--dtype", choices=("bf16", "fp32"), default="bf16")
    raw = commands.add_parser("score-serving")
    raw.add_argument("--records", required=True, type=Path)
    demo = commands.add_parser("demo")
    demo.add_argument("--events", required=True, type=Path)
    demo.add_argument("--calibration", required=True, type=Path)
    demo.add_argument("--cut-seq", required=True, type=int)
    demo.add_argument("--b-state", required=True, type=int)
    for command in (raw, demo):
        command.add_argument("--checkpoint", required=True)
        command.add_argument("--device", default="cuda")
        command.add_argument("--dtype", choices=("bf16", "fp32"), default="bf16")
        command.add_argument("--unmerged", action="store_true")
        command.add_argument("--output", required=True, type=Path)
    parity = commands.add_parser("parity")
    for name in ("selected-training", "selected-serving", "stock-training", "stock-serving", "output"):
        parity.add_argument("--" + name, required=True, type=Path)
    parity.add_argument("--training-hardware", required=True)
    parity.add_argument("--serving-hardware", required=True)
    args = parser.parse_args()
    if args.command == "report":
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = evaluation_report(payload, resamples=args.resamples, seed=args.seed)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        if args.markdown:
            write_results(result, args.markdown)
    elif args.command == "parity":
        pair = (args.training_hardware, args.serving_hardware)
        result = compare_serving_paths(read_jsonl(args.selected_training), read_jsonl(args.selected_serving),
                                       read_jsonl(args.stock_training), read_jsonl(args.stock_serving),
                                       selected_hardware_pair=pair, stock_hardware_pair=pair)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    elif args.command == "score-heldout":
        import torch

        score_heldout(args.manifest, selected=args.selected, stock=args.stock,
                      selected_calibration=args.selected_calibration, stock_calibration=args.stock_calibration,
                      output=args.output, once_ledger=args.once_ledger, device=args.device,
                      dtype=torch.bfloat16 if args.dtype == "bf16" else torch.float32)
    else:
        import torch

        dtype = torch.bfloat16 if args.dtype == "bf16" else torch.float32
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with serving_checkpoint(args.checkpoint, args.device, dtype=dtype, merge=not args.unmerged) as server:
            if args.command == "demo":
                result = demo_check(server, json.loads(args.events.read_text(encoding="utf-8")),
                                    cut_seq=args.cut_seq, b_state=args.b_state,
                                    calibration=json.loads(args.calibration.read_text(encoding="utf-8")))
                args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            else:
                with args.output.open("x", encoding="utf-8") as stream:
                    for record in read_jsonl(args.records):
                        if record.get("_meta", {}).get("split") != "dev":
                            raise ValueError("Unrestricted serving scoring accepts development records only; held-out scoring uses its once-only command.")
                        for row in serving_probabilities(server, record):
                            stream.write(json.dumps(row, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
