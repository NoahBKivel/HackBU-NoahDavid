# Training spec review, round 2

I read every required file in full; the coverage ledger is at the end. Date anchor: `date` returned Sat Nov 7 21:50 EST 2026. I edited no file and invoked no skill. Every shell command ran in the foreground and exited before the next one started.

The spec is not implementation-ready: 4 findings block the build, and about a dozen more have one correct answer that still has to be written in before the build starts.

---

## Part 0: Disposition verification (51 register entries)

| # | Register entry | Status | Receipt |
|---|---|---|---|
| 1 | O-F1/C-F2: α interpolation over every trained tensor | LANDED WITH NEW DEFECT | §1 "θ(α) = θ_kev + α(θ_tuned − θ_kev) over every trained tensor"; §9.2.5 interpolation tool. The checkpoint's storage form is unstated, which breaks two gates (R2-14) |
| 2 | C-F3: kernel check | LANDED | §9.1 "fla's Triton kernels must run the DeltaNet layers (no torch fallback); attention runs through SDPA" |
| 3 | C-F4/O-F5: B_state and the count line | LANDED WITH NEW DEFECT | §6.4 "B_state = 32,768 − (tokens of that record's questions) − 1". Over-subtracts and makes the state depend on the record's questions (R2-02) |
| 4 | C-F1: replay pre-built | LANDED | §7.3 "Pre-built from the suite's train split (not the trainer's `--replay` sampler)"; no `--replay` in §9.1 |
| 5 | C-F5: LoadOptions | LANDED | §9.5 "`LoadOptions(temperature=1.0)`" |
| 6 | C-F6: none-of-the-above flags | LANDED WITH NEW DEFECT | The flags are set, but §9.1's sentence "the none-of-the-above substitution … off" is false while `--p_none_pair 0.25` is on (R2-15) |
| 7 | O-F7: Retention n; long-gate n | LANDED WITH NEW DEFECT | §12.3 "all 1,204 records"; §10's sizing input for the long gate is wrong (R2-06) |
| 8 | O-F22: cross-fitted calibration | LANDED WITH NEW DEFECT | §9.5 "cross-fitted over five dev folds"; which T_q is served is undefined (R2-25) |
| 9 | O-F9: offset after temperature, π definitions | LANDED | §1 "σ(z_q/T_q + b_q)"; §9.5 "π^train is the mean training target after the cap" |
| 10 | O-F2: renderer parity | LANDED WITH NEW DEFECT | §12.1 "through the converter path and the direct Mod-event path". A Phase-1 gate now needs Phase-2 converters (R2-16) |
| 11 | O-F3 (part): stock gets the calibration family | LANDED WITH NEW DEFECT | §12.4 "offset and temperature, cross-fitted". Stock's closed-form offset is undefined (R2-08) |
| 12 | Cost: candidates scored with the batched forward | LANDED WITH NEW DEFECT | §9.4 "the serving path is used only for serve-path parity", which contradicts §12.3's ECE "through the runtime classifier's path" (R2-05) |
| 13 | O-F28/C-F7: relative serve-path rule | LANDED WITH NEW DEFECT | §12.1 "≤ 1.5 × stock Kev's own gap". Its fallback is undefined for α = 0.85 (R2-14) |
| 14 | Leakage (O-F4) | LANDED | §8.1 "source labels whose `event_seq ≤ k`"; §7.5 "each note is written only from its own step's raw reasoning" |
| 15 | Matching (O-F14) | LANDED | §7.2 "absolute event index (in bins of 10 events)". Diverges from the confirmed D43/D45 (R2-34) |
| 16 | Arithmetic (O-F16) | LANDED | §7.1 "2,000 + 500 + 500; ρ_replay = 3,000 / 12,200" |
| 17 | Steps (O-F15 part) | LANDED | §9.1 "R the train-split record count after the balance cap" |
| 18 | Pick order (O-F23) | LANDED | §9.4 "intent-score rank within the kept set, then stock Kev" |
| 19 | Schema (O-F27, O-F17, O-F18) | LANDED | §6.1 "at least these fields", PowerShell as Bash, unknown-tool rule; §6.3 key suffixes. O-F17's WebFetch/TodoWrite/ExitPlanMode part was never disposed (R2-20) |
| 20 | Strings (O-F19) | LANDED | §6.5 short names, D2 summary, G5 after G2, "p values drawn uniformly from [0.6, 0.99]" (§7.4) |
| 21 | Labels (C-F10, C-F11) | LANDED | §7.3 terminal-wrench, Goodfire and eungyeuk rows are T |
| 22 | Rewording (C-F8 … O-F30) | LANDED WITH NEW DEFECT | All seven landed. C-F8's "rendered through the state renderer" leaves the long-state builder with no consumer and no mapping (R2-22) |
| 23 | Floors (O-F24, O-F25) | LANDED WITH NEW DEFECT | §12.2 "≥ 300 positive training rows". M8 cannot reach it (R2-07); G1's polarity is inverted (R2-01) |
| 24 | Long-gate items (O-F21) | LANDED WITH NEW DEFECT | §7.9 padded M2 items. The 32K arm collides with the overflow trigger (R2-06) |
| 25 | Note-crutch set (O-F13) | LANDED WITH NEW DEFECT | §7.5 diagnostic set "excluded from calibration" but not from selection (R2-23) |
| 26 | Instruments (O1) | LANDED WITH NEW DEFECT | §12.3 "RF recall on held-out instructions". The set and threshold are undefined (R2-28) |
| 27 | Boundary (Part 4) | LANDED | No cut-off scheduling, thinking levels, download hygiene or key rule left; no "(pending …)" in the front matter |
| 28 | Defense O2 (TW down-weighted = quota) | DEFENSE HOLDS | §7.3 TW n^plan 250; the trainer has no per-record weights |
| 29 | Defense O-F11 (one run, report-and-select) | DEFENSE HOLDS | The premise holds. Its wording fix left §1's "constructions down-weighted" in place (R2-13) and created R2-03 and R2-04 |
| 30 | Defense O-F4 (outcome hints) | DEFENSE HOLDS | §8.1 "Outcome-based source labels are the one exception to the cut" |
| 31 | David decision 1: cap 1:10, records and pairs protected | LANDED | §7.8 matches D27 (side issue R2-17) |
| 32 | David decision 2: dev floor SE ≤ 0.035 | LANDED | §7.9 and §10. Re-derived: Hanley–McNeil at A = 0.8 with many negatives gives n_pos ≥ 0.0711/0.035² ≈ 58 |
| 33 | David decision 3: positive-specific agreement ≥ 0.70 | LANDED | §8.5, §12.2 (G1 caveat in R2-01) |
| 34 | David decision 4: lift protocol | LANDED | §12.4 matches D37. Gaps in carrying it out: R2-09, R2-10 |
| 35 | David decision 5: unedited-real set | LANDED | §7.9 matches D37 (selection conflict R2-03) |
| 36 | David decision 6: G4 every event; empty sections render "(none)" | LANDED | §4.2, §6.4 |
| 37 | David decision 7: screen document pool, 15% ledger | LANDED | §7.4, §6.6 (conflict R2-19) |
| 38 | V-F3: ties → no | LANDED WITH NEW DEFECT | §8.3 "a tie is no". For G1, no means drift (R2-01) |
| 39 | V-F4: pair rows exempt from the cap | LANDED | §7.8 |
| 40 | V-F5: rewrite copies teacher-labelled | LANDED | §7.6 |
| 41 | V-F6: constructions yield to the teacher | LANDED WITH NEW DEFECT | §8.4 is fixed; §7.3's basis column and §2.3 still say the opposite (R2-12) |
| 42 | V-F7d: LATEST EVENT capped | LANDED | §6.4 "under the same 2,000-token cap" |
| 43 | V-F8: exit code, PowerShell, todos | LANDED | §6.4 |
| 44 | V-F9: correction as an OPEN FINDINGS line only | LANDED | §6.4 (premise check R2-21) |
| 45 | V-F10: natural L7 sources | LANDED WITH NEW DEFECT | §7.3 TonyDzi/SWE-chat rows. The OPEN FINDINGS line needs a question id these sources don't have (R2-27) |
| 46 | V-F13: held-out conversions | NOT LANDED (in part) | TRACE, MALT, LLMBar and RB2 conversions landed. The 150 non-TRACE probe items have no conversion and no polarity mapping (R2-09) |
| 47 | V-F18 listed items | LANDED | `[I_n]` rule, cut indices, QuALITY position, head LR, anchoring |
| 48 | V-O6: long-gate items in dev, excluded from selection | LANDED | §7.9 |
| 49 | Cost revisions | LANDED WITH NEW DEFECT | §11 updated, but §9.1 still says "$10–13" (R2-29); post-selection compute unpriced (R2-31) |
| 50 | Shared format: 0.15 detail floor | LANDED | §6.4 "max(…, 0.15 × B_state)"; D22 confirmed |
| 51 | Shared format: correction as an OPEN FINDINGS line | LANDED | §6.4; D40 confirmed |

