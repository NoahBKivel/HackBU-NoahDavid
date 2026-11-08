"""Check isolation preparation, rule evidence and concurrent spending limits."""

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from intent_training.generation.agent_runs import AgentRunner
from intent_training.generation.agent_runs_rules import check_function_boundary

spec = importlib.util.spec_from_file_location("prepare", ROOT / "scripts/agent_run_prepare.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class BoundaryTests(unittest.TestCase):
    def test_body_change_passes_and_context_change_fails(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            before, after = root / "before", root / "after"
            before.mkdir()
            after.mkdir()
            original = "constant = 1\n\ndef f(x):\n    return x\n\nother = 2\n"
            (before / "code.py").write_text(original)
            (after / "code.py").write_text(original.replace("return x", "return x + 1"))
            good = check_function_boundary(before, after, "code.py", "f", ["code.py"])
            self.assertFalse(good["boundary_violated"])
            (after / "code.py").write_text(original.replace("constant = 1", "constant = 3"))
            bad = check_function_boundary(before, after, "code.py", "f", ["code.py"])
            self.assertTrue(bad["boundary_violated"])
            (after / "code.py").write_text(original.replace("f(x)", "f(x, y)"))
            signature = check_function_boundary(before, after, "code.py", "f", ["code.py"])
            self.assertTrue(signature["boundary_violated"])

    def test_unsafe_archive_members_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            archive = root / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as output:
                for filename in ["safe/code.py", "../escape.py", "/absolute.py", "C:/drive.py", "bad\\path.py"]:
                    member = tarfile.TarInfo(filename)
                    member.size = 1
                    output.addfile(member, io.BytesIO(b"x"))
                member = tarfile.TarInfo("safe/link")
                member.type = tarfile.SYMTYPE
                member.linkname = "../../outside"
                output.addfile(member)
            counts = prepare.safe_extract(archive, root / "extracted")
            self.assertEqual(counts, {"files": 1, "rejected": 5})
            self.assertEqual((root / "extracted/safe/code.py").read_text(), "x")
            self.assertFalse((root / "escape.py").exists())

    def test_concurrent_reservations_preserve_cap_and_release_unused(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "results").mkdir()
            (root / "results/budget.json").write_text(json.dumps({"agent_runs_budget_usd": 1,
                                                                  "total_cap_usd": 2}))
            runner = AgentRunner(root)
            with ThreadPoolExecutor(max_workers=8) as pool:
                accepted = list(pool.map(lambda i: runner.reserve(str(i), .5), range(8)))
            self.assertEqual(sum(accepted), 2)
            reservations = json.loads((root / "results/agent-runs/reservations.json").read_text())
            first = next(iter(reservations))
            runner.settle(first, .1, {"input_tokens": 1})
            self.assertTrue(runner.reserve("released", .4))
            self.assertFalse(runner.reserve("overcap", .01))


if __name__ == "__main__":
    unittest.main()
