"""Preserve QuALITY answers while burying complete stories among other authors."""

import hashlib
import json
from pathlib import Path
import random
import re

from .reading import rows


def permitted(licence):
    """Accept explicit reuse grants, never an uninspected licence URL alone."""
    return isinstance(licence, str) and (
        ("Project Gutenberg License" in licence and "You may copy it" in licence)
        or "Creative Commons Attribution 4.0 International License (CC BY 4.0)" in licence
    )


def token_count(tokenizer, text):
    """Match Kev user_tokens escaping and omit automatic special tokens."""
    text = re.sub(r"<\|([A-Za-z0-9_]+)\|>", r"<¦\1¦>", text)
    return len(tokenizer.encode(text, add_special_tokens=False).ids)


def native_counts(record, tokenizer):
    """Count the state delimiter and each choice branch exactly as Kev encode."""
    state = 1 + token_count(tokenizer, record["state"])
    counts = []
    for question in record["questions"].values():
        branch = 2 + token_count(tokenizer, question["instructions"])
        branch += sum(2 + token_count(tokenizer, f"{key}: {value}")
                      for key, value in question["criteria"].items())
        counts.append(state + branch)
    return state, counts


def validate_native(record, tokenizer):
    """Reject missing labels, malformed choices and records outside the long band."""
    if not isinstance(record.get("state"), str) or not record.get("questions"):
        raise ValueError("A native record needs state text and questions.")
    for question in record["questions"].values():
        if (question.get("type") != "choice" or len(question.get("criteria", {})) != 4
                or question.get("label") not in question["criteria"]
                or not isinstance(question.get("instructions"), str)):
            raise ValueError("A QuALITY question needs four choices and a valid label.")
    state, counts = native_counts(record, tokenizer)
    if state < 16384 or max(counts) > 32768:
        raise ValueError("A native record falls outside the exact long token band.")
    return state, counts


def _state(stories, target):
    pointer = (f"Answer only about target article {target['article_id']}: "
               f"{target['title']} by {target['author']}.\n\n")
    return pointer + "\n\n".join(
        f"ARTICLE {story['article_id']}: {story['title']}\nAUTHOR: {story['author']}\n"
        + story["article"] for story in stories)


def convert(raw_dir: Path):
    """Read only downloaded train rows and emit labelled native Kev records."""
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(Path(__file__).resolve().parents[3]
                                       / "data/tokenizer/tokenizer.json"))
    source_rows = list(rows(raw_dir))
    articles = {}
    for row in source_rows:
        if permitted(row.get("license")) and row.get("author") and row.get("article"):
            previous = articles.setdefault(row["article_id"], row)
            if any(previous[k] != row[k] for k in ("article", "author", "license")):
                raise ValueError("Repeated article metadata disagrees.")
    emitted = 0
    for row in source_rows:
        if row["article_id"] not in articles:
            continue
        pool = [story for story in articles.values()
                if story["article_id"] != row["article_id"]
                and story["author"].casefold() != row["author"].casefold()]
        for original in row["questions"]:
            if emitted >= 200:
                return
            gold = original.get("gold_label")
            if type(gold) is not int or gold not in range(1, 5) or len(original["options"]) != 4:
                continue
            qid = original["question_unique_id"]
            rng = random.Random(int.from_bytes(hashlib.sha256(qid.encode()).digest(), "big"))
            order = list(range(4))
            rng.shuffle(order)
            question = {"type": "choice", "instructions": original["question"],
                        "criteria": {str(i + 1): original["options"][j] for i, j in enumerate(order)},
                        "label": str(order.index(gold - 1) + 1), "src": "quality"}
            record = None
            for _ in range(128):
                count = rng.randint(2, 4)
                candidates = pool.copy()
                rng.shuffle(candidates)
                padding, authors = [], {row["author"].casefold()}
                for story in candidates:
                    if story["author"].casefold() not in authors:
                        padding.append(story)
                        authors.add(story["author"].casefold())
                    if len(padding) == count:
                        break
                if len(padding) != count:
                    continue
                # Length is invariant under article order; draw the target position
                # only after accepting length to keep its draw uniform.
                trial = {"state": _state([row] + padding, row), "questions": {qid: question}}
                state_tokens, row_tokens = native_counts(trial, tokenizer)
                if state_tokens >= 16384 and max(row_tokens) <= 32768:
                    position = rng.randrange(count + 1)
                    padding.insert(position, row)
                    trial["state"] = _state(padding, row)
                    try:
                        state_tokens, row_tokens = validate_native(trial, tokenizer)
                    except ValueError:
                        continue
                    record = trial
                    break
            if record is None:
                continue
            licences = [{"article_id": story["article_id"], "author": story["author"],
                         "title": story["title"], "url": story["url"],
                         "licence": story["license"]} for story in padding]
            provenance = {"source": "quality", "licence": row["license"],
                          "article_licences": licences, "target_position": position,
                          "article_ids": [story["article_id"] for story in padding],
                          "original_gold_label": gold, "option_permutation": order,
                          "state_tokens": state_tokens, "row_tokens": row_tokens,
                          "source_record_id": qid, "group_id": row["article_id"]}
            record["_meta"] = provenance
            meta = {"source": "quality_long", "native": True, "trajectory_id": row["article_id"],
                    "task_id": row["article_id"], "source_record_id": qid, "objective": [],
                    "licence": row["license"], "harness": "QuALITY v1.0.1"}
            yield [], {"native_record": record, "licence": row["license"]}, meta
            emitted += 1


def main():
    """Persist conversion and measured source evidence in the local workspace."""
    root = Path(__file__).resolve().parents[3]
    raw = root / "data/downloads/quality_long"
    destination = root / "data/converted/quality_long.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    records = list(convert(raw))
    with destination.open("w", encoding="utf-8") as handle:
        for events, side, meta in records:
            handle.write(json.dumps({"events": events, "side": side, "meta": meta}, ensure_ascii=False) + "\n")
    observed = list(rows(raw))
    report = {"source": "quality_long", "raw_rows": len(observed),
              "raw_articles": len({r['article_id'] for r in observed}),
              "raw_questions": sum(len(r['questions']) for r in observed),
              "licence_rejected_rows": sum(not permitted(r.get('license')) for r in observed),
              "converted_records": len(records), "target": 200, "errors": [],
              "state_token_range": [min(s['native_record']['_meta']['state_tokens'] for _, s, _ in records),
                                    max(s['native_record']['_meta']['state_tokens'] for _, s, _ in records)],
              "files": [{"path": str(p.relative_to(root)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                        for p in raw.glob("*.jsonl")]}
    target = root / "results/sources/quality_long.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