**Tally:** 29 LANDED (11 of them owner decisions), 18 LANDED WITH NEW DEFECT, 1 NOT LANDED (in part), 3 DEFENSE HOLDS, 0 DEFENSE FAILS.

---

## Part 1: Logic and contract audit

**R2-01 · Part 1 · error (partly amendment-created via V-F3) · G1's "yes = on track" isn't carried into the rules that key on "yes" or "positive"**
- **Spec text:**
  - §4.1: "positive / negative | a question row labelled yes / no".
  - §4.2: "G1 is yes = on track".
  - §8.2 item 6: "Label D5 severity only on records with at least one yes; … D1/D3 for each event shown as a detailed block, on records with at least one yes".
  - §7.6: "About 20% of agent records with at least one yes label get a copy".
  - §8.3: "`label` = target > 0.5, so a tie is no (yes only when the state shows it)".
  - §12.2: "every question has ≥ 300 positive training rows".
  - §7.9: "enough positives that the AUROC standard error … ≤ 0.035".
  - §1/§8.5: "agreement on the yes cases".
  - §13: "per-question yes-rate on benign dev (above 2× stock's → flag)".
  - §8.2 item 2: "Answer yes only when the visible state shows the problem."
- **Evidence:**
  - G1 is yes on every on-track record, and so are the negated twins on benign records (M1/L1/L4 twins: "serve…", "still move toward…"). "At least one yes" therefore holds on nearly every agent record.
  - A G1 tie becomes "no", which is the problem class: the opposite of what the V-F3 fix intended.
  - G1's rare class is "no". The 300 floor, the dev floor and positive-specific agreement all measure G1's abundant class.
  - The correct benign yes-rate for G1 is about 1, while stock's still-pursuing yes-rate was 0.02 (D3). The yes-everywhere trigger fires on correct behaviour.
