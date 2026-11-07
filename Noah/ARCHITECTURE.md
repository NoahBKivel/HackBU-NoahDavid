# Architecture and build guide

This is the single source of truth for anyone working on Noah's part of the project. Read all of it before writing code, and update it whenever a decision changes.

---

## 1. Project

**What it is:** a Claude Code Mod that monitors a coding agent for misalignment with the user's instructions:
- misreading the instructions
- drifting from the goal
- **proxy optimization**: hitting a measurable target at the cost of what the user actually wants, e.g. deleting slow tests to speed up CI when the user said "don't reduce coverage"

The Mod sends what the agent does to a classifier on Modal. Based on the result, it alerts the user in chat, sends the agent a correction, and graphs alignment risk over the course of the task.

**Hackathon:** HackBU. Building runs from 1pm on 2026-11-07 to the **Devpost deadline at 11am on 2026-11-08**.
- All code must be written during that period. Don't reuse earlier code, including Noah's old `tool-pulse` test mod.
- A demo video is required. A live presentation is possible but not confirmed.

**Team:**
- **Noah** builds the Mod, the backend and the integration (this folder).
- **David** builds the classifier: kev, fine-tuning and `classify()` (in `David/`).

**Guiding rule: demo-grade.** Build only what the demo needs. Skip robustness work, and mark extras as "later".

---

## 2. Repository

Repo: https://github.com/NoahBKivel/HackBU-NoahDavid (**public**)

```
README.md          shared, edit sparingly
Noah/
  ARCHITECTURE.md  this file
  mod/             Claude Code Mod (TypeScript)
  backend/         FastAPI on Modal (Python)
David/             classifier (David's layout) — do not edit
```

**Git rules:**
- Only touch `Noah/`. Never edit `David/`.
- Run `git pull --rebase` before every push.
- **Never commit secrets**, because the repo is public. The API token lives only in the Modal Secret and the Mod's `userConfig`.

