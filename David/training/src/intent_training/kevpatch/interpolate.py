"""Export interpolation of merged adapter products and pointer heads."""

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
from typing import Any


def interpolate_tensor(stock: Any, tuned: Any, alpha: float) -> Any:
    """Interpolate compatible tensors with exact copies at both endpoints."""
    import torch
    if not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("The interpolation weight must be finite and between zero and one.")
    if stock.shape != tuned.shape or stock.dtype != tuned.dtype:
        raise ValueError("Interpolation tensors must have matching shapes and dtypes.")
    if alpha == 0:
        return stock.clone()
    if alpha == 1:
        return tuned.clone()
    if not stock.is_floating_point():
        if not torch.equal(stock, tuned):
            raise ValueError("Nonfloating checkpoint tensors must agree.")
        return stock.clone()
    return stock + alpha * (tuned - stock)


def interpolate_state(stock: dict[str, Any], tuned: dict[str, Any], alpha: float) -> dict[str, Any]:
    """Interpolate every corresponding tensor and reject mismatched checkpoints."""
    if stock.keys() != tuned.keys():
        raise ValueError("The two checkpoints have different tensor names.")
    return {name: interpolate_tensor(value, tuned[name], alpha) for name, value in stock.items()}


def export_checkpoint(stock_path: str, tuned_path: str, alpha: float,
                      destination: Path) -> dict[str, Any]:
    """Write full merged weights that Kev's ordinary Checkpoint loader can serve."""
    import torch
    from kev.checkpoint import Checkpoint, LoadOptions, write_meta
    stock_checkpoint, tuned_checkpoint = Checkpoint(stock_path), Checkpoint(tuned_path)
    fields = ("base", "base_revision", "head_dim", "option_isolation")
    if any(getattr(stock_checkpoint.meta, key) != getattr(tuned_checkpoint.meta, key) for key in fields):
        raise ValueError("The checkpoint architectures or base revisions differ.")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("The output checkpoint directory must be empty.")
    destination.mkdir(parents=True, exist_ok=True)
    options = LoadOptions(dtype=torch.float32, merge=True, temperature=1.0, fused=False, cuda_graphs=False)
    tokenizer, stock = stock_checkpoint.load("cpu", options)
    _, tuned = tuned_checkpoint.load("cpu", options)
    stock_state, tuned_state = stock.lm.state_dict(), tuned.lm.state_dict()
    if not stock_state or not stock.head.state_dict():
        raise ValueError("A checkpoint must contain backbone and pointer-head tensors.")
    result = interpolate_state(stock_state, tuned_state, alpha)
    exact = alpha != 0 or all(torch.equal(value, result[name]) for name, value in stock_state.items())
    head = interpolate_state(stock.head.state_dict(), tuned.head.state_dict(), alpha)
    exact = exact and (alpha != 0 or all(torch.equal(value, head[name]) for name, value in stock.head.state_dict().items()))
    stock.lm.save_pretrained(destination, state_dict=dict(result), max_shard_size="5GB")
    meta = replace(stock_checkpoint.meta, lora=0, weights="full", weights_dtype="fp32", head=head,
                   temperature=1.0, extra={"interpolation": {"stock": stock_path, "tuned": tuned_path, "alpha": alpha}})
    write_meta(destination, meta)
    tokenizer.save_pretrained(destination)
    from safetensors import safe_open
    stored = set()
    serialization_exact = True
    for shard in destination.glob("model*.safetensors"):
        with safe_open(shard, framework="pt", device="cpu") as saved:
            for name in saved.keys():
                stored.add(name)
                serialization_exact = serialization_exact and name in result and torch.equal(saved.get_tensor(name), result[name])
    saved_head = torch.load(destination / "head.pt", map_location="cpu", weights_only=True)["head"]
    serialization_exact = serialization_exact and stored == result.keys() and saved_head.keys() == head.keys()
    serialization_exact = serialization_exact and all(torch.equal(saved_head[name], value) for name, value in head.items())
    if not serialization_exact:
        raise ValueError("The written full checkpoint tensors differ from the interpolation result.")
    evidence = {"alpha": alpha, "backbone_tensors": len(result), "head_tensors": len(head),
                "alpha_zero_tensor_identity": exact if alpha == 0 else None,
                "written_tensor_identity": serialization_exact,
                "weights": "full", "weights_dtype": "fp32"}
    (destination / "interpolation.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return evidence


def main() -> None:
    """Export a specified interpolation between stock and trained checkpoints."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock", required=True)
    parser.add_argument("--tuned", required=True)
    parser.add_argument("--alpha", required=True, type=float)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(export_checkpoint(args.stock, args.tuned, args.alpha, args.out)))


if __name__ == "__main__":
    main()
