"""Resolve completed records while leaving incomplete or contradictory rows pending."""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.assemble.stream import completed_votes, resolve_ready
from intent_training.teacher.dispatch import MODELS, digest, write_batches


def fixtures(tmp_path):
    records = [{"record_id": identity, "source": "open_swe", "pass": "main", "state": identity,
        "questions": {"M2": {"type": "noul", "instructions": "Does this break the requirement?"}},
        "teacher_side": {"source_labels": [], "reasoning": {}}} for identity in ("single", "paired")]
    batch = {"batch_id": "bounded", "source": "open_swe", "pass": "main", "records": records,
             "input_sha256": digest(records)}
    entries = write_batches([batch], tmp_path)
    def vote(identity, family, value):
        return {"record_id": identity, "batch_id": batch["batch_id"], "model_family": family,
                "model": MODELS[family], "pass": "main", "input_sha256": batch["input_sha256"],
                "votes": {"M2": value}, "evidence": {"M2": "The observed edit is visible."}}
    Path(entries[0]["output"]).write_text("".join(json.dumps(vote(identity, "sol", False)) + "\n"
                                                 for identity in ("single", "paired")), encoding="utf-8")
    metadata = {"single": {"_meta": {"source": "open_swe", "slice": "claim", "construction": "constraint"}},
                "paired": {"_meta": {"source": "open_swe", "slice": "claim"}}}
    return entries, metadata, vote


def test_single_ready_record_resolves_without_waiting_for_paired_terra(tmp_path):
    entries, metadata, vote = fixtures(tmp_path)
    manifests = [tmp_path / "manifest.json"]
    collected = completed_votes(manifests, repository=tmp_path)
    ready, report = resolve_ready(collected, metadata=metadata)
    assert [row["_meta"]["record_id"] for row in ready] == ["single"]
    assert report["awaiting_required_families"][0]["record_id"] == "paired"
    Path(entries[1]["output"]).write_text(json.dumps(vote("paired", "terra", True)) + "\n", encoding="utf-8")
    ready, report = resolve_ready(completed_votes(manifests, repository=tmp_path), metadata=metadata)
    assert len(ready) == 2 and not report["errors"]
    paired = next(row for row in ready if row["_meta"]["record_id"] == "paired")
    assert paired["questions"]["M2"]["target"] == {"false": .5, "true": .5}


def test_conflicting_duplicate_blocks_only_its_record_and_preserves_other_progress(tmp_path):
    entries, metadata, vote = fixtures(tmp_path)
    with Path(entries[0]["output"]).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(vote("paired", "sol", True)) + "\n")
    collected = completed_votes([tmp_path / "manifest.json"], repository=tmp_path)
    ready, report = resolve_ready(collected, metadata=metadata)
    assert [row["_meta"]["record_id"] for row in ready] == ["single"]
    assert report["blocked_record_ids"] == ["paired"]
    assert "conflicting repeated votes" in report["errors"][0]["error"]
