"""Build fresh native hard-policy decisions using the trusted upstream rule engine."""

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import random
import re
import subprocess
import sys


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def trusted(workspace):
    """Import only the reviewed pinned vendor checkout, never downloaded scripts."""
    vendor = workspace / "vendor" / "kev"
    revision = subprocess.check_output(
        ["git", "-c", f"safe.directory={vendor.as_posix()}", "-C", str(vendor),
         "rev-parse", "HEAD"], text=True).strip()
    frozen = json.loads((vendor / "evals/hard-v1/manifest.json").read_text())
    entry = json.loads(Path(__file__).with_name("entries").joinpath("policy_long.json").read_text())
    if revision != entry["vendor_revision"]:
        raise ValueError("The trusted upstream checkout differs from its contract revision.")
    for name in frozen["code_sha256"]:
        committed = subprocess.check_output(
            ["git", "-c", f"safe.directory={vendor.as_posix()}", "-C", str(vendor),
             "show", f"HEAD:{name}"])
        if (vendor / name).read_bytes().replace(b"\r\n", b"\n") != committed.replace(b"\r\n", b"\n"):
            raise ValueError("The trusted upstream generator has local changes.")
    if "Apache License" not in (vendor / "LICENSE").read_text():
        raise ValueError("The upstream generator licence is missing.")
    sys.path.insert(0, str(vendor))
    from scripts.hard_v1_common import Ctx
    from scripts.hard_v1_policy import generate, solve
    from kev.api import render, SystemOneRequest
    return Ctx, generate, solve, render, SystemOneRequest, revision


def labels(record, solve):
    """Check the existing source labels against the upstream policy solver."""
    truth = solve(record["_meta"]["facts"])
    for key, question in record["questions"].items():
        matches = [name for name, value in record["_meta"]["facts"]["options_q"][key].items()
                   if value == truth[key]]
        if len(matches) != 1 or question.get("label") != matches[0]:
            raise ValueError("A native policy label differs from its original solver.")


def token_count(tokenizer, text):
    """Match Kev's escaping before counting the pinned tokenizer's actual IDs."""
    text = re.sub(r"<\|([A-Za-z0-9_]+)\|>", r"<¦\1¦>", text)
    return len(tokenizer.encode(text, add_special_tokens=False).ids)


def validate_fit(native, tokenizer, schema):
    """Check Kev's exact state, branch and packed allowances without loading torch."""
    from kev.api import to_record
    request = schema.model_validate({"state": native["state"], "questions": native["questions"]})
    internal, _ = to_record(request)
    state_size = token_count(tokenizer, internal["state"]) + 1
    branches = [2 + token_count(tokenizer, q["instr"])
                + sum(2 + token_count(tokenizer, option) for option in q["options"])
                for q in internal["questions"]]
    if (state_size > 32768 or any(state_size + n > 32768 + 640 for n in branches)
            or state_size + sum(branches) > 32768 + 1664):
        raise ValueError("The native state, question branch or packed record exceeds its allowance.")
    return state_size, branches


def policy_text(record):
    state = record["state"]
    if isinstance(state, dict):
        return state["policy"]
    policy, marker, _ = state.partition("\n\n=== CLAIM ===\n")
    if not marker:
        raise ValueError("The original source policy boundary is absent.")
    return policy


