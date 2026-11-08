# Intent-Fidelity Monitor Training Build: Autonomous Task Specification

## Operational guide for the overnight build of the Kev-4B decision adapter: data, labels, one training run, selection, calibration and evaluation

The workspace root for this task is `HackBU-NoahDavid/David/training/` (called `training/` below). Paths starting `David/` are relative to the repository root `C:\Users\david\Documents\GitHub\HackBU-NoahDavid`.

---

## 0. Context Recovery (do this first, every session)

**If this is not your first session, or the context window has rolled over:**

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
11. Read the skills, each in full: `C:\Users\david\.codex\skills\stay-on-goal\SKILL.md`, `C:\Users\david\.claude\skills\reading-context\SKILL.md`, `C:\Users\david\.claude\skills\slopless-writing\SKILL.md`. Declare the goal-directed chain for the current work in one line (current action -> immediate artifact -> required gate -> the 08:00 deliverable).
12. Only after all of the above, resume from where the last session stopped. Read `David/docs/research/` reports or `David/docs/audits/` only when a task row or the spec cites them.

**Do not rely on memory. Read the files.** Tail reads are capped at 10 lines unless a step above says otherwise. Section 0 fires on compaction or rollover only, never on an ordinary turn boundary, and when it fires a partial pass is a false record: execute it exactly as written.

**On-demand data, never Section-0 reads:** everything under `training/data/` and `training/results/`, the spend log, `TASK-CLAIMS.md` beyond its rows, and the dataset dossier `David/docs/DATASET-DOSSIER.md` (read the entry a converter needs, nothing else).

### 0.1 Focused recovery and active-task anchors

- Every recap ends with `Active task anchor: TASKLIST.md:Lx` naming the active or next row. While a sidequest is open, it carries both anchors.
- On recovery, read only the anchored row plus about 2 lines of context, and only the spec sections that row lists in its `Spec` column. Full tracker or spec re-reads are for completeness passes, an explicit user request, or a missing or stale anchor.
- **Spec-section anchors (this spec is long and dense):** in the first session, read the whole spec once and write, in each TASKLIST row, the spec sections it depends on (for example `6.4, 7.8, 12.2`). Recovery then reads only those sections.
- When no valid anchor exists, read the minimum tracker range needed to find the active row, then write a recap with the exact anchor.
- Update the anchor in the recap after every task transition.

---

## 1. Core Principles

### 1.1 You are building one trained, calibrated monitor by 08:00, not a data-engineering showcase

The deliverable is a selected, calibrated Kev-4B decision adapter whose files the runtime can load, plus the measured lift over stock Kev-4B. Every hour spent polishing a converter, a report or a tool that the 08:00 model does not need is an hour taken from the model. "The pipeline is elegant" is never progress; a frozen, gated train split and a finished run are.

### 1.2 The spec is authoritative, and it settles scope

`David/docs/TRAINING-SPEC.md` defines every format, wording, source, rule, threshold and gate. It is the agreed scope: build what it specifies and add nothing outside it. Where it is ambiguous, apply 1.5. Never edit the spec; a defect you find in it is a sidequest row and an alert (2.3), not a silent workaround. `DESIGN-DECISIONS.md` is the design session's ledger; you never read or write it.

### 1.3 Verified means measured against the spec's gate

Nothing counts as done until its spec gate (section 12) logs PASS in `VALIDATION-LOG.md` with the commit hash, or its "reported" item is written to a report with real numbers. "It ran without errors" is not verification. An implausible result (a dev AUROC at chance, a positive rate of 0% or 100%, an agreement of 1.0 everywhere) is a bug signal to root-cause before anything is reported.

### 1.4 Hard boundaries

- **The held-out sets are touched once** (spec 7.9): no held-out item reaches training, selection or calibration, and only the selected candidate and stock Kev are scored on them.
- **Secrets never leave the machine.** Nothing from `.env`, no token and no credential is printed, logged, committed or written into any record; the secrets scan (spec 12.2) runs on every record and on every committed text file.
- **Spend:** at most $200 of Anthropic API credit in total, generation reserved first (spec 8.7).
- **Time:** the selected, calibrated model and its files exist by 08:00 EST on 2026-11-08 (section 4, the clock rule).
When uncertain, take the conservative reading of these four and keep working.

