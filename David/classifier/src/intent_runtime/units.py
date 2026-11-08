"""Maintain accepted requirements using the shared splitter and RF rows."""

from David import monitor_format as shared


def update_units(session, instructions: list[dict], event: dict, runner) -> None:
    """Filter new source units and retain accepted identities across instruction renumbering."""
    header = session.header
    instruction_origins = []
    for stored in session.ordered_events():
        for position, item in enumerate(stored.get("new_items") or []):
            if item.get("kind") == "user_instruction":
                instruction_origins.append(f"instruction:{stored['event_id']}:{position}")
        if (stored.get("action") or {}).get("tool") == "AskUserQuestion":
            instruction_origins.append(f"answer:{stored['event_id']}")
    if len(instruction_origins) != len(instructions):
        raise ValueError("Instruction identities differ from the shared builder output.")
    document_origins = header.setdefault("document_origins", {})
    missing = set(header["documents"]) - set(document_origins)
    for stored in session.events if missing else ():
        for position, item in enumerate(stored.get("new_items") or []):
            if item.get("kind") == "project_doc" and item["path"] in missing:
                document_origins[item["path"]] = f"document:{stored['event_id']}:{position}"
    for position, item in enumerate(event.get("new_items") or []):
        if item.get("kind") == "project_doc":
            document_origins[item["path"]] = f"document:{event['event_id']}:{position}"
    sources = [(origin, f"[{instruction['id']}]", instruction["text"])
               for origin, instruction in zip(instruction_origins, instructions)]
    sources += [(document_origins[path], path, text) for path, text in header["documents"].items()]
    previous = {}
    for unit in header["units"]:
        previous.setdefault(unit.get("origin"), []).append(unit)
    current = []
    requests = []
    pending = []
    for origin, source, text in sources:
        if origin in previous:
            current.extend({**unit, "source": source} for unit in previous[origin])
            continue
        units = shared.split_units(text, source)
        for index, unit in enumerate(units):
            record = {**unit, "origin": origin, "accepted": False, "k": None}
            current.append(record)
            pending.append(record)
            requests.append((shared.rf_window(units, index), {"RF": shared.fill_question("RF")}))
    if requests:
        answers = runner.ask_many(requests)
        for unit, answer in zip(pending, answers, strict=True):
            unit["accepted"] = answer["RF"]["true"] >= .5
            if unit["accepted"]:
                unit["k"] = header["next_requirement"]
                header["next_requirement"] += 1
    header["units"] = current
