"""Stage only the actual rejected original native records for diagnosis."""

from collections import Counter
import json
from pathlib import Path
import modal

ROOT = Path(__file__).resolve().parents[1]


def main():
    config = json.loads((ROOT / "environment.json").read_text(encoding="utf-8-sig"))
    volume = modal.Volume.from_name(config["modal_volume"])
    manifest = json.loads(b"".join(volume.read_file("prepared/native-replay-8191/manifest.json")))
    rejected = {row["line"] for row in manifest["errors"]}
    output = ROOT / "data/prepared/native-rejected-8191.jsonl"
    temporary = output.with_suffix(".jsonl.tmp")
    with (ROOT / "results/remote-preparation/native-replay-8191.jsonl").open(encoding="utf-8") as source, temporary.open("w", encoding="utf-8", newline="\n") as target:
        for number, line in enumerate(source, 1):
            if number in rejected:
                target.write(line)
    temporary.replace(output)
    report = {"rejected": len(rejected),
        "reasons": dict(Counter(row["error"] for row in manifest["errors"])),
        "packet": str(output.relative_to(ROOT)), "errors": manifest["errors"]}
    (ROOT / "results/preparation/native-rejections.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "errors"}), flush=True)


if __name__ == "__main__":
    main()
