"""Render real OpenSWE cuts to obtain construction eligibility votes."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from intent_training.prepare.records import load_tokenizer, prepare_stream
from intent_training.teacher.dispatch import batches, write_batches


def main():
    tokenizer = load_tokenizer(ROOT / "data/tokenizer")
    rows = []
    contexts = []
    with (ROOT / "data/converted/open_swe_bases.jsonl").open(encoding="utf-8") as handle:
        bases = [json.loads(line) for line in handle if line.strip()]
    for index, base in enumerate(bases):
        meta = base["meta"]
        trajectory = str(meta.get("trajectory_id", ""))
        if index < 3:
            cut = max(event["seq"] for event in base["events"] if event["type"] == "turn_completed")
        elif "demisto_demisto-sdk_pr58" in trajectory:
            cut = 11
        else:
            continue
        prepared, _, context = prepare_stream(base, {"cut_seq": cut}, tokenizer)
        rows.extend({key: row[key] for key in ("record_id", "state", "questions", "source", "pass", "teacher_side")}
                    for row in prepared)
        contexts.extend(context if isinstance(context, list) else [context])
    folder = ROOT / "data/votes/anchors"
    manifest = write_batches(batches(rows, count_tokens=lambda text: len(tokenizer(text).input_ids),
                                    input_limit=70000, output_dir=folder), folder)
    (folder / "context.json").write_text(json.dumps(contexts, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"anchors": len(rows), "dispatches": len(manifest), "batches": list(dict.fromkeys(m["batch_id"] for m in manifest))}))


if __name__ == "__main__":
    main()
