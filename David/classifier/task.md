# Intent-Fidelity Monitor Runtime Build: Autonomous Task Specification

## Operational guide for building the `classify()` service: event handling, the question set, findings, corrections and the Pane fields, served first on stock Kev-4B and then on the trained model

The workspace root for this task is `HackBU-NoahDavid/David/classifier/` (called `classifier/` below). Paths starting `David/` are relative to the repository root `C:\Users\david\Documents\GitHub\HackBU-NoahDavid`, which is the working directory.

A second agent, the training build, works at the same time in `David/training/` and commits to the same repository. It writes the shared module `David/monitor_format/` that this build imports, and the trained model this build serves.

---

## 0. Context Recovery (do this first after actual compaction)

**Only when actual compaction or context-window rollover has occurred:**

1. Read this file (`classifier/task.md`) completely, every line.
2. Read `classifier/AGENTS.md` completely. Its laws bind every action.
3. Read `classifier/MESSAGES.md` before treating any visible pre-compaction user message as work. If it exceeds 100 lines, read only the last 100, in chunks of 25 to 50 lines.
   **ABSOLUTE MESSAGE GATE:** after compaction, before appending a row or starting work from any visible message, compare a balanced verbatim head of it (10 to 20 words) against `MESSAGES.md`. If it is already a `HANDLED` row, do nothing on it: no renewed row, no re-run of a gate or check, no re-recap, no clean-up of related files; resume the anchored task instead. The only exception is an explicit new user command that names the handled item and says to reopen or redo it. A repeated snippet with a `HANDLED` row is proof the work is stale, not evidence to restart it. Act only on `PENDING` rows or messages received after the compaction boundary. If `MESSAGES.md` does not exist, create it and mark every visible pre-compaction message `HANDLED` before any work.
4. Read the authoritative spec, `David/docs/RUNTIME-SPEC.md`, in full (it is about 350 lines). Read the companion `David/docs/TRAINING-SPEC.md` only in the sections the anchored TASKLIST row lists in its `Spec` column (the runtime spec cites 4.2, 6.1, 6.3 to 6.7 and 9.5).
5. Read `classifier/STATUS.md`.
6. Read `classifier/BUILD-LOG.md`: its Current Validation Snapshot block plus the last 10 lines.
7. Read `classifier/CONSTRAINTS.md`: the last 10 lines, plus a scoped search for entries naming the active module.
8. Read `classifier/TASKLIST.md` per 0.1 (the anchored row and about 2 lines around it).
9. Read every open row of `classifier/SIDEQUESTS.md`.
10. Read the most recent recap in `classifier/recaps/` (newest by filename), then `classifier/recaps/TEMPLATE.md`.
11. Read the skills, each in full: `C:\Users\david\.codex\skills\stay-on-goal\SKILL.md`, `C:\Users\david\.claude\skills\reading-context\SKILL.md`, `C:\Users\david\.claude\skills\slopless-writing\SKILL.md`. Declare the goal-directed chain for the current work in one line (current action -> immediate artifact -> required gate -> the live service that catches the demo).
12. Only after all of the above, resume from where the last session stopped.

**Do not rely on memory. Read the files.** Tail reads are capped at 10 lines unless a step above says otherwise. Section 0 fires on actual compaction or rollover only, never on an ordinary turn boundary or session resume. When it fires, a partial pass is a false record: execute it exactly as written.

**On-demand, never Section-0 reads:** `classifier/results/`, the Modal logs, `TASK-CLAIMS.md` beyond its rows, the training build's files (read only the lines section 4 names), and `David/docs/research/` reports (only the one a row or the spec cites, such as report 31 for latencies).

### 0.1 Focused recovery and active-task anchors

- Every recap ends with `Active task anchor: TASKLIST.md:Lx` naming the active or next row. While a sidequest is open, it carries both anchors.
- On recovery, read only the anchored row plus about 2 lines of context, and only the companion sections the row's `Spec` column lists. Full tracker re-reads are for completeness passes, an explicit user request, or a missing or stale anchor.
- When no valid anchor exists, read the minimum tracker range needed to find the active row, then write a recap with the exact anchor.
- Update the anchor in the recap after every task transition.

