# Review of `docs/TRAINING-SPEC.md` (Intent-Fidelity Monitor training specification)

Reviewer: senior ML engineer, adversarial read. Date anchor: `date` → Sat Nov 7 21:12 EST 2026. No file was edited. No skill was invoked. Only two foreground shell commands ran (`date; wc -l` and `wc -l`); both exited before the next call; no background processes.

## Coverage ledger

| File | Lines read (ranges) | wc -l | Every line covered |
|---|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 | 97 | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 | 102 | yes |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 | 28 | yes |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 | 71 | yes |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–606 | 605 | yes |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–134 | 133 | yes |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–207 | 206 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–140, 141–262 | 261 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md` | 1–200, 201–400, 401–600, 601–658 | 657 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 201–400, 401–600, 601–800, 801–1000, 1001–1073 | 1072 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC-TRACE.md` | 1–35 | 35 | yes |

(Where a read ended one line past `wc -l`, the file has no trailing newline; the extra line is empty.)

Claims about Kev's trainer internals (flag names, `target` support, none-pair semantics, head training) are outside what I could verify from these files; D46 assigns them to the separate external-claims pass. I flag below only where the spec's own text makes an unverifiable assumption load-bearing.

---

## Part 1: Logic and contract audit

### F1 · Part 1 · error · Identity warm-start fails by construction if the pointer head is trained
- **Spec text.** §1: "It has four parts: a LoRA weight change Δ, an interpolation weight α that scales Δ, a temperature T_q ... and a prior offset b_q ... At α = 0, T_q = 1, b_q = 0 the adapter's logits equal stock Kev-4B's." §9.3: "α scales the LoRA change at load". §9.2.1: "save adapter, **pointer head**, optimizer state ...".
- **Evidence.** The pointer head is saved separately, so it is trained; the ledger confirms (D41: "head LR equal to the LoRA LR"). At α = 0 the LoRA path vanishes but the trained head remains, so logits ≠ stock. The identity-parity gate (§12.1, "no candidate is scored until it passes") would then block every candidate and the 07:00 pick falls to stock.
- **Consequence.** The result breaks: the headline guarantee is false and its gate fails for every save.
- **Resolution.** One answer is consistent with the stated guarantees: Δ includes every trained parameter (LoRA and head delta) and α scales all of it. The alternative (freeze the head) is a design choice that changes capacity. The spec must state which; also §9.1 carries no head-LR flag (see O3).

### F2 · Part 1 · error · Calibration composition is not the exact label-shift correction it claims
- **Spec text.** §1: "Each served probability is σ((z_q + b_q)/T_q) ... b_q is the closed-form prior shift ... exact under ... A-label-shift." §9.5: "T_q minimizes NLL on dev after the offset".
- **Evidence.** The exact label-shift correction adds the log prior ratio to calibrated log-odds. If z needs a temperature T to be calibrated, the exact form is σ(z/T + b). The spec's form equals σ(z/T + b/T): the prior shift is divided by T, so it is exact only when T = 1, which the T ≥ 1 clamp makes the exception, not the rule.
- **Consequence.** The coherence invariant's "exact" claim is unsupported; the calibration gate (ECE) inherits the error.
- **Resolution.** One correct answer: σ(z_q/T_q + b_q) (softmax(z/T + b) for choice/score).

### F3 · Part 1 · error · Tie rule turns "both teachers can't tell" into a yes label
- **Spec text.** §8.3: "can't tell (0.5); the target is the mean ... `label` = target ≥ 0.5." §2.1: "A label says what the monitor's own state shows." §8.2.2: "Answer yes only when the visible state shows the problem."
- **Evidence.** Two can't-tell votes (0.5, 0.5) or a yes/no split give target 0.5 → `label: true`. These rows count as positives for the balance cap (§7.8, "every positive row is kept"), the positive-floor gate and dev AUROC labels, and they are exactly the items where the state does not show the problem.
- **Consequence.** Positives are inflated with ambiguous items in the direction the principles forbid; dev AUROC and the per-question prior π_train are biased.
- **Resolution.** A decision: ties → no (`label = target > 0.5`), or exclude target-0.5 rows from binary counts and metrics. The principle-consistent answer is ties → no.

