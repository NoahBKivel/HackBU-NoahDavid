# Contract: shared context and the Noah ↔ David bridge

This file covers what both halves of the project depend on: shared project context, the system overview, and the exact interface between Noah's backend and David's classifier. Each side's internals are documented separately:
- [NOAH.md](NOAH.md): the Mod and the backend
- [DAVID.md](DAVID.md): the classifier

> **Every agent: keep these docs current.** They're the shared memory between all agents and sessions on this project. Whenever you learn or change something another agent would need, update the right doc **in the same change**.
> - **This file is shared:** change a contract field or rule only once **both Noah and David agree**. Record the change in section 7.
> - **NOAH.md** is maintained by Noah's agents. **DAVID.md** is maintained by David's agents. Either side's agents may read both.
>
> Edit sections in place, so each doc stays a current picture and not a history log. If something turns out to be wrong, fix it. Don't work around it.

---

## 1. Shared context

**What we're building:** a Claude Code Mod that monitors a coding agent for misalignment with the user's instructions:
- misreading them
- drifting from the goal
- **proxy optimization**: hitting a measurable target at the cost of what the user actually wants, e.g. deleting slow tests to speed up CI when the user said "don't reduce coverage"

A classifier on Modal judges each action. Based on its decision, the Mod alerts the user in chat, sends the agent a correction, and graphs alignment risk over the task.

**Hackathon:** HackBU. Building runs from 1pm on 2026-11-07 to the **Devpost deadline at 11am on 2026-11-08**.
- All code must be written during that period. Don't reuse earlier code, including Noah's old `tool-pulse` test mod.
- A demo video is required. A live presentation is possible but not confirmed.
- The demo runs in the Claude Code **desktop app** on Windows 11.

**Team:**
- **Noah** builds the Mod, the FastAPI backend and the integration.
- **David** builds the classifier: kev, fine-tuning and `classify()`.

**Guiding rule: demo-grade.** Build only what the demo needs. Skip robustness work, and mark extras as "later".

**Repo:** https://github.com/NoahBKivel/HackBU-NoahDavid (**public**)
- `Noah/` is Noah's code, `David/` is David's code.
- The root docs (this file, NOAH.md, DAVID.md, README.md) are shared.
- **Never edit the other person's folder.**
- Run `git pull --rebase` before every push.
- **Never commit secrets**, because the repo is public.

---

## 2. System overview

```
 USER'S MACHINE (Claude Code desktop app) ──────────────── Noah
  Claude Code ──events (in-process JS objects)──▶ Mod ──$.state──▶ Pane UI
        ▲                                          │  ▲
        └── user-only notices + context[] ─────────┘  │
                                                      │
              POST /v1/events (JSON over HTTPS)   │  │  200: result + actions (JSON)
                                                  ▼  │
 MODAL (David's workspace) ───────────────────────────────────────────
                         FastAPI ── Noah
                              │  ▲
   BRIDGE ─ classify.remote.aio(dict)  result dict ─ BRIDGE (section 4)
                              ▼  │
                  classify() ── David (kev + his own DB for history)
```

**Flow for one action:**
1. The agent runs a tool. The Mod lets it run normally, then builds an **event** containing everything it collected.
2. The Mod sends the event to FastAPI **without waiting for the response**, so the agent never blocks.
3. FastAPI calls `classify(event)` and returns its result.
4. The Mod runs the result's **`actions`** in order: a notice for the user, and/or a correction attached to the agent's next tool result. It also updates the Pane's graph.

---

## 3. Boundary 1: Mod ↔ FastAPI (both Noah's)

**Core rule: send as much as possible.**
- The Mod sends everything it can collect (the full menu in section 5), and the classifier uses whatever it needs.
- **Large items may be trimmed:** original file contents, very long shell output, the full conversation history, and attachment bytes. **Ask Noah before deciding what to leave out.**
- The backend accepts unknown extra fields (`extra="allow"`) and passes them through untouched.

### Event: Mod → `POST /v1/events` (Bearer token)
The field layout is provisional.
```json
{
  "schema_version": 1,
  "session_id": "uuid",
  "event_id": "toolu_01... | uuid",
  "seq": 42,
  "type": "tool_completed | turn_completed | session_started",
  "ts": "2026-11-07T15:00:00Z",
  "new_items": [
    { "kind": "user_instruction", "id": "I3", "text": "verbatim prompt" },
    { "kind": "project_doc", "path": "CLAUDE.md", "text": "..." }
  ],
  "action": {
    "tool": "Bash",
    "args": { "command": "rm tests/test_slow.py" },
    "result_text": "...",
    "is_error": false,
    "file_changes": [{ "path": "tests/test_slow.py", "op": "delete", "patch": "..." }]
  },
  "agent_text": "visible response / final message",
  "agent_thinking": "displayed thinking, may be summarized",
  "todos": []
}
```
- **Each event carries:**
  - all of the current action's data
  - every new user and session item since the last event