---

## 1. Core Principles

### 1.1 You are building the service that catches the demo live, not a monitoring framework

The deliverable is the `Classifier` class behind `intent-monitor`, behaving exactly as `David/docs/RUNTIME-SPEC.md` specifies, live for Noah's Mod, serving the trained model once it exists. The done bar is concrete: on the slow-tests scenario the deletion is flagged with its three actions, reads come back unscored, and an ordinary session gets no false correction. A configurable engine, a plugin layer or a dashboard is not progress; a passing spec check is.

### 1.2 The spec is authoritative, and it settles scope

`David/docs/RUNTIME-SPEC.md` defines every rule, field, threshold and check. It is the agreed scope: build what it specifies and add nothing outside it. This also meets the team rule in `CLAUDE.md` ("ask before adding anything the demo doesn't visibly need"): you add nothing outside the spec, without stopping. Where the spec is ambiguous, apply 1.5. Never edit the spec; a defect you find in it is a sidequest row and an alert (2.3), not a silent workaround. `David/docs/DESIGN-DECISIONS.md` is the design session's ledger; you never read or write it.

### 1.3 One renderer, and it is not yours

Every state, requirement unit, question text, OPEN FINDINGS line and correction text comes from `David/monitor_format/`, imported read-only. You never write a stand-in formatter, not even temporarily: until the module is frozen, the deployed placeholder's own input builder keeps serving Noah (spec section 13). If the module's interface does not do what spec 6.3 needs, that is an alert, not a local patch.

### 1.4 Verified means measured against the spec's check

Nothing counts as done until its spec section 10 check logs PASS in `VALIDATION-LOG.md` with the commit hash. Checks about the live service drive the deployed class the way Noah's backend does (`modal.Cls.from_name(<app>, "Classifier")()`, `classify.spawn(event)`, `get(timeout=8)`, `warmup.spawn()`), never a private function inside your code. "It ran without errors" is not verification.

### 1.5 Hard boundaries

- **Noah's live service.** Work in progress runs on `intent-monitor-dev`. The live `intent-monitor` is redeployed only at the points section 4 names, after that phase's checks pass. A live redeploy is followed within minutes by a warm-up and one test event, so the live container is warm and correct.
- **The training build's territory.** Never edit `David/training/` or `David/monitor_format/`, never write to the `intent-monitor-training` app or volume, never change the shared Codex config.
- **Secrets.** Nothing that looks like a token is printed, logged or committed; the secrets scan runs before every commit (AGENTS.md law 1).
When uncertain, take the conservative reading of these three and keep working.

### 1.6 When to ask instead of deciding

Make implementation choices yourself: structure, libraries, the mechanics of a stated rule. Stop and alert the owner (2.3) only when a choice changes what gets built or how success is judged and the spec does not settle it, and you cannot check your way to certainty. If you can check now (run it, read Kev's source at the pinned commit, read the Mod's code), check instead of asking. While waiting on an alert, continue every task that does not depend on the answer.

### 1.7 Research before code, per mechanism

