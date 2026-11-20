"""Apply one authorized relabel epoch without averaging it with initial votes."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .labels import resolve_record
from .receipts import _receipt, canonical_payload
from .stream import queue_votes
from intent_training.teacher.dispatch import MODELS, LUNA_MODEL, digest, validate_vote


class OnceRelabel:
    def __init__(self, *, queue, ledger, cohort, base_pass, questions):
        self.queue, self.cohort, self.base_pass = Path(queue), Path(cohort), base_pass
        self.retry_pass = "main_relabel" if base_pass == "main" else base_pass + "_relabel"
        entries = json.loads(Path(ledger).read_text(encoding="utf-8"))
        self.entries = {}
        hashes = {name: hashlib.sha256((self.cohort / name).read_bytes()).hexdigest()
                  for name in ("model-inputs.jsonl", "initial-receipts.jsonl", "initial-instruments.json")}
        for question in questions:
            matching = [entry for entry in entries if entry.get("question") == question and entry.get("action") == "relabel_once"]
            if len(matching) != 1:
                raise ValueError("An approved question must have exactly one relabel attempt.")
            entry = matching[0]
            if Path(entry["relabel_manifest"]).resolve() != self.queue.resolve() or entry["initial_proofs"] != hashes:
                raise ValueError("The relabel authorization differs from its exact initial file proofs or queue.")
            if hashlib.sha256(entry["supplementary_instructions"].encode()).hexdigest() != entry["instructions_sha256"]:
                raise ValueError("The tightened instructions differ from their approved hash.")
            self.entries[question] = entry
        with (self.cohort / "model-inputs.jsonl").open(encoding="utf-8") as handle:
            self.initial = {row["record_id"]: row for row in map(json.loads, handle)}
        self.collection = queue_votes(self.queue, passes={self.retry_pass})
        self.receipts, self.applied, self.pending, self.stale = {}, {}, set(), set()

    def votes_for(self, prepared, initial_votes, *, claims_dir, repository):
        identity = prepared["record_id"]
        original = self.initial.get(identity)
        if original is None:
            return initial_votes, "outside", {}
        expected = {key: row for key, row in original["questions"].items() if key.split("#", 1)[0] in self.entries}
        same = all(prepared.get(key) == original.get(key) for key in ("state", "source", "teacher_side", "row_context"))
        same = same and prepared["questions"] == original["questions"]
        if not same:
            self.stale.add(identity)
            return initial_votes, "stale_body", {}
        for variant in self.collection.get("variants", {}).get(identity, {}).values():
            row = variant["prepared"]
            if variant["blocked"] or row["questions"] != expected or not {"sol", "terra"} <= set(variant["votes"]):
                continue
            if any(row.get(key) != original.get(key) for key in ("state", "source", "teacher_side", "row_context")):
                continue
            origins = {}
            for slot in ("sol", "terra"):
                origin = variant["origins"][slot]
                actual = origin["actual_model"]
                if actual not in ({MODELS["sol"], MODELS["terra"], LUNA_MODEL} if slot == "sol" else {MODELS["terra"], LUNA_MODEL}):
                    raise ValueError("A relabel epoch has an unauthorized actual model.")
                if origin["model_family"] != ("luna" if actual == LUNA_MODEL else "terra" if actual == MODELS["terra"] else "sol"):
                    raise ValueError("A relabel epoch has inconsistent actual model provenance.")
                batch = self.collection["batches"][(origin["batch_id"], origin["input_sha256"])]
                supplement = batch.get("instruction_supplement", "")
                for key in expected:
                    text = self.entries[key.split("#", 1)[0]]["supplementary_instructions"]
                    if text not in supplement and json.dumps(text, ensure_ascii=False)[1:-1] not in supplement:
                        raise ValueError("The frozen relabel prompt omits its approved clarification.")
                cache_key = (batch["batch_id"], batch["input_sha256"], slot, origin["output"])
                if cache_key not in self.receipts:
                    proof = _receipt(batch, slot, Path(origin["output"]), Path(claims_dir), Path(repository))
                    if proof is not None:
                        raw = Path(origin["output"]).read_text(encoding="utf-8")
                        envelopes = json.loads(raw) if raw.lstrip().startswith("[") else [json.loads(line) for line in raw.splitlines() if line.strip()]
                        identities = [item["record_id"] for item in envelopes]
                        if len(identities) != len(batch["records"]) or set(identities) != {row["record_id"] for row in batch["records"]}:
                            raise ValueError("A relabel artifact does not cover the exact frozen batch.")
                        for envelope in envelopes:
                            validate_vote(envelope, proof[0], slot)
                    self.receipts[cache_key] = proof
                proof = self.receipts[cache_key]
                if proof is None:
                    break
                origins[slot] = {**origin, **proof[1]}
            if set(origins) != {"sol", "terra"}:
                continue
            votes = deepcopy(initial_votes)
            for key in expected:
                votes[key] = {slot: variant["votes"][slot][key] for slot in ("sol", "terra")}
            self.applied[identity] = {"prepared": row, "votes": votes, "origins": origins}
            return votes, "applied", origins
        self.pending.add(identity)
        return initial_votes, "pending", {}


def apply_main_relabels(records, initial_collection, reader, *, claims_dir, repository):
    final_votes = {identity: {slot: dict(values) for slot, values in families.items()}
                   for identity, families in initial_collection["votes"].items()}
    for record in records:
        identity = record["_meta"]["record_id"]
        if identity not in reader.initial:
            continue
        prepared = initial_collection["prepared"][identity]
        joined = {key: {slot: values[key] for slot, values in final_votes[identity].items() if key in values}
                  for key in prepared["questions"]}
        votes, status, origins = reader.votes_for(prepared, joined, claims_dir=claims_dir, repository=repository)
        meta = record["_meta"]
        meta["main_relabel_parent_record_id"] = identity
        meta["main_relabel_required_questions"] = sorted(reader.entries)
        meta["main_relabel_complete"] = status == "applied"
        if status != "applied":
            continue
        keys = reader.applied[identity]["prepared"]["questions"]
        stage = {"state": record["state"], "questions": deepcopy(keys), "_meta": deepcopy(meta)}
        resolved, audit = resolve_record(stage, {key: votes[key] for key in keys}, allocation_mode="paired")
        meta["main_relabel_initial_questions"] = {key: deepcopy(record["questions"][key]) for key in keys}
        meta["main_relabel_vote_origins"] = {key: deepcopy(origins) for key in keys}
        meta["main_relabel_audit"] = audit
        for key in keys:
            record["questions"][key] = resolved["questions"][key]
            for slot in ("sol", "terra"):
                final_votes[identity][slot][key] = votes[key][slot]
    return final_votes
