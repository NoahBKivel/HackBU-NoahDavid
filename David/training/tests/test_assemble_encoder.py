"""Check sibling admission using the real pinned BPE and Kev encoder."""

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent), str(ROOT / "vendor/kev")]

from monitor_format import fill_question
from intent_training.assemble import kev_fit, pack_siblings


def test_actual_encoder_packs_full_state_siblings_without_truncating():
    from tokenizers import Tokenizer
    raw = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    class PinnedTokenizer:
        def __call__(self, text, add_special_tokens=False):
            return SimpleNamespace(input_ids=raw.encode(text, add_special_tokens=add_special_tokens).ids)
        def convert_tokens_to_ids(self, token):
            return raw.token_to_id(token)
    fits = kev_fit(PinnedTokenizer())
    record = {"state": " state" * 32700,
              "questions": {"M2#" + str(index): dict(fill_question("M2"), label=False) for index in range(40)},
              "_meta": {"source": "observed", "record_id": "oversized"}}
    assert not fits(record)
    siblings = pack_siblings(record, fits=fits)
    assert len(siblings) > 1
    assert all(fits(sibling) for sibling in siblings)
    assert all(sibling["state"] == record["state"] for sibling in siblings)
    assert sum(len(sibling["questions"]) for sibling in siblings) == len(record["questions"])