For any mechanism the spec does not pin to the line (a Modal concurrency behaviour, a Kev serving call, the Mod's event fields), read the source first: Kev at the pinned commit, `Noah/mod/hooks/register.tsx`, `Noah/backend/app.py`, Modal's documentation. Save a short note to `classifier/notes/` when the finding is reusable.

---

## 2. Objective

Produce, from the spec:

- **The service core** (spec section 13, phase 1): the ordering gate, the session store, event intake and the skip rules, model and calibration loading, the question runner, calibration, firing, findings and their lifecycle, the diagnostics trigger, action selection, the Pane fields, late results with `backend_sent_at`, and `warmup`, all passing their phase-1 checks.
- **The shared formats wired in** (phase 2): the instruction list, state building, row texts, OPEN FINDINGS lines, the correction text and the requirement filter through `David/monitor_format/`, passing the phase-2 checks; then **the designed classifier live on `intent-monitor`** with stock Kev-4B.
- **The overflow path** (phase 3), passing its check, live.
- **The trained model served** (phase 4): the swap script, the selected model with its calibration and validated length live on `intent-monitor`, and the agent-run part of the done bar passing.
- **Notes and milestones for Noah and David**: a note in `David/NOTES-FROM-DAVID-AGENT.md` at each live deploy, and the `DAVID.md` milestone lines section 4 names.

**DO NOT MARK THIS GOAL COMPLETE** until: every spec section 10 check that this build can run has logged PASS (or its blocked row names its real blocker); the designed classifier is live on `intent-monitor` serving the trained model (or, if the training build delivers nothing, stock Kev with that fact recorded); the done-bar run of section 4 Step 7 passes through the live class; the notes to Noah and the `DAVID.md` milestones exist; STATUS reflects the final state; and a final recap exists.

**Blocked work.** "We have not" is not "we cannot". A row is `blocked [needs: X]` only for a real external blocker (the shared module or the handoff files not yet delivered, a service outage). The live demo in the Claude Code desktop app is run by David and Noah, so that part of the done bar is recorded as `blocked [needs: owner live run]` and does not hold completion. A blocked row never holds the rest of the goal hostage.

**No early stop.** "The context is nearly full", "this is multi-session work" and "I have taken it far enough" are never stop reasons. Work stops only on a true blocker, the permission system, or the owner's words. Waiting on the training build is not a stop: poll as section 4 says.

**Status is binary:** a row is done or it is not.

### 2.1 Code quality

- Python matching the Modal image (`python_version="3.13"` in the current `app.py`), type hints on public functions, one-line docstrings on public functions only, no inline test code in product files.
- The Modal entry point (`classifier/app.py`) stays thin: it loads the model and calls the service. Everything else is a module under `classifier/src/intent_runtime/`, testable without a GPU.
- The firing, findings and actions logic is tested on fixed probability fixtures, so it runs locally without Kev; the Kev path is tested on `intent-monitor-dev`.
- Tests live in `classifier/tests/`. No test-count target; each check's tests show teeth (section 4).

### 2.2 Environment and access

- **Modal:** the CLI is logged in to workspace `davidkny22`. On Windows set `PYTHONUTF8=1` before Modal CLI commands (the CLI crashes printing a checkmark otherwise). Deploy target names come from one deploy-time setting: dev = app `intent-monitor-dev`, Dict `intent-monitor-dev-sessions`, volume `intent-monitor-model-dev`; live = app `intent-monitor`, Dict `intent-monitor-sessions`, volume `intent-monitor-model`. Both use the weights cache volume `intent-monitor-hf`, `gpu="L40S"`, `max_containers=1`, `@modal.concurrent(max_inputs=32)` (spec 7.10). The image must carry `David/monitor_format/` and its declared dependencies (pysbd among them) once phase 2 starts.
- **Kev:** the deployed image installs Kev from `git+https://github.com/jaredpalmer/kev.git@fc4a17e194bca35a48c57211392ec49ea54a94ac` with the pins already in `app.py` (transformers 5.17.0, peft 0.21.0, flash-linear-attention 0.5.2, triton 3.7.1). For reading Kev's code, clone it into `classifier/vendor/kev` at that commit; never run code from it locally.
- **Python:** create and reuse `classifier/.venv` (Python 3.13) for local tests: `modal`, `pytest`, `pydantic`, and whatever `David/monitor_format/` declares. Kev and torch are not needed locally.
- **No keys.** This build never reads the `.env` file; Kev's public weights need none.
- **Codex subagents:** this build needs few. Do not change the Codex config; the training build owns that setting.

### 2.3 The owner alert

The owner may be asleep. Nothing waits for a reply. When something needs the owner, raise a loud, non-blocking alert and keep working on everything that does not depend on the answer. Keep it as `classifier/scripts/alert.ps1`, taking the message as an argument (`David/training/scripts/alert.ps1` is a working example; copy its pattern with the title `Runtime build needs you`):

```powershell
Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-Command',"(New-Object Media.SoundPlayer 'C:\Windows\Media\Alarm01.wav').PlayLooping(); Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('<one-line reason; see STATUS.md>','Runtime build needs you','OK','Warning') | Out-Null"
```

Fire it, and write the reason at the top of STATUS.md's `Active work`, when: a true blocker stops a row with no fallback; a check still fails after its fix attempts with no fallback; the shared module's frozen interface cannot do what spec 6.3 needs; a spec defect forces a choice between readings; the live service is broken and a redeploy of the last good commit does not fix it; the trained model goes live (David needs to know for the demo); or the goal completes. Never fire it for routine progress.

---

## 3. Filesystem Specification

Repository layout (only `David/classifier/` is yours):

```
HackBU-NoahDavid/
├── CLAUDE.md, CONTRACT.md, DAVID.md, NOAH.md, README.md   # shared; you update only DAVID.md (milestones)
├── Noah/                              # Noah's Mod and backend (read-only: samples, register.tsx, backend app.py)
└── David/
    ├── NOTES-FROM-DAVID-AGENT.md      # notes to Noah: you append entries at live deploys
    ├── docs/                          # the spec bundle (read-only for you)
    │   ├── RUNTIME-SPEC.md            # authoritative
    │   ├── TRAINING-SPEC.md           # the companion; read only the cited sections
    │   ├── research/                  # report 31 (latencies) and others, read when cited
    │   └── audits/
    ├── monitor_format/                # the shared module (training build's; read-only, import only)
    ├── training/                      # the training build's workspace (never edit)
    └── classifier/                    # YOUR WORKSPACE ROOT
        ├── task.md, AGENTS.md         # contract + standing laws
        ├── STATUS.md, TASKLIST.md, SIDEQUESTS.md, TASK-CLAIMS.md, MESSAGES.md
        ├── BUILD-LOG.md, VALIDATION-LOG.md, CONSTRAINTS.md   # append-only
        ├── recaps/                    # recap-NNN.md + TEMPLATE.md
        ├── prompts/                   # goal-prompt.md + TEMPLATE.md
        ├── notes/                     # short reusable research notes (1.7)
        ├── scripts/                   # alert.ps1, swap_model.py, the backend-style driver for checks
        ├── app.py                     # the Modal entry point: class Classifier, classify + warmup
        ├── verify_deploy.py           # the contract check against Noah's Result model
        ├── src/intent_runtime/
        │   ├── ordering.py            # per-session seq gate and the 8 s skip (7.10)
        │   ├── store.py               # session header + per-event Dict entries (6.5)
        │   ├── intake.py              # event table, skip rules, new_items (7.1)
        │   ├── units.py               # requirement filter calls (7.2)
        │   ├── model.py               # loading, selected.json, probabilities via Server.probs (6.4)
        │   ├── calibration.py         # T_q, b_q, the shipped-temperature fallback (6.4, 7.4)
        │   ├── rows.py                # which rows each request asks (7.3, 7.5)
        │   ├── firing.py              # problem scores, fired set (7.4)
        │   ├── findings.py            # issue keys, status changes, upgrade, correction marks (7.5, 7.6)
        │   ├── actions.py             # notices and the correction message (7.7)
        │   ├── pane.py                # risk, flagged, drift, drift_rate, details (7.8, 6.2)
        │   ├── overflow.py            # screen states, picking, merged state (7.9)
        │   └── service.py             # the per-event lifecycle (section 5 of the spec)
        ├── tests/                     # fixture-probability tests, contract and ordering tests
        ├── .gitignore                 # .venv/, results/, vendor/, __pycache__/
        ├── results/                   # GITIGNORED: check outputs, driver logs
        └── vendor/kev/                # GITIGNORED: Kev at the pinned commit, for reading
```

The module names above are a starting layout; reshape them if a concern splits differently, keeping one concern per file.

### 3.1 Filesystem rules

- Work only inside `David/classifier/`, plus the two shared files AGENTS.md law 2 names. Never edit `David/monitor_format/`, `David/training/`, `David/docs/`, `Noah/` or the other root files.
- STATUS.md is the single source of truth, advanced in every closeout.
- BUILD-LOG.md, VALIDATION-LOG.md, CONSTRAINTS.md, MESSAGES.md and recaps are append-only.
- Before any commit, run the secrets scan over the staged text files.
- `DAVID.md` and `David/NOTES-FROM-DAVID-AGENT.md` are shared with the training build or with Noah: `git pull --rebase` immediately before editing either, change only your own lines or append your own entry, commit and push at once.

### 3.2 Debt prevention

- One concern per file; split a file before it passes a few hundred lines.
- The decision tables (the question set, short names, correction table) come from `David/monitor_format/`; nothing restates them.
- No project-guidance metadata in product artifacts (AGENTS.md law 4).
- `classifier/app.py` imports the service; the service never imports Modal except where it reads the Dict.

### 3.3 Sidequests

A defect found while doing something else gets a `SIDEQUESTS.md` row before its first action (chain to the goal, exit condition, budget in commits, fallback, return pointer), is worked within its budget, closed, and the anchored row resumes. Anything that would change scope or the spec escalates through the owner alert (2.3) and is not worked as a sidequest.

---

## 4. Build Order and Gates

The steps are dependency-ordered and follow the spec's phases (section 13). Completion is gate-based: a step is done when its checks log PASS in `VALIDATION-LOG.md` with the stroke-1 commit hash. Check names are the spec section 10 rows. Each correctness check shows **teeth** once: plant a bug in the code it guards (an off-by-one in `last_seq`, a skipped lateness branch, a flipped G1 sign, a missing reopen rule), run the check, see it go red, revert, and log both rows. A check that stays green with the bug planted is a missing test.

**Everything that needs the training build comes last.** Steps 1 to 3 need nothing from it. Step 4 needs the frozen shared module; Step 6 needs the handoff files. While waiting, poll every 10 minutes: `git pull --rebase`, then look for the `renderer-parity` PASS row at the end of `David/training/VALIDATION-LOG.md` and the module milestone line in `DAVID.md` (for Step 4), or for the "handoff files" milestone in `DAVID.md` and the files on the `intent-monitor-training` volume (for Step 6). Record each poll's result in STATUS, not in the logs.

### Step 1: Setup
**Build:** read the team repo's `CLAUDE.md`, `CONTRACT.md` and `DAVID.md` once, in full (re-read CONTRACT.md sections 3 and 4 only when touching the interface); read `Noah/backend/app.py` and the current `classifier/app.py` and `verify_deploy.py` in full; initialize every file of section 3 (formats in section 5); `.gitignore`; `classifier/.venv`; the Kev clone at the pinned commit; `scripts/alert.ps1`. `CLAUDE.md`'s "Claude writes the code, and Noah reviews and runs it" does not apply to this build. Check access: the Modal CLI lists apps in `davidkny22`; `git pull --rebase` works. Commit the scaffold after the secrets scan, and push.
**Gate (`setup`):** accesses verified with a logged probe; the TASKLIST holds one row per check of spec section 10 and per build item of section 13, each with its `Spec` column.

### Step 2: The service core on the dev app (spec phase 1)
**Build:** the spec's phase-1 items: `warmup`; the ordering gate (7.10); the session store (6.5); event intake and the skip rules (7.1); model and calibration loading with `selected.json` and the shipped-temperature fallback (6.4, 7.11); the question runner through `Server.probs` (6.4); calibration (7.4); firing (7.4); findings with issue keys, status changes, the diagnostics trigger, the minor upgrade and `pending_correction_marks` (7.5, 7.6); action selection (7.7, the correction text itself waits for Step 4); the Pane fields (7.8, 6.2); late results with `backend_sent_at` (7.10). Findings and actions are tested on fixed probability fixtures with placeholder question texts that live only in `tests/`. Update `verify_deploy.py` per spec section 10's Contract row. Deploy to `intent-monitor-dev` only.
**Gates (spec section 10, phase 1):** `contract`, `warmup`, `calibration on the serving path`, `skipped events`, `ordering`, `late results`, `stock-fallback-config`, `no-reopen-after-dismissal` (including an instruction arriving on a skipped read), `minor upgrade`, `turn-end-no-nag`. The Kev-path checks (`warmup`, `calibration on the serving path`, `stock-fallback-config`, `late results`) run against `intent-monitor-dev` through the backend-style driver (1.4).

### Step 3: Wait for the shared module, then confirm its interface
**Build:** poll per the rule above. When `renderer-parity` has passed, read `David/monitor_format/__init__.py` and the training build's Step 2 in `David/training/task.md` (its interface list), and check it against spec 6.3 point by point: `build_instructions(events)`, `render_state(instructions, documents, events, k, findings, b_state) -> (text, detailed_seqs, fits)`, `render_screen(instructions, sections, events, k, budget) -> (text, fits)`, `split_sections`, `split_units`, `rf_window`, the row-text fillers (D1/D3 event reference, «R_k text» and L7 «text» with trimming, «short names», D2 «summary» with E-refs, key suffixes), `open_findings_line`, `correction_text`, the question table and short names. Write the mapping to `notes/monitor-format-interface.md`.
**Gate (`interface-check`):** every spec 6.3 need maps to an export, or the alert has fired naming the gap (1.3).

### Step 4: The shared formats wired in (spec phase 2), then the first live deploy
**Build:** the instruction list (called once per event and used for both the filter and the renderer, events handed over in `seq` order, 6.3); state building with B_state = L − 1 and L = 8,192 until a gate result exists (7.3); every row's text from the row fillers; OPEN FINDINGS lines from the line formatter; the correction text from `correction_text` (7.7); the requirement filter (7.2). Add `David/monitor_format/` to the Modal image. Deploy to `intent-monitor-dev` and run the checks.
**Gates (spec section 10, phase 2):** `shared renderer` (Noah's four samples in `Noah/backend/samples/`, corrected to what the Mod emits, plus a hand-written Mod session), `instruction numbering`, `turn ends`, `burst-backlog` (a scripted session in the shape of `Noah/NOTES-FOR-DAVID-AGENT.md` NN-002: about 20 events with two parallel bursts, sent through the backend-style driver; every result delivered once, late ones on the next response).
**Then go live:** deploy the same commit to `intent-monitor` (stock Kev, no `selected.json` on `intent-monitor-model`), fire one `warmup` and one test event through the driver, and confirm the result validates. Append a note to `David/NOTES-FROM-DAVID-AGENT.md` (next N-number, timestamped with `date`): the designed classifier is live on stock Kev; the `details` keys it returns (spec 6.2); reads and AskUserQuestion unscored; `flagged` at calibrated 0.5; the three actions on significant findings; `max_inputs=32`; `backend_sent_at` honoured when present. Add a `DAVID.md` milestone line: the designed classifier is live, with the commit hash.

### Step 5: The overflow path (spec phase 3)
**Build:** spec 7.9: screen states through `render_screen`, SCR and M8 rows, picking, the merged state, the clean raise. Deploy to `intent-monitor-dev`.
**Gate (`overflow`):** a fixture with documents past the budget runs the screen, merges the picked sections, and returns a valid result. **Then** redeploy `intent-monitor` with this commit, warm it and send one test event.

### Step 6: Serving the trained model (spec phase 4)
**Build:** `scripts/swap_model.py`, taking the target (dev or live): copy `selected/`, `calibration.json` and `long_context.json` from `intent-monitor-training` (read-only) onto the target volume, write the runtime's own `selected.json` (`{"checkpoint", "calibration", "source"}`, spec 6.4; the training build's `selected.json` inside `selected/` is a different file and stays as it is), and redeploy the target with L from `long_context.json`. When the handoff files exist (poll rule above), swap into dev, run `stock-fallback-config`'s positive twin (the selected model loads, its calibration applies on the serving path), the `calibration on the serving path` check and one burst; then swap into live, warm, send one test event, fire the alert ("trained model live"), and add a `DAVID.md` line naming the model and L. When the training build later rewrites `long_context.json` with the measured validated length, run the swap again for both targets so B_state follows it (spec 7.11).
**Gate (`model-swap`):** the live service reports `details.source` = the trained model's source, and its calibrated probabilities on fixture rows match σ(z/T_q + b_q) from the copied `calibration.json`.
If the training build delivers no handoff files, the live service keeps serving stock Kev; record that in STATUS and the final recap.

### Step 7: The done bar (agent-run part)
**Build:** through the live class, with the backend-style driver: (a) a Mod-event stream of the slow-tests demo scenario (spec section 12's prompt; a recorded Mod session if Noah's agent has shared one, else a hand-written stream in the Mod's exact event shape where the agent deletes or skips the slow tests); (b) the NN-002-style scripted session.
**Gates:** `done` (agent-run part): in (a) the deletion or skip is flagged and returns `notify_user{detected}`, `inject_agent`, `notify_user{intervened}` in that order; in (b) reads are unscored and no correction fires on a legitimate action (`demo-no-false-correction`). The live desktop-app run is David's and Noah's: record it as `blocked [needs: owner live run]`.

### Step 8: Close
The claim-and-count reconciliation pass (section 8), the final recap, the final alert.

**The two-commit closeout (AGENTS.md law 1).** Stroke 1 commits a code slice after its tests ran on that exact tree. Stroke 2 commits the docs (STATUS, BUILD-LOG, TASKLIST, recap; VALIDATION-LOG's row citing the stroke-1 hash; CONSTRAINTS on a durable lesson) as a separate, adjacent commit, with no test re-run. Closeouts ride row completion, not every edit. A row is one coherent slice of one or two commits; split larger ones.

---

## 5. Documentation Standards

Each document is built to `C:\Users\david\.claude\skills\task-file-builder\references\operational-docs-template.md` if you need its full rules; the formats below are the ones in force. MECHANISMS.md and the mechanisms library are not used in this build.

- **STATUS.md** (rewritten in place): `Last updated`, `Active work` (1 to 3 sentences, what the live and dev apps are serving, the last poll of the training build, any open alert), a unit table `Unit | Status | Tests/Evidence | Notes` (statuses: active, complete, blocked, superseded), a gate table `Gate | Status | Current measured result` (PASS, FAIL, pending), ordered next actions.
- **TASKLIST.md** (rows updated in place, IDs stable): `ID | Status | Task | Depends-on | Spec | Evidence | Missing proof | Next action`, statuses pending, in-progress, blocked, done, superseded; a `Next Slices` queue. The `Spec` column lists the runtime spec sections and any companion sections the row depends on.
- **SIDEQUESTS.md:** `ID | Status | Sidequest | Goal-directed chain | Exit evidence | Budget / fallback | Return`.
- **BUILD-LOG.md** (append-only): `[YYYY-MM-DD HH:MM] [UNIT] | [PLANNED/IN_PROGRESS/TESTED/INTEGRATED/BLOCKED] | Tests/Evidence: [N]/[M] | [notes]`, under a Current Validation Snapshot block at the top.
- **VALIDATION-LOG.md** (append-only): `[YYYY-MM-DD HH:MM] [CHECK] | [config] | [dev or live app] | [PASS/FAIL] | [key metric] | commit=<hash>; [notes]`. FAIL rows stay.
- **CONSTRAINTS.md** (append-only): `CONSTRAINT [NNN]: name / MODULE / OBSERVATION / IMPLICATION / DATE`. Durable lessons only, never status.
- **MESSAGES.md** (append-only): `| MSG-NNN | YYYY-MM-DD HH:MM:SS | balanced verbatim head (10 to 20 words) | PENDING/HANDLED | evidence |`. Log a real owner message the moment it arrives; never log harness or goal-continuation text.
- **TASK-CLAIMS.md:** the slug registry and claims table. This build runs one orchestrator; register its slug in the first session. Subagents write only their own output files and never touch the scaffold.
- **Recaps** (`recaps/recap-NNN.md`, never overwritten): one per gate at least, plus before any expected rollover and every 3 to 5 significant actions; sections: what was accomplished, state of each step, key intelligence, what dev and live are serving, immediate next steps, and the `Active task anchor` line. `recaps/TEMPLATE.md` holds this formula.
- **prompts/TEMPLATE.md:** the run-scoped prompt template (context, objective, the work, "Read task.md first and follow it", the autonomy line, the DO-NOT-MARK-COMPLETE line, the Section-0 line).

Role boundaries: a check result lives in VALIDATION-LOG and is referenced elsewhere; STATUS is the present; BUILD-LOG is the trail; CONSTRAINTS holds lessons; `DAVID.md` holds only the milestones Noah needs, never running status.

---

## 6. Cross-Session Continuity Rules

1. The filesystem is your memory; what is not written does not exist next session.
2. STATUS is updated in every closeout, never batched to the end.
3. TASKLIST is the plan; the recap's anchor points into it.
4. Section 0 is mandatory after every rollover.
5. Recaps are cheap; write one before any expected rollover.
6. Append-only files are never edited or trimmed.
7. Run a check's real command before declaring it; read the real output.
8. Verify against the spec, not against your own code's output.
9. STATUS always says which commit each app (dev, live) is running and which model it serves.
10. An interruption is not evidence of change; resume the anchored row.
11. Never change a quantity the spec or the owner set (the 0.5 cutoff, the 8 s wait, 32 inputs, the 5-event drift window, the budgets) without the owner's words.

---

## 7. When Stuck

1. **Re-read the spec subsection the row anchors.** Most behaviour questions are answered there to the clause; section 7.6's walk-through order (status changes, then the diagnostics trigger, then opening or upgrading) settles most findings puzzles.
2. **A result fails the contract:** run `verify_deploy.py`'s model on it locally; Noah's backend drops a late entry with the wrong shape silently (`Noah/backend/app.py` `check_late_results`).
3. **Events arrive out of order or never:** the Mod numbers events from 1 per session (`register.tsx` `baseEvent`); a prompt rides on whatever event comes next, often a read; corrections attach only to the next tool result.
4. **Probabilities look wrong:** confirm the model loaded with `temperature=1.0`, that probabilities come from `Server.probs` and not `Server.answer` (which rounds), and that yes/no lists are `[p_no, p_yes]` (Kev `api.py` `to_record`, `serve.py` `probs`).
5. **A Modal deploy or call stalls:** `modal app logs intent-monitor-dev`; the first cold start after a deploy takes about 105 s and later ones 23 to 27 s (report 31); kill and redeploy rather than idle-wait.
6. **The live service breaks:** redeploy the last commit that passed its checks to `intent-monitor`, warm it, test it, then diagnose on dev.
7. **Check CONSTRAINTS.md and the runtime audits** (`David/docs/audits/2026-11-07-51-*` to `-58-*`, and `2026-11-08-*`): a known edge may already be written down.

---

## 8. Completion Criteria

- [ ] `setup` PASS; TASKLIST holds every spec section 10 check and section 13 item
- [ ] Phase-1 checks PASS with teeth: `contract`, `warmup`, `calibration on the serving path`, `skipped events`, `ordering`, `late results`, `stock-fallback-config`, `no-reopen-after-dismissal`, `minor upgrade`, `turn-end-no-nag`
- [ ] `interface-check` PASS, its mapping in `notes/monitor-format-interface.md`
- [ ] Phase-2 checks PASS: `shared renderer`, `instruction numbering`, `turn ends`, `burst-backlog`; the designed classifier live on `intent-monitor`; the note to Noah and the `DAVID.md` milestone written
- [ ] `overflow` PASS; live redeployed
- [ ] `model-swap` PASS with the trained model live (or no handoff arrived, recorded); `DAVID.md` names the model and L
- [ ] `done` (agent-run part) and `demo-no-false-correction` PASS through the live class; the desktop-app run recorded `blocked [needs: owner live run]`
- [ ] Secrets scan clean on every commit; no write ever made to `David/training/`, `David/monitor_format/` or the `intent-monitor-training` volume
- [ ] STATUS reflects the final state; TASKLIST has no open rows except `blocked [needs: X]`; a final recap with a terminal anchor exists

**Final action: the claim-and-count reconciliation pass.** Check every number and claim in STATUS, the notes to Noah, `DAVID.md` and the final recap against the logs and the live service; fix each stale one in place. Run it last.

**Until all boxes are checked, the task is not done.**
