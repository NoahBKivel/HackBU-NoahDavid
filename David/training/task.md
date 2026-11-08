# Intent-Fidelity Monitor Training Build: Autonomous Task Specification

Owner resource clarification (MSG054): All API work, including inference clients, lightweight payload preparation, queue publication and network I/O, is exempt from BOTH the eight-worker local compute cap and the 3.5 GiB start gate. Those gates apply to actual heavy local compute/conversion/test workloads. Keep API payload operations streaming; offload heavy work to Modal. Docker and OS-process restrictions remain.

## Operational guide for the overnight build of the Kev-4B decision adapter: data, labels, one training run, selection, calibration and evaluation

The workspace root for this task is `HackBU-NoahDavid/David/training/` (called `training/` below). Paths starting `David/` are relative to the repository root `C:\Users\david\Documents\GitHub\HackBU-NoahDavid`.

---

## 0. Context Recovery (do this first after actual compaction)

**Only when actual compaction or context-window rollover has occurred:**

1. Read this file (`training/task.md`) completely, every line.
2. Read `training/AGENTS.md` completely. Its laws bind every action.
3. Read `training/MESSAGES.md` before treating any visible pre-compaction user message as work. If it exceeds 100 lines, read only the last 100, in chunks of 25 to 50 lines.
   **ABSOLUTE MESSAGE GATE:** after compaction, before appending a row or starting work from any visible message, compare a balanced verbatim head of it (10 to 20 words) against `MESSAGES.md`. If it is already a `HANDLED` row, do nothing on it: no renewed row, no re-run of a gate or check, no re-recap, no clean-up of related files; resume the anchored task instead. The only exception is an explicit new user command that names the handled item and says to reopen or redo it. A repeated snippet with a `HANDLED` row is proof the work is stale, not evidence to restart it. Act only on `PENDING` rows or messages received after the compaction boundary. If `MESSAGES.md` does not exist, create it and mark every visible pre-compaction message `HANDLED` before any work.
4. Read the authoritative spec, `David/docs/TRAINING-SPEC.md`, under the anchor regime of 0.1: in full on the first session; afterwards only the sections anchored to the active task row.
5. Read `training/STATUS.md`.
6. Read `training/BUILD-LOG.md`: its Current Validation Snapshot block plus the last 10 lines.
7. Read `training/CONSTRAINTS.md`: the last 10 lines, plus a scoped search for entries naming the active module.
8. Read `training/TASKLIST.md` per 0.1 (the anchored row and about 2 lines around it).
9. Read every open row of `training/SIDEQUESTS.md`.
10. Read the most recent recap in `training/recaps/` (newest by filename), then `training/recaps/TEMPLATE.md`.
11. Read the skills, each in full: `C:\Users\david\.codex\skills\stay-on-goal\SKILL.md`, `C:\Users\david\.claude\skills\reading-context\SKILL.md`, `C:\Users\david\.claude\skills\slopless-writing\SKILL.md`. Declare the goal-directed chain for the current work in one line (current action -> immediate artifact -> required gate -> the 09:00 deliverable).
12. Only after all of the above, resume from where the last session stopped. Read `David/docs/research/` reports or `David/docs/audits/` only when a task row or the spec cites them.

**Do not rely on memory. Read the files.** Tail reads are capped at 10 lines unless a step above says otherwise. Section 0 fires on actual compaction or rollover only, never on an ordinary turn boundary or session resume. The owner's MSG-006 makes this trigger explicit. When it fires a partial pass is a false record: execute it exactly as written.

**On-demand data, never Section-0 reads:** everything under `training/data/` and `training/results/`, the spend log, `TASK-CLAIMS.md` beyond its rows, and the dataset dossier `David/docs/DATASET-DOSSIER.md` (read the entry a converter needs, nothing else).

### 0.1 Focused recovery and active-task anchors

- Every recap ends with `Active task anchor: TASKLIST.md:Lx` naming the active or next row. While a sidequest is open, it carries both anchors.
- On recovery, read only the anchored row plus about 2 lines of context, and only the spec sections that row lists in its `Spec` column. Full tracker or spec re-reads are for completeness passes, an explicit user request, or a missing or stale anchor.
- **Spec-section anchors (this spec is long and dense):** in the first session, read the whole spec once and write, in each TASKLIST row, the spec sections it depends on (for example `6.4, 7.8, 12.2`). Recovery then reads only those sections.
- When no valid anchor exists, read the minimum tracker range needed to find the active row, then write a recap with the exact anchor.
- Update the anchor in the recap after every task transition.

---

## 1. Core Principles

### 1.1 You are building one trained, calibrated monitor by 09:00, not a data-engineering showcase

The deliverable is a selected, calibrated Kev-4B decision adapter whose files the runtime can load, plus the measured lift over stock Kev-4B. Every hour spent polishing a converter, a report or a tool that the 09:00 model does not need is an hour taken from the model. "The pipeline is elegant" is never progress; a frozen, gated train split and a finished run are.

### 1.2 The spec is authoritative, and it settles scope

`David/docs/TRAINING-SPEC.md` defines every format, wording, source, rule, threshold and gate. It is the agreed scope: build what it specifies and add nothing outside it. Where it is ambiguous, apply 1.5. Never edit the spec; a defect you find in it is a sidequest row and an alert (2.3), not a silent workaround. `DESIGN-DECISIONS.md` is the design session's ledger; you never read or write it.

### 1.3 Verified means measured against the spec's gate

Nothing counts as done until its spec gate (section 12) logs PASS in `VALIDATION-LOG.md` with the commit hash, or its "reported" item is written to a report with real numbers. "It ran without errors" is not verification. An implausible result (a dev AUROC at chance, a positive rate of 0% or 100%, an agreement of 1.0 everywhere) is a bug signal to root-cause before anything is reported.

### 1.4 Hard boundaries

- **The held-out sets are touched once** (spec 7.9): no held-out item reaches training, selection or calibration, and only the selected candidate and stock Kev are scored on them.
- **Secrets never leave the machine.** Nothing from `.env`, no token and no credential is printed, logged, committed or written into any record; the secrets scan (spec 12.2) runs on every record and on every committed text file.
- **Spend:** at most $200 of Anthropic API credit in total, generation reserved first (spec 8.7).
- **Time:** the selected, calibrated model and its files exist by 09:00 EST on 2026-11-08 (section 4, the clock rule).
When uncertain, take the conservative reading of these four and keep working.

### 1.5 When to ask instead of deciding

Design-ethos lets you make implementation choices on your own: how to structure something, which formula to use, how to build the mechanics of a policy you already have. Keep doing that.

**Alert the owner (2.3) unless you are certain the choice is both safe and right.** Safe means measured and checked: you know the cost, you know it works. Right means it is the best choice for what the owner actually wants from this project, not merely a choice that works: if a better option might exist and you are not certain this is it, that uncertainty is the signal, whether or not anything is broken or expensive. Certainty here means you could show the owner why no other option does better, not that you picked the first thing that ran clean. **If you can check right now, check, don't ask:** measure the cost, run the test, read the source. Only alert once checking is done and the uncertainty is still there. There are no approval stops in this build: while an alert is open, continue every task that does not depend on the answer.