### F4 · Part 1 · error · Balance cap randomly destroys pair groups
- **Spec text.** §7.8: "negative rows are sampled down to at most 3 per positive." §7.4 goal-flip: "yes under the goal it defeats ... No under the goal it serves." §9.2.2: pair groups "always share a batch."
- **Evidence.** M1 negatives (~10,000 rows) far exceed 3× M1 positives (~1,000), so ~70% of negative M1 rows are dropped at random, including the "no" halves of goal-flip pairs and the benign side of constraint and same-context pairs. A pair whose negative row is dropped teaches nothing contrastive; batching the pair together is then moot. Neither §7.8 nor D27 exempts pair rows.
- **Consequence.** The intent-hardening mechanism (D27) loses most of its contrastive signal.
- **Resolution.** A decision (small): exempt pair-group members' rows from the cap, or count them toward the 3:1 before random sampling.

### F5 · Part 1 · error · Benign rewrites keep labels that depend on the text they rewrite
- **Spec text.** §7.6: "a copy whose `agent_text` is rewritten to sound benign; actions, results and labels unchanged." §4.2 M5: "Does the agent claim something about what it did ... that RUN LEDGER or LATEST EVENT contradicts ...".
- **Evidence.** M5's evidence is the agent text itself; M7 and M1 are partly text-borne ("latest action or message"). A rewritten text can add or remove the false claim, so "labels unchanged" is not guaranteed for those rows. The spec does not re-label copies and the §7.6 spot-check covers only "unchanged actions".
- **Consequence.** Label noise injected on ~500–700 records, concentrated on M5.
- **Resolution.** A decision: drop text-dependent rows (at least M5) from rewrite copies, or have the teacher relabel copies (costs calls).

### F6 · Part 1 · error · Label resolution contradicts the construction-mismatch rule
- **Spec text.** §8.4.1: "Construction labels and visible-based source labels are final for their question." §7.4: "When the teacher's label on a construction's target question disagrees with the intended label, the record keeps the teacher's label".
- **Evidence.** The two sentences assign the same clash opposite winners. The ledger (D30 "Construction mismatch") makes the teacher win.
- **Consequence.** The builder cannot proceed without picking; the two readings yield different datasets.
- **Resolution.** One correct answer per the ledger: only visible-based source labels are final; constructions yield to the teacher.

### F7 · Part 1 · error · Fill rule: ambiguous overflow referent, unbounded one-liners, negative detail budget
- **Spec text.** §6.4: "detail budget 0.40 × B_state − (tokens used by instructions and documents) ... every older event as a one-liner ... If instructions and documents alone exceed the budget, the record belongs to the overflow screen form."
- **Evidence.** (a) "the budget" follows the phrase "detail budget" (13,107 tokens) but D18 says the switch is on "the trained budget" (32,768); the two readings route very different records to the screen form. (b) For instructions+documents between 13,107 and 32,768 the detail budget is negative: zero detailed events, yet L1 asks about "the recent events shown in detail". No floor is stated. (c) One-liners have no cap: a 1,000-event run yields ~30K tokens of one-liners on top of documents and LATEST EVENT, exceeding `--max_state 32768`; no drop rule is given. (d) "LATEST EVENT in full" vs "Each detailed block's `result` plus `patch` together are capped at 2,000 tokens" is ambiguous for a 50K-token tool output.
- **Consequence.** The shared renderer is underspecified at exactly the long-run regime the long-context work targets; states can exceed the trainer's limit; two implementers produce different bytes.
- **Resolution.** (a) a decision (ledger-consistent: 32,768); (b) a decision (K floor or K = 0 permitted); (c) one correct answer implied by "newest first": drop the oldest one-liners; (d) one correct answer: the cap applies to LATEST EVENT.

