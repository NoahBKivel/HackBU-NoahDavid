"""Run the ordered per-event lifecycle using an injected shared-format binding."""

import time

from .actions import compose
from .findings import change_status, diagnostics_needed, open_or_upgrade
from .firing import fired, status
from .intake import skipped
from .pane import readings
from .rows import initial
from .store import SessionStore


class Runtime:
    def __init__(self, store: SessionStore, runner, formats, source: str):
        self.store = store
        self.runner = runner
        self.formats = formats
        self.source = source

    def classify(self, event: dict) -> dict:
        """Process one Mod event and deliver pending results once on an on-time response."""
        started = time.time()
        session = self.store.get(str(event.get("session_id", "")))
        session.arrive(event)
        with session.gate.release(event.get("seq"), lambda: self.store.save(session)) as stale:
            result = self._process(session, event, stale)
            if event.get("_test_sleep_s"):
                time.sleep(float(event["_test_sleep_s"]))
            result["details"]["classify_ms"] = int((time.time() - started) * 1000)
            if time.time() - float(event.get("backend_sent_at", started)) >= 8.0:
                session.header["late"].append(result)
            else:
                late = session.header["late"]
                session.header["late"] = []
                if late:
                    result["late_results"] = late
                session.delivered([result] + late)
            return result

    def _process(self, session, event, stale):
        header = session.header
        fresh = self.store.add(session, event)
        instructions = self.formats.instructions(session.ordered_events()) if fresh else None
        if fresh:
            changed = len(instructions) > header["instruction_count"]
            header["instruction_count"] = len(instructions)
            header["new_instruction_pending"] |= changed
            self.formats.update_units(session, instructions, event, self.runner)
        base = {"schema_version": 1, "event_id": event["event_id"], "monitor": "goal_adherence",
                "flagged": False, "risk": None, "drift": None, "drift_rate": None, "actions": []}
        details = {"source": self.source, "fired": {}, "open_findings": self._open_count(header), "classify_ms": 0}
        base["details"] = details
        if skipped(event, not fresh, stale):
            details["skipped"] = True
            return base
        context = self.formats.render(session, instructions, event, self.runner)
        state = context["text"]
        keys = initial(event, header)
        answers = self.runner.ask(state, self.formats.questions(keys, header, context))
        triggered = fired(answers) | context.get("screen_fired", {})
        change_status(header["findings"], answers, triggered, header["new_instruction_pending"])
        header["new_instruction_pending"] = False
        if diagnostics_needed(header["findings"], triggered, event.get("seq")):
            diagnostics = [f"D1#E{seq}" for seq in context["detailed"]] + ["D5"]
            diagnostic_answers = self.runner.ask(state, self.formats.questions(diagnostics, header, context, fired_questions=list(triggered)))
            cited = [seq for seq in context["detailed"] if diagnostic_answers[f"D1#E{seq}"]["true"] >= 0.5]
            if not cited:
                cited = [event.get("seq")]
            severity = {"0": "minor", "1": "significant", "2": "serious"}[status(diagnostic_answers["D5"])]
            requirements = []
            if "M2" in triggered or any(key.startswith("G2#") for key in triggered):
                requirement_keys = [f"D2#R{u['k']}" for u in header["units"] if u["accepted"]]
                summary = self.formats.summary(list(triggered), cited)
                judged = self.runner.ask(state, self.formats.questions(requirement_keys, header, context, summary=summary))
                requirements = [u for u in header["units"] if u["accepted"] and judged[f"D2#R{u['k']}"]["true"] >= 0.5]
            changed = open_or_upgrade(header["findings"], triggered, event.get("seq"), severity, cited)
            correction = lambda findings: self.formats.correction(findings, session, instructions, context, requirements)
            base["actions"] = compose(changed, self.formats.names, correction, header, event["event_id"])
        base.update(readings(answers, header["drift_history"]))
        if context.get("screen_fired"):
            base["risk"] = max(base["risk"], max(context["screen_fired"].values()))
            base["flagged"] = base["risk"] >= 0.5
        details.update(fired=triggered, open_findings=self._open_count(header))
        if context.get("overflow"):
            details["overflow"] = True
        not_done = [u["text"] for u in header["units"] if u["accepted"] and
                    f"G2#R{u['k']}" in answers and status(answers[f"G2#R{u['k']}"]) == "not done"]
        if not_done:
            details["not_done"] = not_done
        return base

    def _open_count(self, header):
        return sum(f["status"] == "open" for f in header["findings"])