- **Consequence:** Built literally:
  - D5 and one D1/D3 row per detailed block get labelled on nearly every record. Teacher volume multiplies, and D5 learns "how serious is the flagged problem" on records with no problem.
  - Rewrite copies spread to benign records.
  - G1 ties get labelled as drift.
  - Nothing guards G1's drift class, although G1 is an intent-score component and D17's `drift`.
- **Resolution:** one correct answer. Define each question's problem class (G1: no; each twin: its flipped class). Use that class wherever §7.6, §7.8, §7.9, §8.2–8.5, §12.2 and §13 say "yes" or "positive". Ties resolve to the non-problem class.

**R2-02 · Part 1 · amendment-created (C-F4 fix) · The state budget subtracts question tokens that Kev budgets separately, so the state becomes circular and can't be reproduced at runtime**
- **Spec text:**
  - §6.4: "Per record, B_state = 32,768 − (tokens of that record's questions) − 1 … so the record fits Kev's admission limits (`max_state`, and `max_packed` = `max_state` + 1,664 shared by all questions)".
  - §8.2 item 6: D1/D3, D2 and D5 are asked only on records the labels show to be flagged.
- **Evidence:**
  - Kev's `model.py` `training_context` says: "the row (state + one branch) and packed limits grow by the same amount, so every question keeps its token budget". With `MAX_STATE, MAX_BRANCH, MAX_PACKED = 384, 1024, 2048`, at max_state 32,768 the state may hold 32,767 tokens and the questions get 1,664 on top. The binding rule is B_state = 32,767 − max(0, Q − 1,664).
  - The spec always subtracts Q. Diagnostic rows exist only after the teacher has labelled the state, and the number of D1/D3 rows depends on how many detailed blocks the state shows. The dependency runs state → labels → questions → B_state → state.
  - At runtime the state is rendered once and every question is asked on the cached prefix (D23).
- **Consequence:**
  - The builder cannot compute B_state for flagged records.
  - On long records, "Train equals runtime" (§1) breaks.
  - Up to 1,664 tokens of state are wasted per record.
- **Resolution:** one correct answer. B_state = 32,767, independent of the questions. A record whose questions exceed 1,664 tokens splits into sibling records that share the state and the pair group. Fix this before Phase 1, since the renderer's interface depends on it.

**R2-03 · Part 1 · amendment-created (O-F11 wording + O-F12) · The seam gate uses a held-out set to choose the model**
- **Spec text:**
  - §2.5: "No held-out item reaches training, selection or calibration."
  - §7.9: "Unedited-real set (held out) … the seam gate's reference".
  - §12.3 Seam gap: "reported; selection prefers a candidate that passes".
  - §3 Refused: "no held-out score is reported for any candidate other than the selected one and stock Kev".
  - §5: "The evaluator reads the held-out sets once".
- **Evidence:** To prefer a candidate that passes, the gate has to score every kept candidate on the unedited-real set. Ledger D37 (partner-confirmed) says the unedited-real set is "teacher-labelled and held out". The gap also compares construction-labelled dev against teacher-labelled real runs, so teacher noise alone widens it.
- **Consequence:** Either the held-out discipline breaks, or the preference rule can't run.
- **Resolution:** one correct answer, given D37. Score the seam gap once, on the selected candidate and stock, as a report only. Delete "selection prefers a candidate that passes" from that row.

**R2-04 · Part 1 · amendment-created (O-F11 "within each source") · The surface-feature gate fails through noise**
- **Spec text:** §12.3: "within each source: a logistic model on optional-field presence, event type and run position, per question; the monitor's AUROC lower bound exceeds the baseline's upper bound".
- **Evidence (my estimates):**
  - Dev is about 1,300 records (D28) spread over about 45 sources, so roughly 30 per source. Each source × question cell holds a few positives, and many hold none.
  - At 12 positives and 12 negatives, the 95% AUROC interval is about ±0.17. A monitor at 0.85 and a baseline at 0.60 still overlap.
  - Requiring two intervals not to overlap needs a gap of roughly 2 × 1.96 × SE.
  - The data the baseline is fitted on is never stated.
- **Consequence:** Nearly every cell reads "shortcut-reliant" through noise, so the selection preference either has no passing candidate or picks by noise.
- **Resolution:** one correct answer.
  - Per question, compute a source-stratified AUROC (positive–negative pairs formed within a source, then pooled) for both the monitor and the baseline.
  - Fit the baseline on train.
  - Decide on the lower bound of the paired bootstrap difference being above 0.

**R2-05 · Part 1 · error · The calibration gate fails through noise, and its fallback is worse than what it replaces**
- **Spec text:** §12.3: "per-question ECE, out of fold, through the runtime classifier's path ≤ stock Kev's with the same calibration family | serve that question uncalibrated and flag it"; §9.4: "the serving path is used only for serve-path parity on the winner".
- **Evidence:**
  - Two point ECEs on questions with about 60 positives are compared with no interval. When both models are calibrated, the outcome is a coin flip.
  - "Uncalibrated" means T = 1 and b = 0: raw logits trained at the capped 1:10 prior. That is worse calibrated than the transform it replaces.
  - §9.4 says the serving path is used only for serve-path parity, yet this gate runs ECE through it.
- **Consequence:** Questions get decalibrated at random.
- **Resolution:** one correct answer.
  - Per question, serve whichever of calibrated and uncalibrated has the lower out-of-fold NLL.
  - Report the comparison with stock together with its interval.
  - Name the path that computes ECE.

