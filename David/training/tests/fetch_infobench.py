"""Fetch bounded inert InFoBench rows from the dataset service."""
import json
import os
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
headers = {"Authorization": "Bearer " + os.environ["HF_TOKEN"]}
url = "https://datasets-server.huggingface.co/splits?dataset=kqsong/InFoBench"
request = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(request, timeout=45) as response:
    data = json.load(response)
print(json.dumps(data))
split = data["splits"][0]
url = "https://datasets-server.huggingface.co/rows?dataset=kqsong/InFoBench&config=" + split["config"] + "&split=" + split["split"] + "&offset=0&length=100"
with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
    data = json.load(response)
rows = [item["row"] for item in data["rows"]]
url = url.replace("offset=0&length=100", "offset=100&length=50")
with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
    rows.extend(item["row"] for item in json.load(response)["rows"])
target = root / "data/downloads/infobench"
target.mkdir(parents=True, exist_ok=True)
(target / "rows.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
for row in rows[:3]:
    print(json.dumps(row, ensure_ascii=True))
print(json.dumps({"downloaded_rows": len(rows)}))
