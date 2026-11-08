"""Render official preference comparisons for frozen held-out evaluation."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT.parent)]
from intent_training.splits.heldout_preferences import preference_pairs, preference_records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--llmbar', type=Path, required=True)
    parser.add_argument('--rewardbench2', type=Path, required=True)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(args.tokenizer))

    class TokenizerAdapter:
        def __call__(self, text, add_special_tokens=False):
            from types import SimpleNamespace
            return SimpleNamespace(input_ids=tokenizer.encode(text, add_special_tokens=add_special_tokens).ids)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        for pair in preference_pairs(args.llmbar, args.rewardbench2):
            for record in preference_records(pair, TokenizerAdapter()):
                stream.write(json.dumps(record, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
