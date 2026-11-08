"""Read-only dashboard projection of the same events/results returned to the Mod.

The backend has max_containers=1. Its async lock serializes snapshot writes;
classification remains concurrent and never runs under this lock.
"""
import asyncio
import copy
import re
import time
import uuid
from datetime import datetime

MAX_POINTS = 2000  # Same retained point count as the Mod.


def compact(value, limit=70):
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit - 3] + "..."


def basename(value):
    return re.split(r"[\\/]", str(value or "").rstrip("/\\"))[-1]


def event_time(event):
    try:
        return int(datetime.fromisoformat(event["ts"].replace("Z", "+00:00")).timestamp() * 1000)
    except (KeyError, TypeError, ValueError, AttributeError):
        return int(time.time() * 1000)


def describe(event):
    if event.get("type") == "turn_completed":
        return "Turn", "Agent finished its turn"
    action = event.get("action") or {}
    tool, args = str(action.get("tool") or "Tool"), action.get("args") or {}
    if tool in {"Edit", "Write", "Read"}:
        verb = {"Edit": "Edited", "Write": "Wrote", "Read": "Read"}[tool]
        return tool, f"{verb} {basename(args.get('file_path'))}"
    for key in ["command", "pattern", "url", "query"]:
        if isinstance(args.get(key), str):
            text = args[key]
            if key == "pattern" and args.get("path"):
                text += " in " + basename(args["path"])
            return tool, compact(text)
    if isinstance(args.get("todos"), list):
        return tool, f"Updated {len(args['todos'])} todos"
    return tool, compact(args.get("description") or tool)


def apply_result(point, result):
    if result.get("pending") is True:
        # A retry/pending envelope must not undo a completed result.
        if point["isPending"]:
            point["details"] = result.get("details") or {}
        return
    notices, correction = [], None
    for action in result.get("actions") or []:
        text = action.get("text")
        if not isinstance(text, str) or not text:
            continue
        if action.get("type") == "notify_user":
            notices.append({"level": action.get("level") or "detected", "text": text})
        elif action.get("type") == "inject_agent":
            correction = text
    details = result.get("details") or {}
    point.update(isPending=False, risk=result.get("risk"), flagged=result.get("flagged") is True,
                 monitor=result.get("monitor"), details=details, notices=notices,
                 correction=correction, corrected=bool(correction), error=details.get("error"),
                 drift=result.get("drift"), driftRate=result.get("drift_rate"))
    if isinstance(result.get("requires_user_intervention"), bool):
        point["requires_user_intervention"] = result["requires_user_intervention"]


def project_event(previous, event, result=None):
    session = copy.deepcopy(previous) if previous else {
        "id": event["session_id"], "name": "Unknown project",
        "task": "Agent " + event["session_id"][:8], "points": [], "lastSeenAt": 0,
    }
    ts = event_time(event)
    session["lastSeenAt"] = max(session["lastSeenAt"], ts)
    info = event.get("session") or {}
    repo = info.get("repo") or {}
    if not isinstance(repo, dict):
        repo = {}
    project = repo.get("name") or basename(repo.get("root") or info.get("root") or info.get("cwd"))
    if project:
        session["name"] = str(project)
    seq = event.get("seq") or 0
    # Automatic app reminders can arrive in new_items too; they are not task titles.
    if session["task"].startswith("<system-reminder>"):
        session["task"] = "Agent " + event["session_id"][:8]
        session.pop("_taskSeq", None)
    for item in event.get("new_items") or []:
        if isinstance(item, dict) and item.get("kind") == "user_instruction" and item.get("text"):
            if str(item["text"]).lstrip().startswith("<system-reminder>"):
                continue
            if "_taskSeq" not in session or seq < session["_taskSeq"]:
                session["task"], session["_taskSeq"] = compact(item["text"], 90), seq
                break
    points = session["points"]
    point = next((p for p in points if p["eventId"] == event["event_id"]), None)
    if point is None and (event.get("action") or event.get("type") == "turn_completed"):
        tool, summary = describe(event)
        point = {"eventId": event["event_id"], "seq": seq, "ts": ts, "tool": tool,
                 "summary": summary, "risk": None, "flagged": False, "corrected": False,
                 "isPending": True, "monitor": None, "details": {}, "notices": [],
                 "correction": None, "error": None, "drift": None, "driftRate": None}
        points.append(point)
    if result:
        if point:
            apply_result(point, result)
        by_id = {p["eventId"]: p for p in points}
        for late in result.get("late_results") or []:
            if late.get("event_id") in by_id:
                apply_result(by_id[late["event_id"]], late)
    session["points"] = sorted(points, key=lambda p: (p["seq"], p["ts"], p["eventId"]))[-MAX_POINTS:]
    return session


class DashboardRepository:
    def __init__(self, load_all, save):
        self.load_all, self.save = load_all, save
        self.lock = asyncio.Lock()
        self.sessions = None
        self.generation = uuid.uuid4().hex
        self.revision = 0
        self.versions = {}

    async def load(self):
        if self.sessions is None:
            self.sessions = {s["id"]: s for s in await self.load_all()}
            self.versions = {key: 0 for key in self.sessions}

    async def record(self, event, result=None):
        async with self.lock:
            await self.load()
            key = event["session_id"]
            updated = project_event(self.sessions.get(key), event, result)
            if updated == self.sessions.get(key):
                return
            # Persist before publishing a new cursor. Failed saves do not poison the cache.
            await self.save(key, updated)
            self.sessions[key] = updated
            self.revision += 1
            self.versions[key] = self.revision

    async def snapshot(self, cursor=None):
        async with self.lock:
            await self.load()
            prefix, _, number = (cursor or "").partition(":")
            valid = prefix == self.generation and number.isdigit() and int(number) <= self.revision
            since = int(number) if valid else -1
            changed = [copy.deepcopy(session) for key, session in self.sessions.items()
                       if not valid or self.versions[key] > since]
            for session in changed:
                session.pop("_taskSeq", None)
            changed.sort(key=lambda s: (-s["lastSeenAt"], s["id"]))
            return {"cursor": f"{self.generation}:{self.revision}", "reset": not valid, "sessions": changed}