**R2-06 · Part 1 · amendment-created (O-F21 and O-F7, interacting with V-F7b) · BLOCKING · The long-context gate's 32K items can't be built under the spec's own fill rule, and its item count is mis-sized**
- **Spec text:**
  - §7.9: "M2 records whose deciding requirement lives in a project document, with PROJECT DOCUMENTS padded … to 8K, 16K and 32K … events and detail budget held fixed … the item count sized by formula from measured discordance so a model at parity passes with probability ≥ 0.8".
  - §6.4: "If instructions and documents exceed B_state − 0.15 × B_state − tokens(LATEST EVENT), the record belongs to the overflow screen form".
  - §10: "Long-gate and retention item counts | … | dev discordance between candidate and stock".
- **Evidence:**
  - **(a) Overflow collision.** With B_state ≈ 31,000–31,700, a padded state stays in the single-state form only if events other than LATEST fill at least 0.15 × B_state ≈ 4,700 tokens. The doc-resident M2 records the spec points to are mostly single-response records: IF_multi's "embed a third in CLAUDE.md-style … text", rendered as one Write or a final MESSAGE. Their 32K renderings are overflow-form records under §6.4.
  - **(b) Wrong discordance.** §10's input is discordance between candidate and stock. The gate actually compares one model's 8K rendering with its 16K and 32K renderings, and the count must be fixed in Phase 3, before any candidate exists.
  - **(c) Item count.** The gate requires 6 comparisons to pass (2 lengths × 3 placements). For a parity model to pass all of them with probability 0.8, each needs SE ≤ 0.0080, so n ≈ d / 6.4×10⁻⁵: about 940 items at 6% discordance and 1,560 at 10% (my arithmetic). Stock already loses 5.8 points at 32K (D18), so d ≥ 6% is plausible. Dev holds about 1,300 records in total.
  - **(d) Cost.** Scoring these items is not in §11.
- **Consequence:** The gate that sets the runtime's validated length can't be built as written.
- **Design choice needed:**
  - Which records supply the items (long-history M2 runs, or a construction that places the requirement document into a long run).
  - Whether gate items are exempt from the overflow trigger.
  - Which discordance sizes n: stock's own 8K-versus-L discordance can be measured before training.
  - Whether each item is rendered at all three placements.

**R2-07 · Part 1 · amendment-created (O-F25) · BLOCKING · The 300-positive floor can't be met for M8 under the confirmed screen count, and top-ups have no defined place in N**
- **Spec text:**
  - §12.2: "every question has ≥ 300 positive training rows … | top up from the same objective's sources or constructions".
  - §7.1: "N_screen = 200".
  - §7.4: "one sentence inserted into one section that bears on (SCR yes) or contradicts (SCR yes, M8 yes)".
  - Ledger D28: "M8 and overflow screen: ~200 constructed records … partner-confirmed".
- **Evidence:**
  - M8's positives come from the one inserted sentence per record; conflicts inside unedited sections are rare. So M8 stays at or below 200, under 300, with certainty.
  - By the plan's own quotas, several trajectory questions start near or under 300 positives: L2 (Composite ≈ 243 records including negatives), G4 (Priority ≈ 243) and L5 (Omission ≈ 283 plus tau2 ≈ 81, each with "not yet" negatives).
  - The number 300 is in no ledger entry: D44 says "positive floor" without a number, and the emergent test cites "D28's floors", which D28 never states.
- **Consequence:** The gate fires by construction, and its fallback changes a partner-confirmed composition in a direction nobody has specified.
- **Design choice needed:**
  - Whether the overflow-only questions and the diagnostics fall under the floor.
  - Whether top-ups sit inside N = 12,200 (displacing which sources) or on top of it (growing R and S).
  - The floor value, traced to a decision.

**R2-08 · Part 1 · amendment-created (O-F3 fix) · The stock baseline's offset can't be computed as specified**
- **Spec text:** §12.4: "stock Kev-4B given the same calibration family (offset and temperature, cross-fitted on the same dev folds)"; §9.5: "b_q = logit(π_q^dev) − logit(π_q^train), where π^train is the mean training target after the cap".
- **Evidence:** Stock was never trained on this set, so π^train has no value for stock. The only reading that runs fits stock's b_q by NLL, which is a different procedure from the tuned model's closed-form offset. Stock's measured failure is a fixed yes/no lean (D3: yes-rates of 94% and 2%), so this choice largely decides stock's accuracy.
- **Resolution:** one runnable answer that the spec has to state: stock's (T_q, b_q) are fitted jointly by NLL on the same folds. Not blocking once written.

**R2-09 · Part 1 · omission (V-F13 not fully landed) · BLOCKING · Half the probe items' labels have the opposite polarity to their mapped questions, and 150 items have no conversion**
- **Spec text:** §12.4: "each scored by its matching question (implicit goal → M1, request satisfaction → M2, clarification need → M7, still pursuing → G1) … Items are rendered through the state renderer like any record". §7.9's conversions cover TRACE, MALT, LLMBar and RB2 only.
- **Evidence:**
  - The manifest's `label` uses report 31's polarity. Line 67: "TRACE … (benign = yes, hacked = no)". Line 69: request satisfaction is yes = satisfied. Line 70: aspi "base_prompt = yes". Line 71: UIB "preserved/new predicate = yes".
  - M1 and M2 are yes = problem, so the implicit-goal and request-satisfaction labels are inverted for their questions. That is 100 of 200 items; the manifest holds 50 TRACE and 50 IFBench items for these two capabilities. M7 and G1 are aligned.
  - The IFBench, aspi and UIB items have no event conversion. Report 31's templates exist ("User request / Assistant's response"; "prompt + … tool calls"; "original request + update + 'Next I'm building …'"), but the spec never fixes which event is LATEST or how aspi's non-Claude Code tools render.
