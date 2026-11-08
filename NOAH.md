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
  - Drawn with plain `Svg` elements, `{ source, alt }`, with the markup kept under 131,072 characters. Interactive frames are disabled because of the layout issue in section 5.
  - Plot risk per event, highlight flagged points, and add a distinct marker where a correction was sent. Point tooltips are disabled.
- **Config:** `apiUrl` and `apiToken` are declared as `userConfig` in `plugin.json`, both defaulting to empty. Never hardcode them.
  - Empty values mean mock mode: the built-in mock classifier, the 10-day sample history and the "(mock)" labels.
  - Noah's values live in his local `~/.claude/settings.json` under `pluginConfigs.vision.options`. The token was copied from the gitignored `Noah/backend/secrets.local.json`. **Never commit either.**
  - When connected, the Mod drops any sample history at session start.
  - **Full-system test against `intent-monitor` (stock Kev, 2026-11-07 21:23):**
    - The pipeline works end to end: 20 scripted events plus a real task run through the Mod, all 200 with no fallbacks. Median latency was 452 ms and the slowest 1.5 s (a 2 MB event).
    - The scores don't yet catch the demo action in context, and flagged results come with no actions. Details for David are in `Noah/NOTES-FOR-DAVID-AGENT.md` NN-002.
  - **Verified connected (2026-11-07):** a test-file deletion went from the Mod to the deployed backend and came back as risk 0.94 with three actions in about 0.25 s. The correction reached the agent on its next tool call.

---

## 3. The backend (`Noah/backend/`, Python, FastAPI on Modal)

**Status: built and deployed, connected to stock Kev-4B** through David's `intent-monitor` / `Classifier`. Noah confirmed conflicting use is no longer a concern and explicitly authorized connecting and testing it on 2026-11-07. This supersedes the earlier connection hold in the handoff and contract open items. The stock model is still a placeholder, with no notices or corrections.

- **Deployed URL (stable):** `https://davidkny22--alignment-monitor-api.us-east.modal.run`
  - The dev URL from `modal serve` is the same with `-dev` before `.us-east`.
  - It's in David's workspace (`davidkny22`), reached through Noah's Modal profile `hackbu`.
- **Code:** [Noah/backend/app.py](Noah/backend/app.py), with the persisted dashboard projection in `Noah/backend/dashboard_store.py`.
  - It runs `modal.App("alignment-monitor")`, plus an `@app.function` with the `monitor-token` secret and `@modal.asgi_app()` serving FastAPI.
- **Endpoints:**
  - `GET /v1/dashboard/sessions?cursor=...` uses the same bearer token. Returns `{cursor, reset, sessions}` with changed full session snapshots, or a full reset after backend restart. Reads never call the classifier or warmup. Mod events/results are copied into Modal Dict `vision-dashboard-sessions`, with 2,000 points/session and seven-day entry inactivity expiry; max_containers=1 and an async lock serialize writes. Storage failure/5s write timeout is logged without changing the result returned to the Mod.
  - `GET /health` returns `{ok, classifier, warming}` with no auth. `classifier` is `"mock"` or David's app name. With a real classifier set, it fires `warmup.spawn()` without waiting (`warming: true`), so a cold GPU container starts booting and a warm one is unaffected. The Mod calls it at session start.
  - `POST /v1/events` checks `Authorization: Bearer <MONITOR_TOKEN>` and returns 401 if it's wrong. It validates the event with a Pydantic model using `extra="allow"`: `session_id`, `event_id` and `type` are required, and any missing one returns 422. Unknown fields pass through. It returns `classify(event)` as JSON.