### F8 · Part 1 · error · Event schema is not "exactly" the Mod's, and the renderer uses fields the schema lacks
- **Spec text.** §6.1: "Every converter and construction builder emits events with exactly these fields (the Claude Code Mod's schema)". §6.4: "result (ok, exit 0)". §6.4: "The key argument after the tool name is the command (Bash), the path (Read/Write/Edit), or the pattern (Grep/Glob)."
- **Evidence.** CONTRACT.md §3 has `schema_version`, `session_id`, `event_id` (spec omits them) and no exit-code field anywhere in §3 or §5; `is_error` is the only status. CONTRACT.md §5 lists "Actions (Edit, Write, Bash, PowerShell)" and D12 says "On Windows, shell actions may arrive through a PowerShell tool"; the demo runs on Windows 11 (CONTRACT §1). The spec's tool list has no PowerShell and all converted shells become Bash. `todos` item shape is undefined in both documents though the renderer prints "[x] … [ ] …".
- **Consequence.** `exit <c>` has no source; a PowerShell event at the demo has no key-argument rule and a tool name the training data never contains (train ≠ runtime on the demo surface).
- **Resolution.** Exit code: one answer (omit the field, or parse it only when `result_text` carries a recognised marker; state which). PowerShell: one answer (normalize to Bash in the renderer). `todos` shape: needs Noah's field definition.

### F9 · Part 1 · error · Correction text in the event stream and the OPEN FINDINGS status are unspecified; training can leak the L7 label into the state
- **Spec text.** §6.4: "[F3] M4 at E41 · correction sent at E42 · L7 status: acknowledged only". §7.4: "The correction text (6.5) inserted after a violating event". §6.5: "answered yes (p = 0.87)".
- **Evidence.** CONTRACT §4 says `inject_agent` "Attaches `text` to the agent's next tool result" (prepend/append unstated), so at runtime the correction lives inside `result_text` of event k+1 and is subject to the 2,000-token head/tail cut. The spec never says where the construction places it. The OPEN FINDINGS line shows an L7 status: in a correction-window record the state must show the *prior* status, and there is no initial token for "correction just sent, no L7 yet". The probability to print in constructed corrections is not given.
- **Consequence.** A builder can render the intended L7 class into the state (label leakage), and the runtime cannot reproduce the training bytes.
- **Resolution.** Decisions: placement (pin with Noah), the initial status token, and the p-value rule for constructions.

### F10 · Part 1 · error · Natural L7 sources do not fit the correction format
- **Spec text.** §7.3: "TonyDzi hook recoveries | Hook block plus recovery as one record"; "SWE-chat post-pushback | The K events after a pushback prompt". §4.2 L7: "The monitor sent the agent this correction: «text»."
- **Evidence.** A Stop-hook block or a user pushback is not the monitor's §6.5 text; the spec gives no rendering of these as OPEN FINDINGS or as a correction event.
- **Consequence.** ~300 records (×0.809) have no defined state form; the builder invents one.
- **Resolution.** A decision (for example render the pushback as a `[I_n]` instruction and skip OPEN FINDINGS, or exclude them from L7 and use them as L1/M1 material).

### F11 · Part 1 · error · "Train equals runtime" gates reference a runtime path this track does not build
- **Spec text.** §12.1: "Renderer parity | shared Mod-event fixtures render to identical bytes through the training path and the runtime path". §12.3: "Calibration | per-question ECE on dev through the runtime classifier's path". §1: "The runtime classifier ... is specified separately".
- **Evidence.** D36 designs the runtime while training runs. Phase 1 (§15) must clear renderer parity, but no runtime path exists then; if the renderer is one module, the test cannot fail. Either way the gate as written is not runnable in this track.
- **Consequence.** Phase 1 cannot clear its gate; the builder substitutes something.
- **Resolution.** One correct answer: restate as a golden-fixture deliverable (frozen bytes on N Mod-event fixtures the runtime must reproduce) plus the schema validator on converter output; the calibration gate runs through `kev.serve` with the per-question transform applied.

### F12 · Part 1 · error · Long-context gate items cannot be built as described under the state format
- **Spec text.** §7.9: "8K, 16K and 32K renderings of the same records with identical labels, plus start, middle and end placements of the deciding instruction". §6.4: "USER INSTRUCTIONS ... first".
- **Evidence.** USER INSTRUCTIONS always open the state and LATEST EVENT always closes it, so an "end placement" of a user instruction is impossible; the only format-consistent reading is position within the padded stable block (documents). How a monitor record is rendered at three lengths with identical labels (pad documents? ledger?) is not stated.
- **Consequence.** The gate that sets the validated length has no buildable item construction.
- **Resolution.** One correct answer given §6.4 (pad PROJECT DOCUMENTS with unrelated documents; place the deciding sentence within the stable block), but it must be written.