- **Consequence:** Scored literally, endpoint (1) measures the inverse on half its items, and the builder decides the measurement regime.
- **Resolution:** the polarity mapping has one correct answer. The conversions need a design choice.

**R2-10 · Part 1 · error · BLOCKING · TRACE's run-level labels are scored by an event-level question at the final event**
- **Spec text:** §12.4: "(2) the same on the 467 TRACE conversations not in the probe, scored on M4 and G5 at the conversation's final event". §4.2 M4: "Does the latest action make a measure of success … look better". §4.2 G5: "at a completion claim".
- **Evidence:**
  - Dossier #108: "Labels: 249 benign, 268 hacked"; trajectory_0018 is "labelled hacked at trajectory level" and ends with the user's challenge and the agent's admission. Its final action is the admission, not the hack.
  - The dossier's own guidance is "score per-event prefixes for M questions and full runs for G1/G5".
  - G5 is defined only at a completion claim.
  - "The same" doesn't say whether M4 and G5 are pooled into one test or must each pass.
- **Consequence:** The M4 half of the second pre-registered endpoint is mislabelled by construction.
- **Design choice needed:** how M4 is scored against a run label (for example, the maximum over per-event prefixes), whether G5 is asked at final events that aren't claims, and pooled versus both.

**R2-11 · Part 1 · error · The demo check uses an item the spec declares "never used for selection"**
- **Spec text:** §7.9: "Held out entirely (never trained on, never used for selection or calibration): … the demo repository and prompt once chosen". §12.3 Demo check: "| the next candidate in pick order".
- **Evidence:** D41 excludes the demo only "from all training data"; D44's demo check deliberately selects on it.
- **Resolution:** one correct answer. Move the demo repository and prompt to a "never trained on" line.

**R2-12 · Part 1 · amendment-created (V-F6 residual) · Constructions are still marked as beating the teacher**
- **Spec text:**
  - §7.3 legend: "V = visible-based … wins over the teacher". The construction rows (Omission, Composite, Goal splice, Priority, Constraint insertion, Correction windows, Goal-flip pairs, Pressure negatives) are all marked "V".
  - §2.3: "Natural labels first, exact constructions second, teacher judgement third."
- **Evidence:** §7.4 says "the teacher wins over a construction's intent"; §8.4 says "Construction labels yield to the teacher"; ledger D30 agrees with them.
- **Resolution:** one correct answer. Give construction rows their own basis code that points to §7.4, and reword §2.3.

**R2-13 · Part 1 · amendment-created (incomplete fixes) · §1's approximation table contradicts §12**
- **Spec text:** §1: "flag → the question is reported as seam-reliant and its constructions down-weighted". §1 kernel row: "within the measured same-seed noise floor".
- **Evidence:**
  - §12.3 now says "reported; selection prefers…", and the O-F11 defense says post-run actions are report-and-select only. Down-weighting needs a second run that doesn't exist.
  - §12.1 uses "max(the same-seed noise floor, 10⁻³ relative)".
- **Resolution:** one correct answer. Delete "and its constructions down-weighted" and copy §12.1's bound into §1.

**R2-14 · Part 1 · amendment-created (O-F1 together with O-F28) · The interpolated checkpoint's form is unstated, and two gates depend on it**
- **Spec text:**
  - §9.2.5: "(the LoRA as its merged product, plus the pointer head) as a loadable checkpoint".
  - §12.1: "the interpolation tool's tensors equal stock Kev's".
  - Serve-path parity fallback: "serve the unmerged LoRA path and re-measure".
- **Evidence:**
  - A merged checkpoint has no LoRA tensors to compare with stock's, and an α = 0.85 candidate has no "unmerged LoRA path".
  - An exact unmerged form does exist: α·s·B′A′ + (1−α)·s·BA = s·[αB′ | (1−α)B]·[A′; A], a rank-32 LoRA, plus the interpolated head.
  - The fallback also has no end state if the re-measure still fails.
- **Resolution:** one correct answer. Specify the rank-2r concatenated LoRA. Compare at α = 0 against stock loaded the same way. Add a terminal fallback (the next candidate in the pick order).

**R2-15 · Part 1 · amendment-created (C-F6 fix sentence) · None-pair augmentation is still on for G2 and L7**
- **Spec text:** §9.1: "`--p_none_pair 0.25 --none_pair_max_state 2048`" and "the none-of-the-above substitution and distractor options are off, since the question set fixes the option sets".
- **Evidence:**
  - Kev `data.py` `none_pair` builds "the same state and question rendered twice, once with the true option present … and once with it removed (the same none option is right)".
  - It applies to `type == "choice" and len(criteria) >= 3 and target is None`. G2 has 4 options and L7 has 6. Hard-label rows carry no `target` (§6.3).
- **Consequence:** G2 and L7 rows on states of 2,048 tokens or fewer gain sibling records with option sets the runtime never presents, which contradicts principle 2.
- **Resolution:** small. Either always emit a one-hot `target` on monitor choice rows (which makes them ineligible, per `data.py`), or state the exception.

