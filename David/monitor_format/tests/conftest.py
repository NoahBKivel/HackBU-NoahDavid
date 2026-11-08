"""Load immutable fixtures and supply isolated tokenizer dependencies."""

import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class CharacterTokenizer:
    def __call__(self, text: str, add_special_tokens: bool = False) -> SimpleNamespace:
        return SimpleNamespace(input_ids=[ord(character) for character in text])


@pytest.fixture
def char_tokenizer():
    return CharacterTokenizer()


@pytest.fixture
def real_tokenizer():
    from tokenizers import Tokenizer
    root = Path(__file__).resolve().parents[2] / "training"
    cached = Path(os.environ.get("MONITOR_TOKENIZER_PATH", root / "data" / "tokenizer"))
    tokenizer = Tokenizer.from_file(str(cached / "tokenizer.json"))

    class PinnedTokenizer:
        def __call__(self, text: str, add_special_tokens: bool = False) -> SimpleNamespace:
            return SimpleNamespace(input_ids=tokenizer.encode(text, add_special_tokens=add_special_tokens).ids)

    return PinnedTokenizer()


@pytest.fixture
def sample_events():
    return json.loads((Path(__file__).parent / "fixtures" / "mod-session.json").read_text(encoding="utf-8"))


@pytest.fixture
def tool_events():
    return json.loads((Path(__file__).parent / "fixtures" / "all-tools.json").read_text(encoding="utf-8"))