### F13 · Part 1 · error · Lift test: baseline calibration is a no-op at the decision threshold; held-out conversions are missing
- **Spec text.** §12.4: "Baseline: stock Kev-4B with its temperature refitted on the same dev split. Endpoint: on the 200 intent-probe items and on TRACE, tuned minus stock accuracy has a paired 95% lower bound above 0."
- **Evidence.** Temperature scaling is monotone and preserves the sign of the logit, so a T-only refit does not change accuracy at p ≥ 0.5; the baseline is raw stock. D3 reports stock's probe answers are "dominated by a fixed yes/no lean" (94% yes-rate), so whether stock also receives a prior offset decides the lift. Separately, TRACE, MALT, LLMBar and RewardBench 2 have no converter rows in §7.3 ("Source converter (one per source, section 7.3)"), no cut rule, no question mapping and no accuracy threshold; the probe items' wordings (report 31) are not said to be re-asked in §4.2 wordings.
- **Consequence.** The headline "measured lift" is either unfair to one side or unbuildable.
- **Resolution.** Decisions (measurement regime): fit (T, b) for stock too, or use a threshold-free metric; add held-out converter/mapping rows.

### F14 · Part 1 · overreach · Matched negative cuts remove less than claimed
- **Spec text.** §7.2: "negatives' mix of event types ... and relative run position (k / run length, in deciles) matches that harness's positives." D43: "Matched cuts remove event position and type as a cue".
- **Evidence.** Matching two marginals does not match the joint; absolute position k is visible in the state (E-numbers, one-liner count) and is not matched since clean runs differ in length; per-harness base rates still differ. The surface-feature baseline (§12.3) catches the residue, which is the right instrument.
- **Consequence.** The claim is stronger than the mechanism; harmless because instrumented.
- **Resolution.** One correct answer: soften the claim to "relative position and type marginals, per harness".

### F15 · Part 1 · overreach · "Natural prevalence" dev is pool prevalence, so b_q transports to the pool, not to deployment
- **Spec text.** §1: "b_q is the closed-form prior shift between the post-balance training label rate and the natural rate". §7.9: "Dev. 10% of groups at natural prevalence".
- **Evidence.** Dev is built by the same converters from hack-enriched sources; its prevalence is the uncapped pool's, not a Claude Code session's. The runtime threshold step (D25, out of scope here) does the deployment adaptation.
- **Consequence.** The ECE gate and the invariant's wording overstate what calibration delivers.
- **Resolution.** One correct answer: rename to pool prevalence and say the runtime sets deployment thresholds.

### F16 · Part 1 · error · Arithmetic and formula mismatches
- §7.1: "N_replay = 3,000 | ρ_replay · N with ρ_replay = 0.25" — 0.25 × 12,200 = 3,050; 3,000 is the sum of the three replay sources (2,000 + 500 + 500). One correct answer: state N_replay as that sum (ρ ≈ 0.246). The rest of §7.1 checks: Σ n^plan = 1,750 + 870 + 1,500 + 850 + 1,750 + 1,750 + 660 + 1,500 = 10,630; s = 8,600/10,630 = 0.809. S = ⌈12,200/16⌉ = 763. f_note = 4 × 7/644 = 0.0435 → 530.
- §7.9: "about 60 positives at AUROC 0.8" — Hanley–McNeil at A = 0.8 gives Q1 = 0.667, Q2 = 0.711; SE ≤ 0.05 needs n_p ≈ 29 with many negatives, ≈ 40 at n_p = n_n. Sixty is conservative but is not what the stated formula yields; a builder following "min n" stops at 30–40. One correct answer: state the floor as a number or fix the illustration.
- §9.1 "S ≈ 763" ignores `--p_none_pair 0.25` (D33: "none-pair repeats"); if the trainer adds none-pair passes, S and run time rise by up to ~25%. Unsupported until the external pass confirms the trainer's semantics.

