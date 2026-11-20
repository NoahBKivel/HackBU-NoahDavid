"""Read actual native and screen job outputs without rerendering them."""

from collections import Counter
import json
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Collect actual native rows and report final screen/native job statuses."""
    config = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
    volume = modal.Volume.from_name(config["modal_volume"])
    reports = []
    for name, filename in (("native-replay-8191", "native.jsonl"), ("screens-budget8192", "main.jsonl")):
        launch = json.loads((ROOT / "results/remote-preparation" / (name + "-manifest.json")).read_text(encoding="utf-8"))
        report = {"name": name, "call_id": launch["function_call_id"]}
        try:
            result = modal.FunctionCall.from_id(launch["function_call_id"]).get(timeout=1)
            report.update(status="FINISHED", returncode=result["returncode"])
        except TimeoutError:
            report["status"] = "RUNNING"
        prefix = launch["remote_output"].removeprefix("/training/")
        manifest = json.loads(b"".join(volume.read_file(prefix + "/manifest.json")))
        report.update(manifest_counts=manifest["counts"], state_budget=manifest["state_budget"],
            screen_budget=manifest["screen_budget"],
            rejected=len(manifest["errors"]), error_types=dict(Counter(row.get("error_type", "unknown") for row in manifest["errors"])))
        destination = ROOT / "data/prepared" / ("recovered-" + name) / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".count-download")
        with temporary.open("wb") as handle:
            for chunk in volume.read_file(prefix + "/" + filename):
                handle.write(chunk)
        ids, source_counts, screens = set(), Counter(), 0
        actual = 0
        for line in temporary.open(encoding="utf-8"):
            if not line.strip():
                continue
            row = json.loads(line)
            actual += 1
            ids.add(row.get("record_id"))
            source_counts[row.get("_meta", {}).get("source", row.get("source", "unknown"))] += 1
            screens += bool(row["questions"]) and all(key.split("#")[0] in {"SCR", "M8"} for key in row["questions"])
        temporary.replace(destination)
        report.update(actual_rows=actual, duplicate_ids=actual - len(ids), source_counts=dict(source_counts),
            actual_screen_rows=screens, collected_path=str(destination.relative_to(ROOT)), training_gate_passed=False)
        reports.append(report)
        print(json.dumps(report), flush=True)
    destination = ROOT / "results/preparation/current-job-counts.json"
    destination.write_text(json.dumps(reports, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