### 1.5 When to ask instead of deciding

Make implementation choices yourself: structure, libraries, formulas the spec implies, the mechanics of a stated rule. Stop and alert the owner (2.3) only when a choice changes what gets built or how success is judged and the spec does not settle it, and you cannot check your way to certainty. If you can check now (run it, measure it, read the source), check instead of asking. While waiting on an alert, continue every task that does not depend on the answer.

### 1.6 Research before code, per mechanism

For any mechanism the spec does not pin down to the line (a dataset's real field layout, Kev's trainer internals, a Codex or Modal setting), read the source first: the dataset files, the code at the pinned commit, the official docs. Save a short note to `training/notes/` when the finding is reusable. Implementing from memory and then checking the code against itself proves nothing.

### 1.7 Scale out, never slow down

You can run up to 100 concurrent subagents. Converters, constructions, generation and labelling are parallel by nature: fan them out. Moving equal-cost work into a second Modal container is pre-approved wherever it shortens the critical path (spec 11). If throughput is the concern, add workers; never stop.

---

## 2. Objective

Produce, from the spec:

- **The shared module `David/monitor_format/`** (section 4, Step 2), with its frozen interface, used by every record and imported read-only by the runtime build.
- **The training data:** N = 12,200 train records (spec 7.1), a grouped dev split with the intent slice and the long-context gate items (7.9), and the held-out conversions (7.9), all labelled (8) and passing the data gates (12.2).
- **The patched trainer and the interpolation tool** (9.2), with the Phase-1 correctness gates passing (12.1).
- **One training run** (9.1) on a Modal H100, saves every ⌈S/10⌉ steps.
- **Selection and calibration** (9.3 to 9.5): five candidates scored, the pick made, calibration fitted, serve-path parity and the demo check passing (12.1, 12.3).
- **The runtime handoff files** on the Modal volume `intent-monitor-training`: `selected/` (a directory Kev's `Checkpoint` loads), `calibration.json` and `long_context.json`, in the formats of section 4, Step 9.
- **The evaluation** (12.3, 12.4): the lift test, LLMBar and RewardBench 2, retention, RF recall, the long-context gate and the "flag everything" report, written to `training/reports/RESULTS.md` with real numbers.

**DO NOT MARK THIS GOAL COMPLETE** until: the handoff files exist on the volume and load through Kev's serving path; serve-path parity and the demo check logged PASS (or their spec fallbacks were taken and logged); every Phase-1 and data gate logged PASS or its spec fallback; `RESULTS.md` carries the lift test and every reported item with measured values; `DAVID.md` carries the handoff milestone; STATUS reflects the final state; and a final recap exists.

**Blocked work.** "We have not" is not "we cannot". A row is `blocked [needs: X]` only for a real external blocker (an access grant that never arrived, a hardware or service outage). A blocked source redistributes its quota (spec 7.1); a blocked row never holds the rest of the goal hostage.

**No early stop.** "The context is nearly full", "this is multi-session work" and "I have taken it far enough" are never stop reasons. Work stops only on a true blocker, the permission system, or the owner's words.

**Status is binary:** a row is done or it is not.

### 2.1 Code quality

- Python 3.11 or newer, type hints on public functions, one-line docstrings on public functions only, no inline test code in product files.
- The shared module is held to the highest bar: pure functions, no I/O, no dependency on anything in `training/`, deterministic output (same inputs, same bytes).
- Every converter and construction is a separate file registered in a registry (section 3.2); adding a source never edits the pipeline.
- Tests live in `training/tests/` and `David/monitor_format/tests/`. No test-count target; each gate's tests must show teeth (section 4).

### 2.2 Environment and access

- **Keys:** `C:\Users\david\Documents\GitHub\classifier-for-metagaming\.env` holds `ANTHROPIC_API_KEY` and `HF_TOKEN`. Load it into the process environment of the commands that need it (Hugging Face downloads, the Anthropic API, `claude -p`). Never print it, copy it, or write it anywhere. No other Anthropic key exists on the machine; every `claude -p` run gets `ANTHROPIC_API_KEY` from this file, so it bills the API credit.
- **Modal:** the CLI is logged in to workspace `davidkny22` with auto-refill on. Training and scoring use the app name `intent-monitor-training` and the volume `intent-monitor-training`. Never modify the deployed app `intent-monitor` or its volume `intent-monitor-model`; they belong to the runtime build.
- **Hugging Face:** `HF_TOKEN` has access to SWE-chat, TRACE and the other gated sets the spec names; impossible-SWE may still be pending (its quota then redistributes).
- **Harbor** (HVTB): installed and logged in as `davidkny22` (`harbor` CLI).
- **Docker Desktop:** start it yourself when the lhaw or SWE-Misbehavior containers need it.
- **Claude Code CLI:** `claude` is on PATH; headless runs use `claude -p` with Haiku 5.5 (`claude-haiku-5-5`) or Sonnet 5.5 (`claude-sonnet-5-5`).
- **Kev:** clone `https://github.com/jaredpalmer/kev` into `training/vendor/kev` and check out `fc4a17e194bca35a48c57211392ec49ea54a94ac`. Environment pins are in spec 9.1.
- **Codex subagents:** raise the concurrent-subagent limit to what the labelling needs (the owner allows up to 100); find the setting in Codex's own config and record what you changed in BUILD-LOG. Labelling and conversion subagents run on fast mode; thinking level medium for most work, low or none for mechanical work (format conversion, rule-checked labels).
- **Python:** create and reuse one environment for this build (`training/.venv`); the team repo's `C:\Projects\...` path in `CLAUDE.md` is Noah's machine and does not exist here.

### 2.3 The owner alert

The owner may be asleep. Nothing waits for a reply. When something needs the owner, raise a loud, non-blocking alert and keep working on everything that does not depend on the answer:

```powershell
Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-Command',"(New-Object Media.SoundPlayer 'C:\Windows\Media\Alarm01.wav').PlayLooping(); Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('<one-line reason; see STATUS.md>','Training build needs you','OK','Warning') | Out-Null"
```

Keep this as `training/scripts/alert.ps1` taking the message as an argument. Fire it, and write the reason at the top of STATUS.md's `Active work`, when: a true blocker stops a row with no fallback; a data gate still fails after its one rebuild or relabel; spend reaches 90% of the $200 cap; the latest training start (section 4) is 15 minutes away and the train split is not frozen; the run crashes twice; a spec defect forces a choice between readings; or the goal completes. Never fire it for routine progress.

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
        │   ├── splits/                # grouping, dev, intent slice, long-gate items, held-out conversions (7.9)
        │   ├── kevpatch/              # trainer patches (9.2) applied to vendor/kev, interpolation tool
        │   ├── modal_app/             # the Modal training and scoring app (intent-monitor-training)
        │   ├── select/                # candidate scoring, pick rule (9.4), calibration (9.5)
        │   └── evaluate/              # lift (12.4), held-out reports, long-context gate (12.3)
        ├── tests/
        ├── .gitignore                 # data/, results/, vendor/, .venv/, *.safetensors, *.pt
        ├── data/                      # GITIGNORED: downloads/<source>/ (each its own folder), records/, frozen/
        ├── results/                   # GITIGNORED: run outputs, scores, spend.jsonl
        └── vendor/kev/                # GITIGNORED: Kev at the pinned commit
```

### 3.1 Filesystem rules

- Work only inside `David/`. Never edit `David/classifier/`, `David/docs/`, `Noah/` or the root files except `DAVID.md`.
- Downloaded data and archives are untrusted: each source downloads into its own new folder under `data/downloads/`, scripts never live there, and any Python reading them runs with `python -I`. Never run code shipped inside a dataset.
- STATUS.md is the single source of truth, advanced in every closeout.
- BUILD-LOG.md, VALIDATION-LOG.md, CONSTRAINTS.md, MESSAGES.md and recaps are append-only.
- Records, model weights, Kev's source and downloads are never committed: they are third-party data under mixed licences and too large; they live in `data/`, `results/`, `vendor/` and on the Modal volume.
- Before any commit, run the secrets scan (spec 12.2 patterns) over the staged text files.

### 3.2 Debt prevention

- One concern per file; split a file before it passes a few hundred lines.
- Contracts are the firewall: every converter implements one interface (`convert(raw_dir) -> iterator of (event_stream, side_record, meta)` plus its declared label bases), every construction another; each is a new file plus a registry entry.
- Decision tables (the question set, short names, correction table, the source quotas of 7.3) ship as data in one place each; nothing restates them.
- No project-guidance metadata in product artifacts (AGENTS.md law 4).
- The shared module imports nothing from `training/`; a test asserts it.

### 3.3 Sidequests

A defect found while doing something else gets a `SIDEQUESTS.md` row before its first action (chain to the goal, exit condition, budget in commits, fallback, return pointer), is worked within its budget, closed, and the anchored row resumes. Anything that would change scope or the spec escalates through the owner alert (2.3) and is not worked as a sidequest.

---

## 4. Build Order and Gates

The steps are dependency-ordered. Completion is gate-based: a step is done when its gate logs PASS in `VALIDATION-LOG.md` with the stroke-1 commit hash. Each correctness gate shows **teeth** once: plant a bug in the code it guards (one changed byte in a rendered field, a skipped resume field, a flipped label), run the gate, see it go red, revert, and log both rows. A gate that stays green with the bug planted is a missing test.

**Concurrency.** Steps overlap wherever the dependency column allows. The background tracks are: agent runs (from Step 1), the smoke run (from Step 3), generation (from Step 4), and, once training starts, the dev and held-out work and candidate scoring (Step 7).

**The clock rule.** Work backward from 08:00 EST:
- `latest_training_start = 08:00 − measured_run_time − 20 min (final-pair scoring, calibration, handoff) − 30 min margin`. Use 2.5 h for the run time until the smoke run measures throughput, then recompute it and record it in STATUS. With 2.5 h it is 04:40.
- `agent_run_cutoff = latest_training_start − 75 min` (converting and labelling their records). Unfinished runs stop at the cut-off; their quota redistributes (spec 7.1).
- At `latest_training_start`, the train split freezes with what has passed labelling. If a data gate's rebuild has not finished, log the shortfall in VALIDATION-LOG and DATA-REPORT, fire the alert, and start training anyway: a model by 08:00 outranks a rebuild.
- If training has not ended by 08:00, select from the saves that exist (spec 9.3) and finish Steps 8 and 9 with them.

### Step 1: Setup (first 20 minutes)
**Build:** read the team repo's `CLAUDE.md`, `CONTRACT.md` and `DAVID.md` once, in full (re-read CONTRACT.md sections 3 and 5 only when touching the event schema); initialize every file of section 3 (formats in section 5); `.gitignore`; `training/.venv` with the spec 9.1 pins; the Kev clone at the pinned commit; `scripts/alert.ps1`; a spend ledger (`results/spend.jsonl`, one line per API job); check each access in 2.2 (Modal, HF gated reads, Harbor, Docker, `claude -p` with the `.env` key on one tiny call, the Codex subagent limit). Then launch the agent runs (spec 8.7) as the first background job, with the cut-off above and the spend rule (generation's estimate reserved first: estimate it now from the 8.6 call count, record it, give runs the rest).
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
**Build:** spec 9.2 items 1 to 4 against `vendor/kev`, kept as code in `src/intent_training/kevpatch/`; the Modal app `intent-monitor-training` (H100, the volume mounted). Then one smoke job: kernel check, accelerated-kernel trial, resume trial, pass-cap measurement on a synthetic record at the largest padded cost, and throughput (records per hour) to settle the run time.
**Gates (spec 12.1):** `identity-parity`, `resume-parity`, `kernel-check`, `accelerated-kernel-parity` (its fallback, the reference path, is a valid outcome), and the measured `P` and run time logged. Recompute the clock (section 4) and record it in STATUS.

### Step 4: Records (parallel subagents)
**Build:** one converter per source in spec 7.3 and one builder per construction in 7.4, fanned out to subagents (each gets: its 7.3 row, its dossier entry, the event schema, the shared module's interface, and its output path); the agent-side generator (8.6) feeding constructions, IF_multi, InFoBench, IN3, SWE-bench annotations, rewrites (7.6) and notes (7.5); the cut rule (7.2) with matched negative cuts; long records (7.7); replay and long-document records in Kev's native format (7.3). Every converter's output validates against the event schema before any of its records are rendered. Order the fan-out by how many positives a source supplies to rare questions (constructions, then V sources), so the labelling queue fills early.
**Gate (`records`):** every converter and construction validates; the secrets scan finds zero matches; per-source record counts against `s · n^plan` written to `reports/DATA-REPORT.md` (shortfalls redistributed per 7.1).

### Step 5: Labels and the train-split freeze
**Build:** the teacher (spec 8): labelling instructions verbatim from 8.2, one Sol vote and one Terra vote per record, batches of 10 to 20 records from one source, vote collection into `data/`; the three ordered diagnostic passes (8.2 item 6); label resolution (8.4), construction mismatch and retries (7.4); twins (4.2); siblings (6.4); the balance cap (7.8); grouping and the train split (7.9). Label the train split first; dev and held-out work moves to Step 7.
**Gates (spec 12.2):** `positive-floor` (max(0.8 · P_q, 60) per question, P_q computed per spec 10 before labelling starts and written to DATA-REPORT), `teacher-agreement`, `cant-tell-rate`, `pair-integrity`, `secrets-scan`. Each failure takes its spec fallback once. Then freeze: write `data/frozen/train.jsonl` and its hash, copy it to the volume.

### Step 6: The training run (background on Modal)
**Build:** the spec 9.1 command on the frozen train split plus replay, saves every ⌈S/10⌉ steps to the volume, on the measured `P`. Watch it; on a crash, resume from the last save (one automatic retry; a second crash fires the alert and the run resumes again).
**Gate (`run`):** the run reaches its final step, or 08:00 arrives (the clock rule).

### Step 7: While training runs (parallel)
**Build:** the dev split at natural prevalence with its per-question floor and top-ups (7.9), the intent slice (9.4), the long-gate pilot on stock Kev and then its items (7.9), the held-out conversions (7.9: TRACE with the teacher locating the exposure cut once per conversation, the probe items mapped to their questions, LLMBar, RewardBench 2), all labelled. In a separate scoring container: stock Kev on dev (and stock's calibration fit, spec 12.4), then each candidate as soon as its save exists (the step-400 save at both α), per 9.4.
**Gate (`dev-ready`):** dev and the intent slice meet their floors; every candidate that exists is scored; stock's lift-baseline calibration is fitted.

### Step 8: Selection, calibration, handoff
**Build:** score the final save's two candidates; apply the pick rule (9.4: paired bootstrap standard error, keep within one, highest intent score, pick order); calibrate the winner (9.5); write the handoff to the volume `intent-monitor-training`:
- `selected/`: the winner as a directory Kev's `Checkpoint` loads (an α = 0.85 winner as full weights), plus `selected.json` naming the candidate, its α, its save step and the commit hash;
- `calibration.json`: `{"<question id>": {"T": float, "b": float}}` for yes/no questions and `{"<question id>": {"T": float, "b": {"<option>": float}}}` for choice and score questions, keyed by base id (no twins), score options keyed `"0"`, `"1"`, `"2"` as Kev reports them;
- `long_context.json`: `{"validated_length": int}`, written after the long-context gate (8,192 until then).
Then serve-path parity on 300 dev records and the demo check through the shared renderer and the serving path (12.3), with the fallbacks of 12.1 and 12.3 if they fail. Add a `DAVID.md` milestone: the handoff files exist, where, and the winner.
**Gates:** `serve-path-parity`, `demo-check`. Fire the alert when both pass ("model ready").

### Step 9: Evaluation (parallel containers, after the handoff)
**Build:** the lift test (12.4), LLMBar and RewardBench 2, retention, RF recall, the "flag everything" report (13), the long-context gate (12.3, then rewrite `long_context.json` and add a `DAVID.md` line with the validated length). Write every number to `reports/RESULTS.md`: each with its n, its interval, and the candidate it describes.
**Gate (`lift`):** the lift test ran on the pre-registered protocol and its result (pass or fail) is in RESULTS.md. A failed lift is reported as measured, never re-run with a changed protocol.

### Step 10: Close
The claim-and-count reconciliation pass (section 8), the final recap, the final alert.

**The two-commit closeout (AGENTS.md law 1).** Stroke 1 commits a code slice after its tests ran on that exact tree. Stroke 2 commits the docs (STATUS, BUILD-LOG, TASKLIST, recap; VALIDATION-LOG's row citing the stroke-1 hash; CONSTRAINTS on a durable lesson) as a separate, adjacent commit, with no test re-run. Closeouts ride row completion, not every edit. A row is one coherent slice of one or two commits; split larger ones.

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
- **TASK-CLAIMS.md:** the slug registry and claims table. This build runs one orchestrator; register its slug in the first session. Subagents doing conversion or labelling write only their own output files and never touch the scaffold.
- **Recaps** (`recaps/recap-NNN.md`, never overwritten): one per gate at least, plus before any expected rollover and every 3 to 5 significant actions; sections: what was accomplished, state of each step, key intelligence, the clock values, immediate next steps, and the `Active task anchor` line.
- **reports/DATA-REPORT.md and RESULTS.md:** the numbers the spec says are reported, each with its n and interval; nothing typed from memory.

Role boundaries: a gate result lives in VALIDATION-LOG and is referenced elsewhere; STATUS is the present; BUILD-LOG is the trail; CONSTRAINTS holds lessons.

---

## 6. Cross-Session Continuity Rules

1. The filesystem is your memory; what is not written does not exist next session.
2. STATUS is updated in every closeout, never batched to the end.
3. TASKLIST is the plan; the recap's anchor points into it.
4. Section 0 is mandatory after every rollover.
5. Recaps are cheap; write one before any expected rollover.
6. Append-only files are never edited or trimmed.
7. Run a gate's real command before declaring it; read the real output.
8. Verify against the spec, not against your own code's output.
9. The clock values in STATUS are recomputed whenever a measured duration changes them.
10. An interruption is not evidence of change; resume the anchored row.
11. Never change a quantity the spec or the owner set (N, quotas, floors, thresholds, the $200 cap, the 08:00 deadline) without the owner's words.
12. Background jobs are tracked in STATUS (job, where it runs, how to check it, expected end) so a recovered session can find them.

---

## 7. When Stuck

1. **Re-read the spec section the row anchors.** Most format questions are answered there to the token.
2. **A dataset field is not where the spec or dossier says:** open three real rows from the download, then the dossier entry, then the dataset card; record the real layout in `notes/` and a CONSTRAINT.
3. **Kev rejects or silently drops records:** check `max_state`, `max_packed` (`max_state` + 1,664) and `max_branch` (`max_state` + 640) in `vendor/kev/kev/model.py` and the trainer's fit test; a state at exactly 32,768 tokens is rejected (spec 6.4 uses 32,767).
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
- [ ] The run finished, or the 08:00 rule applied and logged
- [ ] Five candidates (or those that existed at 08:00) scored; pick logged with its kept set and intent scores
- [ ] Calibration fitted; `selected/`, `selected.json`, `calibration.json`, `long_context.json` on the volume in the Step-8 formats, loading through Kev's serving path
- [ ] `serve-path-parity` and `demo-check` PASS (or their fallbacks taken and logged)
- [ ] RESULTS.md: lift test (both endpoints), LLMBar, RewardBench 2, retention, RF recall, flag-everything, long-context validity, each with n and interval
- [ ] `DAVID.md` milestones: module interface, handoff files, validated length
- [ ] Spend within $200; secrets scan clean on every commit
- [ ] STATUS reflects the final state; TASKLIST has no open rows except `blocked [needs: X]`; a final recap with a terminal anchor exists

**Final action: the claim-and-count reconciliation pass.** Check every number in STATUS, DATA-REPORT, RESULTS, `DAVID.md` and the final recap against the files and logs it came from; fix each stale one in place. Run it last.

**Until all boxes are checked, the task is not done.**