**Local:**
- Working copy: `C:\Projects\NYCAIRRtest` (Windows 11).
- Python 3.12 virtual environment at `.venv\`, with `modal` and `fastapi[standard]` installed.
- Run Modal with `.venv\Scripts\modal`. The default Python is 3.14, so don't use it.

---

## 3. Architecture

```
 USER'S MACHINE (Claude Code desktop app) ────────────────────────────
  Claude Code ──events (in-process JS objects)──▶ Mod ──$.state──▶ Pane UI
        ▲                                          │  ▲
        └── user-only notices + context[] ─────────┘  │
                                                      │
              POST /v1/events (JSON over HTTPS)   │  │  200: result + actions (JSON)
                                                  ▼  │
 MODAL (David's workspace) ───────────────────────────────────────────
                         FastAPI (backend/, Noah)
                              │  ▲
       classify.remote.aio(dict)   result dict
                              ▼  │
                  classify()  (David: kev + his own DB for history)
```

**Flow for one action:**
1. The agent runs a tool. The Mod's `tool.call` hook runs `await next(e)` first, so the tool runs normally.
2. The Mod builds an **event** (section 5) and sends it with `$.http.fetch` **without waiting for the response**, so the agent never blocks.
3. FastAPI checks the token and calls `await classify.remote.aio(event)`. It's **synchronous on the server**: it waits for the result and returns it.
4. The response carries the `result` and an ordered **`actions`** list.
5. The Mod runs the actions in order:
   - `notify_user`: shown right away as a user-only notice in chat.
   - `inject_agent`: queued, then attached to the agent's **next** tool result as `context[]`.
6. The Mod stores `{ts, risk, flagged, corrected}` in `$.state`, which redraws the Pane and its graph.

**Storage:**
- The Mod uses no backend storage. History for the classifier lives in **David's own database** on Modal.
- The graph's data lives in the Mod's `$.state`. It covers **one task, meaning the current session**, and survives Mod reloads.
- Modal Dict is **not used**. Add it only if the browser dashboard gets built.

---

## 4. Components

### 4.1 Mod (`Noah/mod/`, TypeScript)
- **Files:**
  - `.claude-plugin/plugin.json`
  - `hooks/hooks.json` = `{ "modules": ["./register.tsx"] }`
  - `hooks/register.tsx`
  - `types/index.d.ts`: the `$.state` contract, named in `plugin.json` as `"types"`
- **Development:**
  - Load the `plugin-authoring` skill first. It sets up hot reloading and says where the session's mods folder is (`C:\Users\noahk\.claude\dev-mods\<session-id>\<mod-name>\`).
  - Write the Mod there so it reloads at the end of each turn, and copy it into `Noah/mod/` before each commit.
  - The API types are in the skill's `types/claude-code.d.ts`. **Grep them before using any API; don't guess.**
- **Hooks:**
  - `session.start`: get the session ID with `$.session.id()`, read CLAUDE.md, AGENTS.md and README with `$.fs.read`, send `GET /health` to wake Modal, and open the Pane.
  - `prompt.submit`: record each user instruction **verbatim** with its timestamp and order.
  - `tool.call` on **Edit, Write, Bash and PowerShell**: on Windows the agent may use PowerShell instead of Bash.
    - Run `const r = await next(e)`.
    - Build the event and send it without waiting.
    - If there are queued corrections and the call is from the main agent (no `agentId`), return `{ ...r, context: [...(r.context ?? []), ...queued] }`.
  - `turn.complete`: send the agent's final message as a `turn_completed` event.
- **Actions:**
  - `notify_user`: `$.session.append({ message: { type: "system", content: [{ type: "text", text }] } })` adds a notice **the model never reads**. `$.ui.log(text)` is the quieter dim-line version.
  - `inject_agent`: queue the text in `$.state` and attach it on the next main-agent tool call.
  - Run actions **in list order**, so the classifier controls whether a notice comes before or after an intervention.
  - There's **no toggle**: installing the Mod means monitoring is on.
- **Pane:**
  - Open it with `$.ui.open({ id, title })` and draw it in a `ui.render` hook on `{ component: 'Pane', requestId: id }`.
  - It shows status, the latest risk, flagged events (Buttons that expand to details), and the graph.
- **Graph:**
  - An `Svg` element, `{ source, alt, isInteractive: true }`, with the markup kept under 131,072 characters.
  - Plot risk per event, highlight flagged points, add a distinct marker where a correction was sent, and show `<title>` tooltips.
  - `Svg` is available on the desktop surface.
- **Config:** use `userConfig` for `apiUrl` and `apiToken`. Never hardcode them.

### 4.2 Backend (`Noah/backend/`, Python, FastAPI on Modal)
- One `app.py`: `modal.App("alignment-monitor")`, plus `@app.function(secrets=[modal.Secret.from_name("monitor-token")])` and `@modal.asgi_app()` for a FastAPI app.
- **Endpoints:**
  - `GET /health` returns `{ok: true}` with no auth, used for warm-up.
  - `POST /v1/events` takes a Bearer token, validates the event, runs `await classify.remote.aio(event)`, and returns the response (section 5).
- **Calling the classifier:** `classify = modal.Function.from_name("<david-app>", "classify")`. Until David's is live, use a **mock** `classify()` in this app that returns the contract's shape.
- **Commands:**
  - `.venv\Scripts\modal serve Noah/backend/app.py` is for development. It gives a temporary URL ending in `-dev`.
  - `.venv\Scripts\modal deploy Noah/backend/app.py` gives the stable URL for the demo. Put that URL in the Mod's `apiUrl`.

### 4.3 Classifier (`David/`, owned by David)
- Built on kev (github.com/jaredpalmer/kev, Apache-2.0), an open-source clone of TypeSafe's Jev "System One" decision model.
- **What kev does:**
  - Questions come in three types: `noul` (yes/no, returns `{noul: p_yes}`), `choice` (up to 255 options supplied with each request) and `score`.
  - The pointer head scores **only the answer options**. It can't point into the input.
  - The 0.8B, 4B and 9B models are validated up to about 8K tokens of input. Kev-4B uses about 14 GB of GPU memory.
- **Fallback:** if fine-tuning fails, David runs kev without fine-tuning. The architecture doesn't change.
- David decides when a correction is needed and what the `actions` list contains. The Mod and backend never apply thresholds.
- **Correction text:** a deterministic template that names its source (the monitor), shows what was evaluated, and tells the agent to re-check. It also says the agent can ignore the correction if no violation occurred, and what to do if one did.

---

## 5. Contract (provisional)

The event payload will change to whatever agent data David's classifier needs. The full menu of available data is in section 8. Only the event-building code in the Mod and the Pydantic model in the backend need to change when it does.

### Event: Mod → `POST /v1/events`
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
    "result_text": "...(truncated)",
    "is_error": false,
    "file_changes": [{ "path": "tests/test_slow.py", "op": "delete", "patch": "..." }]
  },
  "agent_text": "final message, for turn_completed"
}
```
- The Mod sends **deltas**: only what's new since the last event.
- `new_items` always carries the user's words verbatim. How requirements get extracted is **David's open decision**. The Mod has `$.model.complete` available but doesn't use it unless David decides to.

### Response: backend → Mod
```json
{
  "schema_version": 1,
  "event_id": "same as request",
  "monitor": "goal_adherence",
  "flagged": true,
  "risk": 0.93,
  "details": { },
  "actions": [
    { "type": "notify_user", "level": "potential | detected | intervened", "text": "..." },
    { "type": "inject_agent", "text": "correction template" }
  ]
}
```
- `risk` is the probability of a violation from kev's noul.
- `details` is open-ended. The Pane shows it as expandable key/value data.
- `actions` can be empty. A below-threshold "potential" detection sends only a `notify_user` action.

### Python side
`classify(event: dict) -> dict` returns the response shape above. If the name or arguments don't match David's, one side changes to match. That's a trivial fix.

---

## 6. Modal

- **Workspace:** David's. Noah is a member and David's workspace has the credits. Check with `.venv\Scripts\modal profile current`.
- **Shared names:**
  - App `alignment-monitor` (Noah's backend).
  - Secret `monitor-token` (key `MONITOR_TOKEN`).
  - David's app name is still to be confirmed.
- **Cold starts:** set `min_containers=1` on GPU functions during the demo, and store kev's weights on a Modal Volume. That's David's side.

---

## 7. Build plan

The order doubles as the cut list: each step leaves something you can demo.

1. [ ] Repo setup and this document
2. [ ] **First test Mod (do this first):** check that
   - `tool.call` sees an Edit or Bash call and its result
   - `context[]` reaches the agent
   - a `system` notice shows in the desktop app
   - **a request sent without waiting still completes after the hook returns.** If it doesn't, wait for it with a `Promise.race` of about 1.5 s.
3. [ ] Backend with a mock `classify()`, deployed to get a stable URL
4. [ ] The full Mod: collection, sending events, running actions
5. [ ] Hook up David's real `classify()`
6. [ ] The Pane with the graph
7. [ ] Demo repo and scenario, rehearsal, **demo video recorded tonight**
8. [ ] Extras: the browser dashboard served by FastAPI, mobile through Remote Control, packaging the Mod as a marketplace for `/plugin install`
9. [ ] README and Devpost write-up (morning of 11-08)

---

## 8. What the Mod can provide to the classifier

David picks from this menu.

- **Session:** ID, cwd/root, git repo (root, remote, name), model and effort, Claude Code version, surface, start time, context usage and cost.
- **The user:**
  - every prompt verbatim, with timestamp and order
  - slash commands
  - attachment details
  - interruptions
  - answers to AskUserQuestion
  - approved plans
- **Project documents:** any file by path, the nearest CLAUDE.md or AGENTS.md to an edited file, directory listings, file details.
- **Actions:** tool name, ID and timestamps, plus full arguments (Edit old and new text, Write content, shell commands, search patterns, URLs) and whether the call was read-only.
- **Results:** the result text as the agent sees it, is_error, Edit/Write diffs and the file's original contents, shell stdout and stderr, interrupted or timed out, and blocked calls.
- **What the agent says:**
  - its visible response text
  - **displayed** thinking, which may be summarized and isn't the full internal reasoning
  - each turn's final message and why the turn ended
  - token usage per step
- **Plan:** TodoWrite lists, the plan-mode plan, turn and step counts.
- **On request:** the full conversation, via `$.session.messages()`.
- **Computed by the Mod:** git diff and status after shell commands, the list of files touched, counts, and action counts since the last instruction.
- **Not available:** hidden model reasoning, and anything outside Claude Code.

---

## 9. Build notes

- `$.http.fetch(url, { method, headers, body })`: `body` must be a **string** (use `JSON.stringify`), and the response is `{ status, ok, headers, text }` (use `JSON.parse(text)`). **It has no timeout option**, so use `Promise.race`.
- Hook budget: 10 s of the hook's own time per call. Time spent waiting on `$` calls or `next()` doesn't count.
- Send events after `next(e)` and never make the agent wait on the network.
- Keep each event under about 256 KB. Send the diff, not the original file. Truncate shell output and leave out `.env` files.
- The `-dev` URL from `modal serve` is not the URL from `modal deploy`, so the Mod's `apiUrl` has to match whichever you're using.
- Keep queued corrections in `$.state`, because module variables reset when the Mod reloads.
- `$.session.append` with `type: "user"` **is** read by the model. Use `type: "system"` for notices meant only for the user.
- `$.ui.notify` doesn't work in the desktop app (`no-surface`), so use notices, `$.ui.toast` or the Pane.

---

## 10. Open items

- **The event payload:** waiting on what data David needs.
- **David's app name and `classify()` signature:** agree on them early.
- **The demo scenario:** it has to make the agent misbehave reliably. Build a demo repo that tempts the shortcut, and keep a backup prompt.
- **How requirements are extracted (David's decision):** don't assume an approach.

---

## 11. Decisions log

| Decision | Why |
|---|---|
| Claude Code Mod only | Native UI and event hooks, and users install one thing |
| FastAPI and the classifier on Modal | Nothing runs locally for users, and David has credits there |
| The server waits for the classifier | The Mod's request doesn't block the agent anyway, so the server-side async machinery isn't needed |
| Corrections go through `context[]` on the next tool result | The agent reads the correction right after its action, and the user doesn't see it as their own message |
| Only the main agent gets corrections; subagents are ignored | Demo scope |
| No toggle | Installing the Mod means the user wants monitoring |
| The classifier decides when to intervene | The Mod and backend just pass things along and run actions |
| The browser dashboard is an extra | Not core to the demo |
| The graph's data stays in the Mod, for one task | No backend storage needed |
| No Modal Dict | David's database holds the history |