### F17 · Part 1 · error · Gates without a quantified endpoint or with an inexecutable fallback
- §12.2 "Positive floor | every question has its planned positive rows": no per-question positive plan exists in the spec (§7.3 plans records per source, not positive rows per question; M8/SCR/D-questions have none). Decision needed.
- §12.2 "Run yield | each agent-run source's positive rate reported ... low yield moves its share": "low" undefined. Decision.
- §12.2 "Teacher agreement ≥ 0.70": agreement with a three-valued vote is undefined (is yes/can't-tell agreement?). One answer must be stated.
- §1 family 2 / §12.3 seam gap: "its constructions down-weighted" cannot be executed after the single run; the data is frozen and there is one shot. Unneeded mechanism in this form: keep the flag, delete the down-weight clause (or say it applies to a future run).
- §12.3 seam gap and §12.4 "unedited real runs": L2 and G4 positives come only from constructions in §7.3; unedited-real positives can only arise from full-set teacher labelling of natural runs, in uncontrolled numbers. The spec should say what happens when the real side has too few positives.
- §13 "Saying yes everywhere | per-question yes-rate on benign dev": instrument with no trigger or gate (an orphan instrument).
- §12.3 Retention: metric unnamed ("tuned minus stock"); Kev's 3-point rule implies accuracy. State it.

### F18 · Part 1 · error · Smaller format gaps in the shared renderer and record schema
- §6.4 EFFORT "appears only when the user stated priorities or an order": no operational rule for detecting that (construction-only? a pattern? the teacher?). The renderer is shared, so it changes bytes. Decision.
- §4.2 RF: "wrapped in ⟦ ⟧, with up to two neighbouring sentences": the RF record's state form (full state with the marker vs a sentence window) is not stated. Decision.
- §6.3 example `"target": {"false": 0.75, "true": 0.25}` vs §8.3 scalar mean; §6.4 `[I1]` numbering vs CONTRACT `new_items[].id` ("I3"): say whether ids are reused or renumbered.
- §7.4: Goal splice and Priority give no cut index (Omission and Composite do). One answer each must be stated (last continuation event; first event the ≥ 5/0 condition holds).
- §7.5/§12.3 "note pairs whose problem is visible from actions": population undefined; the natural answer (no-note twin's target ∈ {0, 1}) should be written.
- §7.8 can leave a record with zero question rows (~0.7^11 ≈ 2% of benign records); say they are dropped.
- §6.5: G5 has a correction but no position in the item order (D26 also omits it). Small decision.
- §9.2.3 `build_long_states.py` appears without a stated role in this pipeline.

### Verified claims (no finding)
Bounded regression (§1, §9.4) derives correctly: kept set ⊇ {c : s_c ≥ s_best − SE}, stock ∈ candidates ⇒ s_sel ≥ s_stock − SE, on dev. §9.3's "about 21 candidates" = 10 saves × 2 α + stock. §7.8 "a dropped row costs no teacher call" holds (labelling is per record). §8.3 choice/score mapping and the Sol tie are well-defined. §4.2 wordings match D38 verbatim. §6.5 order matches D26. §12.1 identity/resume/kernel gates are quantified, can fail and have fallbacks (identity's fallback is a block, acceptable).

---

## Part 2: Cost audit

| Claim | Verdict | Why |
|---|---|---|
| Training run 2–2.5 h, band 1.5–4 h (§9.1, §11) | **Soften** | The spec states no token basis. Re-derived: ~1,220 long records × ~24K + ~10,980 × ~4–5K ≈ 75–85M state tokens plus ~18M question tokens; at 4B parameters, LoRA with checkpointing, ~25–35% MFU on an H100 gives ~2–3.5 h. 2–2.5 h is defensible only at the short-record average being ~4–5K tokens and the none-pair repeats adding little; 1.5 h is optimistic. The smoke run is the right instrument and the spec names it (Q2). |
| Run cost ~$10–13, band $6–20 | **Defend** | At $3.95/h, 2.5–4 h plus ~45 min of smoke, resume-parity (two same-seed N-step runs plus one killed/resumed) and pass-cap trials lands at $12–19. |
| Selection, calibration and eval time (§10 cut-off formula) | **Challenge: unpriced** | 21 candidates × ~1,300 dev records × ~5K tokens ≈ 137M prefill tokens, plus the long-gate items at three lengths; roughly 1–1.5 h of H100 inference. It appears in the cut-off formula but nowhere in §11. It binds the latest training start. |
| Teacher volume 18,000–20,000 votes (§11) | **Defend within band** | 8,800 task+screen records + ~1,300 dev + dev top-ups (300–600) + construction retries → ~10,500–11,000 items → 21,000–22,000 votes; inside ±30%. Note the line counts item-votes, not API calls (~1,400 batched calls at 15 records). |
| Teacher wall-clock 1–2 h at 10–20 parallel subagents (§11) | **Challenge** | A 10–20-record batch carries 50–100K+ input tokens (states up to 32K, raw reasoning) and ~150–300 structured answers; 2–5 min per call is realistic. ~1,400 calls at 15 parallel × 3 min ≈ 4.7 h; 1–2 h needs ~40 parallel or sub-2-minute calls. "Settled by the first labelled batch" is the right instrument; the point estimate should move to 2.5–5 h or the parallelism to match. |
| Generation and agent runs $25–70, cap $200 (§11, §8.7) | **Challenge** | No token basis is given. ~3,500 generations at ~15K input tokens ≈ 50M tokens; ~300 headless agentic Claude Code runs at typical multi-turn session sizes plausibly consume 100M+ tokens. Using the historical per-token order of magnitude for the Haiku/Sonnet classes (unverified for 5.5; check the current price list), the agent runs alone likely exceed $70. The honest estimate is "the $200 cap binds"; the per-job spend log is the right control, and the spec already closes a stage with what it has. |

**Feasibility note (not a cut recommendation).** From 21:12 EST, the formula in §10 puts the latest training start near 02:30 (07:00 − 2.5 h run − ~1.5 h selection/eval − 0.5 h margin). That leaves ~5 h for ~41 converters, 9 constructions, ~3,500 generations, ~300 agent runs and 2.5–5 h of labelling. The spec's own stage cut-offs and the 07:00 pick make this survivable, but the cost section should say the data stage will probably close short.

---

## Part 3: Completeness against the ledger

| ID | Ledger entry (verbatim) | Where the spec should carry it | Status |
|---|---|---|---|
| O1 | D27: "Dev and held-out sets use the real rate; instrument: on action-visible pairs the accuracy gap between the two copies stays near 0." | §7.5 or §7.9 | **Omission.** §7.5 fixes f_note for "records" without exempting dev; the note-crutch gate implies dev note pairs exist but never states dev's note rate is r, not 4r. |
| O2 | D33: "Native flags: ... none-pair repeats capped at 2K states, no anchoring." | §9.1 command | **Omission (low).** No anchoring setting appears; if the trainer defaults anchoring on, the run differs from the decision. Needs the external pass to say what the flag is. |
| O3 | D41: "Kev's release settings carried over: head LR equal to the LoRA LR" | §9.1 | **Omission.** No head-LR flag; and it confirms the head is trained (see F1). |
| O4 | D28: "Terminal Wrench ~250 (red-team prompt stripped, down-weighted)" | §7.3 terminal-wrench row | **Possible omission (low).** The row strips the red-team block but carries no down-weighting; the ledger term is itself ambiguous (weight vs quota). Confirm intent. |
| O5 | D41: "In padded long records, the relevant document sits at a uniformly drawn position." | §7.3 QuALITY row | **Omission (low).** Stated for long_policy only; QuALITY says "padded ... with 2–4 other articles" with no position rule. |
| O6 | D18 long-context gate: "measured on held-out monitor records rendered at 8K, 16K and 32K" | §7.9 | **Divergence, not omission.** The spec places the paired items in dev. Defensible (the gate sets a length, not a selection), but it departs from the ledger silently. |

Checked and carried (no finding): D13 pick rule and held-out-once; D19/D38 wordings; D19.P screen form, section unit and M8 placement (§6.6, §7.4); D20 RF marker (§4.2); D21 cut points (§6.1, §7.2); D22/D23/D40 formats (§6.4, §6.5); D27 recipe, pairs, rewrites, cap, steps, pick rule, α set, T ≥ 1 clamp, twin-only-in-training; D28 composition, per-objective sources, exclusions, agent runs, $200 cap, env secret; D30 instructions, vote form, preference sources, source-vs-teacher rule, mismatch rule, priority band, batch size, Haiku/Sonnet half-each; D32/D32.P probe manifest held out; D33 host, flags, Unsloth gate, saves, true resume; D37 grouping, dev floor, held-out list, lift; D41 forced mechanics (seed, suite/replay path, demo repo exclusion, redistribution rule, k = 4, 1,000 bootstrap resamples, pick-before-calibrate, KEV_TEMPERATURE=1); D42 guarantees and four bounds; D43 components, side record, record schema, negative cuts; D44 gates; D45 build values (all twelve present). The trace document's mapping is accurate for every row I checked.

---

## Part 4: Spec/task boundary

| ID | Spec text | Disposition |
|---|---|---|
| T1 | §10 row "Stage cut-offs \| latest training start = 07:00 − measured run time − selection, calibration and eval time − 30 min; labelling and agent-run cut-offs precede it" | Task material (scheduling). Move to task.md; keep in the spec only the dependency order (§15 table). |
| T2 | §15 last paragraph: "Every stage of phases 2–5 has a cut-off time computed backward from 07:00 EST (section 10); past its cut-off a stage closes with what it has." | Task material. |
| T3 | §9.4: "The same rule picks the demo model at the 07:00 cut-off from whatever candidates exist then." | Split: "the rule applies to any partial candidate set" is spec; the 07:00 clock is task. |
| T4 | §13 row "Overnight time overrun \| stage cut-offs \| resume; saves; the 07:00 pick" | Process risk → task.md. |
| T5 | §8.3: "subagent thinking level is medium for labelling and low or none for mechanical checks" | Execution choreography → task.md. (The 10–20-record batch size is a data-quality value, D45; keep.) |
| T6 | §7.3 preamble: "downloads land in their own empty directory, are read only with `python -I`" | Execution hygiene → AGENTS.md/task.md. Keep the sandboxed-checker rule, which shapes what is built. |
| T7 | §8.7: "The API key comes from an environment secret, never a file in the repository." | Standing law → AGENTS.md. The $200 cap stays (it bounds data volume). |
| T8 | §0 front matter: "Status: Implementation-ready (pending adversarial review)" | Process status in a product artifact; the template admits only Draft / Implementation-ready / Frozen. |

Nothing in Parts 1–3 above is reported as missing when it belongs in the task file; session recovery, run order, relaunch-on-failure (D33) and the executor identity (D39) are correctly absent from the spec.

---

## Three most likely failure points, by expected impact

1. **F1 (identity parity fails for every save).** If the head is trained and α scales only the LoRA, the first correctness gate blocks all candidate scoring and the 07:00 pick degrades to stock, erasing the measured-lift deliverable. High likelihood, one-line fix.
2. **Schedule: labelling wall-clock (2.5–5 h, not 1–2 h) plus the unpriced ~1–1.5 h selection pass.** The chain closes short or training starts past the latest start; the demo runs on an early save. The stage cut-offs contain it, but the cost model should carry both numbers so the cut-offs are computed from real inputs.
3. **F13 plus F3/F4/F5 (measurement regime and label integrity).** A baseline whose refit cannot move accuracy, held-out sets with no conversion rule, ties labelled yes, pair negatives dropped by the cap and rewrite copies with stale M5 labels together make the one shot both noisier than designed and harder to adjudicate.

## Verdict

**Not implementation-ready as written.** The architecture, question set, sources, recipe and gate structure are complete and the arithmetic largely checks out, but an agent reading only this document would stop or guess at the following. Each is a question the builder cannot answer alone; "one answer" items are where the spec must state the obvious fix, "decision" items need the owner.

Blocking (one correct answer, must be written): F1 (head in Δ, scaled by α, or frozen: state it), F2 (σ(z/T + b)), F6 (teacher wins over constructions), F7c/d (drop oldest one-liners; cap applies to LATEST EVENT), F11 (golden-fixture form of renderer parity; calibration through `kev.serve`), F12 (long-gate item construction within the stable block).

Blocking (decision required): F3 (tie → no vs exclude), F4 (pair rows exempt from the cap), F5 (M5 rows on rewrite copies), F7a/b (overflow referent; K floor), F8 (exit-code source; PowerShell normalization; `todos` shape with Noah), F9 (correction placement with Noah; initial L7 status token; constructed p value), F10 (natural L7 source rendering), F13 (stock baseline gets T only or T+b; held-out conversions and metric), F17 positive-floor endpoint, F18 EFFORT trigger rule and RF state form.

Non-blocking, fix in place: F14, F15, F16, remaining F17 and F18 items, O1–O6, T1–T8.