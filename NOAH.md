# Noah's side: the Mod and the backend

This is the architecture and build guide for `Noah/`: the Claude Code Mod and the FastAPI backend on Modal.
- Shared context, the system overview and the interface with David's classifier are in [CONTRACT.md](CONTRACT.md). **Read it first.**
- David's side is in [DAVID.md](DAVID.md).

> **Every agent: keep this file current.** Maintained by Noah's agents. Whenever you learn or change something another agent would need, update the right section **in the same change**:
> - a decision or a reversal (add it to section 7 with the reason)
> - a new gotcha or a verified API detail (section 5)
> - build progress (tick the boxes in section 4)
> - an open item (section 6)
>
> Interface changes go in CONTRACT.md, and only with both sides agreeing. Edit sections in place. If something turns out to be wrong, fix it. Don't work around it.

---

## 1. Working with Noah

- Claude writes the code, and Noah reviews and runs it. Give him exact commands to run.
- Keep explanations brief but complete. Go deeper only when asked.
- Demo-grade: build only what the demo needs.
- **Local:**
  - Working copy: `C:\Projects\NYCAIRRtest` (Windows 11).
  - Python 3.12 virtual environment at `.venv\`, with `modal` and `fastapi[standard]` installed.
  - Run Modal with `.venv\Scripts\modal`. The default Python is 3.14, so don't use it.
- **Git:** only touch `Noah/` and the shared root docs. Run `git pull --rebase` before pushing, and never commit secrets.
- **Commit messages** (also in Noah's `~/.claude/CLAUDE.md`):
  - **Title:** Conventional Commits with a scope (`feat(mod): ...`, `fix(backend): ...`, `docs(contract): ...`). Plain, descriptive words, so someone reading only the title knows what changed. No jargon, internal names, or phase and step language.
  - **Body:** a short paragraph with more detail than the title, never just repeating it.
  - **Never:** em dashes, or `Co-Authored-By` and other attribution lines. Attribution is turned off in Noah's Claude Code settings.

```
Noah/
  mod/       Claude Code Mod (TypeScript)
  backend/   FastAPI on Modal (Python)
```

---

## 2. The Mod (`Noah/mod/`, TypeScript)

The full requirements are in [Noah/MOD_PRD.md](Noah/MOD_PRD.md). This section is the build summary.

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
  - `session.start`:
    - get the session ID with `$.session.id()`
    - read CLAUDE.md, AGENTS.md and README with `$.fs.read`
    - collect repo, model and version info
    - send a `session_started` event and `GET /health` to wake Modal
    - open the Pane
  - `prompt.submit`: record each user instruction **verbatim** with its timestamp and order.
  - `turn.step`: collect the visible text and displayed thinking.
  - `tool.call` on **Edit, Write, Bash and PowerShell**: on Windows the agent may use PowerShell instead of Bash.
    - Run `const r = await next(e)`.
    - Build the event and send it without waiting.
    - If there are queued corrections and the call is from the main agent (no `agentId`), return `{ ...r, context: [...(r.context ?? []), ...queued] }`.
  - `turn.complete`: send the agent's final message as a `turn_completed` event.
- **Actions** (see CONTRACT.md section 4):
  - `notify_user`: `$.session.append({ message: { type: "system", content: [{ type: "text", text }] } })` adds a notice **the model never reads**. `$.ui.log(text)` is a quieter dim line, which may suit `level: "potential"`.
  - `inject_agent`: queue the text in `$.state` and attach it on the next main-agent tool call.
  - Run actions **in list order**. There's **no toggle**: installing the Mod means monitoring is on.
- **Pane:**
  - Open it with `$.ui.open({ id, title })` and draw it in a `ui.render` hook on `{ component: 'Pane', requestId: id }`.
  - It shows status, the latest risk, flagged events (Buttons that expand to show `details`), and the graph.
- **Graph:**
  - Covers **one task, meaning the current session**.
  - Points `{ts, risk, flagged, corrected}` are kept in `$.state`, which survives Mod reloads.
  - Drawn with an `Svg` element, `{ source, alt, isInteractive: true }`, with the markup kept under 131,072 characters.
  - Plot risk per event, highlight flagged points, add a distinct marker where a correction was sent, and show `<title>` tooltips.
- **Config:** use `userConfig` for `apiUrl` and `apiToken`. Never hardcode them.

---

## 3. The backend (`Noah/backend/`, Python, FastAPI on Modal)

- One `app.py`: `modal.App("alignment-monitor")`, plus `@app.function(secrets=[modal.Secret.from_name("monitor-token")])` and `@modal.asgi_app()` for a FastAPI app.
- **Endpoints:**
  - `GET /health` returns `{ok: true}` with no auth, used for warm-up.
  - `POST /v1/events` takes a Bearer token and validates the event with a Pydantic model using `extra="allow"`. It runs `await classify.remote.aio(event)` and returns the result.
- **Calling the classifier:** `modal.Function.from_name("<david-app>", "classify")`. Until David's is live, use a **mock** `classify()` in this app that returns the contract's output shape.
- **No server-side storage.** David's database holds the history, and the Mod holds the graph data.
- **Commands:**
  - `.venv\Scripts\modal serve Noah/backend/app.py` is for development. It gives a temporary URL ending in `-dev`.
  - `.venv\Scripts\modal deploy Noah/backend/app.py` gives the stable URL for the demo. Put that URL in the Mod's `apiUrl`.

---

## 4. Build plan

The order doubles as the cut list: each step leaves something you can demo.

1. [x] Repo setup and docs
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

## 5. Build notes

- `$.http.fetch(url, { method, headers, body })`: `body` must be a **string** (use `JSON.stringify`), and the response is `{ status, ok, headers, text }` (use `JSON.parse(text)`). **It has no timeout option**, so use `Promise.race`.
- Hook budget: 10 s of the hook's own time per call. Time spent waiting on `$` calls or `next()` doesn't count.
- Send events after `next(e)` and never make the agent wait on the network.
- The `-dev` URL from `modal serve` is not the URL from `modal deploy`, so the Mod's `apiUrl` has to match whichever you're using.
- Keep queued corrections in `$.state`, because module variables reset when the Mod reloads.
- `$.session.append` with `type: "user"` **is** read by the model. Use `type: "system"` for notices meant only for the user.
- `$.ui.notify` doesn't work in the desktop app (`no-surface`), so use notices, `$.ui.toast` or the Pane.
- `$.model.complete` is available for requirement extraction, but **don't use it** unless David decides to. He's concerned it would share the agent's proxy bias.

---

## 6. Open items

- **The demo scenario:** it has to make the agent misbehave reliably. Build a demo repo that tempts the shortcut, and keep a backup prompt.
- See CONTRACT.md section 7 for open interface items.

---

## 7. Decisions log

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
| The Mod sends as much data as possible | No need to agree on a payload first. Only large items are trimmed, and only with Noah's OK. |
| Docs are split into CONTRACT, NOAH and DAVID, all in the root | Each side keeps its own doc, the bridge is shared, and any agent can read all three |
| Large items in events: drop `originalFile`, cap shell output at about 20 KB, no full conversation, no attachment bytes | Keeps events small, and the diff already shows each change. See MOD_PRD.md FR-16. |
| A root CLAUDE.md holds the rules every agent must follow | Claude Code loads it automatically, so new agents find the docs and the update rule without being told |
