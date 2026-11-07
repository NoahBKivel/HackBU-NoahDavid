# Mod PRD: alignment monitor for Claude Code

The product requirements for the Claude Code Mod in `Noah/mod/`. It covers what the Mod must do and how each part behaves.
- System context and the backend interface: [CONTRACT.md](../CONTRACT.md).
- Build details and API notes: [NOAH.md](../NOAH.md).

Keep this file current like the other docs. Mark requirements done as they ship, and record changes in section 10.

**Status:** approved, 2026-11-07. Items marked **(verify)** need checking against the Mod type definitions at build time.

---

## 1. Purpose

While a coding agent works, the Mod gives the user a live, explainable view of whether the agent is still doing what they asked. When the classifier says so, it nudges the agent back on course.

**The demo moment:**
1. The user asks for faster tests without reducing coverage.
2. The agent deletes slow tests.
3. A notice appears in chat naming the behavior and the requirement it breaks.
4. The agent receives a correction and restores the tests.
5. The Pane's graph shows the risk spike and the correction marker.

## 2. Users and surface

- **User:** a developer running Claude Code in the **desktop app** on Windows 11. The Pane also draws on mobile, but that isn't a target.
- **Installing the Mod means monitoring is on.** There's no toggle.

## 3. Scope

**In scope:**
- Capturing session, user and agent data, and sending it to the backend
- Running the actions the classifier returns
- A Pane with status, a risk graph and flag details
- A status line entry

**Out of scope:**
- Thresholds or judgment of any kind (the classifier decides everything)
- Blocking tool calls
- Subagents
- History across sessions
- The browser dashboard (an extra)
- Retries and offline queuing

---

## 4. Functional requirements

