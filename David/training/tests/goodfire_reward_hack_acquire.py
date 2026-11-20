"""Fetch an ordered public prefix until the eligible conversion quota is met."""
import itertools
import json
import math
from pathlib import Path
from urllib.request import urlopen


def eligible(label):
    flags = label.get("flags") or []
    visible = any(f.get("status") == "enacted" and f.get("channel") in
                  {"content", "tool_calls"} for f in flags)
    negative = label.get("verdict") == "no" or bool(flags) and all(
        f.get("status") == "considered" for f in flags)
    return label.get("judged") and label.get("verdict") != "split" and (visible or negative)


def main():
    root = Path(__file__).resolve().parents[1]
    destination = root / "data" / "downloads" / "goodfire_reward_hack"
    destination.mkdir(parents=True, exist_ok=True)
    base = ("https://huggingface.co/datasets/Goodfire/reward-hack-data/resolve/main/"
            "swebench-verified-kimi-k3-nohack/")
    target = math.ceil(100 * 8600 / 10630 * 1.1)
    # Keep an explicit upper bound even when required filters exclude rows.
    limit = target * 2
    with urlopen(base + "labels/judge_rollouts.jsonl?download=true", timeout=30) as response:
        labels = [json.loads(line) for line in itertools.islice(response, limit)]
    lookup = {label["row_id"]: label for label in labels}
    used, count = [], 0
    temporary = destination / "traces.partial"
    with urlopen(base + "traces.jsonl?download=true", timeout=30) as response, temporary.open("wb") as handle:
        for line in itertools.islice(response, limit):
            row = json.loads(line)
            label = lookup[row["id"]]
            handle.write(line)
            used.append(label)
            count += bool(eligible(label))
            if count >= target:
                break
    temporary.replace(destination / "traces.jsonl")
    with (destination / "judge_rollouts.jsonl").open("w", encoding="utf-8") as handle:
        for label in used:
            handle.write(json.dumps(label, ensure_ascii=False) + "\n")
    print(f"Downloaded source rows={len(used)}; eligible records={count}.")


if __name__ == "__main__":
    main()
