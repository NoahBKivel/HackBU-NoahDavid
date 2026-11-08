"""Run the existing single-question input builder with ordered session handling."""

import time

from .intake import skipped
from .store import SessionStore


class SingleQuestionRuntime:
    def __init__(self, store: SessionStore, runner, builder, question: str, source: str):
        self.store = store
        self.runner = runner
        self.builder = builder
        self.question = question
        self.source = source

    def classify(self, event: dict) -> dict:
        """Score the existing input format and preserve late responses for one delivery."""
        started = time.time()
        session = self.store.get(str(event.get("session_id", "")))
        session.arrive(event)
        with session.gate.release(event.get("seq"), lambda: self.store.save(session)) as stale:
            fresh = self.store.add(session, event)
            ignored = skipped(event, not fresh, stale)
            risk = None
            if not ignored:
                instructions = [item["text"] for e in session.ordered_events() for item in e.get("new_items") or []
                                if item.get("kind") == "user_instruction" and item.get("text")]
                state = self.builder(instructions, event)
                answer = self.runner.ask(state, {"M1": {"type": "noul", "instructions": self.question}})
                risk = answer["M1"]["true"]
            if event.get("_test_sleep_s"):
                time.sleep(float(event["_test_sleep_s"]))
            result = {"schema_version": 1, "event_id": event["event_id"], "monitor": "goal_adherence",
                      "flagged": risk is not None and risk >= .5, "risk": risk,
                      "drift": None, "drift_rate": None, "actions": [],
                      "details": {"source": self.source, "placeholder": True, "question": self.question,
                                  "fired": {"M1": risk} if risk is not None and risk >= .5 else {},
                                  "open_findings": 0, "classify_ms": int((time.time() - started) * 1000)}}
            if ignored:
                result["details"]["skipped"] = True
            if time.time() - float(event.get("backend_sent_at", started)) >= 8.0:
                session.header["late"].append(result)
            else:
                late = session.header["late"]
                session.header["late"] = []
                if late:
                    result["late_results"] = late
            return result