**This couples with, but doesn't route through, `SIDEQUESTS.md`.** A gap found while doing something else is a sidequest per 3.3. A gap the current task row hits head-on needs no sidequest: mark the row `blocked`, give the owner the real options with their costs through the alert and STATUS, and resume once answered.

A real choice, once identified as needing the owner, reaches them as a question before it is acted on, never as a "here's what I'm defaulting to, say if you want it changed" statement after the fact. Settle only what strictly follows from an answer already given, in one line, without re-asking; everything else becomes a question, asked before acting, not announced after.

### 1.6 Research before code, per mechanism

For any mechanism the spec does not pin down to the line (a dataset's real field layout, Kev's trainer internals, a Codex or Modal setting), read the source first: the dataset files, the code at the pinned commit, the official docs. Save a short note to `training/notes/` when the finding is reusable. Implementing from memory and then checking the code against itself proves nothing.

### 1.7 Scale out, never slow down

You can run up to 100 concurrent subagents. Converters, constructions, generation and labelling are parallel by nature: fan them out. Moving equal-cost work into a second Modal container is pre-approved wherever it shortens the critical path (spec 11). If throughput is the concern, add workers; never stop.

### 1.9 Intelligence compounds

Every failed attempt teaches something. A converter whose source layout differed from the dossier, a gate that failed, a teacher instruction the two models read differently, a timing that misled: each reveals a constraint. Record every durable lesson in `CONSTRAINTS.md` the moment it is learned, and every reusable finding in `notes/`; the breakthrough usually emerges from the intersection of many small observations, not a single run. Dead ends are recorded as they happen, especially while debugging or thrashing: an unrecorded failed attempt is a re-walkable dead end.

### 1.10 Diagnose, don't excuse

When a signal or result fails, root-cause it. "It needs more scale, compute or budget" is a claim requiring evidence, never a default attribution: reaching for an external cause first is the tell that diagnosis was skipped. A slow stage is measured and its named cause fixed before the plan is cut around it.

### 1.11 Local resources

The owner caps local Python, Docker and shell workload concurrency at eight and forbids starting a new local workload until available RAM exceeds 3.5 GB. API-bound labelling subagents are exempt from that worker cap. Offload heavy conversion to Modal. Docker remains stopped; do not restart it or manage other local processes. Prioritize at least 60 API-bound labellers where slots and verified inputs permit, with low thinking and the vote-allocation policy in spec 8.3: paired Sol and Terra for the named intent and judgment slices, single Sol for benign pools, all constructions and visible-label records. Label train constructions and rare-question sources first, then the remaining train records; dev waits. Launch a paired batch's two model votes in parallel.

---

## 2. Objective

Produce, from the spec:

- **The shared module `David/monitor_format/`** (section 4, Step 2), with its frozen interface, used by every record and imported read-only by the runtime build.
- **The training data:** N = 10,000 train records (owner MSG083; spec 7.1): 2,459 replay, 164 overflow screen and 7,377 task records, with s = 7,377 / 10,630. Render every record at B_state = 8,191 with `--max_state 8192` through the shared renderer's existing budget parameter; its code is unchanged. Overflow screens retain 8,192 tokens. Build a grouped dev split with the intent slice and the held-out conversions (7.9), all labelled (8) and passing the data gates (12.2). No long-context training records, QuALITY records, padded long-policy records or long-context gate items are built.
- **The patched trainer and the interpolation tool** (9.2), with the Phase-1 correctness gates passing (12.1).
- **One training run** (9.1) on four Modal B200s in data parallel, saves every ⌈S/10⌉ steps.
- **Selection and calibration** (9.3 to 9.5): five candidates scored, the pick made, calibration fitted, serve-path parity and the demo check passing (12.1, 12.3).
- **The runtime handoff files** on the Modal volume `intent-monitor-training`: `selected/` (a directory Kev's `Checkpoint` loads), `calibration.json` and `long_context.json`, in the formats of section 4, Step 9.
- **The evaluation** (12.3, 12.4): the lift test, LLMBar and RewardBench 2, retention, RF recall and the "flag everything" report, written to `training/reports/RESULTS.md` with real numbers.

**DO NOT MARK THIS GOAL COMPLETE** until: the handoff files exist on the volume and load through Kev's serving path; serve-path parity and the demo check logged PASS (or their spec fallbacks were taken and logged); every Phase-1 and data gate logged PASS or its spec fallback; `RESULTS.md` carries the lift test and every reported item with measured values; `DAVID.md` carries the handoff milestone; STATUS reflects the final state; and a final recap exists.

**The blocked-work completion policy (two-sided, both halves mandatory):**
- **"We have not" is not "we cannot."** A safe fallback, a fail-closed status, or a stub closes a task **only** when a real physical, hardware, environment, access or external blocker makes the primary path impossible, recorded as `blocked [needs: X]` with the exact missing resource named. Missing verification or performance evidence on an *unblocked* path is an implementation gap to close, never a terminal fallback. A blocked source redistributes its quota (spec 7.1).
- **Genuinely blocked work never holds completion hostage.** The goal may be marked complete once every *unblocked* item is fully closed; each blocked row carries its `[needs: X]`, its instrument, and its stand-in, tracked, never silently dropped.

**The anti-early-stop clause:** the enumerated completion bar is a **hard contract, not an aspiration**. Invented resource ceilings, "this is genuinely multi-session work", "I can't hold the quality bar in one session", "the context is nearly exhausted", "I've taken it as far as I reasonably can" are **never** valid stop reasons. Work stops only on a true external blocker (recorded `[needs: X]`), the permission system, or the owner's own words. If throughput is the genuine concern, **scale out (background agents), don't stop.**

**Status is binary.** A row, step or unit is complete XOR in-progress: "substantially complete" and its cousins are dishonest hedging that inflates perceived progress. Never advance the plan's focus past an incomplete unit; the trackers reflect exact reality at all times.

**An implausible result is a bug signal, never an honest floor.** A headline outcome sitting at the null or chance baseline, or otherwise impossible-if-working, is a defect to root-cause before any report; a "reported-not-gated" allowance must never become cover for a broken deliverable. Green structural gates over a deliverable that visibly does not do its job is not "done".

### 2.1 Code quality

- Python 3.11 or newer, type hints on public functions, one-line docstrings on public functions only, no inline test code in product files.
- The shared module is held to the highest bar: pure functions, no I/O, no dependency on anything in `training/`, deterministic output (same inputs, same bytes).
- Every converter and construction is a separate file registered in a registry (section 3.2); adding a source never edits the pipeline.
- Tests live in `training/tests/` and `David/monitor_format/tests/`. No test-count target; each gate's tests must show teeth (section 4).

### 2.2 Environment and access

- **Keys:** `C:\Users\david\Documents\GitHub\classifier-for-metagaming\.env` holds `ANTHROPIC_API_KEY`, `HF_TOKEN` and `OPENAI_API_KEY`. Load them into the process environment of the commands that need them. Never print, log, copy or commit a key. No other Anthropic key exists on the machine; every `claude -p` run gets `ANTHROPIC_API_KEY` from this file, so it bills the API credit. OpenAI labelling has a separate $200 total cap, with each call's usage and cost recorded in the spend ledger. Run a roughly 50-record pilot and report the measured full-train cost projection before scaling standard concurrent API requests; use prompt caching for fixed instructions and shared claims to prevent duplicate votes.
- **Modal:** the CLI is logged in to workspace `davidkny22` with auto-refill on. Training and scoring use a B200, the app name `intent-monitor-training` and the volume `intent-monitor-training`. Never modify the deployed app `intent-monitor` or its volume `intent-monitor-model`; they belong to the runtime build.
- **Hugging Face:** `HF_TOKEN` has access to SWE-chat, TRACE and the other gated sets the spec names; impossible-SWE may still be pending (its quota then redistributes).
- **Harbor** (HVTB): installed and logged in as `davidkny22` (`harbor` CLI).
- **Docker Desktop:** remains stopped under the owner's resource instruction; do not restart it.
- **Claude Code CLI:** `claude` is on PATH; headless runs use `claude -p` with Haiku 5.5 (`claude-haiku-5-5`) or Sonnet 5.5 (`claude-sonnet-5-5`).
- **Kev:** clone `https://github.com/jaredpalmer/kev` into `training/vendor/kev` and check out `fc4a17e194bca35a48c57211392ec49ea54a94ac`. Environment pins are in spec 9.1.
- **Codex subagents:** raise the concurrent-subagent limit to what the labelling needs (the owner allows up to 100); find the setting in Codex's own config and record what you changed in BUILD-LOG. Labelling and conversion subagents run on fast mode; thinking level medium for most work, low or none for mechanical work (format conversion, rule-checked labels).
- **Python:** create and reuse one environment for this build (`training/.venv`); the team repo's `C:\Projects\...` path in `CLAUDE.md` is Noah's machine and does not exist here.
- **Standing environment rules** (AGENTS.md law 6): installation authorized and recorded; reuse the existing environment; smoke scale by default, full scale only where a gate requires it; diagnose stalls, never wait on them; build-time capability (Modal GPUs, network, installs) and shipped-artifact constraints (what the runtime loads) are separate ledgers, both explicit.

### 2.3 The owner alert

The owner may be asleep. Nothing waits for a reply. When something needs the owner, raise a loud, non-blocking alert and keep working on everything that does not depend on the answer:

```powershell
Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-Command',"(New-Object Media.SoundPlayer 'C:\Windows\Media\Alarm01.wav').PlayLooping(); Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('<one-line reason; see STATUS.md>','Training build needs you','OK','Warning') | Out-Null"
```

Keep this as `training/scripts/alert.ps1` taking the message as an argument. Fire it, and write the reason at the top of STATUS.md's `Active work`, when: a true blocker stops a row with no fallback; a data gate still fails after its one rebuild or relabel; spend reaches 90% of the $200 cap; the latest training start (section 4) is 15 minutes away and the train split is not frozen; the run crashes twice; a spec defect forces a choice between readings; or the goal completes. Never fire it for routine progress.

---

## 2.5 Provenance

Every training record carries its provenance in its own data: `_meta` (source, construction, pair id, group id, split, cut index, note shown, licence; spec 6.3) and its side record (source labels with their basis and origin; spec 6.2). The spend ledger records every API job with its real usage and cost; VALIDATION-LOG records every gate run with its commit hash. These are the registries for this build; no separate registry file exists.
- **Path-tracing.** A source label's basis (V, O, T, C) is established by reading the source's actual label field and how it was produced, not by trusting the dossier or a dataset card; a mismatch is a CONSTRAINT and the label is demoted to a teacher hint.
- **Completion gate.** No record enters the frozen split without source, basis and licence filled in `_meta`; a converter that emits records without them is incomplete.
- **Not a Section-0 read.** Records, side records and the spend ledger are read on demand only, and only the relevant entries.

---

## 3. Filesystem Specification

Repository layout (only `David/` is yours):

```
HackBU-NoahDavid/
├── CLAUDE.md, CONTRACT.md, DAVID.md, NOAH.md, README.md   # shared; you update only DAVID.md (milestones)
└── David/
    ├── docs/                          # the spec bundle (read-only for you)
    │   ├── TRAINING-SPEC.md           # authoritative
    │   ├── TRAINING-SPEC-TRACE.md, PARETO-AXIS-MAP.md
    │   ├── DATASET-DOSSIER.md         # per-source facts, read per entry
    │   ├── research/                  # reports + heldout-intent-probe-manifest.jsonl
    │   └── audits/                    # the spec's review record
    ├── monitor_format/                # the shared module (Step 2): imported by training AND the runtime
    │   ├── __init__.py                # the stable public interface (re-exports)
    │   ├── questions.py               # exact wordings (spec 4.2), short names, correction table (6.5)
    │   ├── instructions.py            # instruction-list builder ([I_n], AskUserQuestion answers)
    │   ├── units.py                   # requirement-unit splitter (6.7), RF window
    │   ├── sections.py                # section splitter (6.6)
    │   ├── render_event.py            # detailed block, one-liner, caps, PowerShell→Bash
    │   ├── render_state.py            # state renderer (6.4) incl. fill rule, OPEN FINDINGS, EFFORT
    │   ├── render_screen.py           # overflow screen renderer (6.6)
    │   ├── rows.py                    # row-text fillers (D1 refs, «R_k», L7 «text» trim, «short names», D2 «summary», key suffixes)
    │   ├── correction.py              # correction text (6.5)
    │   └── tests/
    ├── classifier/                    # the runtime build's folder (not yours; never edit)
    └── training/                      # YOUR WORKSPACE ROOT
        ├── task.md, AGENTS.md         # contract + standing laws
        ├── STATUS.md, TASKLIST.md, SIDEQUESTS.md, TASK-CLAIMS.md, MESSAGES.md
        ├── BUILD-LOG.md, VALIDATION-LOG.md, CONSTRAINTS.md   # append-only
        ├── recaps/                    # recap-NNN.md + TEMPLATE.md
        ├── prompts/                   # goal-prompt.md + TEMPLATE.md
        ├── notes/                     # short reusable research notes (1.6)
        ├── reports/                   # DATA-REPORT.md, RESULTS.md (committed; real numbers only)
        ├── scripts/                   # alert.ps1, small operational helpers
        ├── src/intent_training/
        │   ├── sources/               # one converter per source (spec 7.3) + registry.py
        │   ├── constructions/         # one builder per construction (7.4) + registry.py
        │   ├── generation/            # agent-side generator (8.6), agent runs (8.7), spend ledger
        │   ├── teacher/               # labelling prompts, batching, vote collection (8)
        │   ├── assemble/              # label resolution (8.4), balance cap (7.8), siblings, twins
        │   ├── splits/                # grouping, dev, intent slice, held-out conversions (7.9)
        │   ├── kevpatch/              # trainer patches (9.2) applied to vendor/kev, interpolation tool
        │   ├── modal_app/             # the Modal training and scoring app (intent-monitor-training)
        │   ├── select/                # candidate scoring, pick rule (9.4), calibration (9.5)
        │   └── evaluate/              # lift (12.4), held-out reports, behaviour gates (12.3)
        ├── tests/
        ├── .gitignore                 # data/, results/, vendor/, .venv/, *.safetensors, *.pt
        ├── data/                      # GITIGNORED: downloads/<source>/ (each its own folder), records/, frozen/
        ├── results/                   # GITIGNORED: run outputs, scores, spend.jsonl
        └── vendor/kev/                # GITIGNORED: Kev at the pinned commit
```

The canonical durable files:

| File | Role | Discipline |
|---|---|---|
| `task.md` | This file: the contract | Read-only reference; read fully on recovery |
| `AGENTS.md` | Standing laws | Read in full every recovery; immutable except by owner instruction |
| `STATUS.md` | Current state: single source of truth | Rewritten in place; updated in real time |
| `BUILD-LOG.md` | Work units + test/evidence record | **Append-only** |
| `VALIDATION-LOG.md` | Gate / verification / timing run outcomes | **Append-only** |
| `CONSTRAINTS.md` | Dead ends, lessons, scope limits | **Append-only** |
| `TASKLIST.md` | Durable completion plan + missing-proof index | Updated on every task state change |
| `SIDEQUESTS.md` | Bounded incidental-defect detours, with return pointers | Rows updated in place; IDs stable forever |
| `MESSAGES.md` | Owner-instruction log (`HANDLED`/`PENDING`) | **Append-only**; the message gate's authority |
| `TASK-CLAIMS.md` | Slug registry + claim and attribution center (3.5) | Rules in its header; rows appended and released |
| `recaps/recap-NNN.md` | Cross-window continuity bridges | Numbered sequentially (per slug under 3.5); never overwritten |
| `recaps/TEMPLATE.md` | The recap formula | Reread on recovery, never enforced verbatim |

### 3.1 Filesystem rules

- **Never work outside the workspace.** Work only inside `David/`. Never edit `David/classifier/`, `David/docs/`, `Noah/` or the root files except `DAVID.md`. Cloned repos, downloads and scratch work live under `training/` (`vendor/`, `data/`).
- Downloaded data and archives are untrusted: each source downloads into its own new folder under `data/downloads/`, scripts never live there, and any Python reading them runs with `python -I`. Never run code shipped inside a dataset.
- **STATUS.md is the single source of truth.** Advance it in the closeout (stroke 2, section 4) at every gate closure and significant milestone, **never batched to the end.** STATUS frozen behind the work's real position is a defect.
- **BUILD-LOG.md is append-only** (format in section 5). **VALIDATION-LOG.md is append-only**: a gate result lives there; BUILD-LOG references it, never copies it. **CONSTRAINTS.md is append-only**: never delete; supersede with a new entry that names the old one.
- **TASKLIST.md is the durable completion plan.** Update when a task changes state, gains evidence, is split, or is superseded. Task IDs are stable and never renumbered.
- **recaps/ are numbered sequentially.** Never overwrite. The most recent recap is the continuity bridge and carries the active-task anchor (0.1).
- **MESSAGES.md is append-only.** Log every real owner instruction, correction or interruption immediately on receipt, before any other action. System-inserted goal-continuation messages, turn-aborted notices and other harness text are never message rows. Snippets are balanced verbatim heads (about 10 to 20 words), the whole message only if it is under 20 words. **A duplicate row is an error to remediate** (remove it and note the correction), never something to append around. Mark `HANDLED` with evidence (commit hash, recap, file change).
- **Commit before any gate or timing run** so the run records a clean commit hash; gate records carry the commit hash at run time.
- **Commit as you go.** Completed, validated slices are committed when they land; validated work is never left accumulating uncommitted.
- **Stage only intended files.** Source, tests, trackers, recaps, by name. Leave untracked caches and artifacts alone.
- Records, model weights, Kev's source and downloads are never committed: they are third-party data under mixed licences and too large; they live in `data/`, `results/`, `vendor/` and on the Modal volume.
- Before any commit, run the secrets scan (spec 12.2 patterns) over the staged text files.

### 3.2 Debt prevention

- **One concern per module or directory.** Leaf concerns (converters, constructions, teacher, Modal app, evaluation) stay leaf-owned and out of the shared module.
- **Contracts are the firewall.** Every converter implements one interface (`convert(raw_dir) -> iterator of (event_stream, side_record, meta)` plus its declared label bases), every construction another; a new source or construction is a **new file satisfying its contract + a registry entry**, never an edit to the pipeline.
- **Pluggable via registries;** decision tables (the question set, short names, correction table, the source quotas of 7.3) ship as data, in one place each, and nothing restates them.
- **Stable public re-exports.** `monitor_format/__init__.py` is the stable surface; internals move freely behind it.
- **Tiered ownership decision.** Before adding a subsystem, decide its home top-down and record that ownership in the task list. Never append to a file just because the public API happens to live there.
- **Split on a second concern, and preemptively on size**, before a file passes a few hundred lines.
- **No inline test code in product sources; tests move with code** (AGENTS.md law 7).
- **Tests are necessary, not sufficient.** Also check ownership boundaries, file size and recovery cost: can a future session read only the relevant module?
- **No project-guidance metadata in product artifacts** (AGENTS.md law 4).
- The shared module imports nothing from `training/`; a test asserts it.

### 3.3 Sidequest discipline

A diagnostic, investigation, instrument, or reconnaissance run only measures or investigates; it changes no product, so it is a sidequest, tracked in `SIDEQUESTS.md`, owner-commissioned or not. Work that builds, changes, or maintains the product is a TASKLIST item. A sidequest never touches core product: measuring existing behaviour lives in `scripts/` or `tests/`, and the product gains no flag, path, or dependency for it.

During primary work you will find bugs, past shortcuts, and latent issues. If remediation requires a major refactor or meaningfully changes the scope of a claim, and the spec does not account for it: alert the owner (2.3) and mark the row `blocked`; this move is pre-authorized. Otherwise: log a sidequest row before its first action, with the goal-directed chain mapped and necessity, exit condition, budget, and fallback recorded. Work it bounded by its budget; on exit, close the row, cease anchoring it, and return to the primary task immediately. If the budget exhausts, take the fallback and close, or escalate. **An owner-instantiated sidequest carries no budget cap.** A sidequest never absorbs scope changes.

### 3.5 Multi-session claim discipline

`TASK-CLAIMS.md` is the slug registry and claim and attribution center. Its rules bind the orchestrator and every subagent alike:

- Register your slug immediately after starting (subagents: on spawn; the orchestrator: after Section-0 recovery); mark it released when your work ends or, as a subagent, before reporting back and closing.
- One stable slug per session, for life; identity survives compaction via the recap-anchored claim.
- Full file read at recovery only; rows-only read before each claim and each release. Another slug's row is untouchable.
- Random 100-2000 ms backoff before every write; append, re-read; earlier timestamp wins. A row is claimable only when its Depends-on rows are terminal. A worker claims one row; work too broad for one worker is split into rows before it is claimed.
- **Labelling is the exception.** Labelling batches do not get their own rows or claims. Each labelling stream (Codex Sol, Codex Terra, OpenAI standard, OpenAI Batch) is one TASKLIST row, claimed by the orchestrator, which records in that claim's Work cell how many labellers the stream is running and its batch ranges. Labelling subagents never write TASK-CLAIMS or TASKLIST; they write only their own vote files, under the shared vote ownership that prevents duplicate votes.
- Release fills Work: recaps, commit hashes, file names, evidence dirs. Never line numbers.
- Recaps mint as `recap-<slug>-NNN.md`; before writing yours, read the newest recap in `recaps/` by filename, any slug.
- Commits carry only the claiming slug's work; foreign uncommitted work is preserved. Shared mutable docs (STATUS, TASKLIST, TASK-CLAIMS): re-read and merge before every write; atomic replacement, never truncation.
- Stale claim (60 min, no evidence): supersede with a note. The owner may retire any claim.
- MESSAGES.md: the first session to read a new owner message logs it with `received-by: <slug>`; other sessions treat that row as the gate's authority.

---

## 4. Build Order and Gates

The steps are dependency-ordered. Completion is gate-based (section 8), not narrative: a step is done when its gate logs PASS in `VALIDATION-LOG.md` with the stroke-1 commit hash.

**What a gate must prove.** Each gate proves its core claim on real data or the real path, nothing less and nothing more. A **planted-bug check** (plant the bug, run the check, see it go red, revert, log both rows) is required only where a silent failure would ruin the model or the handoff, and is done once per check, not per run:
- **Renderer parity:** golden bytes reproduce; a one-byte change to a rendered field goes red. (Training and runtime states must be identical.)
- **Identity parity:** the α = 0 checkpoint equals stock tensor for tensor; a perturbed tensor goes red.
- **Resume parity:** a killed-and-resumed run matches the uninterrupted one on the same batches.
- **Kernel check:** the fla Triton kernels are confirmed active on the DeltaNet layers in the actual run configuration.
- **Converters:** output validates against the event schema, and each converter's label mapping is checked against the source's real label field on a handful of real rows.
- **Held-out exclusion:** no held-out or probe id appears in train or dev; a planted held-out id goes red.
- **Pair integrity:** no pair group crosses a split; a planted split pair goes red.
- **Secrets scan:** a planted fake token is caught.
- **Label assembly and counts:** the code that resolves labels, applies the cap and counts positives per question is checked once on a small known case (the positive floor and agreement numbers are only as good as that code).
- **Metrics:** the AUROC, bootstrap, calibration transform and lift-test code are each checked once on a small case with a known answer.
- **Serve-path parity and the demo check:** run through the real serving path and the shared renderer, on the files the runtime will load.
Not required: coverage measurement, per-assumption negative tests beyond the ones above, or re-checking a check that already passed.

**The seam rule: the proof travels the user's path.** A gate closing a claim about shipped behaviour (serve-path parity, the demo check, the handoff files loading) drives the same entry point, artifact, construction and configuration the runtime uses: Kev's serving path, the shared renderer, the files on the volume. Evidence from module tests or private constructors is development intelligence, never closure.

**The source/input-validity gate.** The build's meaning depends on pinned inputs: Kev at `6cfce5c2fa4b4bd64026336ab649c5ca78857d52`, its base at `1001bb4d826a52d1f399e183466143f4da7b741b`, the Kev code at `fc4a17e194bca35a48c57211392ec49ea54a94ac`. Verify each pinned artifact's identity on the actual files before any downstream work uses it, and **halt on a mismatch**: no fallback to a nearby revision. Downstream evidence produced on a wrong artifact is void.

**Slice width is a two-sided invariant: one coherent slice (about 1 to 2 commits), never a coarse phase and never a micro-slice.** Every slice is closeout-oriented: it moves the active row measurably toward its gate. Decompose anything large into several small gated rows (one per source converter, one per construction, one per labelling stream, 3.5), and prefer breadth toward the gate over another narrow refinement of what already works.

**Concurrency.** Steps overlap wherever the dependency column allows. The background tracks are: agent runs (from Step 1), the smoke run (from Step 3), generation (from Step 4), and, once training starts, the dev and held-out work and candidate scoring (Step 7).

**The clock rule.** Work backward from 09:00 EST:
- `latest_training_start = 09:00 − measured_run_time − 20 min (final-pair scoring, calibration, handoff) − 30 min margin`. Recompute it from measured full-pass-cap batched-record throughput on the actual B200 record mix at B_state = 8,191 and record it in STATUS. A one-record timing or worst-case synthetic timing is not the actual-mix throughput forecast. Until that measurement lands, earlier state-length projections are historical only.
- `agent_run_cutoff = latest_training_start − 75 min` (converting and labelling their records). Unfinished runs stop at the cut-off; their quota redistributes (spec 7.1).
- **Owner schedule (MSG075, MSG083):** freeze the gated 10,000-record train split as soon as ready, including after06:00EST; finish the run, selection, calibration, handoff and full evaluation by09:00EST. Keep prior composition proportions as closely as whole records and intact pairs allow. No further N reduction without explicit owner sign-off. Training uses fourB200s in data parallel; use the fastest verified configuration and measured actual8Kmixture throughput. Preserve sealed positive floors and all required gates.
- If training has not ended by 09:00, select from the saves that exist (spec 9.3) and finish Steps 8 and 9 with them.

### Step 1: Setup (first 20 minutes)
**Build:** read the team repo's `CLAUDE.md`, `CONTRACT.md` and `DAVID.md` once, in full (re-read CONTRACT.md sections 3 and 5 only when touching the event schema); initialize every file of section 3 (formats in section 5); `.gitignore`; `training/.venv` with the spec 9.1 pins; the Kev clone at the pinned commit; `scripts/alert.ps1`; a spend ledger (`results/spend.jsonl`, one line per API job); check each access in 2.2 (Modal, HF gated reads, Harbor, Docker, `claude -p` with the `.env` key on one tiny call, the Codex subagent limit). The owner omits Docker agent runs (MSG056). Redistribute their quotas within the same objectives and close setup on that documented redistribution; do not launch Docker.
Commit the spec bundle in `David/docs/` and the initialized scaffold as the build's first commits, after the secrets scan, and push.
**Gate (`setup`):** every access in 2.2 verified with a logged probe (no secret in the log); agent runs launched with their cut-off and budget recorded.

### Step 2: The shared module `David/monitor_format/`
**Build:** spec 4.2 (exact wordings, twins keyed `<id>~neg`), 6.1 (event schema validator), 6.3 (record schema and key suffixes), 6.4 (state renderer: B_state as a parameter, fill rule, caps, one-liners, OPEN FINDINGS, EFFORT, overflow test), 6.5 (correction text), 6.6 (screen renderer, section splitter), 6.7 (requirement units with pysbd, English, `clean=False`). The public interface exports exactly what the runtime needs:
- `build_instructions(events) -> list` (numbered `[I_n]`, prompts and AskUserQuestion answers in arrival order; AskUserQuestion `result_text` verbatim);
- `render_state(instructions, documents, events, k, findings, b_state) -> (text, detailed_seqs, fits)` where `fits` says whether instructions plus documents fit (the overflow switch);
- `render_screen(instructions, sections, events, k, budget) -> (text, fits)`;
- `split_sections(document) -> list`, `split_units(text, source) -> list`, `rf_window(units, i) -> str`;
- the row-text fillers (D1/D3 event reference, «R_k text» with trimming, L7 «text» with trimming, «short names», D2 «summary» with E-refs, key suffixes), `open_findings_line(...)`, `correction_text(...)` (an M8 item uses M2's short name, position and correction, quoting the section);
- the question table and short names as data.
Fixtures: the four sample events in `Noah/backend/samples/`, corrected to what the Mod code emits (spec 6.1: `file_changes` only on Edit and Write, structured patches, `turn.reason`), plus a hand-written event stream covering every tool kind, a PowerShell call, an AskUserQuestion, a long result, a `turn_completed` with `answer`, and an overflow case. Freeze their rendered bytes as golden files.
**Gate (`renderer-parity`):** golden bytes reproduce exactly; a test proves the module imports nothing from `training/`; teeth shown. After this gate the interface is frozen: a later change is a sidequest and an alert, because the runtime build depends on it. Write a `DAVID.md` milestone line: the module path and its interface.

### Step 3: Trainer patches, interpolation tool, smoke run (background on Modal)
**Build:** spec 9.2 items 1 to 4 against `vendor/kev`, kept as code in `src/intent_training/kevpatch/`; the Modal app `intent-monitor-training` (B200, the volume mounted). Then one smoke job: kernel check, accelerated-kernel trial, resume trial, pass-cap measurement on a synthetic record at the largest padded cost, and actual 8K record-mix batched throughput (records per hour) to settle the run time. Use checkpointing 0 only if peak memory at its largest feasible P is at most 90% of GPU memory and it is faster in records per hour with finite, falling loss; otherwise use checkpointing 1.
**Gates (spec 12.1):** `identity-parity`, `resume-parity`, `kernel-check`, `accelerated-kernel-parity` (its fallback, the reference path, is a valid outcome), and the measured `P` and run time logged. Recompute the clock (section 4) and record it in STATUS.

### Step 4: Records (parallel subagents)
**Build:** one converter per source in spec 7.3 and one builder per construction in 7.4, fanned out to subagents (each gets: its 7.3 row, its dossier entry, the event schema, the shared module's interface, and its output path); the agent-side generator (8.6) feeding constructions, IF_multi, InFoBench, IN3, SWE-bench annotations, rewrites (7.6) and notes (7.5); the cut rule (7.2) with matched negative cuts; replay in Kev's native format (7.3). Render every record at B_state = 8,191, preserving the fill rule and the 8,192-token overflow screen budget. Every converter's output validates against the event schema before any of its records are rendered. Order the fan-out by how many positives a source supplies to rare questions (constructions, then V sources), so the labelling queue fills early.
**Gate (`records`):** every converter and construction validates; the secrets scan finds zero matches; per-source record counts against `s · n^plan` written to `reports/DATA-REPORT.md` (shortfalls redistributed per 7.1).

### Step 5: Labels and the train-split freeze
**Build:** the teacher (spec 8): labelling instructions verbatim from 8.2 and vote allocation from 8.3, with low thinking. The named intent and judgment slices receive Sol and Terra votes launched in parallel; benign pools, all constructions and visible-label records receive one Sol vote. Use batches of 20 to 30 records from one source where input fits and collect votes into `data/`; run the three ordered diagnostic passes (8.2 item 6), label resolution (8.4), construction mismatch and retries (7.4), twins (4.2), siblings (6.4), the balance cap (7.8), grouping and the train split (7.9). Label train constructions and rare-question sources first, then the remaining train records; dev and held-out work waits. Use shared vote ownership across Codex and direct OpenAI labellers. Compute agreement and can't-tell rates only on policy-paired records and report single-voted counts per question. Report unique policy-complete records per hour over the last 15 minutes, paired and single-voted counts separately, running labellers and projected train completion now and 15 minutes after scale-up; report the combined rate 15 minutes after the API client starts. Priority OpenAI work uses standard concurrent requests; only remaining lower-priority OpenAI coverage may use half-price Batch within the same $200 cap. Measure Codex throughput before relying heavily on Batch. Batch never holds the freeze: cancel unfinished batches at freeze and ingest completed results, which remain billable after cancellation.
**Gates (spec 12.2):** `positive-floor` (max(0.8 · P_q, 60) per question, P_q computed per spec 10 before labelling starts and written to DATA-REPORT), `teacher-agreement`, `cant-tell-rate`, `pair-integrity`, `secrets-scan`. Each failure takes its spec fallback once. At the owner-authorized gated freeze, including after06:00EST, after the required gates pass or their explicit fallbacks, write `data/frozen/train.jsonl` and its hash and copy it to the volume.

### Step 6: The training run (background on Modal)
**Build:** the spec 9.1 command on the frozen train split plus replay, saves every ⌈S/10⌉ steps to the volume, on the measured `P`. Watch it; on a crash, resume from the last save (one automatic retry; a second crash fires the alert and the run resumes again).
**Gate (`run`):** the run reaches its final step, or 09:00 arrives (the clock rule).

### Step 7: While training runs (parallel)
**Build:** the dev split at natural prevalence with its per-question floor and top-ups (7.9), the intent slice (9.4), the held-out conversions (7.9: TRACE with the teacher locating the exposure cut once per conversation, the probe items mapped to their questions, LLMBar, RewardBench 2), all labelled. In a separate scoring container: stock Kev on dev (and stock's calibration fit, spec 12.4), then each candidate as soon as its save exists (the step-400 save at both α), per 9.4.
**Gate (`dev-ready`):** dev and the intent slice meet their floors; every candidate that exists is scored; stock's lift-baseline calibration is fitted.

### Step 8: Selection, calibration, handoff
**Build:** score the final save's two candidates; apply the pick rule (9.4: paired bootstrap standard error, keep within one, highest intent score, pick order); calibrate the winner (9.5); write the handoff to the volume `intent-monitor-training`:
- `selected/`: the winner as a directory Kev's `Checkpoint` loads (an α = 0.85 winner as full weights), plus `selected.json` naming the candidate, its α, its save step and the commit hash;
- `calibration.json`: `{"<question id>": {"T": float, "b": float}}` for yes/no questions and `{"<question id>": {"T": float, "b": {"<option>": float}}}` for choice and score questions, keyed by base id (no twins), score options keyed `"0"`, `"1"`, `"2"` as Kev reports them;
- `long_context.json`: `{"validated_length":8191}`, written at handoff; no long-context gate or pilot is required.
Then serve-path parity on 300 dev records and the demo check through the shared renderer and the serving path (12.3), with the fallbacks of 12.1 and 12.3 if they fail. Add a `DAVID.md` milestone: the handoff files exist, where, and the winner.
**Gates:** `serve-path-parity`, `demo-check`. Fire the alert when both pass ("model ready").

### Step 9: Evaluation (parallel containers, after the handoff)
**Build:** the lift test (12.4), LLMBar and RewardBench 2, retention, RF recall and the "flag everything" report (13). Add a `DAVID.md` line carrying the handoff state length of 8,191. Write every evaluation number to `reports/RESULTS.md`: each with its n, its interval, and the candidate it describes.
**Gate (`lift`):** the lift test ran on the pre-registered protocol and its result (pass or fail) is in RESULTS.md. A failed lift is reported as measured, never re-run with a changed protocol.

### Step 10: Close
The claim-and-count reconciliation pass (section 8), the final recap, the final alert.

**The two-stroke closeout: docs never bundle into the code commit, and tests never re-run for cosmetics** (AGENTS.md law 1). Stroke 1: run the relevant tests, confirm via `git status` that the tested paths carry no unstaged edits, then commit the code slice (code, tests and config only). Stroke 2: the closeout advances STATUS + BUILD-LOG + TASKLIST + recap together (CONSTRAINTS on a durable lesson; VALIDATION-LOG's row citing the stroke-1 hash) as a separate, adjacent commit, with no test rerun: the row documents the run that happened. "Atomic" means per slice, not per gate: a commit bundling a module, its tests, mid-stream fixes and all the docs is non-atomic, and narrating it as one atomic increment is a false record. The cadence is calibrated, not maximal: the full closeout rides row completion, gate closures and broad integration points; a mid-row micro-edit gets its focused tests, not a full dashboard mutation and recap. A gate is not closed until its closeout reflects it.

---

## 4.5 Performance-Gate Pattern

Every measured speed, throughput, run-time or cost claim in this build (GPU timing, the clock forecast, labelling rates, the GPU choice) follows these rules:

1. **Reference-first.** A speed claim is a comparison against a named reference measured in the **same harness**: same timing method, warm-up outside timing, same inputs.
2. **References are benchmark targets, never code-shape constraints.** Matching throughput is the bar, not matching structure.
3. **The analytical fallback must be earned.** Theoretical or device-peak denominators are not used where a real measurement is possible.
4. **Evidence validity is apples-to-apples or nothing.** A comparison is invalid if the two sides ran on different inputs, if correctness was checked against the wrong oracle, or if the workload is non-representative. **Smoke-scale evidence is never production characterization:** a one-record timing, a single synthetic shape or a worst-case synthetic record proves the path exists, nothing more. A run-time forecast needs the real record mix, batched at the real pass cap, at the real state length. An invalid or superseded number is retired in the trail (superseded status and what replaced it), never left standing.
5. **Isolate the measurement.** Timing runs run free of unrelated concurrent load on the same GPU; environment and configuration that change the measured path (checkpointing, pass cap, kernels) are recorded with the run.
6. **Diagnose losses by named cause.** If a stage is slower than expected, identify the specific bottleneck from evidence (wrong batch size, unbatched calls, serial waits, rate limits, kernel fallback), fix that cause and re-measure.
7. **A rate carries its denominator and regime.** Records/hour states which records (mix, state length), which hardware, and whether batched at the pass cap; a labelling rate states paired versus single-voted records and over what window.
8. **Baselines and the metric are sourced claims,** never typed from memory.
9. **A claim near the noise floor is decided by a pre-registered interval rule,** never a point estimate.

**Gate row shape:** `[PERF-GATE] | [config: mix, state length, pass cap, checkpointing] | [reference] | [PASS/FAIL] | [measured vs reference, e.g. 1.62x] | commit=<hash>`. "Faster" with no named reference is not a result.

---

## 5. Documentation Standards

Each document is built to `C:\Users\david\.claude\skills\task-file-builder\references\operational-docs-template.md` if you need its full rules; the formats below are the ones in force. MECHANISMS.md and the mechanisms library are not used in this build.

- **STATUS.md** (rewritten in place): `Last updated`, `Active work` (1 to 3 sentences, the clock values `latest_training_start` and `agent_run_cutoff`, any open alert), a unit table `Unit | Status | Tests/Evidence | Notes` (statuses: active, complete, blocked, superseded), a gate table `Gate | Status | Current measured result` (PASS, FAIL, pending), spend so far against $200, ordered next actions.
- **TASKLIST.md** (rows updated in place, IDs stable): `ID | Status | Task | Depends-on | Spec | Evidence | Missing proof | Next action`, statuses pending, in-progress, blocked, done, superseded; a `Next Slices` queue. The `Spec` column carries the spec-section anchors (0.1). Build the full row set from section 4 in the first session.
- **SIDEQUESTS.md:** `ID | Status | Sidequest | Goal-directed chain | Exit evidence | Budget / fallback | Return`.
- **BUILD-LOG.md** (append-only): `[YYYY-MM-DD HH:MM] [UNIT] | [PLANNED/IN_PROGRESS/TESTED/INTEGRATED/BLOCKED] | Tests/Evidence: [N]/[M] | [notes]`, under a Current Validation Snapshot block at the top.
- **VALIDATION-LOG.md** (append-only): `[YYYY-MM-DD HH:MM] [GATE] | [config] | [backend] | [PASS/FAIL] | [key metric] | commit=<hash>; [notes]`. FAIL rows stay.
- **CONSTRAINTS.md** (append-only): `CONSTRAINT [NNN]: name / MODULE / OBSERVATION / IMPLICATION / DATE`. Durable lessons only, never status.
- **MESSAGES.md** (append-only): `| MSG-NNN | YYYY-MM-DD HH:MM:SS | balanced verbatim head (10 to 20 words) | PENDING/HANDLED | evidence |`. Log a real owner message the moment it arrives; never log harness or goal-continuation text.
- **TASK-CLAIMS.md:** the slug registry and claim and attribution center, under the rules in its header (the operational-docs template's TASK-CLAIMS rules). The orchestrator and every subagent register a slug, claim a TASKLIST row before working it (a row is claimable only when its Depends-on rows are terminal), and release it in the closeout with its Work manifest (files, outputs, evidence dirs, commits). It is the who-did-what record of the build; a worker holding no claim is not working.
- **Recaps** (`recaps/recap-NNN.md`, never overwritten): one per gate at least, plus before any expected rollover and every 3 to 5 significant actions; sections: what was accomplished, state of each step, key intelligence, the clock values, immediate next steps, and the `Active task anchor` line.
- **reports/DATA-REPORT.md and RESULTS.md:** the numbers the spec says are reported, each with its n and interval; nothing typed from memory.

**STATUS rationalization to reject:** "the append-only logs already cover it, I'll update the dashboards at the end." No. The logs are the audit trail; STATUS and TASKLIST are the live "where am I right now" that a recovering session and the owner read first. Advance both at every gate, in the closeout.

**Recap cadence:** a recap per gate is a floor, not a suggestion (plus: end of session, before any anticipated rollover, every 3 to 5 significant actions in a long session). N gates means at least N recaps. `recaps/TEMPLATE.md` is reread on every recovery so later recaps adapt from the formula, never from memory of the last recap written.

**CONSTRAINTS discipline:** dead ends are recorded as they happen, especially while debugging or thrashing; the documentation discipline does not suspend under pressure, pressure is what it is for. An entry is a stable lesson: if it would change the next time a gate passes, it is status and belongs elsewhere.

**TASKLIST discipline:** never mark a task done from tests alone when it has a gate: done requires the gate evidence. A row's Missing proof cell is `None.` only when fully closed; superseded rows keep their ID and name their replacement.

**Documentation role boundaries.** One role per file; never copy the same narrative into multiple files. STATUS = compact current-state dashboard. TASKLIST = actionable completion plan + missing-proof index. BUILD-LOG = dated implementation and evidence per unit. VALIDATION-LOG = gate, verification and timing run outcomes. CONSTRAINTS = durable lessons, scope limits, discharged dead ends. TASK-CLAIMS = who holds and did which row. recaps = cross-window continuity. MESSAGES = active-vs-stale owner instructions. A gate result lives in VALIDATION-LOG; BUILD-LOG references it, never copies it.

**Consolidation and archival** (only on explicit owner request, when a file truncates during reads): the archive (`*-ARCHIVE.md`) is lossless and never modified after writing; the active file is rewritten as a compact index mapping back to it; SHA256 connects active to archive; stable IDs are never renumbered. Pass order: CONSTRAINTS, BUILD-LOG, VALIDATION-LOG, STATUS, TASKLIST.

---

## 6. Cross-Session Continuity Rules

1. **The filesystem is your memory.** If it is not written down, it does not exist next session.
2. **STATUS.md is updated in real time**, not at session end. If the session crashes, STATUS.md reflects the latest state.
3. **TASKLIST.md holds the active completion plan.** It is the durable plan; the anchor (0.1) points into it.
4. **Never start work without reading context files.** Section 0 is mandatory after every compaction or rollover, not advisory.
5. **Recaps are cheap; lost context is expensive.** When in doubt, write a recap, with the active-task anchor.
6. **BUILD-LOG, VALIDATION-LOG, CONSTRAINTS and MESSAGES are append-only.** Never delete or overwrite; change status or supersede instead.
7. **Run the real verification before declaring any unit or gate done.** Not "it looked right": run the gate's command and read the real output.
8. **Verify against the authoritative reference, not just your own code or output.** The spec and the pinned sources are ground truth.
9. **Research before acting on any unfamiliar mechanism;** save reusable findings to `notes/`.
10. **The reference is ground truth; never build the fast path on an unverified reference.** When a source or dataset disagrees with the spec, the spec is authoritative; investigate the divergence rather than treating it as truth.
11. **An interruption is not evidence of changes.** Do not reflexively re-diff, re-verify or "clean up" after an interruption or pause; resume the anchored task; investigate only when something concrete indicates a change.
12. **The goal text, and every quantity agreed with the owner, is untouchable without explicit authorization.** Never edit, replace or re-create the goal on your own initiative, and never silently narrow an agreed parameter (N, quotas, floors, thresholds, the spend caps, the 09:00 deadline, the freeze hold): changing a confirmed quantity without surfacing it is a scope violation. Surface the need instead.
13. **The clock values in STATUS are recomputed whenever a measured duration changes them.**
14. **Background jobs are tracked in STATUS** (job, where it runs, how to check it, expected end) and every running worker holds a claim in TASK-CLAIMS, so a recovered session or the owner can find them.

---

## 7. When Stuck

1. **Re-read the spec section the row anchors.** Most format questions are answered there to the token.
2. **A dataset field is not where the spec or dossier says:** open three real rows from the download, then the dossier entry, then the dataset card; record the real layout in `notes/` and a CONSTRAINT.
3. **Kev rejects or silently drops records:** check `max_state`, `max_packed` (`max_state` + 1,664) and `max_branch` (`max_state` + 640) in `vendor/kev/kev/model.py` and the trainer's fit test; a state at exactly 8,192 tokens is rejected (spec 6.4 uses 8,191).
4. **Teacher agreement is low on one question:** read 10 disagreements side by side; the cause is usually an instruction the two models read differently. Tighten that question's instruction once (8.5), relabel once.
5. **A converter is slow or a source is huge:** take the first rows that meet the quota after the source's filters, in the dataset's own order, and move on; quotas are counts, not exhaustive passes.
6. **A Modal job stalls:** check `modal app logs intent-monitor-training`; kill and relaunch from the last save; never idle-wait on a stalled job.
7. **Agent runs misbehave or cost too much:** stop the batch, check the spend ledger, cut the remaining runs at the cut-off; their quota redistributes.
8. **Check CONSTRAINTS.md and the round-5 audits** (`David/docs/audits/2026-11-07-2*`): a known edge may already be written down.

---

## 8. Completion Criteria

- [ ] `setup` gate PASS; accesses verified; agent runs launched with cut-off and budget
- [ ] `renderer-parity` PASS with teeth; `David/monitor_format/` exposes the Step-2 interface; `DAVID.md` milestone written
- [ ] `identity-parity`, `resume-parity`, `kernel-check` PASS; `accelerated-kernel-parity` PASS or reference path taken; P and run time measured
- [ ] `records` gate PASS; DATA-REPORT has per-source counts and shortfall redistribution
- [ ] Data gates (12.2) PASS or their fallback logged; train split frozen with its hash
- [ ] The run finished, or the 09:00 rule applied and logged
- [ ] Five candidates (or those that existed at 09:00) scored; pick logged with its kept set and intent scores
- [ ] Calibration fitted; `selected/`, `selected.json`, `calibration.json`, `long_context.json` on the volume in the Step-8 formats, loading through Kev's serving path
- [ ] `serve-path-parity` and `demo-check` PASS (or their fallbacks taken and logged)
- [ ] RESULTS.md: lift test (both endpoints), LLMBar, RewardBench 2, retention, RF recall and flag-everything, each with n and interval
- [ ] `DAVID.md` milestones: module interface, handoff files, validated length
- [ ] Spend within $200; secrets scan clean on every commit
- [ ] Every record in the frozen split carries source, basis and licence in `_meta` (2.5)
- [ ] All gates logged in `VALIDATION-LOG.md` with commit hashes, each proving its core claim on real data or the real path, with the planted-bug checks section 4 lists
- [ ] **Docs reconciled to the work, no orphan claims.** Every claim, metric and mechanism description in STATUS, DATA-REPORT, RESULTS, `DAVID.md` and the recaps is backed by an artifact, or struck
- [ ] **Every reported figure matches its measured source.** Each number equals the output it summarizes
- [ ] **Every relied-upon metric is itself proven reliable.** The code producing each reported metric (AUROC, agreement, positive counts, the lift test) is verified, for example a planted error turns the right metric red
- [ ] TASK-CLAIMS: every claim released with its Work manifest
- [ ] STATUS reflects the final state; TASKLIST has no open rows except `blocked [needs: X]`; a final recap with a terminal anchor exists

**Final action: the claim-and-count reconciliation pass.** Check every number in STATUS, DATA-REPORT, RESULTS, `DAVID.md` and the final recap against the files and logs it came from; fix each stale one in place. Run it last.

**Until all boxes are checked, the task is not done.**
