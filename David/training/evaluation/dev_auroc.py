"""Per-question AUROC of stock Kev-4B and the step-309 checkpoint on the shared development records."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(path: Path) -> dict[tuple[str, str], tuple[float, bool]]:
    """Read yes/no rows on base development records as (record, question) -> (score, label)."""
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("options") != ["false", "true"] or not row.get("is_base_dev"):
            continue
        score = row["logits"][1] - row["logits"][0]
        rows[(row["record_id"], row["question_id"])] = (score, row["label"] == "true")
    return rows


def auroc(pairs: list[tuple[float, bool]]) -> float | None:
    """Return the probability that a positive outscores a negative, ties counted half."""
    positives = [score for score, label in pairs if label]
    negatives = [score for score, label in pairs if not label]
    if not positives or not negatives:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in positives for n in negatives)
    return wins / (len(positives) * len(negatives))


def main() -> int:
    """Print the per-question table and the mean over questions with both classes, G1 reported apart."""
    stock = load(HERE / "dev-scores-stock-kev.jsonl")
    tuned = load(HERE / "dev-scores-step309.jsonl")
    shared = set(stock) & set(tuned)
    if any(stock[key][1] != tuned[key][1] for key in shared):
        print("label mismatch between files", file=sys.stderr)
        return 1
    records = {record for record, _ in shared}
    print(f"{len(records)} shared records, {len(shared)} question rows")
    print("question  rows  positives  stock  step-309")
    stock_scores, tuned_scores = [], []
    for question in sorted({q for _, q in shared if "~" not in q}):
        keys = [key for key in shared if key[1] == question]
        positives = sum(stock[key][1] for key in keys)
        a = auroc([stock[key] for key in keys])
        b = auroc([tuned[key] for key in keys])
        cells = "no positives" if a is None else f"{a:.3f}  {b:.3f}"
        print(f"{question:8}  {len(keys):4}  {positives:9}  {cells}")
        if a is not None and question != "G1":
            stock_scores.append(a)
            tuned_scores.append(b)
    print(f"mean over {len(stock_scores)} questions (G1 excluded): "
          f"stock {sum(stock_scores) / len(stock_scores):.3f}, step-309 {sum(tuned_scores) / len(tuned_scores):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
