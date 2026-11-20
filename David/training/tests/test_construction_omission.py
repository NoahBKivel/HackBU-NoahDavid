"""Check paired omission cuts, provenance, and preserved real events."""

from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))
from intent_training.constructions.omission import build, generation_requests, parse_alignment_response
from monitor_format import validate_events


def fixture():
    def event(seq, tool=None, text=""):
        return {"seq": seq, "type": "tool_completed" if tool else "session_started",
                "ts": "", "new_items": [], "action": {
                    "tool": tool, "args": {"command": text}, "result_text": "",
                    "is_error": False} if tool else {}, "agent_text": "",
                "agent_thinking": "", "todos": [], "turn": {}}
    events = [event(1), event(2, "Bash", "inspect"), event(3, "Bash", "verify"),
              event(4, "Read", "notes.txt"), event(5, "Bash", "package")]
    events[0]["new_items"] = [{"kind": "user_instruction", "id": "I1",
                               "text": "1. Inspect files.\n2. Verify changes.\n3. Package files."}]
    alignment = {"source_seq": 1, "requirement": "Verify changes.",
                 "remove_seqs": [3], "continuation_seq": 5}
    side = {"reasoning": {"3": "A private note.", "5": "Later note."},
            "source_labels": [{"question": "L5", "value": False, "event_seq": 5,
                               "basis": "visible", "origin": "rule"}]}
    meta = {"source": "example", "trajectory_id": "run", "group_id": "original",
            "source_record_id": "item", "licence": "MIT"}
    return events, side, meta, alignment


class OmissionTests(unittest.TestCase):
    def test_pair_preserves_events_groups_and_cut_timing(self):
        events, side, meta, alignment = fixture()
        original = deepcopy((events, side, meta))
        positive, negative = list(build(events, side, meta, alignment=alignment))
        self.assertEqual([e["seq"] for e in positive[0]], [1, 2, 4, 5])
        self.assertEqual([e["seq"] for e in negative[0]], [1, 2])
        for output, intended in ((positive, True), (negative, False)):
            validate_events(output[0])
            self.assertEqual(output[2]["group_id"], meta["group_id"])
            self.assertEqual(output[1]["construction"]["intended"], {"L5": intended})
            self.assertEqual(output[1]["source_labels"], [])
            self.assertEqual(output[2]["base_source_labels"], side["source_labels"])
            for event in output[0]:
                self.assertEqual(event, events[event["seq"] - 1])
        self.assertEqual(positive[2]["pair_id"], negative[2]["pair_id"])
        self.assertNotIn("3", positive[1]["reasoning"])
        self.assertEqual(negative[1]["reasoning"], {})
        self.assertEqual((events, side, meta), original)

    def test_request_has_prefix_references_and_accepts_central_response(self):
        events, side, meta, alignment = fixture()
        request, = generation_requests(events, side, meta)
        self.assertEqual(set(request), {"id", "purpose", "prompt", "max_output_tokens", "refs"})
        self.assertLessEqual(max(request["refs"]["event_seqs"]), request["refs"]["cut_seq"])
        outputs = list(build(events, side, meta,
                             generated_texts={request["id"]: json.dumps(alignment)}))
        self.assertEqual(len(outputs), 2)
        self.assertEqual(list(build(events, side, meta)), [])
        self.assertEqual(list(build(events, side, meta,
                                   generated_texts={request["id"]: "null"})), [])

    def test_rejects_unsupported_requirements_and_wrong_continuation(self):
        events, side, meta, alignment = fixture()
        for changes in ({"requirement": "Invented task."}, {"continuation_seq": 4},
                        {"remove_seqs": [2, 4]}, {"remove_seqs": [99]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                list(build(events, side, meta, alignment={**alignment, **changes}))
        events[2]["new_items"] = deepcopy(events[0]["new_items"])
        with self.assertRaises(ValueError):
            list(build(events, side, meta, alignment=alignment))

    def test_limits_attempts_and_does_not_invent_numbered_plans(self):
        events, side, meta, alignment = fixture()
        for attempt in (0, 4, True):
            with self.assertRaises(ValueError):
                list(build(events, side, meta, alignment=alignment, attempt=attempt))
        events[0]["new_items"][0]["text"] = "Please improve these files."
        self.assertEqual(list(generation_requests(events, side, meta)), [])
        events[1]["todos"] = [{"content": "Verify changes.", "status": "pending"}]
        self.assertEqual(len(list(generation_requests(events, side, meta))), 1)


class AlignmentResponseTests(unittest.TestCase):
    def envelope(self, text, **changes):
        return {"status": "completed", "stop_reason": "end_turn", "text": text, **changes}

    def test_only_lossless_json_fences_are_normalized(self):
        alignment = fixture()[3]
        text = json.dumps(alignment)
        self.assertEqual(parse_alignment_response(self.envelope(text)), alignment)
        self.assertEqual(parse_alignment_response(self.envelope("```json\n" + text + "\n```")), alignment)
        self.assertIsNone(parse_alignment_response(self.envelope("null")))
        self.assertIsNone(parse_alignment_response(self.envelope("```json\nnull\n```")))

    def test_rejects_incomplete_refused_missing_and_prose_wrapped_content(self):
        for envelope in (self.envelope("{}"), self.envelope(None), self.envelope("{\"source_seq\":"),
                         self.envelope("I cannot do that."), self.envelope("null", stop_reason="max_tokens"),
                         self.envelope("null", status="failed"),
                         self.envelope("Here is the result.\n```json\nnull\n```")):
            with self.subTest(envelope=envelope), self.assertRaises(ValueError):
                parse_alignment_response(envelope)


if __name__ == "__main__":
    unittest.main()
