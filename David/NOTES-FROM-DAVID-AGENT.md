# Notes from David's agent to Noah

Requests and heads-ups from David's side. Entries are numbered in order and never edited after the fact; a later entry supersedes an earlier one by ID.

---

## N-001 · 2026-11-07 15:11 EST · How classifier results get back to the Mod (delivery option 3)

**What David decided (agreed with Noah):** "wait a little, then fall back." The backend waits briefly for `classify()`. If the result is ready in time, it goes back in the same response, as today. If not, the response is a quick "got it" for that event. The finished result then rides on the **next** response for the same session instead of being thrown away.

**Why:** most classifications will be fast once warm. Three moments can be slow: a cold start, the first event after the user's instructions change (the classifier rebuilds its cached copy of the instructions and docs), and very large project docs. Today a slow result is dropped after 45 s. With this change nothing is lost, and the common case stays exactly as simple as now.

### What changes on Noah's side

**1. Backend (`Noah/backend/app.py`), small:**
- Keep the `spawn` + `get(timeout=...)` pattern. It is already right: the call keeps running on David's side after the backend stops waiting.
- Lower `CLASSIFY_TIMEOUT_S` from 45 to a short **wait budget**: **8 s**. That's long enough for a warm classification (well under 1 s expected), short enough that the Mod (60 s) never gives up first, with a wide margin.
- On timeout, return an **"accepted, pending"** result instead of the error fallback:
  ```json
  {"schema_version": 1, "event_id": "<same>", "monitor": "goal_adherence",
   "flagged": false, "risk": null, "pending": true,
   "details": {"source": "backend", "status": "classifying"}, "actions": []}
  ```
  Keep the existing error fallback for real failures (exceptions, wrong shape).

**2. Contract: one new optional field in every result, `late_results`:**
- `late_results` is a list of full results (same shape as a normal result, each with its own `event_id`) for **earlier events in this session** that finished after their own wait ran out.
- **David's side fills it.** `classify()` stores any result that finished late and attaches it to the next response it returns for that session. So the backend needs **no storage and no queue**: it passes the field through like everything else (`extra="allow"` already does this).
- A late result is delivered exactly once.

**3. Mod (`Noah/mod/hooks/register.tsx`), small:**
- In `dispatch`, after `applyResult($, event.event_id, result)`, also run `applyResult($, late.event_id, late)` for each entry in `result.late_results ?? []`. `applyResult` already patches the right point by `event_id`, so the graph point flips from "checking" to its real risk, and any notices or corrections are run in order.
- When `result.pending === true`, leave the point in its "checking" state (`isPending: true`) instead of marking it done with no risk.
- Corrections from late results queue exactly like normal ones and attach to the next main-agent tool result.

**Known edge, accepted for the demo:** if the agent's very last action of a session finishes late and no further event follows, its result has nothing to ride on and only shows up if another event arrives.

### Related decisions already made on David's side that need Mod changes (heads-up)

These come from the same planning session. They are David's decisions about what his side needs, listed here so Noah can plan.

- **Send every tool call, not just Edit/Write/Bash/PowerShell.** Remove the `WATCHED_TOOLS` filter (or include all tools) so reads (Read, Grep, Glob, WebFetch, ...), TodoWrite, ExitPlanMode and AskUserQuestion results are sent as `tool_completed` events too. David's side decides which ones it actually classifies:
  - reads are stored as history only
  - TodoWrite and ExitPlanMode plans are classified
  - AskUserQuestion answers are treated as user instructions

  Unclassified events get an immediate empty result, so they cost almost nothing.
- **Agent text should cover everything since the previous sent event.** `lastStep` currently keeps only the latest step's text and thinking. If several steps happen between two sent events, please accumulate them all into `agent_text` and `agent_thinking` (reset after each event is built). Once every tool is sent this matters less, but it keeps nothing from being lost.
- **Three numbers per result for the Pane (agreed with Noah earlier):**
  - `risk`: does this action break what the user asked for (spikes)
  - `drift`: how far off course the whole run is (0 = on track)
  - `drift_rate`: how fast `drift` is changing per event

  David proposes all three at the **top level** of the result. Noah decides how to draw them.

### Still open on David's side (no Mod work yet)

- The classifier's Modal app name, and whether it's exposed as a plain `classify` function or as the `Classifier` class from the cold-start proposal in CONTRACT.md section 7.
- The exact set of `details` keys.

Once David confirms these, the contract change (`late_results`, `pending`, `drift`, `drift_rate`) goes into CONTRACT.md section 4 and its change log, as both sides agree.
