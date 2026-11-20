"""Factor repeated side reasoning without changing any logical teacher payload."""

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json

from .dispatch import MODELS, digest, encoded, prompt
from .openai_client import request_body


REFERENCE_RULE = ("Reasoning values may be references of the form {\"ref\": key}. Resolve each from "
                  "shared_reasoning[key] for that record and sequence before judging. This is exactly "
                  "the original side value, never visible-state evidence. Do not borrow evidence "
                  "between record IDs. State and questions remain literal and authoritative.")


def compact_payload(payload):
    """Share only repeated reasoning values whose references reduce serialized bytes."""
    result = deepcopy(payload)
    values = {}
    counts = Counter()
    for record in result["records"]:
        for value in record.get("teacher_side", {}).get("reasoning", {}).values():
            key = digest(value)
            values[key] = value
            counts[key] += 1
    shared = {}
    for key, count in counts.items():
        size = len(encoded(values[key]).encode("utf-8"))
        reference = len(encoded({"ref": key}).encode("utf-8"))
        if (count - 1) * size > count * reference + len(key) + 4:
            shared[key] = values[key]
    for record in result["records"]:
        reasoning = record.get("teacher_side", {}).get("reasoning", {})
        for seq, value in reasoning.items():
            key = digest(value)
            if key in shared:
                reasoning[seq] = {"ref": key}
    if shared:
        result["shared_reasoning"] = shared
    return result


def expand_payload(payload):
    """Restore every original value for lossless round-trip validation."""
    result = deepcopy(payload)
    shared = result.pop("shared_reasoning", {})
    for record in result["records"]:
        reasoning = record.get("teacher_side", {}).get("reasoning", {})
        for seq, value in reasoning.items():
            if isinstance(value, dict) and set(value) == {"ref"} and value["ref"] in shared:
                reasoning[seq] = deepcopy(shared[value["ref"]])
    return result


def memory_request(batch, family, max_output_tokens=16000):
    """Build the cached request in memory while preserving the canonical record hash."""
    body = request_body(batch, family, max_output_tokens)
    prefix = body["input"][0]["content"][0]
    prefix["text"] += "\n\n" + REFERENCE_RULE
    body["prompt_cache_key"] = sha256(prefix["text"].encode("utf-8")).hexdigest()
    payload = json.loads(body["input"][-1]["content"])
    body["input"][-1]["content"] = encoded(compact_payload(payload))
    return body


def compact_prompt(batch, family, *, actual_model=None):
    """Return the Codex prompt with the same lossless side-data reference protocol."""
    actual_model = actual_model or batch.get("model_overrides", {}).get(family, MODELS[family])
    checked = dict(batch, model_overrides={**batch.get("model_overrides", {}), family: actual_model})
    original = prompt(checked, family)
    prefix, _ = original.rsplit("\n\nFROZEN INPUT:\n", 1)
    prefix += (f"\nInclude vote_slot={family} and actual_model={actual_model} in every envelope. "
               "These identify the logical vote slot and the model actually producing this independent vote.")
    return (prefix + "\n\n" + REFERENCE_RULE + "\n\nFROZEN INPUT:\n"
            + encoded(compact_payload({"records": batch["records"]})))
