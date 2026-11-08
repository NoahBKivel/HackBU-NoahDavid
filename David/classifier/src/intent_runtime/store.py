"""Keep session headers and immutable event entries in a mapping."""

import copy
import threading
from collections.abc import MutableMapping

from .ordering import OrderingGate


def new_header() -> dict:
    """Return an empty persistent session header."""
    return {"documents": {}, "units": [], "event_ids": [], "last_seq": 0,
            "findings": [], "drift_history": [], "late": [],
            "pending_correction_marks": [], "messages": {},
            "next_requirement": 1, "instruction_count": 0,
            "new_instruction_pending": False}


class Session:
    def __init__(self, sid: str, header: dict, events: list[dict]):
        self.sid = sid
        self.header = header
        self.events = events
        self.gate = OrderingGate(header)
        self.arrival_lock = threading.RLock()

    def ordered_events(self) -> list[dict]:
        """Return sequenced events in order while retaining arrival order for unnumbered ones."""
        numbered = iter(sorted((e for e in self.events if e.get("seq") is not None), key=lambda e: e["seq"]))
        return [next(numbered) if e.get("seq") is not None else e for e in self.events]

    def arrive(self, event: dict) -> None:
        """Mark delivered corrections on the next eligible tool result before ordering."""
        with self.arrival_lock:
            if event.get("type") != "tool_completed" or (event.get("action") or {}).get("denied") is not None:
                return
            pending = self.header["pending_correction_marks"]
            for finding in self.header["findings"]:
                if finding["id"] in pending:
                    finding["reached_at"] = event.get("seq")
            pending.clear()

    def delivered(self, results: list[dict]) -> None:
        """Queue correction marks only after their results become visible to the backend."""
        event_ids = {r["event_id"] for r in results if any(a["type"] == "inject_agent" for a in r["actions"])}
        with self.arrival_lock:
            pending = self.header["pending_correction_marks"]
            for finding in self.header["findings"]:
                message = self.header["messages"].get(finding.get("message"), {})
                if message.get("event_id") in event_ids and finding.get("reached_at") is None and finding["id"] not in pending:
                    pending.append(finding["id"])


class SessionStore:
    def __init__(self, mapping: MutableMapping):
        self.mapping = mapping
        self.sessions = {}
        self.lock = threading.Lock()

    def get(self, sid: str) -> Session:
        """Load each session once per container from its header and event entries."""
        with self.lock:
            if sid not in self.sessions:
                header = copy.deepcopy(self.mapping.get(sid) or new_header())
                events = [copy.deepcopy(self.mapping[f"{sid}:e:{eid}"]) for eid in header["event_ids"]]
                self.sessions[sid] = Session(sid, header, events)
            return self.sessions[sid]

    def add(self, session: Session, event: dict) -> bool:
        """Store one complete event once and apply its latest document replacements."""
        eid = event["event_id"]
        if eid in session.header["event_ids"]:
            return False
        saved = copy.deepcopy(event)
        self.mapping[f"{session.sid}:e:{eid}"] = saved
        session.events.append(saved)
        session.header["event_ids"].append(eid)
        for item in event.get("new_items") or []:
            if item.get("kind") == "project_doc":
                session.header["documents"][item["path"]] = item["text"]
        return True

    def save(self, session: Session) -> None:
        """Write through the small mutable header after an event finishes."""
        with session.arrival_lock:
            self.mapping[session.sid] = copy.deepcopy(session.header)
