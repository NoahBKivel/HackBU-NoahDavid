"""Summarize actual source edge cases without printing whole trajectories."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path("src").resolve()))
from intent_training.sources.reward_hack_lcb import _stream

for path in sorted(Path("data/downloads/reward_hack_lcb").rglob("*.traj.json")):
    row = json.loads(path.read_text())
    try:
        _stream(row["messages"])
    except ValueError as error:
        print(path.as_posix(), str(error))
        print([(i, item["role"], len(item.get("extra", {}).get("actions", [])), item["content"][:160])
               for i, item in enumerate(row["messages"])][-5:])