def prepare(raw_dir, *, count=200, seed="policy_long_fresh_train"):
    """Cache fresh train-template originals and rule labels, without any API use."""
    workspace = Path(__file__).resolve().parents[3]
    Ctx, generate, solve, render, schema, revision = trusted(workspace)
    published = json.loads((workspace / "vendor/kev/evals/hard-v1/manifest.json").read_text())
    if seed in published["seeds"]["long_policy"].values():
        raise ValueError("Fresh training instances need a distinct generation seed.")
    raw_dir.mkdir(parents=True, exist_ok=True)
    context = Ctx(seed)
    originals, seen = [], set()
    # Disjoint target and padding pools avoid replaying a target as its own filler.
    for _ in range(count + 100):
        while True:
            template = context.rng.choice((0, 1, 2, 3))
            item = generate(context, template)
            if item is None:
                continue
            key = sha256(render(item["state"]).encode()).hexdigest()
            if key not in seen:
                break
        seen.add(key)
        facts = json.loads(json.dumps(item["facts"]))
        truth = solve(facts)
        questions = deepcopy(item["questions"])
        for qid, question in questions.items():
            matches = [name for name, value in facts["options_q"][qid].items()
                       if value == truth[qid]]
            if len(matches) != 1:
                raise ValueError("The upstream rule engine has ambiguous option values.")
            question["label"] = matches[0]
        record = {"state": item["state"], "questions": questions,
                  "_meta": {"source": "hard_long_policy", "family": "long_policy",
                            "split": "train", "template": f"long_policy/t{template}",
                            "id": key, "facts": facts, **item["meta"]}}
        schema.model_validate({"state": record["state"], "questions": questions})
        originals.append(record)
    source = raw_dir / "native_train.jsonl"
    source.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in originals), encoding="utf-8")
    vendor = workspace / "vendor/kev"
    manifest = {"dataset": "jaredpalmer/kev-suites", "suite": "hard-v1",
                "split": "train", "licence": "Apache-2.0", "revision": revision,
                "seed": seed, "fresh_instances": True, "target_count": count,
                "source_sha256": digest(source), "licence_sha256": digest(vendor / "LICENSE"),
                "tokenizer_sha256": digest(workspace / "data/tokenizer/tokenizer.json"),
                "generation": "trusted upstream long_policy.generate and solve",
                "code_sha256": {name: digest(vendor / name) for name in published["code_sha256"]}}
    (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def convert(raw_dir):
    """Yield native long records with original question wording, labels and source."""
    from tokenizers import Tokenizer
    workspace = Path(__file__).resolve().parents[3]
    _, _, solve, render, schema, revision = trusted(workspace)
    raw_dir = Path(raw_dir)
    manifest = json.loads((raw_dir / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("split") != "train" or manifest.get("suite") != "hard-v1"
            or manifest.get("dataset") != "jaredpalmer/kev-suites"
            or manifest.get("fresh_instances") is not True
            or manifest.get("licence") != "Apache-2.0"
            or manifest.get("revision") != revision):
        raise ValueError("Fresh licensed native train provenance is required.")
    source = raw_dir / "native_train.jsonl"
    tokenizer_path = workspace / "data/tokenizer/tokenizer.json"
    if (digest(source) != manifest["source_sha256"]
            or digest(tokenizer_path) != manifest["tokenizer_sha256"]
            or digest(workspace / "vendor/kev/LICENSE") != manifest["licence_sha256"]):
        raise ValueError("The cached native source or tokenizer hash differs.")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    seen = set()
    for record in records:
        meta = record["_meta"]
        if (meta.get("source") != "hard_long_policy" or meta.get("split") != "train"
                or meta.get("family") != "long_policy"
                or meta.get("template") not in {f"long_policy/t{i}" for i in range(4)}):
            raise ValueError("Only native long_policy training templates are admitted.")
        schema.model_validate({"state": record["state"], "questions": record["questions"]})
        labels(record, solve)
        key = sha256(render(record["state"]).encode()).hexdigest()
        if key != meta["id"] or key in seen:
            raise ValueError("Native state identity is invalid or duplicated.")
        seen.add(key)
    count = manifest["target_count"]
    targets, filler = records[:count], records[count:]
    if not targets or not filler:
        raise ValueError("Separate native target and padding policies are required.")
    rng = random.Random(manifest["seed"] + ":padding")
    for original in targets:
        pool = [record for record in filler
                if record["_meta"]["subtype"] != original["_meta"]["subtype"]]
        rng.shuffle(pool)
        documents, ids = [], []
        desired = rng.randint(16384, 28000)
        def assemble(position):
            blocks = list(documents)
            blocks.insert(position, "TARGET POLICY AND CLAIM\n" + render(original["state"]))
            return ("Apply only TARGET POLICY AND CLAIM to the claim in that document. "
                    "All other numbered documents are unrelated policies for other policyholders.\n\n"
                    + "\n\n".join(f"DOCUMENT {i + 1}\n{block}" for i, block in enumerate(blocks)))
        for other in pool:
            if token_count(tokenizer, assemble(0)) >= desired:
                break
            documents.append(policy_text(other))
            ids.append(other["_meta"]["id"])
        position = rng.randrange(len(documents) + 1)
        state = assemble(position)
        measured = token_count(tokenizer, state)
        if not 16384 <= measured <= 32767:
            raise ValueError("The native policy state does not fit the long-state budget.")
        native = deepcopy(original)
        native["state"] = state
        validate_fit(native, tokenizer, schema)
        yield [], {"native_record": native, "original_native_record": original,
                   "licence": manifest["licence"]}, {
                       "source": "policy_long", "native": True, "objective": [],
                       "source_record_id": original["_meta"]["id"],
                       "trajectory_id": original["_meta"]["id"], "licence": manifest["licence"],
                       "harness": "kev", "split": "train", "state_tokens": measured,
                       "padding_policy_ids": ids, "relevant_position": position,
                       "document_count": len(documents) + 1, "revision": revision}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_dir", type=Path)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare(args.raw_dir, count=args.count)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as handle:
            for events, side, meta in convert(args.raw_dir):
                handle.write(json.dumps({"events": events, "side": side, "meta": meta}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
