"""Check label semantics, article provenance and real native token accounting."""

import json
from pathlib import Path
import sys

import pytest
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from intent_training.sources.quality_long import permitted, token_count, validate_native


def test_licence_requires_explicit_reuse_grant():
    assert permitted("Creative Commons Attribution 4.0 International License (CC BY 4.0)")
    assert permitted("You may copy it under the Project Gutenberg License")
    for licence in (None, "", "unknown", "https://www.anc.org/OANC/license.txt", "all rights reserved"):
        assert not permitted(licence)


def test_invalid_native_label_is_rejected_before_tokenizing():
    with pytest.raises(ValueError, match="valid label"):
        validate_native({"state": "story", "questions": {"answer": {
            "type": "choice", "instructions": "Why?", "criteria": dict.fromkeys("1234", "x"),
            "label": "5"}}}, None)


def test_actual_converted_answers_and_full_article_padding():
    path = ROOT / "data/converted/quality_long.jsonl"
    if not path.exists():
        pytest.skip("The downloaded source conversion is not present.")
    raw = [json.loads(line) for line in (ROOT / "data/downloads/quality_long/QuALITY.v1.0.1.htmlstripped.train.jsonl").open(encoding="utf-8")]
    questions = {q["question_unique_id"]: (r, q) for r in raw for q in r["questions"]}
    articles = {r["article_id"]: r for r in raw}
    tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    count = 0
    for line in path.open(encoding="utf-8"):
        value = json.loads(line)
        record = value["side"]["native_record"]
        assert value["events"] == []
        assert value["meta"]["native"] is True
        assert value["meta"]["objective"] == []
        assert record["_meta"]["source"] == "quality"
        for qid, question in record["questions"].items():
            original_row, original = questions[qid]
            assert question["instructions"] == original["question"]
            assert question["criteria"][question["label"]] == original["options"][original["gold_label"] - 1]
            assert sorted(question["criteria"].values()) == sorted(original["options"])
        ids = record["_meta"]["article_ids"]
        assert 3 <= len(ids) <= 5
        assert len(set(ids)) == len(ids)
        assert len({articles[i]["author"].casefold() for i in ids}) == len(ids)
        assert ids[record["_meta"]["target_position"]] == original_row["article_id"]
        for article in record["_meta"]["article_licences"]:
            assert permitted(article["licence"])
            assert article["licence"] == articles[article["article_id"]]["license"]
            assert articles[article["article_id"]]["article"] in record["state"]
        state, rows = validate_native(record, tokenizer)
        assert state == record["_meta"]["state_tokens"]
        assert rows == record["_meta"]["row_tokens"]
        count += 1
    assert count > 0


def test_control_token_text_is_escaped():
    tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    assert token_count(tokenizer, "<|im_start|>") == len(tokenizer.encode("<¦im_start¦>", add_special_tokens=False).ids)