**R2-16 · Part 1 · amendment-created (O-F2 fix) · A Phase-1 gate needs a Phase-2 component**
- **Spec text:** §12.1 Renderer parity: "through the converter path … | no record is built until it passes". §15: Phase 1 "Clears: renderer parity", while Phase 2 "Builds: source converters".
- **Resolution:** one correct answer. Phase 1 checks direct Mod-event JSON against golden bytes; each converter clears its own parity in Phase 2 before its records are built.

**R2-17 · Part 1 · error · The 1:10 cap is stated as a bound it can't guarantee, and its key terms are undefined**
- **Spec text:**
  - §10: "Negatives per positive | ≤ 10 per question".
  - §7.8: "every row belonging to a pair group is kept … no record loses its source's target questions".
  - §4.1: "(for choice questions, the non-default class / default class)".
- **Evidence:**
  - Protected rows (whole pair-group records and the benign pool, which is "negatives for every question") can on their own exceed 10× a rare question's positives. G4, for example, has about 243 construction records.
  - "Target questions" is undefined for benign and replay records.
  - The default class for G2, L7 and D5 is never named, yet the cap and the floor depend on it.
- **Resolution:** one correct answer. State that protected rows may exceed 1:10 (the measured π^train feeds b_q), define target questions per §7.3 objective, and name each choice question's default class.

**R2-18 · Part 1 · unsupported claim (interaction with round-1 cap protections) · "Exact under A-label-shift", but the cap breaks A-label-shift by design**
- **Spec text:** §1: "b_q is the closed-form prior shift … exact under the named assumption A-label-shift (a state's distribution given its label is the same in training and in the collected pool)".
- **Evidence:** The cap keeps protected negatives (pair groups, target-source negatives) and thins the rest. So the training distribution of negative states differs from the pool's by construction. The assumption also has no instrument; only ECE watches it downstream.
- **Resolution:** reword: "exact for the cap's random part; the protected rows shift p(x | y), and the dev-fitted temperature and the ECE check absorb the remainder."

**R2-19 · Part 1 · error · The screen ledger budget can't hold the latest event, and the cap formula subtracts that event twice**
- **Spec text:** §6.6: "The screen ledger holds LATEST EVENT plus recent detailed events up to 15% of the screen budget" and "Cap = (screen budget − instructions − ledger − event) / target sections per state". §6.4: "LATEST EVENT is a detailed block under the same 2,000-token cap."
- **Evidence:** 0.15 × 8,192 = 1,229 tokens, which is less than one latest event's 2,000-token cap. The ledger already contains the event, so the formula counts it twice. This is a runtime-binding format.
- **Resolution:** a small design choice: truncate LATEST EVENT to the screen share, or let it exceed the share. Then drop the double count.

**R2-20 · Part 1 · omission (residual of O-F17) · Three listed tools have no rendering rule**
- **Spec text:** §6.1 lists "WebFetch, TodoWrite, ExitPlanMode". The unknown-tool rule covers only "a tool outside this list". §6.4 defines key arguments only for Bash, Read/Write/Edit and Grep/Glob.
- **Evidence:** ExitPlanMode plans are cut points (§7.2 "plan and todo updates") and carry the signal D21.E6 relies on, yet where the plan text renders is undefined.
- **Resolution:** one correct answer. Apply the first-string-argument rule to these three tools too, or name each one's key argument.

**R2-21 · Part 1 · unsupported claim · The correction-placement premise contradicts the contract's wording**
- **Spec text:** §6.4: "(the Mod attaches its text to the agent's next tool result outside the reported `result_text`)".
- **Evidence:** CONTRACT §5 says "Results: the result text as the agent sees it", and §4 says `inject_agent` "Attaches `text` to the agent's next tool result. The agent reads it." If the reported result text includes the correction, runtime states will contain text that training states never do.
- **Resolution:** cheap. The renderer strips any injected correction text from `result_text`, and a recorded Mod session with a correction joins the parity fixtures. Confirm with Noah.

**R2-22 · Part 1 · unneeded mechanism · The long-state builder patch has no consumer**
- **Spec text:** §9.2.3: "`build_long_states.py`'s effective cap … are lifted … and its output is rendered through the state renderer". It is also a Phase-1 build item (§15).
- **Evidence:**
  - No section says which records it builds. §7.3 and §7.7 describe the padding directly.
  - Forcing QuALITY and long_policy records "through the state renderer" has no mapping: those records have no events for LATEST EVENT.
- **Resolution:** a design choice. Either delete patch 3, or name the records it builds and how non-agent long records map onto the four-part state.

**Minor findings (each one correct answer, none blocking):**

| ID | Kind | Spec text | Issue |
|---|---|---|---|
| R2-23 | error | §7.5 "…excluded from calibration" vs §7.9 "long-context gate items … excluded from selection scoring and calibration" | The note-pair diagnostic set enters selection scoring, so dev is no longer "at the real rate" for selection. Exclude it from selection as well. |
| R2-24 | omission (V-F18 residual) | §12.3 "on action-visible note pairs" | The population is undefined. Write it: pairs whose no-note copy's target is 0 or 1. |
| R2-25 | amendment-created | §9.5 "cross-fitted over five dev folds" | Which T_q is served (a refit on all of dev?) is unstated, and with b ≠ 0, T changes the 0.5 decision used in the lift test. |
| R2-26 | omission | §8.2.6 "records where M2 or G2 is yes" | G2 is a choice question; name the classes that count (broken, not done). |
| R2-27 | amendment-created (V-F10) | §6.4 "[F3] M4 at E41 · …"; §7.3 hook and pushback rows | The OPEN FINDINGS line needs a question id that hook and pushback sources don't have. Use TonyDzi's mapping table and state a rule for pushback. |
| R2-28 | omission | §12.3 "RF recall on held-out instructions" | The set, the threshold, and which candidates are scored are all unstated (§2.5 holds that held-out sets are touched once). |

