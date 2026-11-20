"""Prove that linked-record validation rejects a planted implementation fault."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


def mutation_case(name: str, relative: str, before: str, after: str, test: str) -> dict:
    """Require a planted defect to fail its real test and its restoration to pass."""
    root = Path(__file__).resolve().parents[1]
    target = root / relative
    original = target.read_text(encoding="utf-8")
    if original.count(before) != 1:
        raise ValueError("The expected mutation anchor changed.")
    command = [sys.executable, "-m", "pytest", "tests/test_kev_extensions.py", "-q",
               "--basetemp", str(root / "results" / "trainer" / f"teeth-temp-{name}"), "-k", test]
    output = root / "results" / "trainer"
    output.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(original.replace(before, after, 1), encoding="utf-8")
        red = subprocess.run(command, cwd=root, capture_output=True, text=True)
    finally:
        target.write_text(original, encoding="utf-8")
    green = subprocess.run(command, cwd=root, capture_output=True, text=True)
    evidence = {"time": datetime.now(timezone.utc).isoformat(), "mutation": name,
                "planted_returncode": red.returncode, "restored_returncode": green.returncode,
                "planted_output": red.stdout, "restored_output": green.stdout}
    (output / f"{name}-teeth.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in evidence.items() if not key.endswith("output")}))
    if red.returncode != 1 or green.returncode != 0:
        raise RuntimeError("The mutation did not fail and recover as required.")
    return evidence


def main() -> None:
    """Prove grouping, continuation and interpolation checks reject planted defects."""
    base = "src/intent_training/kevpatch/"
    mutation_case("grouping", base + "grouping.py", "                    join(i, labels[key])",
                  "                    pass", "pair_and_sibling_links_are_transitive")
    mutation_case("resume", base + "persistence.py", "    scheduler.load_state_dict(saved[\"scheduler\"])",
                  "    pass", "resume_restores_weights_optimizer_scheduler_and_every_rng")
    mutation_case("identity", base + "interpolate.py", "    if alpha == 0:\n        return stock.clone()",
                  "    if alpha == 0:\n        return tuned.clone()", "interpolation_uses_merged_products_and_exact_endpoints")
    mutation_case("serialization-reference", base + "interpolate.py", "state_dict=dict(result)",
                  "state_dict=result", "checkpoint_export_survives_destructive_upstream_serialization")


if __name__ == "__main__":
    main()