- Session-level data such as project docs and repo info goes in a `session_started` event, and again whenever it changes.
- User instructions are always **verbatim**.
- `seq` keeps the order, because HTTP requests can arrive out of order.

### Response: FastAPI → Mod
This is exactly what `classify()` returns (section 4).

---

## 4. Boundary 2: FastAPI ↔ `classify()` — the bridge

### How it's called
```python
classify = modal.Function.from_name("<david-app>", "classify")   # David's app name: TBD
result: dict = await classify.remote.aio(event)                  # event = the dict from section 3
```
- **Input:** the event exactly as the Mod sent it (section 3).
  - David picks the fields he needs and ignores the rest.
  - **History:** David's side stores whatever history it needs in **its own database**. Noah's side keeps none.
- If the name or arguments don't match, one side changes to match. That's a trivial fix.

### Output: David must return this shape
```json
{
  "schema_version": 1,
  "event_id": "same as the input event",
  "monitor": "goal_adherence",
  "flagged": true,
  "risk": 0.93,
  "details": { },
  "actions": [
    { "type": "notify_user", "level": "potential | detected | intervened", "text": "..." },
    { "type": "inject_agent", "text": "correction text" }
  ]
}
```
| Field | Meaning | Used by |
|---|---|---|
| `event_id` | Echoes the input, so a result matches its action | Mod |
| `monitor` | Which monitor produced this (only `goal_adherence` for now) | Pane |
| `flagged` | Whether this is a flagged event | Pane (highlight) |
| `risk` | 0–1, the probability of a violation (kev's noul) | Pane graph |
| `details` | Anything else, open-ended | Pane shows it as expandable key/value data |
| `actions` | An ordered list. Can be empty. | Mod runs them in order |

### Actions
| Type | What the Mod does |
|---|---|
| `notify_user` | Shows `text` in chat as a notice **the model never reads**. `level` sets the styling: `potential` (below the threshold, no intervention), `detected`, or `intervened`. |
| `inject_agent` | Attaches `text` to the agent's **next** tool result. The agent reads it, and the user doesn't see it as their own message. |

- **David's side decides everything:** whether to act, the threshold, the wording, and the order. The order controls whether a notice comes before or after an intervention.
- **The Mod and FastAPI never apply thresholds.** They just run the actions as given.
- **Corrections are only applied to the main agent.** Subagents are out of scope.

---

## 5. Data the Mod can provide

This is everything the Mod sends, subject to the large-item exception.

- **Session:** ID, cwd/root, git repo (root, remote, name), model and effort, Claude Code version, surface, start time, context usage and cost.
- **The user:**
  - every prompt verbatim, with timestamp and order
  - slash commands
  - attachment details
  - interruptions
  - answers to AskUserQuestion
  - approved plans
- **Project documents:** any file by path, the nearest CLAUDE.md or AGENTS.md to an edited file, directory listings, file details.
- **Actions (Edit, Write, Bash, PowerShell):**
  - tool name, ID and timestamps
  - full arguments (Edit old and new text, Write content, shell commands)
  - whether the call was read-only
- **Results:** the result text as the agent sees it, is_error, Edit/Write diffs and the file's original contents, shell stdout and stderr, interrupted or timed out, and blocked calls.
- **What the agent says:**
  - its visible response text
  - **displayed** thinking, which may be summarized and isn't the full internal reasoning
  - each turn's final message and why the turn ended (answer, aborted, refusal, error)
  - token usage per step
- **Plan:** TodoWrite lists, the plan-mode plan, turn and step counts.
- **On request:** the full conversation.
- **Computed by the Mod:** git diff and status after shell commands, the list of files touched, counts, and action counts since the last instruction.
- **Not available:** hidden model reasoning, and anything outside Claude Code.

---

## 6. Modal (shared)

- **Workspace:** David's. It has the credits, and Noah is a member. Check with `modal profile current`.
- **Names:**

| Resource | Name | Owner |
|---|---|---|
| Backend app | `alignment-monitor` | Noah |
| API token secret | `monitor-token` (key `MONITOR_TOKEN`) | Noah |
| Classifier app | TBD | David |

---

## 7. Open contract items and change log

**Open:**
- David's app name, and confirmation of the `classify()` call and output shape.
- Which large items get trimmed (Noah decides when building events).

**Changes:** (date, change, agreed by)
- 2026-11-07: first version.
