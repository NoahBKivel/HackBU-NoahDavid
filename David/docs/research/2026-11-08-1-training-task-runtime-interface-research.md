## Runtime-relevant findings from the training task files

Key to files (all under `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\training\`):
- **T** = `task.md` (339 lines)
- **A** = `AGENTS.md` (53 lines)
- **L** = `TASKLIST.md` (18 lines)
- **PT** = `prompts\TEMPLATE.md` (13 lines)
- **PG** = `prompts\goal-prompt.md` (9 lines)

Nothing was written to disk. I used one read-only `wc` and `ls` to get line counts and to check for `David\monitor_format\`.

### 1. Shared module `David/monitor_format/`

- **Status:** not built yet. A listing of `David\` shows no `monitor_format` folder. It contains `.gitkeep`, `NOTES-FROM-DAVID-AGENT.md`, `classifier`, `docs` and `training`.
- **Built by:** Step 2, T:222 `### Step 2: The shared module \`David/monitor_format/\``. No task row ID is given in these files. The build is T:223, which says "The public interface exports exactly what the runtime needs:". The listed exports are at T:224-229:
  - `build_instructions(events) -> list`
  - `render_state(instructions, documents, events, k, findings, b_state) -> (text, detailed_seqs, fits)`, where `fits` is the overflow switch
  - `render_screen(instructions, sections, events, k, budget) -> (text, fits)`
  - `split_sections(document) -> list`, `split_units(text, source) -> list`, `rf_window(units, i) -> str`
  - "the row-text fillers ... `open_findings_line(...)`, `correction_text(...)`"
  - "the question table and short names as data."
- **Dependency:** T:223 includes "requirement units with pysbd, English, `clean=False`". The runtime's environment will need pysbd.
- **Layout:** T:142-143 `├── monitor_format/ # the shared module (Step 2): imported by training AND the runtime` and `├── __init__.py # the stable public interface (re-exports)`.
- **Freeze:** T:231 `**Gate (\`renderer-parity\`):** golden bytes reproduce exactly; a test proves the module imports nothing from \`training/\`; teeth shown. After this gate the interface is frozen: a later change is a sidequest and an alert, because the runtime build depends on it. Write a \`DAVID.md\` milestone line: the module path and its interface.` The gate result is logged in VALIDATION-LOG (T:207, T:280).
- **Editing rules:**
  - T:81 "used by every record and imported read-only by the runtime build."
  - T:100 "pure functions, no I/O, no dependency on anything in `training/`, deterministic output (same inputs, same bytes)."
  - T:197 "The shared module imports nothing from `training/`; a test asserts it."
  - T:184 "Never edit `David/classifier/`, `David/docs/`, `Noah/` or the root files except `DAVID.md`."
  - T:201 says a change that would alter scope or the spec escalates to the owner alert.
- **Tests:** T:102 "Tests live in `training/tests/` and `David/monitor_format/tests/`."
- **Fixtures:** T:230 freezes golden bytes from "the four sample events in `Noah/backend/samples/`" plus a hand-written stream.

### 2. What the training run hands to the runtime

- **Location and volume:** T:86 "**The runtime handoff files** on the Modal volume `intent-monitor-training`: `selected/` (a directory Kev's `Checkpoint` loads), `calibration.json` and `long_context.json`, in the formats of section 4, Step 9." This cross-reference is inconsistent. The formats are written in Step 8 (T:254-257), not Step 9. Treat T:254-257 as authoritative.
- **Formats and timing (T:254-257, Step 8):**
  - T:254: "**Build:** score the final save's two candidates; apply the pick rule (9.4: paired bootstrap standard error, keep within one, highest intent score, pick order); calibrate the winner (9.5); write the handoff to the volume `intent-monitor-training`:"
  - T:255 `selected/`: "the winner as a directory Kev's `Checkpoint` loads (an α = 0.85 winner as full weights), plus `selected.json` naming the candidate, its α, its save step and the commit hash;"
  - T:256 `calibration.json`: `{"<question id>": {"T": float, "b": float}}` for yes/no questions and `{"<question id>": {"T": float, "b": {"<option>": float}}}` for choice and score questions, keyed by base id (no twins), score options keyed `"0"`, `"1"`, `"2"` as Kev reports them;
  - T:257 `long_context.json`: `{"validated_length": int}`, written after the long-context gate (8,192 until then).
  - T:262 (Step 9) rewrites `long_context.json` with the measured validated length after the long-context gate.
- **Saves (T:246):** "saves every ⌈S/10⌉ steps to the volume". The selected model is picked from the final save's two candidates (T:254).
- **Milestones and gates:**
  - T:258 "Then serve-path parity on 300 dev records and the demo check through the shared renderer and the serving path (12.3)... Add a `DAVID.md` milestone: the handoff files exist, where, and the winner."
  - T:259 "**Gates:** `serve-path-parity`, `demo-check`. Fire the alert when both pass ("model ready")."
  - PG:9 "DO NOT MARK THIS GOAL COMPLETE until the handoff files (selected checkpoint, calibration.json, long_context.json) are on the intent-monitor-training volume and load through Kev's serving path".
- **Fallback if the run is cut short:** T:215 "If training has not ended by 08:00, select from the saves that exist (spec 9.3) and finish Steps 8 and 9 with them." These files do not say what happens if no save exists.

### 3. Shared infrastructure

- **Modal app and volumes:**
  - T:107 "Training and scoring use the app name `intent-monitor-training` and the volume `intent-monitor-training`. Never modify the deployed app `intent-monitor` or its volume `intent-monitor-model`; they belong to the runtime build."
  - A:33 repeats this.
  - T:107 also says "the CLI is logged in to workspace `davidkny22` with auto-refill on."
- **GPU:** A:33 "H100 for training and scoring." T:84 "on a Modal H100".
- **Modal credit budget:** none in T, A, L, PT or PG. The only numeric budget is the Anthropic cap.
- **Anthropic credit:**
  - T:59 "**Spend:** at most $200 of Anthropic API credit in total, generation reserved first (spec 8.7)."
  - A:32 "up to $200 in total for this build, every job logged in `results/spend.jsonl`."
  - T:124 fires the owner alert when "spend reaches 90% of the $200 cap".
- **Keys:** T:106 gives the path `C:\Users\david\Documents\GitHub\classifier-for-metagaming\.env`, which is outside the HackBU repo. It holds `ANTHROPIC_API_KEY` and `HF_TOKEN`. It also says "No other Anthropic key exists on the machine; every `claude -p` run gets `ANTHROPIC_API_KEY` from this file, so it bills the API credit."
- **Other services:**
  - T:108 Hugging Face `HF_TOKEN`.
  - T:109 "**Harbor** (HVTB): installed and logged in as `davidkny22`".
  - T:110 "**Docker Desktop:** start it yourself when the lhaw or SWE-Misbehavior containers need it."
  - T:111 "`claude` is on PATH; headless runs use `claude -p` with Haiku 5.5 (`claude-haiku-5-5`) or Sonnet 5.5 (`claude-sonnet-5-5`)."
- **Locks and resource rules:**
  - A:37 "Every output that matters ends up on the Modal volume or in `David/`, never only in a container."
  - A:41 "Reuse `David/training/.venv`; a second environment needs a recorded conflict."
  - T:114 "create and reuse one environment for this build (`training/.venv`)".
  - No lock file or claims file is defined for cross-agent use. T:283 TASK-CLAIMS.md is described as "This build runs one orchestrator."
- **Codex settings:**
  - T:73 "You can run up to 100 concurrent subagents."
  - A:35 "**Codex subagents:** up to 100 concurrent."
  - T:113 "raise the concurrent-subagent limit to what the labelling needs (the owner allows up to 100); find the setting in Codex's own config and record what you changed in BUILD-LOG. Labelling and conversion subagents run on fast mode; thinking level medium for most work, low or none for mechanical work (format conversion, rule-checked labels)."
  - T:24 names `C:\Users\david\.codex\skills\stay-on-goal\SKILL.md`, which suggests both agents share one Codex config tree.

### 4. Conventions the runtime task should mirror

- **Filesystem layout:** T:130-180 is the full tree. The root shared files are at T:134: "CLAUDE.md, CONTRACT.md, DAVID.md, NOAH.md, README.md # shared; you update only DAVID.md (milestones)".
- **Gitignore (training only):** T:176 "├── .gitignore # data/, results/, vendor/, .venv/, *.safetensors, *.pt". The `training/.gitignore` is the only one specified. Nothing covers `David/classifier/`.
- **Committed and never committed:** A:18 "Committed: `David/monitor_format/` (code and tests), and in `David/training/` the code, tests, `task.md`, this file, STATUS, TASKLIST, ..." and "Never committed: `.env` or any key, `data/` ..., `results/`, `vendor/`, `.venv/`, model weights."
- **Commit rules (A:7-14):**
  - A:7 "Conventional commits with a scope: `type(scope): title`. Types: feat, fix, docs, refactor, test, chore, perf, build. Scopes: `training`, `monitor-format`, `docs`."
  - A:10 "No `Co-Authored-By`, "Generated with" or any attribution line; a commit that lands with one is amended once, immediately."
  - A:11 "Two commits per slice. The code commit carries code, tests and config only..."
  - A:12 "Stage by name. Leave untracked caches and build artifacts alone."
  - A:13 "`git pull --rebase` before every push... Never force-push or rewrite pushed history."
  - A:14 "Run the secrets scan (TRAINING-SPEC 12.2 patterns) over staged text files before every commit."
- **Task.md section structure:** headings at T:9 (section 0), T:31 (0.1 anchors), T:41 (1), T:77 (2), T:97 (2.1), T:104 (2.2), T:116 (2.3 owner alert), T:128 (3), T:182 (3.1), T:191 (3.2), T:199 (3.3 sidequests), T:205 (4 build order and gates), T:272 (5 documentation), T:291 (6 continuity), T:308 (7 when stuck), T:321 (8 completion).
- **Anchor line:** T:33 "Every recap ends with `Active task anchor: TASKLIST.md:Lx` naming the active or next row."
- **Companion documents:**
  - T:157-158 lists STATUS, TASKLIST, SIDEQUESTS, TASK-CLAIMS, MESSAGES, BUILD-LOG, VALIDATION-LOG, CONSTRAINTS.
  - T:159 `recaps/ # recap-NNN.md + TEMPLATE.md`.
  - T:160 `prompts/ # goal-prompt.md + TEMPLATE.md`.
  - T:162 `reports/ # DATA-REPORT.md, RESULTS.md`.
  - T:276-285 gives each document's format. T:282 is MESSAGES.md: "| MSG-NNN | YYYY-MM-DD HH:MM:SS | balanced verbatim head (10 to 20 words) | PENDING/HANDLED | evidence |".
  - T:274 "MECHANISMS.md and the mechanisms library are not used in this build."
- **MESSAGES gate:** T:15 "Read `training/MESSAGES.md` before treating any visible pre-compaction user message as work." T:16 begins "**ABSOLUTE MESSAGE GATE:** after compaction, before appending a row or starting work from any visible message...".
- **Goal prompt:** saved at `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\training\prompts\goal-prompt.md`. PG:1 "Read C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\training\task.md completely and follow it exactly; that folder is your workspace root." PT:7 "Read task.md first and follow it." PT:13 "If context rolls over, execute Section 0 of task.md before anything else, including the MESSAGES.md gate."

### 5. Training task mentions of the runtime, classify(), classifier, Noah, demo, 08:00

- `classify()` does not appear in any of the five files.
- **Runtime:**
  - T:81 "imported read-only by the runtime build."
  - T:107 "they belong to the runtime build."
  - T:142 "imported by training AND the runtime".
  - T:231 "the runtime build depends on it."
- **Classifier folder:** T:154 `classifier/ # the runtime build's folder (not yours; never edit)`. T:184 "Never edit `David/classifier/`..."
- **Noah:**
  - T:114 "the team repo's `C:\Projects\...` path in `CLAUDE.md` is Noah's machine and does not exist here."
  - T:134 mentions `NOAH.md` as a shared root file.
  - T:184 lists `Noah/` as never edited.
  - T:230 "the four sample events in `Noah/backend/samples/`".
- **Demo:** T:258 "the demo check through the shared renderer and the serving path (12.3)". T:331 "`serve-path-parity` and `demo-check` PASS". T:259 fires an alert "model ready".
- **08:00 deadline and fallback:**
  - T:45 "the 08:00 model does not need is an hour taken from the model."
  - T:60 "the selected, calibrated model and its files exist by 08:00 EST on 2026-11-08 (section 4, the clock rule)."
  - T:212 `latest_training_start = 08:00 − measured_run_time − 20 min (final-pair scoring, calibration, handoff) − 30 min margin`. "With 2.5 h it is 04:40."
  - T:213 `agent_run_cutoff = latest_training_start − 75 min`.
  - T:214 "a model by 08:00 outranks a rebuild."
  - T:215 "If training has not ended by 08:00, select from the saves that exist (spec 9.3) and finish Steps 8 and 9 with them."
  - T:247 "the run reaches its final step, or 08:00 arrives (the clock rule)."
  - T:328 "or the 08:00 rule applied and logged"

### 6. Rules that would conflict if both agents work in `David/`

1. **DAVID.md:** T:134 says training "update[s] only DAVID.md (milestones)". Training writes milestones at T:231, T:258, T:262 and T:333. No lock or coordination rule is written for the runtime's edits.
2. **Shared module:** T:231 freezes it after `renderer-parity`. A change after that is "a sidequest and an alert". T:197 says it imports nothing from `training/`. No channel is defined for the runtime to ask for a change. MESSAGES.md is training-only (T:15-16).
3. **Git:** A:13 requires `git pull --rebase` before every push. A:12 says to stage by name. No branch, lock or scope rule covers the runtime. A:7 lists only `training`, `monitor-format` and `docs` as scopes.
4. **Codex config:** T:113 tells training to change the concurrent-subagent limit in "Codex's own config". If that config is shared, the runtime agent inherits the change. T:24 shows `C:\Users\david\.codex\` is shared with the Codex skills.
5. **Anthropic credit and `.env`:** A:32 caps spend at "$200 in total for this build". T:106 says the `.env` key is the only Anthropic key. Any runtime `claude -p` or API use bills the same credit and would not appear in training's `results/spend.jsonl`. The files do not say whether the cap counts the runtime's spend.
6. **Python environment:** A:41 requires reuse of `David/training/.venv`. T:114 repeats it. If the runtime builds its own venv, the files do not say whether that conflicts with this rule. The runtime also needs pysbd (T:223).
7. **Docker and Modal:** T:110 says start Docker Desktop yourself, and T:107 says the Modal CLI is shared and auto-refills. No GPU or credit split is set.
8. **Commit and git scopes:** A:7 lists only training scopes. The runtime needs its own scope, which these files do not provide.
9. **Unlisted file:** `David\NOTES-FROM-DAVID-AGENT.md` sits at the `David\` root. It is not in the layout at T:130-155, and no rule in these files covers it. I did not read it.
10. **Handoff timing:** T:60 promises the files by 08:00, and T:215 falls back to any existing save. These files do not say what happens if no save exists. The runtime's task should plan for a missing or partial handoff.

### Coverage ledger

- `task.md`: lines 1-200 read in one chunk; lines 200-339 read in a second chunk. **Every line covered.**
- `AGENTS.md`: lines 1-53. **Every line covered.**
- `TASKLIST.md`: lines 1-18. **Every line covered.**
- `prompts\TEMPLATE.md`: lines 1-13. **Every line covered.**
- `prompts\goal-prompt.md`: lines 1-9. **Every line covered.** This is the only file in `prompts\`.
- Not read, outside this scope: `David\docs\TRAINING-SPEC.md` (the spec's 9.1 pins, 9.4 pick rule and 12.x gates), `STATUS.md`, `BUILD-LOG.md`, `recaps\`, `NOTES-FROM-DAVID-AGENT.md`, and any `training\` file other than the five above. I did not list the top level of `training\`.