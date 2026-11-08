"""Check profiler summaries without a local accelerator or model import."""

from types import SimpleNamespace
import unittest

from intent_training.kevpatch.profile_training import event_rows


class ProfileSummaryTests(unittest.TestCase):
    def test_operator_ranking_uses_device_time(self):
        events = [SimpleNamespace(key='cpu_wait', count=4, self_cpu_time_total=1000,
                                  self_device_time_total=0, device_time_total=0),
                  SimpleNamespace(key='flash_attention', count=2, self_cpu_time_total=2,
                                  self_device_time_total=50, device_time_total=60)]
        rows = event_rows(SimpleNamespace(key_averages=lambda: events))
        self.assertEqual(rows[0]['name'], 'flash_attention')
        self.assertEqual(rows[0]['device_total_us'], 60)

    def test_cpu_only_event_has_zero_device_time(self):
        event = SimpleNamespace(key='encode', count=1, self_cpu_time_total=8)
        self.assertEqual(event_rows(SimpleNamespace(key_averages=lambda: [event]))[0]['device_us'], 0)
