import asyncio
import copy
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from Noah.backend.dashboard_store import DashboardRepository, project_event
from Noah.backend import app as backend


def event(number=1, session="agent-a", **extras):
    return {"session_id": session, "event_id": f"event-{number}", "seq": number,
            "type": "tool_completed", "ts": "2026-11-08T12:00:00Z",
            "action": {"tool": "Edit", "args": {"file_path": "C:/project/app.py"}}, **extras}


def result(number=1, **extras):
    return {"event_id": f"event-{number}", "monitor": "goal_adherence", "risk": .2,
            "flagged": False, "details": {}, "actions": [], **extras}


class ProjectionTests(unittest.TestCase):
    def test_automatic_reminders_do_not_replace_a_task_title(self):
        session = project_event(None, event(new_items=[{"kind": "user_instruction", "text": "<system-reminder>Automatic update</system-reminder>"}]))
        self.assertEqual(session["task"], "Agent agent-a")
        session = project_event(session, event(2, new_items=[{"kind": "user_instruction", "text": "Fix checkout"}]))
        self.assertEqual(session["task"], "Fix checkout")

    def test_late_result_updates_original_point_without_losing_pending_next_event(self):
        session = project_event(None, event())
        session = project_event(session, event(2))
        session = project_event(session, event(2), result(2, pending=True, risk=None,
            late_results=[result(1, flagged=True, risk=.9, requires_user_intervention=True,
                actions=[{"type": "inject_agent", "text": "Stop and ask the user."}])]))
        self.assertEqual(len(session["points"]), 2)
        first, second = session["points"]
        self.assertTrue(first["requires_user_intervention"])
        self.assertEqual(first["risk"], .9)
        self.assertTrue(first["corrected"])
        self.assertFalse(first["isPending"])
        self.assertTrue(second["isPending"])

    def test_retries_and_out_of_order_events_do_not_duplicate_or_regress_results(self):
        session = project_event(None, event(2), result(2, requires_user_intervention=False))
        session = project_event(session, event(1), result(1, requires_user_intervention=True))
        session = project_event(session, event(2), result(2, pending=True, risk=None))
        self.assertEqual([p["seq"] for p in session["points"]], [1, 2])
        self.assertEqual(session["points"][1]["risk"], .2)
        self.assertFalse(session["points"][1]["isPending"])

    def test_metadata_arrives_late_and_read_events_do_not_become_fake_scores(self):
        session = project_event(None, event(2, new_items=[{"kind": "user_instruction", "text": "Fix checkout", "id": "I1"}]))
        start = event(1, type="session_started", action=None)
        start["session"] = {"cwd": "C:/project/demo-shop"}
        session = project_event(session, start, result(1, risk=None))
        self.assertEqual(session["name"], "demo-shop")
        self.assertEqual(session["task"], "Fix checkout")
        self.assertEqual(len(session["points"]), 1)
        self.assertEqual(session["points"][0]["summary"], "Edited app.py")
        self.assertNotIn("requires_user_intervention", session["points"][0])


class RepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.saved = {}
        async def load():
            return list(copy.deepcopy(self.saved).values())
        async def save(key, value):
            await asyncio.sleep(0)
            self.saved[key] = copy.deepcopy(value)
        self.load, self.save = load, save
        self.repo = DashboardRepository(load, save)

    async def test_parallel_events_and_distinct_agents_are_retained(self):
        await asyncio.gather(*(self.repo.record(event(n)) for n in range(1, 51)), self.repo.record(event(1, session="agent-b")))
        snapshot = await self.repo.snapshot()
        self.assertEqual(len(snapshot["sessions"]), 2)
        self.assertEqual(len(next(s for s in snapshot["sessions"] if s["id"] == "agent-a")["points"]), 50)

    async def test_cursors_include_late_updates_and_reset_after_container_restart(self):
        await self.repo.record(event())
        first = await self.repo.snapshot()
        self.assertEqual((await self.repo.snapshot(first["cursor"]))["sessions"], [])
        await self.repo.record(event(), result())
        changed = await self.repo.snapshot(first["cursor"])
        self.assertFalse(changed["reset"])
        self.assertEqual(changed["sessions"][0]["points"][0]["risk"], .2)
        restarted = DashboardRepository(self.load, self.save)
        reset = await restarted.snapshot(changed["cursor"])
        self.assertTrue(reset["reset"])
        self.assertEqual(reset["sessions"][0]["points"][0]["risk"], .2)

    async def test_storage_failure_does_not_publish_unsaved_cursor_or_data(self):
        initial = await self.repo.snapshot()
        self.repo.save = AsyncMock(side_effect=RuntimeError("storage unavailable"))
        with self.assertRaises(RuntimeError):
            await self.repo.record(event())
        after = await self.repo.snapshot(initial["cursor"])
        self.assertEqual(after["cursor"], initial["cursor"])
        self.assertEqual(after["sessions"], [])


class EndpointTests(unittest.TestCase):
    def test_pages_read_key_and_cors_allow_reads_but_not_event_submission(self):
        with patch.dict(os.environ, MONITOR_TOKEN="mod-token", DASHBOARD_TOKEN="read-token"), patch.object(backend, "DashboardRepository") as repo:
            repo.return_value.snapshot = AsyncMock(return_value={"cursor": "test:0", "reset": True, "sessions": []})
            client = TestClient(backend.create_web())
            headers = {"authorization": "Bearer read-token", "origin": "https://noahbkivel.github.io"}
            read = client.get("/v1/dashboard/sessions", headers=headers)
            self.assertEqual(read.status_code, 200)
            self.assertEqual(read.headers["access-control-allow-origin"], "https://noahbkivel.github.io")
            self.assertEqual(client.post("/v1/events", json=event(), headers=headers).status_code, 401)
            preflight = client.options("/v1/dashboard/sessions", headers={"origin": "https://noahbkivel.github.io", "access-control-request-method": "GET", "access-control-request-headers": "authorization"})
            self.assertEqual(preflight.status_code, 200)
            other = client.get("/v1/dashboard/sessions", headers={"authorization": "Bearer read-token", "origin": "https://other.example"})
            self.assertNotIn("access-control-allow-origin", other.headers)

    def test_dashboard_auth_and_reads_never_call_classifier_or_warmup(self):
        with patch.dict(os.environ, MONITOR_TOKEN="test-token"), patch.object(backend, "DashboardRepository") as repo, patch.object(backend, "classify", new_callable=AsyncMock) as classify, patch.object(backend, "warm_classifier", new_callable=AsyncMock) as warm:
            repo.return_value.snapshot = AsyncMock(return_value={"cursor": "test:0", "reset": True, "sessions": []})
            client = TestClient(backend.create_web())
            self.assertEqual(client.get("/v1/dashboard/sessions").status_code, 401)
            response = client.get("/v1/dashboard/sessions", headers={"authorization": "Bearer test-token"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["sessions"], [])
            classify.assert_not_called()
            warm.assert_not_called()

    def test_storage_failure_does_not_change_result_delivered_to_mod(self):
        answer = result(requires_user_intervention=True)
        with patch.dict(os.environ, MONITOR_TOKEN="test-token"), patch.object(backend, "DashboardRepository") as repo, patch.object(backend, "classify", new_callable=AsyncMock, return_value=(answer, None)):
            repo.return_value.record = AsyncMock(side_effect=RuntimeError("unavailable"))
            client = TestClient(backend.create_web())
            response = client.post("/v1/events", json=event(), headers={"authorization": "Bearer test-token"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), answer)
            self.assertEqual(repo.return_value.record.await_count, 2)


if __name__ == "__main__":
    unittest.main()
