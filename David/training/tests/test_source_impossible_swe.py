"""An unavailable source never fabricates records or accepts unseen schemas."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intent_training.sources.impossible_swe import convert, UninspectedSourceError


class UnavailableSourceTests(unittest.TestCase):
    def test_file_listing_is_not_a_trajectory(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            (folder / "repository-files.json").write_text('["rollouts/data.parquet"]')
            self.assertEqual(list(convert(folder)), [])

    def test_new_rows_require_verified_mapping(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            (folder / "rows.jsonl").write_text('{"is_hack": true}\n')
            with self.assertRaises(UninspectedSourceError):
                list(convert(folder))


if __name__ == "__main__":
    unittest.main()
