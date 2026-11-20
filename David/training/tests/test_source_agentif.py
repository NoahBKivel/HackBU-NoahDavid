"""Check paragraph pointers, verbatim units and continuation boundaries."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]
from monitor_format import validate_events
from intent_training.sources.agentif import chinese_heavy, convert, generation_requests, locate_constraints, check_code


class AgentIFTests(unittest.TestCase):
    def row(self):
        return {"id": "sample", "agent_name": "fixture", "input": [
            {"role": "system", "content": "Context only.\n\nYou must use short sentences. Extra context."},
            {"role": "user", "content": "Explain the result."}], "constraints": [
                {"id": 1, "desc": "must use short sentences", "state": "success",
                 "other_info": {"from": "system_para_1"}, "evaluation": []}]}

    def test_zero_based_pointer_and_verbatim_sentence(self):
        matches, residual = locate_constraints(self.row())
        self.assertEqual(matches[0]["text"], "You must use short sentences. ")
        self.assertEqual(matches[0]["paragraph"], 1)
        self.assertFalse(residual)
        row = self.row()
        row["constraints"][0]["other_info"]["from"] = "system_para_0"
        self.assertFalse(locate_constraints(row)[0])

    def test_system_only_projection_emits_no_private_conversation(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "downloads" / "agentif"
            raw.mkdir(parents=True)
            (raw / "eval.json").write_text(json.dumps([self.row()]))
            source_hash = hashlib.sha256((raw / 'eval.json').read_bytes()).hexdigest()
            (raw / 'rf-eligibility.json').write_text(json.dumps({
                'source_sha256': source_hash, 'target_count': 1, 'excluded_source_row_indices': []}))
            events, side, meta = next(convert(raw))
            validate_events(events)
            self.assertTrue(all(not e["agent_text"] for e in events))
            self.assertEqual(meta["objective"], ["RF"])
            self.assertTrue(all(label["question"] == "RF" for label in side["source_labels"]))
            self.assertNotIn('Explain the result.', json.dumps([events, side]))
            self.assertEqual(side['source_provenance']['projection'], 'system_messages_only')

    def test_known_exclusion_and_private_system_case_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            private = self.row()
            private['input'][0]['content'] += '\n\nPatient name: sensitive fixture case.'
            (raw / 'eval.json').write_text(json.dumps([self.row(), self.row(), private]))
            policy = {'source_sha256': hashlib.sha256((raw / 'eval.json').read_bytes()).hexdigest(),
                      'target_count': 3, 'excluded_source_row_indices': [0]}
            (raw / 'rf-eligibility.json').write_text(json.dumps(policy))
            records = list(convert(raw))
            self.assertEqual([meta['source_row_index'] for _, _, meta in records], [1])
            self.assertNotIn('sensitive fixture case', json.dumps(records))
            policy['source_sha256'] = 'different source artifact'
            (raw / 'rf-eligibility.json').write_text(json.dumps(policy))
            with self.assertRaisesRegex(ValueError, 'different source artifact'):
                list(convert(raw))

    def test_chinese_heavy_and_sandbox_command(self):
        self.assertTrue(chinese_heavy([{"content": "\u4e2d\u6587\u5185\u5bb9"}]))
        with patch("intent_training.sources.agentif.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = '{"value": true}'
            self.assertEqual(check_code("irrelevant", "response"), {"value": True})
            args = run.call_args.args[0]
            self.assertIn("--read-only", args)
            self.assertEqual(args[args.index("--network") + 1], "none")
            self.assertIn("--cap-drop", args)


if __name__ == "__main__":
    unittest.main()
