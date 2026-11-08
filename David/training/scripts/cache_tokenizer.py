"""Fetch only the pinned public tokenizer into the training data cache."""

import json
from pathlib import Path


def main() -> None:
    """Save the pinned tokenizer locally and report its resolved token counts."""
    from transformers import AutoTokenizer
    root = Path(__file__).resolve().parents[1]
    contract = json.loads((root / "environment.json").read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(contract["base"],
        revision=contract["base_revision"], cache_dir=str(root / "data" / "tokenizer-cache"), token=False)
    destination = root / "data" / "tokenizer"
    tokenizer.save_pretrained(destination)
    evidence = {"base": contract["base"], "revision": contract["base_revision"],
                "saved_to": str(destination.relative_to(root)),
                "tokenizer_class": type(tokenizer).__name__,
                "sample_tokens": len(tokenizer("USER INSTRUCTIONS\n[I1] Preserve test coverage.",
                                               add_special_tokens=False).input_ids)}
    (root / "results" / "tokenizer.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