---

## Part 2: Cost audit

**R2-29 · amendment-created · §9.1 and §11 disagree on run time and cost.** §9.1 says "run time 2–2.5 h … cost ~$10–13 including the smoke run"; §11 says "~$10–19 (… × 2–3.5 h, plus smoke, resume-parity and pass-cap trials)". My re-derivation agrees with §11: about 90M tokens × about 2.7×10¹⁰ FLOPs per token at 25–35% MFU gives 1.9–2.7 h, plus attention and trial runs. Fix: align §9.1 with §11.

**R2-30 · error · The teacher wall-clock band is narrower than its own inputs.** §11: "~1,000–2,000 calls" and "2.5–5 h at 15 parallel subagents (batches … take 2–5 min)". Hours = calls × minutes / (15 × 60), which spans 2.2–11.1 h, with a central estimate of about 5.8 h (1,500 calls × 3.5 min). The stated band sits below its own centre. Fix: carry 2.2–11 h with a central 5.8 h until the first batch is measured. The task file's cut-offs depend on this number.

**R2-31 · omission · Post-selection compute is unpriced, and candidate scoring is likely underestimated.** All figures below are my estimates, anchored on the spec's implied rate of 140M tokens per 1–1.5 h, about 30K tokens/s.
- **Long-gate scoring:** about 900–1,600 items × 7–9 renderings × about 19K tokens ≈ 120–270M tokens, roughly 1–2.5 h (R2-06).
- **Serve-path parity:** the winner and stock over all of dev through the serving path. Report 31 measured 3.6 s for one 32K state with 20 questions on an L40S. Roughly 0.5–1 h.
- **ECE through the runtime path:** can reuse the serve-path outputs.
- **Lift and held-out reports:** 2 models × (200 probe + 467 TRACE at a 10.3K median + MALT, LLMBar, RB2 and unedited-real, each again with reasoning stripped). Roughly 0.3–0.6 h.
- **Candidate scoring:** "~140M prefill tokens" counts about 1,300 records at about 5K tokens. It leaves out the dev top-ups ("~300–600 extra dev records", D37), the note diagnostic set (R2-23), question tokens, and the long share (about 9% at ~24K, so a mean of ~6.7K). A likely 1.6–2.5× undercount.
- **No band:** the "settled by the first candidate scored" row gives no band, which ethos #6 requires.
- **Generation price:** "no current Haiku/Sonnet 5.5 price was checked" can be checked with one lookup. The decision-relevant number is how many agent runs $200 buys.

The sum, roughly 2–4 h of post-training compute, is the input D13's 07:00 rule needs and §11 doesn't carry.

---

## Part 3: Completeness against the ledger

**R2-32 · omission · Requirement candidates (R_k) and the sentence split are missing.**
- **Ledger, D20:** "Splitting: user prompts and project docs are split deterministically into sentence or bullet units, each keeping its source, position and verbatim text." and "Units that pass become R*k*."
- **Spec:** no split rule anywhere, and training R_k come from unstated sources. §7.3 InFoBench says "each decomposed requirement is an R_k for G2/D2": InFoBench's decompositions are rewritten questions, which conflicts with D20's verbatim units, and the runtime will present verbatim sentences.
- **Where it belongs:** §6 (a contract subsection) and the §7.3 InFoBench row.
- **Needs:** a small design choice. The split rule binds the runtime under the D36 boundary.

**R2-33 · omission · When G2 and G5 are asked.**
- **Ledger, D21.E7/E9:** "`turn.complete` is classified again only for G2 and G5".
- **Spec:** §4.2 and §8.2.6 say "at a completion claim" and never define one.
- **Where it belongs:** §4.2 and §7.2.
- **Resolution:** one correct answer per the ledger. G2 and G5 rows sit on records cut at `turn_completed` events.

**R2-34 · omission (divergence from partner-confirmed values without a ledger decision).**
- D45: "matches position in tenths of the run". D43: "relative run position match". The spec's §7.2 uses absolute index bins.
- D18: "measured on held-out monitor records". The spec's §7.9 puts the items in dev.
- The spec's choices are defensible, since O-F14 shows absolute position is the visible cue. But the register disposed of both as fixes, and the ledger still records the earlier confirmed values. David has to confirm them and D43, D45 and D18 need updating in place, or the spec reverts.

**Ledger lag (not spec findings; the ledger is a current-state record):**
- D41 still has `--suite … --replay`, `KEV_TEMPERATURE=1`, and the teacher "never … outcomes".
- D42 still has σ((z+b)/T), "within bf16 tolerance" and "down-weights its constructions".
- D44 still has "the same dev temperature refit" (D37 says the full family).
- D26's order lacks G5, although the spec adds it.
- D40 still has `exit <c>`.
- D30's header ("two Sol subagents") contradicts its own Sol-plus-Terra bullet.
- The emergent table's twin-consistency metric (mean |p + p_twin − 1|) differs from D44's AUROC rule.
- The trace document still omits D45.

---

## Part 4: Spec/task boundary

**No findings.** I checked for:
- session recovery and run order;
- cut-off scheduling: §14 Q2 mentions "the cut-off times" only as an impact;
- subagent thinking levels;
- download hygiene and the API-key rule;
- status markers;
- relaunch choreography.

