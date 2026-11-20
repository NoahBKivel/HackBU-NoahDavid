import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.teacher.dispatch import _batch, encoded, batch_input_hash
from intent_training.teacher.claims import claim_next, batch_claim_path, claim_batch_once
from intent_training.teacher.queue_index import request_rescan, refresh_index


def task(rid, stage="requirements", state="Use English."):
    row = {"record_id": rid, "state": state, "questions": {"RF": {"type": "noul"}},
           "source": "example", "pass": stage, "teacher_side": {}}
    return {"batch": _batch("example", stage, [row]), "allocation": "single_sol", "required_families": ["sol"]}


def append(path, value):
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded(value) + "\n")


def test_fresh_process_uses_compact_index_not_previous_main_payload(tmp_path):
    queue, claims = tmp_path / "queue", tmp_path / "claims"
    append(queue, task("heavy", "main", "HEAVY_MAIN_SENTINEL" + "x" * 100000))
    first, second = task("first"), task("second")
    append(queue, first)
    append(queue, second)
    assert claim_next(queue, claims, "a", ("single_sol",), allowed_passes=("requirements",))["batch"]["batch_id"] == first["batch"]["batch_id"]
    code = f"""import sys,json
sys.path[:0]={[str(ROOT / 'src'), str(ROOT.parent)]!r}
from intent_training.teacher.claims import claim_next
original=json.loads
def guarded(value,*args,**kwargs):
    assert 'HEAVY_MAIN_SENTINEL' not in str(value), 'previous main payload was reparsed'
    return original(value,*args,**kwargs)
json.loads=guarded
item=claim_next(sys.argv[1],sys.argv[2],'b',('single_sol',),allowed_passes=('requirements',))
print(item['batch']['input_sha256'])
"""
    result = subprocess.check_output([sys.executable, "-c", code, str(queue), str(claims)], text=True)
    assert result.strip() == second["batch"]["input_sha256"]


def test_append_rescan_and_hash_guard_preserve_claims(tmp_path):
    queue, claims = tmp_path / "queue", tmp_path / "claims"
    first = task("first")
    append(queue, first)
    assert claim_next(queue, claims, "owner", ("single_sol",), resume_owned=True)
    assert claim_next(queue, claims, "owner", ("single_sol",), resume_owned=True) is None
    request_rescan(claims)
    recovered = claim_next(queue, claims, "owner", ("single_sol",), resume_owned=True)
    assert recovered["claim"]["owner"] == "owner"
    second = task("second")
    append(queue, second)
    assert claim_next(queue, claims, "other", ("single_sol",))["batch"]["batch_id"] == second["batch"]["batch_id"]
    third = task("third")
    append(queue, third)
    refresh_index(queue, claims)
    body = queue.read_text(encoding="utf-8")
    position = body.rfind("Use English.")
    queue.write_text(body[:position] + body[position:].replace("Use English.", "Use Spanish.", 1), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="changed after indexing"):
        claim_next(queue, claims, "last", ("single_sol",))
    assert not batch_claim_path(claims, third["batch"]).exists()


def test_index_cannot_change_required_vote_families(tmp_path):
    queue, claims = tmp_path / "queue", tmp_path / "claims"
    original = task("original")
    append(queue, original)
    state = refresh_index(queue, claims)
    index = Path(state["index"])
    metadata = json.loads(index.read_text(encoding="utf-8"))
    metadata["required_families"] = ["sol", "terra"]
    index.write_text(encoded(metadata) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="routing or family"):
        claim_next(queue, claims, "owner", ("single_sol",))
    assert not batch_claim_path(claims, original["batch"]).exists()


def test_supplement_is_part_of_the_frozen_claim_input(tmp_path):
    batch = task("clarified", "main_relabel")["batch"]
    batch["instruction_supplement"] = "Use only the visible latest action."
    batch["input_sha256"] = batch_input_hash(batch)
    assert claim_batch_once(tmp_path, batch, "owner", ["sol", "terra"])
    changed = dict(batch, instruction_supplement="Different clarification.")
    with pytest.raises(ValueError, match="frozen hash"):
        claim_batch_once(tmp_path, changed, "other", ["sol", "terra"])
