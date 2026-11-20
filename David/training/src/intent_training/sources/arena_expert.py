"""Download and convert the Arena expert pairwise preference source."""

import argparse
import ast
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import tokenize


DATASET = "lmarena-ai/arena-expert-5k"
LICENCE = "CC-BY-4.0 (prompts only; response licence unspecified)"


def decode_conversation(value: str) -> list[dict]:
    """Read NumPy display syntax as inert literals with a restricted AST."""
    tokens = []
    previous = None
    for token in tokenize.generate_tokens(io.StringIO(value).readline):
        if token.type in {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT}:
            continue
        current = (token.type, token.string)
        if previous == (tokenize.OP, "}") and current == (tokenize.OP, "{"):
            tokens.append((tokenize.OP, ","))
        tokens.append(current)
        previous = current

    def literal(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, (ast.List, ast.Tuple)):
            return [literal(item) for item in node.elts]
        if isinstance(node, ast.Dict):
            return {literal(k): literal(v) for k, v in zip(node.keys, node.values)}
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "array" and len(node.args) == 1
                and all(k.arg == "dtype" and isinstance(k.value, ast.Name)
                        and k.value.id == "object" for k in node.keywords)):
            return literal(node.args[0])
        raise ValueError("Conversation contains unsupported nonliteral syntax.")

    result = literal(ast.parse(tokenize.untokenize(tokens), mode="eval").body)
    if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
        raise ValueError("Conversation must be a list of messages.")
    return result


def _text(item: dict) -> str:
    content = item["content"]
    if isinstance(content, str):
        return content
    if any(block.get("type") != "text" or block.get("image") for block in content):
        raise ValueError("Nontext content cannot be represented faithfully.")
    return "\n".join(block["text"] for block in content)


def _pair(row: dict):
    from intent_training.sources.events import instruction, message

    conversations = [decode_conversation(row[f"conversation_{arm}"]) for arm in ("a", "b")]
    if any(len(c) < 2 or c[-1].get("role") != "assistant" for c in conversations):
        raise ValueError("A conversation must end with an assistant answer.")
    context = []
    for conversation in conversations:
        history = conversation[:-1]
        if any(item.get("role") not in {"system", "user", "assistant"} for item in history):
            raise ValueError("Unsupported context role.")
        context.append("\n\n".join(f"{item['role']}:\n{_text(item)}" for item in history)
                       if len(history) > 1 else _text(history[0]))
    if any(not text.strip() for text in context):
        raise ValueError("The request is empty.")
    answers = [_text(c[-1]) for c in conversations]
    if any(not answer.strip() for answer in answers):
        raise ValueError("An answer is empty.")
    pair = "arena_expert:" + row["id"]
    for index, arm in enumerate(("a", "b")):
        events = [instruction(context[index]), message(answers[index], 2)]
        side = {"reasoning": {}, "source_labels": [], "licence": LICENCE,
                "outcomes": {"expert_vote": row["winner"], "candidate": "model_" + arm,
                             "basis": "outcome", "origin": "expert preference vote"}}
        meta = {"source": "arena_expert", "source_record_id": pair + ":" + arm,
                "trajectory_id": pair + ":" + arm, "pair_id": pair,
                "objective": ["M1", "G1"], "licence": LICENCE,
                "harness": "expert pairwise chat", "cut_seq": 2}
        yield events, side, meta


def convert(raw_dir: Path):
    """Yield paired final answers in dataset order, skipping incomplete pairs."""
    for path in sorted(raw_dir.glob("rows-*.json")):
        for wrapper in json.loads(path.read_text(encoding="utf-8"))["rows"]:
            if wrapper.get("truncated_cells"):
                continue
            try:
                records = list(_pair(wrapper["row"]))
            except (ValueError, KeyError, SyntaxError, TypeError, tokenize.TokenError):
                continue
            yield from records


def write_output(raw_dir: Path, output: Path, report: Path) -> None:
    from monitor_format import validate_events

    counts = Counter()
    files = []
    for path in sorted(raw_dir.glob("rows-*.json")):
        files.append({"path": path.as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for wrapper in json.loads(path.read_text(encoding="utf-8"))["rows"]:
            counts["raw_rows"] += 1
            counts["vote:" + wrapper["row"]["winner"]] += 1
            if wrapper.get("truncated_cells"):
                counts["filtered:truncated_cells"] += 1
                continue
            try:
                list(_pair(wrapper["row"]))
            except (ValueError, KeyError, SyntaxError, TypeError, tokenize.TokenError) as error:
                counts["filtered:" + str(error)] += 1
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        for events, side, meta in convert(raw_dir):
            validate_events(events)
            stream.write(json.dumps(dict(events=events, side=side, meta=meta), ensure_ascii=False) + "\n")
            counts["output_records"] += 1
    counts["pair_groups"] = counts["output_records"] // 2
    counts["visible_positive_labels"] = 0
    counts["validated_records"] = counts["output_records"]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"source": "arena_expert", "counts": dict(counts),
                                 "source_files": files, "errors": [],
                                 "output": output.as_posix()}, indent=2), encoding="utf-8")
    print(json.dumps(dict(counts)))


def fetch(raw_dir: Path, count: int = 56) -> None:
    """Fetch a bounded prefix from the dataset server without dataset code."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    for offset in range(0, count, 100):
        query = urlencode(dict(dataset=DATASET, config="default", split="train",
                               offset=offset, length=min(100, count - offset)))
        headers = {"Authorization": "Bearer " + os.environ["HF_TOKEN"]}
        with urlopen(Request("https://datasets-server.huggingface.co/rows?" + query,
                             headers=headers), timeout=60) as response:
            payload = json.load(response)
        (raw_dir / f"rows-{offset:06d}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/downloads/arena_expert"))
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--count", type=int, default=56)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--convert", action="store_true")
    args = parser.parse_args()
    if args.fetch:
        fetch(args.raw_dir, args.count)
    if args.inspect:
        payload = json.loads(next(args.raw_dir.glob("rows-*.json")).read_text(encoding="utf-8"))
        for wrapper in payload["rows"][:3]:
            row = wrapper["row"]
            conversations = [decode_conversation(row[f"conversation_{arm}"]) for arm in ("a", "b")]
            print(json.dumps({"row_idx": wrapper["row_idx"], "id": row["id"], "winner": row["winner"],
                              "messages": [[{"role": item["role"], "text_prefix": _text(item)[:180],
                                             "text_length": len(_text(item))} for item in c]
                                           for c in conversations]}, ensure_ascii=True))
    if args.convert:
        import sys
        workspace = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(workspace / "src"))
        sys.path.insert(0, str(workspace.parent))
        write_output(args.raw_dir, Path("data/converted/arena_expert.jsonl"),
                     Path("results/sources/arena_expert.json"))
