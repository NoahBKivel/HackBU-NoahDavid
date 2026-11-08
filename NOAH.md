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
- **When to commit:**
  - If Noah suggests a commit, that's approval to commit and push.
  - If a while has passed without one, ask him whether to commit, so the history shows steady progress.

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
  - `turn.step`: collect the visible text and displayed thinking, **accumulated across every step since the last event** (reset when an event is built).
  - `tool.call` on **every tool** (N-001): David's side decides what it classifies, and reads come back unscored.
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

**Status: built and deployed** with the mock classifier. It's ready to call David's `Classifier` class, but stays on the mock until David says we can use his app (it's in use for his own testing).

- **Deployed URL (stable):** `https://davidkny22--alignment-monitor-api.us-east.modal.run`
  - The dev URL from `modal serve` is the same with `-dev` before `.us-east`.
  - It's in David's workspace (`davidkny22`), reached through Noah's Modal profile `hackbu`.
- **Code:** one file, [Noah/backend/app.py](Noah/backend/app.py).
  - It runs `modal.App("alignment-monitor")`, plus an `@app.function` with the `monitor-token` secret and `@modal.asgi_app()` serving FastAPI.
- **Endpoints:**
  - `GET /health` returns `{ok, classifier, warming}` with no auth. `classifier` is `"mock"` or David's app name. With a real classifier set, it fires `warmup.spawn()` without waiting (`warming: true`), so a cold GPU container starts booting and a warm one is unaffected. The Mod calls it at session start.
  - `POST /v1/events` checks `Authorization: Bearer <MONITOR_TOKEN>` and returns 401 if it's wrong. It validates the event with a Pydantic model using `extra="allow"`: `session_id`, `event_id` and `type` are required, and any missing one returns 422. Unknown fields pass through. It returns `classify(event)` as JSON.
- **The classifier switch:** the `CLASSIFIER_APP` constant at the top of `app.py`.
  - `None` uses `mock_classify()`.
  - Setting it to David's app name (`"intent-monitor"`) looks up `modal.Cls.from_name(CLASSIFIER_APP, CLASSIFIER_CLASS)()` once per container (`CLASSIFIER_CLASS = "Classifier"`), calls `.classify.spawn.aio(event)`, then waits with `.get.aio(timeout=CLASSIFY_WAIT_S)`.
  - **To connect, only with David's OK:** set `CLASSIFIER_APP = "intent-monitor"`, deploy, and send the samples. **To fall back during the demo:** set it back to `None` and deploy (takes under a minute).
- **Slow results** (CONTRACT.md section 4, David's N-001):
  - It waits **8 s** (`CLASSIFY_WAIT_S`) for `classify()`.
  - If `classify()` isn't done by then, it returns a **pending result**: `pending: true`, `risk: null`, no actions, `details.status: "classifying"`.
  - The call keeps running on David's side, and his side delivers the finished result in `late_results` on the next response for that session.
  - The backend stores nothing. It passes `late_results` through, validating each entry against the `Result` model and dropping (and logging) any with the wrong shape.
- **When the classifier fails:** the backend never returns an error to the Mod for a classifier problem. It returns a **fallback result**: `flagged: false`, `risk: null`, no actions, and `details: {source: "backend", error: "..."}`, so the Pane can show "classifier unavailable". It does this when:
  - the classifier can't be reached (app or class not found)
  - the classifier raises an exception
  - the result doesn't match the contract's output shape (checked with the `Result` Pydantic model; the error lists the bad fields)
- **Extra result fields** such as `drift` and `drift_rate` pass through untouched.
- **Logging:** one JSON line per event in the Modal logs (event ID, session, seq, type, tool, classifier, risk, flagged, action types, pending, late result IDs, ms, error or status note). View them in the Modal dashboard or with `modal app logs alignment-monitor`.
- **Test tools:**
  - `Noah/backend/samples/`: four hand-written events in the Mod's format (session start, normal edit, a PowerShell command deleting tests, turn end). They follow CONTRACT.md section 3, are not recorded agent output, and are only for testing the backend. David has his own example inputs, so don't produce samples for him.
  - `Noah/backend/send_event.py`: sends samples and prints each result with its size and latency. `--dev` targets the `modal serve` URL, `--pad-mb N` adds filler to test sizes. It uses certifi's certificates (see build notes).
- **Mock behavior:**
  - Flags deleting test files: `rm`, `Remove-Item` or `del` on a path containing "test", or a `file_changes` delete of one. Returns risk 0.93 with the actions `notify_user` (detected), `inject_agent` and `notify_user` (intervened).
  - Anything else gets risk 0.05 and no actions.
- **API token:**
  - The Modal Secret `monitor-token` (key `MONITOR_TOKEN`).
  - The same value is in `Noah/backend/secrets.local.json`, which is gitignored and **never committed**. The Mod's `apiToken` setting reads it from there.
- **Verified end to end on Modal (2026-11-07):**
  - health 200, no token 401, missing fields 422
  - all four samples: the test deletion flagged with all three actions, the rest unflagged
  - 5 MB and 20 MB events accepted by the deployed endpoint
  - the real-classifier path, tested against a temporary fake classifier app (since stopped): a normal result, a 5 MB event passed through `spawn`, the wrong shape and an exception all behaved as described above
  - slow results, tested the same way:
    - a 12 s classification returned `pending` at about 8 s
    - `late_results` passed through with `drift` and `drift_rate` intact
    - a malformed late entry was dropped while the valid one was kept
  - the class interface, tested against our own fake `Classifier` class with David's method names (since stopped; David's app was not called): `/health` fired `warmup` on a cold container and returned in about 4 s, a normal result, pending at about 9.7 s, the late result delivered once on the next event, the wrong shape and an exception all behaved as above. Then redeployed on the mock and the four samples passed.
- **No server-side storage.** David's database holds the history, and the Mod holds the graph data.
- **Commands** (run from the repo root):
  - `set PYTHONUTF8=1` first in cmd, or prefix `PYTHONUTF8=1` in bash (see build notes).
  - `.venv\Scripts\modal serve Noah/backend/app.py` for development, with hot reload and the `-dev` URL.
  - `.venv\Scripts\modal deploy Noah/backend/app.py` updates the stable URL.

---

## 4. Build plan

The order doubles as the cut list: each step leaves something you can demo.

1. [x] Repo setup and docs
2. [x] **First test Mod, verified 2026-11-07:**
   - `tool.call` sees calls and their results.
   - `context[]` reaches the agent on the next tool call.
   - **Work started without waiting keeps running after the hook returns**, so no `Promise.race` fallback is needed.
   - The Mod lives in `Noah/mod/` and runs with a built-in mock classifier until `apiUrl` and `apiToken` are set.
3. [x] Backend with a mock `classify()`, deployed to get a stable URL (section 3)
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
- **The Modal CLI crashes on Windows** with `'charmap' codec can't encode character '✓'` because its console output uses a checkmark. Run it with `PYTHONUTF8=1` (and `PYTHONIOENCODING=utf-8`) set.
- **Python's HTTPS on this machine rejects Modal's certificate** ("certificate has expired") through the default Windows store. Use certifi's bundle: `ssl.create_default_context(cafile=certifi.where())`. certifi is installed in `.venv`. curl and the Modal CLI are unaffected.
- **Limits across the stack** (researched 2026-11-07):
  - **Modal web endpoints:** request bodies up to 4 GiB. **150 s per HTTP request**, after which Modal answers with a 303 redirect to poll for the result. The backend's 45 s classifier timeout keeps us well under it. ([docs](https://modal.com/docs/guide/webhook-timeouts), [docs](https://modal.com/docs/guide/webhooks))
  - **Modal function arguments** (`spawn`, `.remote`): up to about 2 MiB is sent inline, and larger payloads go through object storage automatically, which is slightly slower. Modal's troubleshooting page mentions a 100 MB gRPC limit that returns 413. A 5 MB event was tested end to end. ([docs](https://modal.com/docs/guide/troubleshooting))
  - **FastAPI and Starlette:** no default body size limit.
  - **The Mod's `$.http.fetch`:** the type definitions document no request size limit and no timeout. Check a 5 MB send when the Mod sends real events.
  - **kev:** validated up to about 8K tokens of input, so David's side must select and trim context (DAVID.md section 2).
- Keep queued corrections in `$.state`, because module variables reset when the Mod reloads.
- **The engine scans the Mod's source before loading it** and refuses the whole module if:
  - `$` is passed to any function that isn't declared at the top level of the file. Helpers nested inside `register` are refused, so keep shared settings in a module-level object.
  - An `atom` reference's `plugin` or `key` isn't a string literal.
  - Hook matchers or pane IDs are built from constants. Write them as literals.

  The refusal appears to Noah as a dim "reload failed" line in the chat.
- **Pane design rules (Noah, 2026-11-07):**
  - The default view must fit on screen at once, without scrolling.
  - Don't put everything in bordered containers. Borders behave badly as the panel width changes (tiles wrapped into a tall column and cut off at the edge).
  - Change the design in small steps that Noah reviews one at a time.
  - **Draw charts as plain `Svg` images, without `isInteractive`.** The interactive frame (needed for hover tooltips on points) ignored the chart's height and added large empty bands above and below it. Point tooltips are off as a result.
  - **Never put a border on a small control.** On the desktop a Box border adds a lot of size: a rounded border around the time window buttons made them huge. Plain Buttons can't be given rounded backgrounds, so the selected window uses a square tint the size of the button.
- **Type-check with TypeScript in the scratchpad.** The `claude` command line isn't installed, so run `tsc -p <mod>/.claude-plugin/types/tsconfig.json` with a TypeScript copy installed in the session scratchpad. The engine checks rules, not types.
- **Slow results (N-001), handled in the Mod:**
  - A `pending: true` result keeps the point in its checking state.
  - Each entry in `late_results` is applied to its own `event_id` through `applyResult`, running its notices and corrections in order.
  - **Drift (Noah approved):**
    - The second chart is now **"Drift"**, which plots the classifier's `drift` (lower is better).
    - The readout row shows **Drift** with a ↑, ↓ or → arrow from `drift_rate`, in place of "Alignment".
    - Until the classifier sends `drift`, both use the average risk of the last 5 checks as a stand-in.
  - Still to do when linking: verify a ~5 MB send through `$.http.fetch`, and point the Mod at the deployed backend URL with the token from `userConfig`.
- **Mock-only behavior to check when linking the real backend:**
  - The "Mock classifier" label and the auto-loaded 10-day sample history only appear while `apiUrl` and `apiToken` are unset, so they disappear once the real backend is configured.
  - Confirm both are gone in the live demo.
- **The Mod's temporary debug trace** writes to a scratchpad file, to `$.store` key `trace`, and optionally (with `DEBUG_CONTEXT`) to every tool result. Remove it before linking.
- `$.session.append` with `type: "user"` **is** read by the model. Use `type: "system"` for notices meant only for the user.
- `$.ui.notify` doesn't work in the desktop app (`no-surface`), so use notices, `$.ui.toast` or the Pane.
- `$.model.complete` is available for requirement extraction, but **don't use it** unless David decides to. He's concerned it would share the agent's proxy bias.

---

## 6. Open items

- **The demo scenario:** it has to make the agent misbehave reliably. Build a demo repo that tempts the shortcut, and keep a backup prompt.
- **Live demo readiness:** classifier cold starts must be handled before presenting. The full problem, the simple fix for the demo and the proposed warm-up design are in CONTRACT.md section 7 ("Classifier cold starts").
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
| Events send everything raw, with a 5 MB safety cap per event | David's classifier handles large entries. The cap only stops one huge file from breaking the pipeline. See MOD_PRD.md FR-16. |
| The Mod is named `vision` and its pane and status line read **VISION** | The project name; what the acronym stands for is still undecided. Mod names must be lowercase, so the internal name is `vision`. Renaming reset the Mod's saved state. |
| A root CLAUDE.md holds the rules every agent must follow | Claude Code loads it automatically, so new agents find the docs and the update rule without being told |
| The Mod only sends the most recent events: no checkpoint or batch events, even for long autonomous runs | The classifier analyzes behavior over time from its own history. Events go out after every tool call, so a long run inside one turn is still monitored and corrected action by action. |