### 4.1 Configuration
- **FR-1:** The manifest declares `userConfig` fields:
  - `apiUrl` (string): the URL from `modal deploy`
  - `apiToken` (string, **sensitive**, so it's kept in secure storage)

  The values come into `register(on, options)`. **(verify)** Check the exact manifest field syntax: `type`, `default`, `sensitive`, `required`.
- **FR-2:** If `apiUrl` or `apiToken` is missing, the Mod still loads. The Pane and status line show "Not configured", and no requests are sent.

### 4.2 Session start (`session.start`)
- **FR-3:** Reset the session's state, then collect:
  - the session ID (`$.session.id()`) and cwd/root
  - the git repo (`$.session.repo()`)
  - the model, Claude Code version (`$.session.version()`) and surface
- **FR-4:** Read the project docs with `$.fs.read`: `CLAUDE.md`, `AGENTS.md` and `README.md` at the root, if they exist.
- **FR-5:** Send `GET /health` without waiting, to wake Modal. Then send a `session_started` event carrying the session info and docs.
- **FR-6:** Open the Pane: `$.ui.open({ id: "alignment", title: "Alignment" })`.

### 4.3 Capturing the user's instructions (`prompt.submit`)
- **FR-7:** Record each prompt **verbatim** with a timestamp, an ID (`I1`, `I2`, ...) and its order. Include slash command details and attachment details (not the bytes).
- **FR-8:** Don't change the prompt. Pass it on with `next(e)` unchanged.
- **FR-9:** New instructions go out as `new_items` on the next event.

### 4.4 Capturing what the agent says (`turn.step`, `turn.complete`)
- **FR-10:** Stream through `turn.step` (an async generator) and collect the visible text and **displayed** thinking chunks of every step since the last event. Reset them when an event is built. Don't change any chunk.
- **FR-11:** On `turn.complete`, send a `turn_completed` event with the final message, the reason the turn ended, and token usage.
- **FR-12:** Collect the latest TodoWrite list from that tool's calls. The plan-mode plan from ExitPlanMode is **not** collected, because the demo doesn't use plan mode.

### 4.5 Capturing actions (`tool.call`)
- **FR-13:** Send **every** tool call (changed for N-001). The classifier decides which ones to score, and reads come back unscored.
  - Read, Grep and Glob are not sent, but they still get queued corrections attached (FR-22).
- **FR-14:** Run `const r = await next(e)` first, so the tool runs exactly as it would without the Mod.
- **FR-15:** Build a `tool_completed` event as in CONTRACT.md section 3:
  - full arguments, result text and `is_error`
  - Edit/Write diffs (`structuredPatch`)
  - shell stdout, stderr and interrupted state
  - the step's text, thinking and todos
  - any new instructions since the last event
  - `seq` and timestamps
- **FR-16: Send everything raw.** David's classifier handles large entries, so the Mod doesn't trim:
  - `originalFile` (the whole file before an edit) is sent.
  - Shell stdout and stderr are sent in full. When Claude Code keeps only a preview, the Mod reads the saved full output from `rawOutputPath` and sends it as `full_output`.
  - Agent text, thinking and project docs are sent in full.
  - **Safety cap:** if one event goes over 5 MB, the Mod cuts its longest strings, keeping the start and end with a `[cut N chars]` marker, until it fits.
  - Still not sent: the full conversation on every event (events already carry everything new) and attachment bytes.
- **FR-17:** No `git status` after shell commands. In the demo, the deletion shows up in the command itself.

### 4.6 Sending events
- **FR-18:**
  - **Request:** `POST {apiUrl}/v1/events` with `Authorization: Bearer {apiToken}`, `content-type: application/json`, and `body: JSON.stringify(event)`.
  - **Never awaited inside a hook:** the agent never waits on the network.
- **FR-19:** Wrap each request in a timeout race of about 60 s. `$.http.fetch` has no timeout option, and the classifier can be slow. When the timer wins, treat it as an error.
- **FR-20:** On a network error or a non-2xx response, set the connection status to `error` and log it with `$.ui.log(..., { to: "debug" })`. Don't retry. The next event tries again.
- **FR-21:** On success, run `JSON.parse(res.text)`, then:
  - record a graph point
  - update the Pane state
  - run the response's actions (4.7)

### 4.7 Actions
- **FR-22:** Run `actions` **in list order**.
- **FR-23 `notify_user`:** show `text` to the user only. The model never reads it.
  - `detected` and `intervened`: `$.session.append({ message: { type: "system", content: [{ type: "text", text }] } })`, so it stays in the transcript.
  - `potential`: a quieter dim line with `$.ui.log(text)`, so only real detections get a full notice.
  - Prefix each notice so its source is clear, e.g. `Alignment monitor: ...`.
- **FR-24 `inject_agent`:** add `text` to the correction queue in `$.state`.
  - On the next `tool.call` from the **main agent** (no `agentId`), on any tool, return `{ ...r, context: [...(r.context ?? []), ...queue] }` and clear the queue.
  - Mark the matching graph point `corrected: true`.
  - The queue carries over into the next turn if no tool call comes first.
- **FR-25:** Ignore unknown action types. Show them only in debug logs.

### 4.8 Pane
- **FR-26:** One Pane (`id: "alignment"`), drawn by a `ui.render` hook on `{ component: 'Pane', requestId: 'alignment' }`. It's sized to `e.props.bodyColumns`. Top to bottom:
  1. **Status row:** connection (`Not configured`, `Connecting`, `Live`, `Classifying`, `Error`), number of events, number of flags, number of corrections.
  2. **Latest assessment:** risk as a percentage, a `flagged` badge, and the monitor name.
  3. **Risk graph** (FR-27).
  4. **Flagged events:** one Button per flagged event, newest first, showing the time, tool, a short summary and the risk. Pressing one expands it to show `details` as key/value pairs, the notices shown, and the correction text if one was sent.
  5. **Recent events** (optional, last 10): one line each.
- **FR-27 Risk graph:** an `Svg` element, `{ source, alt, isInteractive: true }`, with the markup under 131,072 characters.
  - The x axis is the event index across this session, and the y axis is risk from 0 to 1.
  - A line through all points, flagged points highlighted, and a distinct marker on points where a correction was sent.
  - `<title>` tooltips: time, tool, risk, and whether it was flagged or corrected.
  - The `alt` text summarizes the latest risk and the counts.
- **FR-28:** A `/alignment` slash command reopens the Pane if the user closes it.

### 4.9 Status line
- **FR-29:** `$.ui.status("Alignment: 12% risk, 1 correction")`, updated on each result. Shows `Alignment: offline` on an error.

---

## 5. Non-functional requirements

- **NFR-1:** The Mod never noticeably slows the agent. Hooks do only local work before returning, and network calls aren't awaited.
- **NFR-2:** A failure in the Mod never breaks the agent. Each hook catches its own errors and falls back to `next(e)`.
- **NFR-3:** No secrets in source. The URL and token come only from `userConfig`.
- **NFR-4:** Event bodies stay under 5 MB (FR-16).
- **NFR-5:** State that has to survive a Mod reload lives in `$.state`, not in module variables.

---

## 6. State (`$.state`, declared in `types/index.d.ts`)

| Key | Type | Purpose |
|---|---|---|
| `session` | `{ id, cwd, startedAt }` | Session identity |
| `conn` | `"unconfigured" \| "connecting" \| "live" \| "classifying" \| "error"` | Status row and status line |
| `seq` | `number` | Event counter |
| `pendingItems` | `Item[]` | New instructions and docs not yet sent |
| `stepText` | `{ text, thinking }` | Current step's text and thinking, from `turn.step` |
| `todos` | `Todo[]` | Latest TodoWrite list |
| `corrections` | `{ eventId, text }[]` | Queue for `inject_agent` |
| `points` | `{ eventId, ts, tool, summary, risk, flagged, corrected }[]` | Graph and event list |
| `results` | `Record<eventId, Result>` | Full results for the flag details |
| `expanded` | `string \| null` | Which flag is open in the Pane |

---

## 7. Module layout

```
Noah/mod/
  .claude-plugin/plugin.json   name, version, description, types, userConfig
  hooks/hooks.json             { "modules": ["./register.tsx"] }
  hooks/register.tsx           all hooks and the Pane
  types/index.d.ts             PluginState contract (section 6)
```
Keep it to one module unless it gets hard to read. Development happens in the session's dev-mods folder, and the Mod is copied to `Noah/mod/` before each commit (NOAH.md section 2).

---

## 8. Acceptance checks (the demo)

1. Install the Mod with the URL and token, and start a session. The Pane opens and shows `Live`.
2. Give a prompt with an explicit requirement. The prompt reaches the backend verbatim in `new_items`.
3. The agent edits a file. An event arrives with the diff, a graph point appears, and the agent wasn't slowed down.
4. The agent deletes a test file (Bash or PowerShell):
   - a `detected` notice appears in chat
   - the next tool result carries the correction
   - the agent acknowledges it and changes course
   - the graph shows a spike plus a correction marker
   - the flag's details show the reason
5. Stop the backend. The status shows `Error` or `offline`, and the agent keeps working normally.

---

## 9. Build order

1. **Proof of risky APIs:** `tool.call` capture, `context[]` injection, a `system` notice, and a request that completes after the hook returns.
2. FR-1 to FR-21 against the mock backend (events end to end).
3. FR-22 to FR-25 (actions).
4. FR-26 to FR-29 (Pane, graph, status line).
5. Run against David's real classifier, then go through the acceptance checks.

---

## 10. Open questions and changes

**Open:** none.

**Changes:** (date, change)
- 2026-11-07: FR-16 changed to send everything raw with a 5 MB per-event safety cap, because the classifier handles large entries (Noah).
- 2026-11-07: first draft.
- 2026-11-07: Noah approved the defaults:
  - FR-16: drop `originalFile`, cap shell output at about 20 KB, no full conversation, no attachment bytes
  - FR-17: no `git status`
  - FR-23: `potential` notices as a dim line
  - FR-12: no plan-mode plan
