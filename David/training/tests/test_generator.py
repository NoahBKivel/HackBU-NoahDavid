"""Verify queue deduplication, API envelopes and shared spending safety."""

from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
from pathlib import Path
import sys
import shutil
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from intent_training.generation.generator import Generator
from intent_training.generation.request_io import fingerprint, load_requests
from intent_training.generation.spending import Spending, MODELS, usage_cost


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / "results").mkdir()
        (self.root / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/scan_secrets.py", self.root / "scripts/scan_secrets.py")
        (self.root / "results/budget.json").write_text(json.dumps({"generation_reserve_usd": 1, "total_cap_usd": 2}))

    def test_concurrent_spending_and_unknown_cost_hold(self):
        spending = Spending(self.root)
        with ThreadPoolExecutor(max_workers=8) as pool:
            models = list(pool.map(lambda i: spending.reserve(str(i), .25, str(i)), range(8)))
        self.assertEqual(sum(model is not None for model in models), 4)
        self.assertEqual(models.count(MODELS[0]), models.count(MODELS[1]))
        spending.settle("0", None, {}, "failed")
        self.assertIsNone(spending.reserve("another", .01, "a"))
        self.assertTrue(spending.state()["0"]["charged_usd"] == .25)

    def test_other_active_run_reservations_count(self):
        target = self.root / "results/agent-runs"
        target.mkdir()
        (target / "reservations.json").write_text(json.dumps({"run": {"maximum_usd": 1.9}}))
        self.assertIsNone(Spending(self.root).reserve("text", .2, "hash"))

    def test_request_conflict_and_path_escape_fail(self):
        target = self.root / "data/generation/requests"
        target.mkdir(parents=True)
        item = {"id": "sample", "purpose": "sample", "prompt": "Describe this.", "max_output_tokens": 20}
        path = target / "sample.jsonl"
        path.write_text(json.dumps(item) + "\n" + json.dumps(item))
        self.assertEqual(len(load_requests(self.root)), 1)
        path.write_text(json.dumps(item) + "\n" + json.dumps(dict(item, prompt="Changed.")))
        with self.assertRaises(ValueError):
            load_requests(self.root)
        path.write_text(json.dumps(dict(item, id="../outside")))
        with self.assertRaises(ValueError):
            load_requests(self.root)

    def test_string_content_preserved_and_not_billed_twice(self):
        usage = {"input_tokens": 10, "output_tokens": 4}
        response = SimpleNamespace(content='{"answer":"complete"}', usage=SimpleNamespace(model_dump=lambda **_: usage),
                                   stop_reason="end_turn", id="provider-response")
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return response
        runner = Generator(self.root, SimpleNamespace(messages=SimpleNamespace(create=create)))
        request = {"id": "answer", "purpose": "sample", "prompt": "Describe this.", "max_output_tokens": 20}
        self.assertEqual(runner.generate(request)["status"], "completed")
        self.assertEqual(runner.generate(request)["status"], "cached")
        saved = json.loads((runner.output / "answer.json").read_text())
        self.assertEqual(saved["text"], response.content)
        self.assertEqual(saved["usage"], usage)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len((self.root / "results/spend.jsonl").read_text().splitlines()), 1)

    def test_failure_never_persists_raw_exception(self):
        def create(**kwargs):
            raise RuntimeError("sensitive error detail")
        runner = Generator(self.root, SimpleNamespace(messages=SimpleNamespace(create=create)))
        result = runner.generate({"id": "failure", "purpose": "sample", "prompt": "Describe this.", "max_output_tokens": 20})
        self.assertEqual(result["status"], "failed")
        self.assertFalse((runner.output / "failure.json").exists())
        saved = (runner.spending.folder / "failure.error.json").read_text()
        self.assertNotIn("sensitive", saved)
        self.assertFalse(runner.spending.state()["failure"]["actual_cost_known"])

    def test_cache_tiers_and_inclusive_output_pricing(self):
        usage = {"input_tokens": 100001, "output_tokens": 10, "cache_creation_input_tokens": 5,
                 "cache_creation": {"ephemeral_5m_input_tokens": 3, "ephemeral_1h_input_tokens": 2},
                 "cache_read_input_tokens": 7, "output_tokens_details": {"thinking_tokens": 8}}
        expected = (100001 * .5 + 10 * 2.5 + 3 * .625 + 2 * 1 + 7 * .05) / 1000000
        self.assertAlmostEqual(usage_cost(MODELS[0], usage), expected)

    def test_credential_markers_block_before_any_reservation(self):
        runner = Generator(self.root)
        marker = "-----" + "BEGIN RSA PRIVATE KEY" + "-----"
        result = runner.generate({"id": "blocked", "purpose": "sample", "prompt": marker, "max_output_tokens": 20})
        self.assertEqual(result["status"], "credential_marker_blocked")
        self.assertEqual(runner.spending.state(), {})

    def test_truncated_response_is_not_a_consumable_answer(self):
        usage = {"input_tokens": 10, "output_tokens": 4}
        response = SimpleNamespace(content="partial", usage=SimpleNamespace(model_dump=lambda **_: usage),
                                   stop_reason="max_tokens", id="provider-response")
        client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: response))
        runner = Generator(self.root, client)
        request = {"id": "truncated", "purpose": "sample", "prompt": "Describe this.", "max_output_tokens": 4}
        self.assertEqual(runner.generate(request)["status"], "incomplete")
        self.assertFalse((runner.output / "truncated.json").exists())
        self.assertTrue(runner.spending.state()["truncated"]["actual_cost_known"])

    def test_approved_fingerprint_rejects_changed_prompt_before_reserving(self):
        approved = hashlib.sha256(b"Approved prompt.").hexdigest()
        runner = Generator(self.root, approved_prompt_sha256=approved)
        with self.assertRaises(ValueError):
            runner.generate({"id": "changed", "purpose": "sample", "prompt": "Another prompt.", "max_output_tokens": 4})
        self.assertEqual(runner.spending.state(), {})

    def test_refusal_is_billed_but_never_published_or_automatically_retried(self):
        usage = {"input_tokens": 10, "output_tokens": 4}
        response = SimpleNamespace(content='{"messages":["partial',
                                   usage=SimpleNamespace(model_dump=lambda **_: usage),
                                   stop_reason="refusal", id="provider-refusal")
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return response
        runner = Generator(self.root, SimpleNamespace(messages=SimpleNamespace(create=create)))
        request = {"id": "refused", "purpose": "sample", "prompt": "Describe this.", "max_output_tokens": 20}
        self.assertEqual(runner.generate(request)["status"], "refused")
        self.assertFalse((runner.output / "refused.json").exists())
        saved = json.loads((runner.spending.folder / "refused.refused.json").read_text())
        self.assertEqual(saved["stop_reason"], "refusal")
        self.assertEqual(saved["text"], response.content)
        self.assertTrue(runner.spending.state()["refused"]["actual_cost_known"])
        self.assertEqual(runner.generate(request)["status"], "refused")
        retrying = Generator(self.root, runner.client, retry_failed=True)
        self.assertEqual(retrying.generate(request)["status"], "refused")
        self.assertEqual(len(calls), 1)

    def test_legacy_refusal_envelope_is_not_a_cached_completion(self):
        runner = Generator(self.root)
        request = {"id": "legacy", "purpose": "sample", "prompt": "Describe this.", "max_output_tokens": 20}
        path = runner.output / "legacy.json"
        path.write_text(json.dumps({"request_hash": fingerprint(request), "stop_reason": "refusal",
                                    "text": "preserved refusal"}))
        self.assertEqual(runner.generate(request)["status"], "refused")
        self.assertTrue(path.exists())
        self.assertEqual(runner.spending.state(), {})

    def test_correction_text_generation_keeps_reasoning_between_tools(self):
        usage = {"input_tokens": 10, "output_tokens": 4}
        response = SimpleNamespace(content='{"events":[]}',
                                   usage=SimpleNamespace(model_dump=lambda **_: usage),
                                   stop_reason="end_turn", id="correction-response")
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return response
        runner = Generator(self.root, SimpleNamespace(messages=SimpleNamespace(create=create)))
        runner.spending.reserve("seed", .001, "seed")
        runner.spending.settle("seed", 0, {}, "completed")
        for identifier in ("first", "second"):
            request = {"id": identifier, "purpose": "correction_window",
                       "prompt": "Continue the coding conversation.", "max_output_tokens": 4096}
            self.assertEqual(runner.generate(request)["status"], "completed")
        self.assertEqual(calls[0]["model"], MODELS[1])
        self.assertEqual(calls[0]["thinking"], {"type": "between_tools"})
        self.assertEqual(calls[1]["model"], MODELS[0])
        self.assertEqual(calls[1]["thinking"], {"type": "disabled"})
        self.assertTrue(all("tools" not in call for call in calls))


if __name__ == "__main__":
    unittest.main()