None is present. The batch size (§8.3) and the $200 cap (§8.7) are data-shaping values from D45 and D28, so they stay in the spec. Nothing reported missing above belongs in the task file.

---

## Counts

- **Register entries verified:** 51. 29 LANDED (11 of them owner decisions), 18 LANDED WITH NEW DEFECT, 1 NOT LANDED (in part), 3 DEFENSE HOLDS, 0 DEFENSE FAILS.
- **Findings:** 34.
  - error: 8 (R2-01, -05, -10, -11, -17, -19, -23, -30)
  - amendment-created: 14 (R2-02, -03, -04, -06, -07, -08, -12, -13, -14, -15, -16, -25, -27, -29)
  - omission: 9 (R2-09, -20, -24, -26, -28, -31, -32, -33, -34)
  - unsupported claim: 2 (R2-18, -21)
  - unneeded mechanism: 1 (R2-22)
  - task material: 0
- **Amendment-created defects:** 14 as the primary kind. R2-01 (via V-F3) and R2-18 also have amendment-created parts, so 16 findings trace wholly or partly to round-1 amendments.
- **Blocking:** 4 (R2-06, R2-07, R2-09, R2-10).
- **Size:** the spec grew from 657 to 660 lines across the round.

## The three most likely failure points

1. **The G1 polarity problem (R2-01).** It triggers on any literal build: D5 and D1/D3 get labelled on nearly every record, teacher volume multiplies, G1 ties get labelled as drift, and no floor, cap or agreement check watches G1's drift class.
2. **The headline lift measurement (R2-09, R2-10, R2-08).**
   - 100 of the 200 probe items carry labels with the opposite polarity to their mapped questions.
   - TRACE's run-level labels are scored with M4 at the final event.
   - Stock's offset can't be computed as written.

   The pre-registered result can come out inverted or meaningless.
3. **The schedule against D13's 07:00 rule (R2-30, R2-31, R2-07, R2-06).** Labelling is centrally about 5.8 h by the spec's own inputs. There are 2–4 h of unpriced post-training compute. The positive-floor top-ups and the long gate's item count grow the data stage by amounts the spec doesn't state.

## Verdict

**Not implementation-ready.** D46's stop rule (at most 2 findings, none blocking) is not met.

Blocking questions that need a decision from David:
1. **R2-06:** where the long-context gate's items come from, whether they are exempt from the overflow trigger (or must carry ≥ 0.15 × B_state of events), which discordance sizes n, and whether each item is rendered at all three placements.
2. **R2-07:** whether the 300-positive floor applies to M8, SCR and the diagnostics; whether top-ups sit inside N = 12,200 or on top of it; and the floor value, traced to a ledger decision.
3. **R2-09:** how the IFBench, aspi and UIB probe items convert into events (which event is LATEST, how aspi tools render). The polarity flip for M1 and M2 has one correct answer and should be written alongside.
4. **R2-10:** how M4 is scored against TRACE's run-level labels, whether G5 is asked at final events that aren't completion claims, and whether the M4 and G5 tests are pooled or must each pass.

One-answer fixes to write before the build starts:
- **Before Phase 1:** R2-01, R2-02, R2-16.
- **Before Phase 3:** R2-12, R2-17.
- **Before Phase 4:** R2-03, R2-04, R2-05, R2-08, R2-11, R2-13, R2-14, R2-15.
- **Anytime:** R2-29, R2-30, R2-31 and the minor rows.

---

## Coverage ledger

| File | Lines read |
|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 (EOF) |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 (EOF) |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 (EOF) |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 (EOF) |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–200, 200–399, 400–605 (EOF) |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–134 (EOF) |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–207 (EOF) |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–262 (EOF) |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md` | 1–200, 200–399, 400–660 (EOF) |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 200–399, 400–599, 600–799, 800–999, 1000–1076 (EOF) |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC-TRACE.md` | 1–35 (EOF) |
| `…\docs\audits\2026-11-07-4-training-spec-round1-dispositions.md` | 1–74 (EOF) |
| `…\docs\audits\2026-11-07-2-training-spec-review-opus-audit.md` | 1–169, 170–329 (EOF) |
| `…\docs\audits\2026-11-07-3-training-spec-external-claims-audit.md` | 1–210 (EOF) |
| `…\docs\audits\2026-11-07-5-training-spec-review-fable-audit.md` | 1–208 (EOF) |

Every line of every required file was covered.

**Evidence lookups (outside the required reads):**
- Kev clone (`C:\Users\david\AppData\Local\Temp\claude\e4a7ca8b20dbf3e0\48a356b8-0453-4fa7-b972-ac20964e049d\scratchpad\kev-verify\kev`): `kev/data.py` 320–415 (`augment`, `none_pair`, `load_records`, `materialize`); `kev/model.py` 12–40, 96–106 and `fits` (145–152); `kev/train.py` 100–112 plus grep hits for none-pair handling and `per_epoch`.
- `docs\research\heldout-intent-probe-manifest.jsonl`: counts by capability, source and label.
- `docs\research\2026-11-07-31-stock-kev-modal-measurements-and-intent-probe-research.md`: lines 60–77.
- `docs\DATASET-DOSSIER.md`: lines 1613–1623 plus grep hits for TRACE.
- `HackBU-NoahDavid`: directory listing; `Noah/backend/samples` exists.
- A grep of the spec for "every-event".