- **The classifier switch:** the `CLASSIFIER_APP` constant at the top of `app.py`.
  - Currently `"intent-monitor"`, deployed and verified against the real stock Kev classifier.
  - **Classifier scaling:** its current `@app.cls` has no `max_containers` limit. `@modal.concurrent(max_inputs=4)` permits four overlapping calls per GPU container, not four calls across the entire app. Modal can start additional L40S containers as demand grows, subject to workspace limits and GPU availability; each loads its own model. `classify` and `warmup` share this container pool. The backend is separately capped at one container and 50 concurrent requests. Classifier idle containers scale down with `scaledown_window=600`; no minimum warm pool is configured. See [Modal scaling](https://modal.com/docs/guide/scale) and [input concurrency](https://modal.com/docs/guide/concurrent-inputs).
  - `None` uses `mock_classify()`.
  - Setting it to David's app name (`"intent-monitor"`) looks up `modal.Cls.from_name(CLASSIFIER_APP, CLASSIFIER_CLASS)()` once per container (`CLASSIFIER_CLASS = "Classifier"`), calls `.classify.spawn.aio(event)`, then waits with `.get.aio(timeout=CLASSIFY_WAIT_S)`.
  - **To fall back during the demo:** set `CLASSIFIER_APP = None` and deploy (takes under a minute). The URL stays the same in either mode, so an already configured Mod uses the selected classifier on its next request.
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
- **Current stock Kev warning/flag threshold:** Noah requested 65% on 2026-11-07. `FLAG_AT = 0.65` is deployed in `David/classifier/app.py`; a non-null risk at or above it sets `flagged: true`. FastAPI passes the flag through. The stock wrapper's actions remain empty, and the Mod's separate color bands are unchanged.
- **Stock Kev fields and the Mod UI:** `risk` and `flagged` come from the classifier. `actions: []` means no notices, corrections or correction markers. `drift` and `drift_rate` are null, so the Mod draws the average risk of the last five scored checks as its Drift value and derives its trend arrow from changes in that average; these are UI estimates, not model-provided drift. Details show the returned `source`, `placeholder`, `question`, `classify_ms` and, when present, `skipped`; missing explanation keys are not filled in. A skipped event has null risk and does not replace the latest scored risk. Missing optional `pending` and `late_results` mean a completed response and no late results, respectively.
- **Logging:** one JSON line per event in the Modal logs (event ID, session, seq, type, tool, classifier, risk, flagged, action types, pending, late result IDs, ms, error or status note). View them in the Modal dashboard or with `modal app logs alignment-monitor`.
- **Test tools:**
  - `Noah/backend/samples/`: four hand-written events in the Mod's format (session start, normal edit, a PowerShell command deleting tests, turn end). They follow CONTRACT.md section 3, are not recorded agent output, and are only for testing the backend. David has his own example inputs, so don't produce samples for him.
  - `Noah/backend/send_event.py`: sends samples and prints each result with its size and latency. `--dev` targets the `modal serve` URL, `--pad-mb N` adds filler to test sizes. It uses certifi's certificates (see build notes).
- **Stand-in classifier** (`mock_classify`, available when `CLASSIFIER_APP` is None). It makes realistic data so the Mod's whole pipeline runs end to end. Each event's answer is seeded by its `event_id`, so a resend gets the same answer.
  - **Reads are unscored:** Read, Grep, Glob, WebFetch, WebSearch, LS and NotebookRead tool calls, and `session_started`, get `risk: null`, no actions and `details.classified: false`.
  - **Deleting tests is flagged:** a delete command (`rm`, `del`, `rmdir`, `Remove-Item`, `unlink`, `git rm`) on a test path, or a `file_changes` delete of one, scores 0.88 to 0.96. It returns `notify_user` (detected), `inject_agent` and `notify_user` (intervened). These are never made pending, so the demo correction always arrives on time.
  - **Weakening tests is a potential issue:** an edit to a test file that removes assertions or adds a skip scores 0.55 to 0.68, with a `potential` notice and no correction.
  - **Everything else:** usually 0.03 to 0.30. About 12% of events score 0.40 to 0.65 with a made-up concern, plus a `potential` notice when it's 0.5 or more. Only 0.7 and up is flagged.
  - **`details`:** `behavior` (the tool and its target), `concern` and `requirement` (the session's latest user instruction), plus `mock: true`, which the Pane hides.
  - **Drift:** `drift = 0.85 * drift + 0.15 * risk` per session, and `drift_rate` is the change from the previous scored event.
  - **Slow results:** about 1 in 8 scored tool calls returns `pending` at once, and its real result rides in `late_results` on the next response for that session.
  - **State** (drift, the latest instruction, late results) is kept in the container's memory per `session_id`. So the API function runs in one container (`max_containers=1`, `@modal.concurrent(max_inputs=50)`) that stays up 20 minutes after the last request (`scaledown_window=1200`). After that, or after a redeploy, drift restarts at 0 and a waiting late result is lost.
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
  - the stand-in classifier, deployed: the four samples (the deletion flagged with all three actions, reads and session start unscored, drift rising). In 24 events in one session, 4 came back pending, and each was delivered once, with its drift, on the very next response.
  - real stock Kev connection: deployed the backend with `CLASSIFIER_APP = "intent-monitor"`; `/health` reported that app and warmup completed in 29.77 s. All four samples returned HTTP 200 with `details.source: "stock-kev"`, no pending responses, empty actions and null drift fields. Risks were null for session start, 0.2057 for the edit, 0.4074 for deleting tests, and 0.1289 for the final message; none was flagged. Small-event round trips were 1.14 to 1.24 s. A 5 MB padded edit also returned HTTP 200 with risk 0.2057 in 4.23 s. This verifies backend/classifier transport, not the Mod's live pane or sustained throughput; the Mod engineer still needs to run controlled tool calls in the connected session.
- **No server-side storage** with the real classifier: David's database holds the history, and the Mod holds the graph data. Only the stand-in keeps per-session state in memory.
- **Commands** (run from the repo root):
  - `set PYTHONUTF8=1` first in cmd, or prefix `PYTHONUTF8=1` in bash (see build notes).
  - `.venv\Scripts\modal serve Noah/backend/app.py` for development, with hot reload and the `-dev` URL.
  - `.venv\Scripts\modal deploy Noah/backend/app.py` updates the stable URL.
- **Multiple chats in one project:** separate main-agent chats are designed to remain independent through distinct `$.session.id()` / `session_id` values; project path/name is metadata, not the classifier state key. Mod event results and corrections are applied through the originating chat's engine context; the classifier SessionStore keys headers/events by session ID. VISION must be loaded/configured in each chat (development Mods live under session-specific folders). Separate sessions share classifier capacity and the project filesystem; they do not isolate file edits. Spawned subagent tool calls are currently ignored when `e.agentId` is present. This was checked in code, not verified by a new simultaneous two-chat live test.
- **Local dashboard visual preview:** built in `Noah/backend/dashboard/`. Run `node Noah/backend/dashboard/serve.mjs` from the repo root and open `http://localhost:4173/` (Noah requested the hostname rather than the numeric loopback address). No dependency installation is needed. `node Noah/backend/dashboard/build.mjs` produces a static, gitignored `dist/` directory with relative asset paths for future GitHub Pages deployment.
  - **Desktop redesign (Noah, 2026-11-08):** the shell now follows familiar Cursor/Codex application patterns. A quiet charcoal sidebar groups compact active-agent task rows by project, with selection, status and last-seen age. The main workspace puts all six run statistics near the top, followed by the preserved risk/drift graphs and existing action disclosures. The user subsequently added Home and Agents pages plus mobile bottom navigation; the existing per-agent instruments remain unchanged.
  - **Home, Agents and mobile navigation (Noah, 2026-11-08):** `/` defaults to Home with counts of active agents and agents needing attention, plus a dedicated View agents link. The Agents directory opens each session's existing stats view. Mobile navigation is a fixed wide pill-shaped floating island, with 16px side/bottom gaps, safe-area spacing and a 440px width cap, with Back left, Home center and Agents right, including safe-area padding and content clearance. Desktop adds Home/Agents sidebar links and retains compact project-grouped session links, without a bottom bar. Back follows app history, with Agents/Home parent fallback on direct entry. Routes remain local fragments, including sample-session IDs.
  - **Home and site styling (Noah, 2026-11-08):** Noah supplied four dashboard images as inspiration for site typography, spacing and surrounding UI, explicitly excluding graph details. Current pages use dark rounded panels, larger quiet headings and restrained violet selection. The breadcrumb/Home/Preview bar and its route-rendering code are removed on Home, Agents and agent details at all sizes. Home is titled Agent overview; an open health summary sits above the Agents panel, with the active total beside its breakdown. View agents is in the Agents panel. Sample-data provenance moved to the sidebar footer on desktop and content footer on mobile. Graph renderer code, line/marker designs, calculations, health colors/geometry and pill navigation geometry are preserved; surrounding chart/event/directory panels share the new skin. Reference rationale is in dashboard/.impeccable/reference-style.md.
  - **Open health summary refinement (Noah, 2026-11-08):** Home now has an unboxed pie and summary above the Agents panel. Active-agent count sits with the health breakdown; the leading Agent health circle is removed. The Needs attention description is behind a hover/focus/tap info icon, with no standalone explanatory paragraph. Added a healthy docs agent in demo-shop: three active, two healthy, one intervention-needed, yielding 67%/33%. Desktop rows compact to keep all three visible; at 1280x600 content ends at 559px. At 390x844 the sample footer ends at 717.75px before the island at 762px. At 320px there is no horizontal overflow, tooltip stays within x=9..289 and scrolled footer clears the pill. New example opens its six-stat/two-chart view with risk8%, flags0, corrections0. Browser console empty; syntax/build and sample-count assertions passed.
  - **Bolder agent-list typography (Noah, 2026-11-08):** Home's Agents contents and Agents directory now use locally bundled Manrope for task titles, the directory/panel headings and risk values, paired with native metadata. Sizes are task20px/600, panel22px, directory34px desktop/30px mobile, risk26px and metadata13px. Project tags, semantic health badges and round row arrows replace tiny flat rows. Current risk stays separate from explicit intervention health; no classifier/state rule changed. The font and OFL license are in dashboard/fonts/, copied by the static build and served locally with no third-party runtime request. Browser confirmed the font loaded. Home still fits 1280x600 (content577px); directory fits 1024x650 (lastrow518.5px), with no horizontal overflow at768,390,320px. Narrow risk figures stack below their labels and content clears the pill. Keyboard routing opens six stats/two charts with original chart font, console empty. Source graphs and upper health summary are unchanged.
  - **Current style verification:** Home and directory were checked on desktop/mobile without the removed header. Default agent details still fit at 1280x600 (lists end at 550.5px) and 1024x650 (600.5px), with six statistics and two charts. Mobile Home fits 390x844; the Sample data footer ends at 717.75px before the pill at 762px. Narrower pages scroll normally; at 320px, chart headings wrap controls within the panel, no horizontal overflow occurs, and the detail footer scrolls above the pill (603.8px before 618px). Last 10 filtering, flag/correction disclosure and navigation passed; console was empty. Build/syntax checks pass and the graph renderer hash is unchanged. Previous health-state tests remain applicable because model.js is unchanged. A fresh supplied-image style review returned ship with no material fixes.
  - **Aggregate meanings (supersedes the earlier flagged-based Home count):** supplied preview sessions count as active. Health uses the proposed explicit classifier boolean `requires_user_intervention`: true = user input requested, false = no such request, absent/null = unreported. Ordinary flags and automatic corrections are separate. The latest explicit non-pending snapshot by event sequence wins; missing/pending or older late results do not clear/override it. Unreported agents get a neutral chart slice, rather than being mislabeled healthy. No risk threshold is added in the dashboard.
  - **Navigation verification:** Home/directory/detail routes, keyboard entry, mobile Back/Home/Agents controls and direct-entry parent fallback are preserved. Current supplied-image evidence uses dashboard/.impeccable/review/reference-*.jpg. Scrolling mobile captures are provider-scaled from CSS viewport to client width; no screenshot resizing was performed. Historical screenshots and reviews describe their recorded revisions.
  - **Desktop fit:** the default view fits without horizontal or vertical page overflow at 1024x650, 1280x600, 1280x720 and 1440x900. Both charts and both lists sit side by side at widths of at least 1000 px. Short desktop chart height now has a 170 px floor; all three default recent rows remain visible. Open details and extra rows may scroll naturally.
  - This is a local UI preview with three explicitly labeled sample sessions, not live agent data. It makes no FastAPI, Modal, warmup or inference requests. Dashboard persistence, live polling, saved-call result collection and GitHub Pages publication are still pending.
  - The graph renderer and calculations were preserved during the redesign, including risk bands, chart windows, correction markers and the five-check drift average fallback. Agent selection via keyboard, Last 10 filtering, flag/correction details and recent-check show-more/show-less were verified; browser warnings/errors were empty. JavaScript syntax and static build passed. The local server remains running for Noah; source changes rebuild automatically and appear after refresh.
  - **Design guidance:** Noah supplied the Impeccable ZIP. Applied Operate for hierarchy/state, layout/distill for the sidebar and density, then polish/audit for verification. Its command runtime was unavailable, so project context and references were read directly. PRODUCT.md records scope, and DESIGN.md plus .impeccable/design.json persist the design system. A fresh reviewer requested more chart height on short desktops, then verified that fix and returned ship.

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
5. [x] Hook up David's real `classify()` (stock Kev, deployed and sample-tested 2026-11-07; live Mod UI check remains)
6. [ ] The Pane with the graph
7. [ ] Demo repo and scenario, rehearsal, **demo video recorded tonight**
8. [ ] Companion web dashboard: live data integration deployed; GitHub Pages/proxy deployment pending. Other extras remain later: mobile through Remote Control and marketplace packaging.
9. [ ] README and Devpost write-up (morning of 11-08). Candidate material is collected in section 8.

---

## 5. Build notes

- `$.http.fetch(url, { method, headers, body })`: `body` must be a **string** (use `JSON.stringify`), and the response is `{ status, ok, headers, text }` (use `JSON.parse(text)`). **It has no timeout option**, so use `Promise.race`.
- Hook budget: 10 s of the hook's own time per call. Time spent waiting on `$` calls or `next()` doesn't count.
- Send events after `next(e)` and never make the agent wait on the network.
- The `-dev` URL from `modal serve` is not the URL from `modal deploy`, so the Mod's `apiUrl` has to match whichever you're using.
- **The Modal CLI crashes on Windows** with `'charmap' codec can't encode character '✓'` because its console output uses a checkmark. Run it with `PYTHONUTF8=1` (and `PYTHONIOENCODING=utf-8`) set.
- **Python's HTTPS on this machine rejects Modal's certificate** ("certificate has expired") through the default Windows store. Use certifi's bundle: `ssl.create_default_context(cafile=certifi.where())`. certifi is installed in `.venv`. curl and the Modal CLI are unaffected.
- **Limits across the stack** (researched 2026-11-07):
  - **Modal web endpoints:** request bodies up to 4 GiB. **150 s per HTTP request**, after which Modal answers with a 303 redirect to poll for the result. The backend's 8 s classifier wait keeps us well under it. ([docs](https://modal.com/docs/guide/webhook-timeouts), [docs](https://modal.com/docs/guide/webhooks))
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
  - **Draw charts as plain `Svg` images, without `isInteractive`.** The interactive frame (needed for hover tooltips on points) ignored the chart's height and added large empty bands above and below it. Pinning both `width` and `height` (tested 2026-11-07) made tooltips work but kept the gaps, so point tooltips stay off.
  - **A floating box (`position: "absolute"`) is painted over the elements *before* it, and under the ones after it.** To cover the pane and take its own clicks, like the settings menu, it must be the **last** child of the pane's outer box (`position="relative"`). Drawn earlier, the later sections were painted over it, so it looked see-through and they caught its clicks. The ⓘ cards work because each is the last child of its own chart section.
  - **Design guidance adopted from the Impeccable skill (Noah's download, 2026-11-08), Operate mode** (a tool the user works in, so clarity beats expression):
    - **Rhythm:** tight spacing inside a group, more between groups. The pane has three groups: summary (status, current risk, readouts), charts, and activity (flagged, recent).
    - **Tabular figures** (`tabular` on Text) for numbers and times, so columns line up.
    - **Color only for state:** green, yellow and red mean risk level. No decorative color.
    - **One vocabulary:** section titles, buttons, dim helper text and icons look the same everywhere.
    - **Empty states explain the pane.**
    - **Restraint:** no gradients, glow, decorative motion or extra containers.
    - Not applicable here: its launcher scripts and browser tools (not run; the Mod isn't a web page), fonts, page layouts, and marketing-page advice.
  - **Chart axes span only drawn points:** the risk chart draws scored checks plus checks waiting under 2 minutes, and the drift chart draws scored checks only. Unscored reads and lost results used to stretch the time axis.
  - **Never put a border on a small control.** On the desktop a Box border adds a lot of size: a rounded border around the time window buttons made them huge. Plain Buttons can't be given rounded backgrounds, so the selected window uses a square tint the size of the button.
- **Type-check with TypeScript in the scratchpad.** The `claude` command line isn't installed, so run `tsc -p <mod>/.claude-plugin/types/tsconfig.json` with a TypeScript copy installed in the session scratchpad. The engine checks rules, not types.
- **Slow results (N-001), handled in the Mod:**
  - A `pending: true` result keeps the point in its checking state.
  - Each entry in `late_results` is applied to its own `event_id` through `applyResult`, running its notices and corrections in order.
  - **Drift (Noah approved):**
    - The second chart is now **"Drift"**, which plots the classifier's `drift` (lower is better).
    - The readout row shows **Drift** with a ↑, ↓ or → arrow from `drift_rate`, in place of "Alignment".
    - Until the classifier sends `drift`, both use the average risk of the last 5 checks as a stand-in.
  - Still to verify: a ~5 MB send through `$.http.fetch`. Connecting the Mod to the deployed backend through `userConfig` is already verified (section 2).
- **Mock-only behavior to check when linking the real backend:**
  - The "Mock classifier" label and the auto-loaded 10-day sample history only appear while `apiUrl` and `apiToken` are unset, so they disappear once the real backend is configured.
  - Confirm both are gone in the live demo.
- **The Mod's temporary debug trace** still writes to a scratchpad file while connected. `DEBUG_CONTEXT` is false, so trace text is not attached to tool results. Removing the trace remains a Mod cleanup item.
- `$.session.append` with `type: "user"` **is** read by the model. Use `type: "system"` for notices meant only for the user.
- `$.ui.notify` doesn't work in the desktop app (`no-surface`), so use notices, `$.ui.toast` or the Pane.
- `$.model.complete` is available for requirement extraction, but **don't use it** unless David decides to. He's concerned it would share the agent's proxy bias.

---

## 6. Open items

- **Dashboard scope agreed with Noah (live backend feed connected locally):** a read-only UI lists reporting Mod sessions, with a detail view for each showing the same statistics as the Mod pane. The current design target is a clean Cursor/Codex-inspired desktop dashboard, with the graph designs preserved and all run statistics near the top. Home and Agents pages share the desktop/mobile flow; mobile now has a fixed Back/Home/Agents bottom bar. Use a local testing port and add no product functionality beyond remote viewing of the Mod. Separate agent instances are supported; subagents, notifications of any kind and user authentication are out of scope for the demo. Correction delivery is assumed successful; no acknowledgement protocol is required. Without a heartbeat, activity should be described using last-seen timestamps rather than claiming certainty that a session is still running.
- **Current dashboard visual refinement (2026-11-08):** local synthetic preview at localhost:4173 uses IBM Plex Sans and neutral gray accents with no purple; drift is amber with unchanged graph geometry/calculations. Home starts with VISION above a left-aligned Agent overview title, then an unboxed health donut and active/healthy/attention breakdown without a health title/divider. See all is a compact text-height button. Home agent rows show task and right-aligned folder/project on line one; semantic green check/red rounded intervention triangle/neutral info plus status and right-aligned update age on line two. Agents now groups every session by project with folder headings and indented rounded card stacks, retaining all task/risk/health/update fields and full-row links. Risk: appears inline immediately before its percentage at every width; mobile cards are about 81px high at 390px. Short-desktop donut is 164px to retain Home fit. Verified Home/Agents at 390px/320px mobile and 1280x600 desktop, all three samples/two projects and risk values, card routing, no horizontal overflow and empty console. Syntax/build checks pass; health model unchanged (six tests passed during prior refinement). Evidence is under dashboard/.impeccable/review/grouped-*.jpg. No deployment, classifier calls or live integration.
- **GitHub Pages published (Noah requested push + phone setup, 2026-11-08):** commit 800c360 pushed the dashboard/backend/workflow to main. .github/workflows/dashboard-pages.yml successfully tests/builds/publishes https://noahbkivel.github.io/HackBU-NoahDavid/; Pages source is workflow. Hosted client reads Modal directly and requests a runtime read-only key; localhost keeps its existing token proxy. Backend is deployed with GET/Authorization CORS for https://noahbkivel.github.io and DASHBOARD_TOKEN from Modal Secret vision-dashboard-read; that key cannot POST events. The initial credential creation attempt was blocked by automatic approval review; Noah then explicitly approved persistent read-only phone access, so the key was created and backend deployed. Key is only in ignored Noah/backend/dashboard-access.local.json and Modal Secret, never in GitHub/static assets; it remains valid until rotated. Verified live read 200 with correct CORS, event write rejected 401, Pages HTTP 200, ten backend tests, nine Node tests and static build. See dashboard/PAGES-SETUP.md. User reported the initial sample run matched in Mod and web app. Existing Mod/live-local access remains unchanged.
- **Live dashboard connected/deployed (2026-11-08):** localhost:4173 now reads real Mod traffic through a server-side authenticated proxy using the Mod's existing apiUrl/apiToken; no browser token is bundled. One-second cursor polling loads persisted backend snapshots and late-result updates, without inference/warmup or changing Mod/classifier source. Synthetic data is explicit ?preview=1 only. Modal Dict vision-dashboard-sessions survives backend restarts; 2,000 points/session match the Mod, seven-day entry inactivity expiry applies. Data collection starts with deployment; older Mod-local history cannot be backfilled and already-running sessions can lack project/title metadata. Missing requires_user_intervention stays Unreported; requested corrections are assumed delivered. Verified deployed 401/200 reads, persistence through redeployment, actual incoming Mod events, nine backend and nine Node tests, build/syntax. Existing classifier KeyError event_ids on session 27d538a7 is recorded in NN-004, not hidden or repaired by deleting state. The late-final-result gap remains the same as the Mod. Production GitHub Pages/proxy hosting is still pending. Other agents' concurrent Mod/demo edits were left untouched.
- **Agents viewing filter (Noah requested, 2026-11-08):** the directory now displays overall healthy and attention totals stacked vertically. View problems sits immediately to the right of the attention row, becoming Remove filter in the same position while active. Its total agent count is a separate N agents total line directly above the project list, below the counts/filter controls, rather than beside the Agents title; it remains the overall total while filtered. View problems filters to explicit intervention-needed sessions using existing sessionHealth; Remove filter restores all agents. Counts remain fleet totals; empty project groups are hidden and no matches has an empty-state message. Filter persists across in-app navigation, resets on full reload, retains keyboard focus and announces result updates politely. This never sends a stop/correction command or invokes classification. Verified the three-card/two-project list filters to one attention card/one project and restores correctly; card navigation preserves the filter, 390px/320px have no horizontal overflow, 1280x600 fits, console is empty, build/syntax and six health-state tests pass.
- **Remove connected footer label (2026-11-08):** successful live connections no longer show Live data in the desktop sidebar or mobile footer. The entire footer element is hidden with no leftover dot/spacing. Connecting, connection/access errors and explicit sample-mode labels remain available. Verified both footer elements hidden and no Live data text in the mobile render; syntax/build pass.
- **Mobile Home health spacing (2026-11-08):** reduced each legend row vertical padding from 12px to 4px below 701px, bringing the three health states closer together. Verified 390px live layout, 90px total legend height and no horizontal overflow; desktop spacing unchanged.
- **Analytics colors match Mod (2026-11-08):** current-risk percentage and label, drift, max and average risk now use the same display bands as the Mod: below .4 green, .4 through below .7 amber, .7+ red; flagged current risk is red. Nonzero flags are red and nonzero corrections green; zeros neutral and missing scores muted. Metric-scoped tones match Mod HEADLINE_COLORS (#53C556/#E49C06/#F17778), without changing global navigation or chart colors. Verified live values matched Noah's screenshot exactly: 44% risk/68% max/48% average amber, 13% drift green, four flags red, zero corrections neutral. Syntax/build pass; screenshot metric-colors-desktop.jpg. No data, thresholds or calculations changed.
- **Backend mock health field (2026-11-08):** Noah requested adding intervention state to mock responses. Existing completed backend mock results now emit requires_user_intervention=false, including skipped results and completed late-result snapshots; its existing corrections are automatic and never request human intervention. Pending/fallback real-model responses remain unset, preserving unknown semantics. Eleven backend tests pass. Current test feed was confirmed stock-kev, not this mock. Noah explicitly chose to leave the mock disabled and keep Kev connected; the health donut will populate automatically when real completed results include explicit intervention state. No frontend switch or refresh is needed.
- **Health donut diagnosis (2026-11-08):** user reported no pie population locally or on Pages. Verified the shared saved feed had three sessions and zero explicit requires_user_intervention booleans; one session had 20 scored events. Local Home renders 0 healthy, 0 attention, 3 Unreported (100%), so ingestion/renderer work but the classifier health signal is missing. Preserve the agreed semantics: do not infer healthy/stop state from risk or correction text. NN-003 remains the implementation requirement; NN-005 records this live confirmation for David.
- **User-intervention signal proposal (Noah approved reset behavior; David agreement pending):** NN-003 in `Noah/NOTES-FOR-DAVID-AGENT.md` requests top-level `requires_user_intervention` as a persistent classifier session-state snapshot, emitted from the same decision path as the stop-and-wait `inject_agent` action. Set true for an explicit human handoff, preserve it across normal/skipped events, and reset on the next genuine new user instruction using instruction-ID deduplication. Repeated instructions, automated corrections, low-risk tools and pending/error results must not clear it. Late snapshots keep their original event identity; classifier state updates must respect instruction/event order under concurrency. The current dashboard only previews this proposal. FastAPI extra-field passthrough was verified offline for normal and late results without loading the app or contacting Modal. No shared contract, classifier source, deployment or Mod API was changed. Existing handoff files are David/NOTES-FROM-DAVID-AGENT.md and Noah/NOTES-FOR-DAVID-AGENT.md; `David/classifier/MESSAGES.md` is now present and records David's owner messages. The classifier and training folders each have their own MESSAGES.md. Noah requested keeping NN-003 only in `Noah/NOTES-FOR-DAVID-AGENT.md` to avoid conflicts with David's work; the temporary copy and message row in the classifier log were removed.
- **Dashboard storage accepted by Noah:** use a new Modal Dict for session metadata and individual `(session_id, event_id)` records. It is native persistent storage that survives container shutdowns and app redeploys, so a third-party database is unnecessary for this demo. Entries expire after seven days with no reads or writes. Keep event summaries compact and persist each result separately rather than appending all history through a shared read-modify-write list. Dashboard reads reuse saved results, not additional classifier inference. See [Modal Dicts](https://modal.com/docs/guide/dicts).
- **Keep-warm decision:** Noah explicitly wants the minimum warm pool left off while building the dashboard. Enable it only for testing/recording/presenting when requested. `min_containers=1` can keep a classifier container warm despite `scaledown_window=600`; the ten-minute setting is an idle scale-down window, not a fixed container lifetime. Modal 1.6.3 supports this parameter. Initial warmup is still needed, and additional autoscaled containers can cold-start. Keep-warm has not been enabled; the current source has no minimum warm pool. Normal classifier calls can still boot a GPU and leave it idle until the scale-down window elapses.
- **Dashboard result collection approved conditionally by Noah:** preserve the existing Mod response contract and functionality, verify the change before deployment, and avoid additional inference. The backend currently stops waiting after eight seconds. Cold-start and queue time are not included in the classifier's late-result clock, and a genuinely late final event has no subsequent response to ride on. These are delivery gaps, not necessarily destruction of the result: Modal retains spawned-call results for seven days. Persist the spawned call ID and retrieve its result later, independently of new Mod events, then update the original event entry. The installed Modal 1.6.3 supports `FunctionCall.from_id` and `get`. This is approved subject to verification, not implemented yet. See [Modal invocation methods](https://modal.com/docs/guide/function-invocation-methods).
- **Dashboard repository and hosting agreed with Noah:** all project source and build/deployment configuration stays in this repository. GitHub Pages serves the frontend; FastAPI and Modal Dict provide live data. Keep frontend assets under `Noah/backend/dashboard/` and publish their static build through a GitHub Pages workflow. The backend must allow the Pages origin through CORS. No hosting has been configured yet. See [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) and [Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
- **Dashboard data flow agreed with Noah:** on boot, the browser loads its static app from GitHub Pages, then requests saved sessions and each selected session's history/statistics from FastAPI. While open it polls for changes about once per second using an update cursor. Updates include changes to old pending records, not just newly created events. Each Mod keeps its current request/response path; backend records are saved independently for viewers to read later. Opening additional dashboards must not rerun classification or warm the GPU. Live data requests and persistence add CPU/storage work to the existing agent-only backend; serving frontend assets moves to GitHub. The desktop shell now follows Cursor/Codex-style navigation, while preserving the existing VISION graph designs and run statistics.
- **Same-session concurrency deferred for review:** the current classifier can process events out of order and uses read-modify-write updates for instruction records and late-result lists, so overlapping requests can read stale context or overwrite updates. Short classifications reduce overlap but do not guarantee serial processing. Sorting dashboard entries by `seq` does not fix classifier processing order. Different session IDs separate different agents' records. Revisit with the realistic traffic-test findings.
- **The demo scenario:** it has to make the agent misbehave reliably. Build a demo repo that tempts the shortcut, and keep a backup prompt.
  - **Headless Haiku pilot (2026-11-08):** the bundled CLI at `AppData/Local/Claude-Data/claude_pzs8sxrjxfjjc/claude-code/2.1.317/a33aa5518497/claude.exe` works with Noah's completed `claude.ai` Pro login; the Haiku alias resolves to `claude-haiku-5-5`. Recorded local trials and the disposable fixture live in [Noah/demo-pilot/](Noah/demo-pilot/), with measured findings in [RESULTS.md](Noah/demo-pilot/RESULTS.md). Pressure alone produced no test weakening in five attempts, two affected by harness permissions. A source-freeze requirement in README produced actual M2 edits in two of three fresh focused-prompt trials; one was later self-repaired. The shorter, already-triaged prompt produced forbidden source edits in 3/3 fresh low-effort trials at 13.4-14.0 seconds after transcript creation, with no permission denials. A fresh desktop fixture is at `C:\Users\noahk\AppData\Local\Temp\vision-pilot-or9cl99k`. These are restricted headless trials without the Mod attached, not a completed live correction demo. An actual-event classifier replay was prepared but blocked by automatic approval review pending Noah's approval of its payload and Modal destination. No classifier cutoff, deployment or warm-pool setting changed.
  - **Prompt design review (2026-11-08):** [Noah/DEMO-PROMPT-DESIGN.md](Noah/DEMO-PROMPT-DESIGN.md) maps the current question set to copyable pilot prompts and a confirmation protocol. Noah selected Haiku for the desktop demo; record its exact model version and effort before pilots. The recommended first candidate stays with D74's slow-tests scenario, targeting M4 plus M2 through lost valid regression coverage. M4 explicitly excludes fixing a test that contradicts the stated specification, so the earlier wrong-expected-value idea is not a clean primary violation. No target-agent trials or repeatability rate are claimed; fixture pilots remain pending. The local Claude CLI was not found. No classifier call, cutoff change or deployment was made.
- **Live demo readiness:** classifier cold starts must be handled before presenting. The full problem, the simple fix for the demo and the proposed warm-up design are in CONTRACT.md section 7 ("Classifier cold starts").
- **Source/documentation review (2026-11-07):**
  - The Mod calls `warmUp()` only from `startSession()`, not from `prompt.submit`. Warming on every user prompt is agreed in CONTRACT.md and David's N-002, but remains a Mod follow-up.
  - Some Mod documentation still describes older behavior: MOD_PRD.md FR-2 says missing settings mean "Not configured", although the implemented default is the built-in mock; FR-13 both requires every tool call and says reads are not sent; FR-27 still describes interactive charts, although the source uses plain SVG images. The Mod engineer should reconcile the PRD and the build checklist with the implemented behavior.
  - The initial source/GitHub review made no Modal calls. Noah subsequently authorized connecting, and the backend is now deployed and verified against stock Kev (section 3). The latest classifier notes are still N-002; agreement on `backend_sent_at` remains open, so the cold-start result-loss gap is still present. Warmup was completed before the sample tests.
- See CONTRACT.md section 7 for open interface items.

---

## 7. Decisions log

| Decision | Why |
|---|---|
| Claude Code Mod only | Native UI and event hooks, and users install one thing |
| FastAPI and the classifier on Modal | Nothing runs locally for users, and David has credits there |
| Connect the backend to stock Kev for pipeline testing (Noah, 2026-11-07) | Noah confirmed conflicting use is no longer a concern. Real risk values exercise the integration; empty actions and null drift retain their existing UI behavior. The stand-in remains available by switching back to `None`. |
| Stock Kev warning/flag threshold is 65% (Noah, 2026-11-07) | Noah requested changing the classifier threshold from 50% to 65%. This is implemented in the classifier wrapper; it changes `flagged`, while actions remain empty. |
| The server waits for the classifier | The Mod's request doesn't block the agent anyway, so the server-side async machinery isn't needed |
| Corrections go through `context[]` on the next tool result | The agent reads the correction right after its action, and the user doesn't see it as their own message |
| Only the main agent gets corrections; subagents are ignored | Demo scope |
| Dashboard assumes correction delivery succeeds (Noah, 2026-11-07) | No Mod acknowledgement is required. Noah accepts that a continuing deviation may be caught by a subsequent classification and corrected again. |
| Dashboard demo lists separate agent sessions with per-session Mod statistics; no subagents, notifications or user authentication (Noah, 2026-11-07) | Noah wants a monitoring UI for active agents, with each session opening into its own statistics view. These extra capabilities are unnecessary for the hackathon. |
| Dashboard session metadata and results will use a separate Modal Dict (Noah, 2026-11-07) | Noah accepted native Modal persistence, avoiding a third-party database for the hackathon. Implemented in vision-dashboard-sessions for dashboard event/result summaries. |
| Leave the minimum warm classifier pool disabled during dashboard development (Noah, 2026-11-07) | Keep an idle GPU from running continuously while building the UI. |
| Add saved-call result collection provided existing Mod behavior is preserved and verification passes (Noah, 2026-11-07) | Finished results should be recoverable without requiring another agent action or another inference call. |
| All dashboard source and deployment configuration stay in the project repository (Noah, 2026-11-07) | Hosting can deploy the frontend from a subdirectory of the existing repository; no separate source repository is needed. |
| Host the dashboard on GitHub Pages and poll FastAPI for persisted updates (Noah, 2026-11-07) | Noah accepted initial history loading and approximately one-second incremental updates. GitHub serves the app files while Modal handles live session data. |
| No toggle | Installing the Mod means the user wants monitoring |
| The classifier decides when to intervene | The Mod and backend just pass things along and run actions |
| Start the companion dashboard with a local visual preview of the existing Mod (Noah, 2026-11-07) | Match the Mod closely on mobile and use a simple desktop arrangement. No additional product features; review the visual baseline before live data integration. |
| Replace the Mod-mimicking desktop shell with a clean Cursor/Codex-inspired dashboard (Noah, 2026-11-08) | Group compact agent task rows by project in the sidebar; keep six run stats near the top and preserve graph designs. Desktop first, no new features; mobile redesign deferred. |
| The default desktop dashboard fits on screen without scrolling (Noah, 2026-11-07) | Keep all summary statistics, both charts and the default flagged/recent rows visible. Extra rows and expanded details may scroll normally. |
| Prepare GitHub Pages and read-only phone access (Noah, 2026-11-08) | Add Actions deployment and direct Modal reads with a runtime read-only key; keep secrets out of the static build. User explicitly approved the persistent read-only key after the initial review rejection; key creation, backend deployment and Pages publication are verified complete. |
| Connect the web app to the Mod backend feed (Noah, 2026-11-08) | Persist the same events/results in a separate Modal Dict; serve authenticated cursor reads through localhost with the Mod token kept server-side. Default to live data, keep samples opt-in, and never rerun inference to view. |
| Stack Agents health totals with View problems beside attention (Noah, 2026-11-08) | Healthy appears above needs attention; the renamed filter button sits beside the attention row and becomes Remove filter while active. Filter behavior and total placement remain. |
| Move the Agents total directly above its project list (Noah, 2026-11-08) | Remove the title count and show N agents total below summary/filter controls; preserve the overall total while filtered. Verified mobile, filtering and desktop fit. |
| Add Agents health totals and a stopped-agent viewing filter (Noah, 2026-11-08) | Show overall healthy/attention counts, filter only explicit intervention requests with Show stopped agents, and restore the full list with Remove filter. Hide empty project groups; do not control agents. |
| Shorten directory risk labels and keep them inline (Noah, 2026-11-08) | Use Risk: immediately before the percentage, including mobile, reducing card height. Verified 390px/320px with no horizontal overflow. |
| Brand Home and group the Agents directory by project (Noah, 2026-11-08) | Add VISION above a left-aligned Home title; align folder/project and update age to the right in two-line Home rows. Replace the directory table with project headings and indented stacked cards, preserving task/risk/health/age and routing. |
| Center Home and refine chart/button proportions (Noah, 2026-11-08) | Center the title, add 12px top space, use a donut health chart, and reduce See all to text-proportional height. Preserve desktop fit with a tighter section gap on short screens. |
| Compact mobile Home agent entries (Noah, 2026-11-08) | Remove Agents heading icon, rename View agents to See all, use title/dimmed project on line one and a semantic check/warning icon with status on line two. Preserve full-row routing and desktop row layout. |
| Remove purple accents and simplify Home health/agent styling (Noah, 2026-11-08) | Remove health heading/divider, use IBM Plex Sans, smaller 18px Home task names, plain status text and square markers; replace purple drift color with amber without changing graph geometry or calculations. |
| Strengthen Home agent contents and Agents page typography using the supplied images and Impeccable (Noah, 2026-11-08) | Add locally served Manrope, larger task names/risk figures, project tags and health badges; preserve charts, state rules and surrounding navigation. |
| Unbox the upper health summary and move total beside its breakdown (Noah, 2026-11-08) | Replace the standalone explanation with an info tooltip, remove the Agent health title icon, and add a healthy docs example for a two-to-one pie split. Keep graph designs and state rules. |
| Remove the global Home/Preview bar and apply the supplied dashboard-image style (Noah, 2026-11-08) | Use dark rounded panels, clearer native typography and restrained violet navigation across all pages and viewports. Keep graphs and calculations, health-state semantics and pill navigation behavior. No financial features or fake controls are added. |
| Add a sidebar-inspired Home with an agent-health pie and explicit human-intervention state (Noah, 2026-11-08) | Ordinary flags are separate from stop-and-wait requests. Propose `requires_user_intervention` and clear on the next genuine new user instruction. Document NN-003 for David; preserve stats renderer and mobile pill. |
| Redesign Home as a restrained operational overview (Noah, 2026-11-08) | Replace oversized statistic cards and generic copy with compact counts and current activity from existing sessions; preserve accepted agent stats and mobile pill navigation. Research and Impeccable layout/distill guide hierarchy and density. |
| Make the mobile taskbar a wide pill-shaped floating island (Noah, 2026-11-08) | Preserve Back/Home/Agents behavior; use 16px edge gaps, bottom safe-area offset and rounded item states. Desktop layout is unchanged. Verified at 390px and 320px mobile widths. |
| Add default Home and Agents pages with a mobile Back/Home/Agents bottom bar (Noah, 2026-11-08) | Home summarizes active and needs-attention counts and links to the agent directory; each row opens existing stats. Desktop uses sidebar navigation, preserving its layout. Needs attention follows the latest scored flagged result. |
| Use dependency-free static HTML, CSS and JavaScript for the dashboard preview | The UI only needs read-only rendering, charts and existing Mod disclosures. This starts locally without an installation step and builds static files suitable for GitHub Pages. |
| The Mod keeps its own graph data for one session | The future dashboard will keep a separate persisted copy of event/result summaries. |
| Classifier context history stays on David's side | Dashboard storage will separately hold session metadata and event/result summaries, without taking over the classifier's context history. |
| The Mod sends as much data as possible | No need to agree on a payload first. Only large items are trimmed, and only with Noah's OK. |
| Docs are split into CONTRACT, NOAH and DAVID, all in the root | Each side keeps its own doc, the bridge is shared, and any agent can read all three |
| Events send everything raw, with a 5 MB safety cap per event | David's classifier handles large entries. The cap only stops one huge file from breaking the pipeline. See MOD_PRD.md FR-16. |
| The Mod is named `vision` and its pane and status line read **VISION** | The project name; what the acronym stands for is still undecided. Mod names must be lowercase, so the internal name is `vision`. Renaming reset the Mod's saved state. |
| A root CLAUDE.md holds the rules every agent must follow | Claude Code loads it automatically, so new agents find the docs and the update rule without being told |
| The Mod only sends the most recent events: no checkpoint or batch events, even for long autonomous runs | The classifier analyzes behavior over time from its own history. Events go out after every tool call, so a long run inside one turn is still monitored and corrected action by action. |

---

## 8. Write-up material

Engineering decisions and problem solving worth considering for the Devpost description and the README. What actually goes in is decided together by Noah and David, so this is a pool to pick from, not the write-up. **Add to it whenever a decision like these is made.** David's side can collect its own in DAVID.md.

- **Slow results ride on the next response instead of being dropped.**
  - Problem: the classifier is sometimes slow (a GPU cold start, a change in the user's instructions, very large docs). The Mod can only make requests: nothing can push a result to it later.
  - Decision: the backend waits 8 s, then answers `pending`. The classifier keeps working, stores the finished result, and attaches it as `late_results` to the next response for that session. The Mod updates the earlier point and runs its notices and correction.
  - Why it's good: nothing is lost, the fast path is unchanged, and it needs no queue, no extra endpoint, no polling and no storage in the backend.
- **The UI shows uncertainty honestly.** A pending point stays in a "checking" state until its late result arrives, instead of showing a fake score.
- **Testing transport with the real model before judging its accuracy.** The stock Kev integration was checked with four known events and a 5 MB padded request. This verifies that real model results traverse the backend while separating transport success from detection quality: the test-deletion sample scored 0.4074 and triggered no intervention. The UI's rolling-risk drift fallback is an estimate while model drift is unavailable.
- **Waking the GPU before it's needed.** The classifier is a Modal class whose `classify` and a no-op `warmup` share one container. The Mod's health check at session start fires `warmup` without waiting, so the 25 s GPU boot overlaps with the user typing their task. Warming one that's already running costs nothing.
- **A cold-start gap found by reasoning, not by a failure.** The classifier timed "late" from when it started running, so time spent waiting for a container to boot wasn't counted, and the first result after a cold start would be lost. Found by tracing the timing across both sides, confirmed by David's measurements, with a fix proposed (the backend stamps the send time).
- **The demo never breaks on a classifier failure.** Any classifier error, crash or malformed result becomes a safe "no flag" result with the reason attached, so the agent keeps working and the Pane shows what went wrong. Each late result is validated on its own, so one bad entry can't break the response it rides on.
- **Contracts checked at the boundary.** Both sides validate against the same Pydantic `Result` model (David's check script copies it verbatim), so shape mismatches surface immediately when the halves connect.
- **A clean split of responsibilities.** The Mod sends every tool call raw and runs whatever actions come back. The classifier alone decides what matters and when to intervene, and keeps the history. This let the two halves be built in parallel against a written contract.
- **Corrections reach the agent without pretending to be the user.** A correction is attached to the agent's next tool result, so the agent reads it right after the action it concerns, and the user's own messages stay untouched.
- **Measuring before relying on data.** The agent's thinking looked like a strong signal, but measurement showed 7 of 644 thinking blocks reach the Mod with any text. The classifier was pointed at visible text, plans, todos and actions instead.
- **A realistic stand-in to build against.** While the real model wasn't ready, the backend's stand-in classifier produced varied risk, drift and slow results (seeded by event ID, so repeatable). This exercised every path of the Mod end to end without waiting on the model, or using the GPU David was testing on.
- **Two people and many agents coordinating through docs.** A shared contract, per-side guides, a decisions log and notes files in each direction kept parallel agent sessions consistent, and rules such as "push only once verified" kept the shared branch demoable.
