# TRAINING-SPEC.md review: findings, cost audit and verdict

The spec is **not implementation-ready**. The most serious problem is that the identity guarantee the spec is built on does not hold as written (F1). Below that, several gates are sized so they fail through noise or cannot fail at all, and about a dozen questions need a decision from David before an agent can build. Scope was left alone. Each finding below carries its receipt; where a number is my own estimate, it is labelled as one.

## Coverage ledger

| File | Lines read |
|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 (EOF) |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 (EOF); `date` = 2026-11-07 |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 (EOF) |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–71 (EOF) |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–200, 200–399, 400–605 (EOF) |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–133 (EOF) |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–206 (EOF) |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–261 (EOF) |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md` | 1–199, 200–399, 400–657 (EOF) |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–199, 200–399, 400–599, 600–799, 800–1064 (EOF) |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC-TRACE.md` | 1–35 (EOF) |

Every line of all eleven required files was read. After the interruption, the content was still in my context and had not been summarised, so I did not need to re-read anything.

**Evidence lookups (outside the required reads):**
- `docs\research\2026-11-07-1-kev-repo-pipeline-research.md`, lines 40–84, plus grep hits at lines 5 and 56.
- `docs\research\heldout-intent-probe-manifest.jsonl`: line count, head, and counts per source.
- Grep hits in `docs\research\2026-11-07-31-stock-kev-modal-measurements-and-intent-probe-research.md`.
- One local Python run for the arithmetic.

**Leads I dropped after checking evidence:**
- **Anchoring and head learning rate.** `--anchor_w` defaults to 0 and `--head_lr` 0 means "same as `--lr`", so the two omissions from D33 and D41 change nothing.
- **Version pins.** torch 2.8.0 with triton 3.7.1 was measured working in deployment (report 31, line 87). That evidence covers serving only; the smoke run settles training.
- **Probe contamination.** The probe manifest is 50 items each from TRACE, aspi, UserIntentBench and IFBench, with no AgentIF, so the contamination I suspected does not exist.

---

## Part 1: Logic and contract audit

**F1 (part 1, error).** §1: "a LoRA weight change Δ, an interpolation weight α that scales Δ … At α = 0, T_q = 1, b_q = 0 the adapter's logits equal stock Kev-4B's". §9.3: "α scales the LoRA change at load". §9.2: "save adapter, pointer head, optimizer state…".
- **Evidence:**
  - Kev-4B is "Qwen3.5-4B-Base + rank-16 LoRA (alpha 32) + pointer head". `--init_from` "Loads LoRA adapter … AND pointer head".
  - `--head_lr` 0 means the head trains at `--lr` (kev pipeline research, lines 5, 56 and 65).
  - So the run continues Kev's own LoRA factors and also trains the head. If α scales only the LoRA change, then at α = 0 the trained head is still loaded, the logits are not stock's, and identity parity fails. The rule "no candidate is scored until it passes" then blocks all selection.
  - Separately, scaling the continued factors (B′, A′) does not interpolate the product: B′A′ ≠ BA + α(B′A′ − BA). The four-part list in §1 also leaves out the head change.
- **Consequence:** the builder either cannot pass a gate, or invents an interpolation that silently changes what the 0.85 candidates are.
- **Fix:** one correct answer. θ(α) = θ_kev + α(θ_tuned − θ_kev) over every trained tensor, with the LoRA taken as its merged product and the head included. Δ should then be described as "LoRA and head change".

**F2 (part 1, error; blocking).** §12.1 Renderer parity: "shared Mod-event fixtures render to identical bytes through the training path and the runtime path | no record is built until it passes". §12.3 Calibration: "ECE on dev through the runtime classifier's path".
- **Evidence:** §1 Scope puts "the classifier's serving logic" out of scope, and D36 has the runtime track designed while training builds. During the data build no runtime path exists, and no source for the "shared Mod-event fixtures" is named.
- **Consequence:** read literally, Phase 2 never starts. Read loosely, the gate compares one function with itself and cannot fail.
- **Fix:** a decision. What counts as "the runtime path" at training time (for example, a thin adapter from Mod event JSON into the renderer), and which recorded Mod sessions are the fixtures and who supplies them.

**F3 (part 1, error).** §12.4: "Baseline: stock Kev-4B with its temperature refitted on the same dev split. Endpoint: on the 200 intent-probe items and on TRACE, tuned minus stock accuracy has a paired 95% lower bound above 0."
- **Evidence:**
  - σ(z/T) ≥ 0.5 if and only if z ≥ 0, and the argmax of softmax(z/T) is the argmax of z. Refitting the temperature therefore never changes accuracy.
  - The tuned model gets b_q, a bias shift. Stock gets none, although its measured failure is exactly a fixed yes/no lean (D3: 94% and 2% yes-rates).
  - "On the probe and on TRACE" does not say whether that is one pooled test or two tests that must both pass.
  - 50 of the 200 probe items are TRACE (manifest), so the two endpoints overlap.
  - Nothing says how TRACE or the probe items are converted into events, which monitor question scores them, or how their raw reasoning is rendered. §12.4 reports "each again with reasoning stripped", which implies the first pass shows reasoning.
- **Consequence:** the headline lift partly measures a bias correction the baseline was denied, and the builder must make protocol choices that decide the result.
- **Fix:** a decision. Give stock the same calibration family (a bias offset fitted on dev). Fix the TRACE and probe question mapping and how reasoning is rendered. State pooled versus both, and how the overlapping items are handled.

**F4 (part 1, error; leakage).** §8.1: the teacher receives "the raw reasoning for events with seq ≤ k and any source labels with their basis. It never receives later events or outcomes after the cut."
- **Evidence:**
  - Source labels are not filtered by `event_seq` (§6.2 has `"event_seq": 41`).
  - Negatives cut "from the prefix before the offending event of positive runs" (§7.2) therefore send the teacher a label that points at a later offence.
  - Outcome-based labels ("O (hidden-test reward) → T", §7.3; §8.2 item 5 "hints") are outcomes from after the cut, which contradicts "never receives … outcomes".
  - The note generator (§8.6) has no rule limiting a step's note to reasoning at or before that step.
- **Consequence:** labels on prefix negatives and notes can carry future information into the training targets and into visible text.
- **Fix:** filtering source labels to seq ≤ k and limiting each note to its own step's reasoning are one correct answer. Whether the teacher sees outcome hints at all is a decision.

**F5 (part 1, error).** §6.4 fill rule: "detail budget 0.40 × B_state − (tokens used by instructions and documents) … every older event as a one-liner; OPEN FINDINGS and EFFORT always. If instructions and documents alone exceed the budget…"
- **Evidence:**
  - One-liners have no cap, so instructions + LATEST + detail + one-liners can exceed 32,768 on long runs. Those long runs are the main source of the 10% long records (§7.7).
  - Kev's trainer drops records over `--max_state` ("Records over are DROPPED with a printed count", kev research line 43).
  - When instructions plus documents exceed 13,107 tokens, the detail budget goes negative, and nothing says what happens then.
  - "The budget" in the last sentence is ambiguous: it could mean B_state or the detail budget.
- **Consequence:** long records are lost silently, and the runtime inherits an unbounded state.
- **Fix:** a decision. What is cut when one-liners overflow (drop the oldest, or switch to the overflow form), and which budget the overflow trigger uses.

**F6 (part 1, error).** §6.4 says "OPEN FINDINGS and EFFORT always" and also "EFFORT appears only when the user stated priorities or an order". §4.2 asks G4 "only when the user stated priorities or an order".
- **Evidence:** the two sentences contradict each other. No rule says how a converter decides that priorities were stated on natural runs (only the Priority construction knows). The rendering of an empty OPEN FINDINGS section is also unspecified, and byte parity with the runtime depends on it.
- **Consequence:** state bytes and G4 row presence depend on a predicate the runtime must reproduce, and nobody has defined it.
- **Fix:** a decision on the "priorities stated" predicate, used by both training and runtime, and the rendering of empty sections.

**F7 (part 1, error; gates fail through noise).** §12.3 Retention: "Kev's decision-v7 dev (300 records): tuned minus stock, lower bound ≥ −0.03". §12.3 Long-context validity: "within 3 points … on the paired 95% lower bound", with no item count anywhere (§7.9 and §10).
- **Evidence:**
  - Computed lower bound when the tuned model truly equals stock, at n = 300: −0.0277 at 6% discordant items, −0.0299 at 7%, −0.032 at 8%, −0.0358 at 10%.
  - So any fine-tune that changes 8% or more of answers, with no net change, fails Retention.
  - The long gate's n is unsized. By the same arithmetic, at 10% discordance it needs about 430 paired items just to pass at parity.
- **Consequence:** Retention pushes selection to α = 0.85, then to the next candidate, then possibly to stock Kev, and the long gate drops the validated length, without either reflecting any real regression. This breaks principle 6 (sizes by formula).
- **Fix:** a decision. Size both gates' n by formula from measured discordance, or change the decision rule.

**F8 (part 1, error).** §7.9: "AUROC standard error (Hanley–McNeil) is ≤ 0.05, about 60 positives at AUROC 0.8". §10 states the formula "min n with Hanley–McNeil SE(AUROC) ≤ 0.05".
- **Evidence:**
  - Computed minimum positives at AUROC 0.8: 33 at 1:3 negatives, 29 with many negatives. At 60 positives the SE is 0.035.
  - The formula and the "~60" disagree by about 2×.
  - D37 shows David rejected "a fixed 30 positives" and chose the SE rule believing it meant about 60.
- **Consequence:** the builder implementing the formula gets roughly the floor David turned down.
- **Fix:** a decision. Either the threshold (an SE of about 0.035 matches 60 positives) or the stated number.

**F9 (part 1, overreach plus error).** §1 coherence invariant: "σ((z_q + b_q)/T_q) … b_q is the closed-form prior shift between the post-balance training label rate and the natural rate, exact under A-label-shift".
- **Evidence:**
  - Dividing by T scales the shift to b/T, so the claim is exact only at T = 1. The exact form would be σ(z/T + b).
  - The dev set is not at natural prevalence for rare questions, because §7.9 tops them up ("rare questions top up from their own sources or constructions"). For exactly those questions, π^dev is inflated.
  - "Natural rate" is the prevalence of the collected pool, not deployment prevalence (the pool is enriched with hack datasets), yet the invariant names "deployment".
  - With soft targets, it is unclear whether π^train means the hard-label rate or the mean target. The model learns the mean target.
- **Consequence:** b_q is wrong exactly where it matters (rare questions), and the claim of exactness is unsupported.
- **Fix:** one correct answer for the formula order and for π (exclude top-ups, use the mean target). Rewording the invariant to "corrects the balance cap, not deployment prevalence" makes the claim true.

**F10 (part 1, error; gate cannot fail).** §1 and §12.2: "per-question agreement between the two teacher models ≥ 0.70".
- **Evidence:** the agreement statistic is undefined, and votes have three values. With raw percentage agreement, a question with about 5% positives scores 0.90 or more even if the teachers never agree on a single positive.
- **Consequence:** the label-quality bound is blind on the rare questions (L6, L2, G4, M7), where it matters most.
- **Fix:** a decision. Use Cohen's kappa or positive-class agreement, and set its threshold.

**F11 (part 1, error; fallbacks cannot run).** §12.3 Surface-feature baseline: "the monitor's AUROC lower bound exceeds the baseline's upper bound | … its sources re-balanced". Seam gap: "flag, down-weight its constructions". §1 table: "its constructions down-weighted".
- **Evidence:**
  - These gates run on dev after the single run (D5: one recipe), so re-balancing or down-weighting needs a second run that does not exist.
  - The surface model includes source identity, and sources were chosen by label (hack sets versus benign pools). Its AUROC is therefore high because the data is confounded, not because the monitor relies on shortcuts. A monitor that reads content can still fail to clear non-overlapping intervals.
- **Consequence:** the gate likely produces many false "shortcut-reliant" verdicts, and its remedy cannot be executed.
- **Fix:** a decision. Measure per-source (stratified) AUROC, and either accept report-only fallbacks or define a retrain.

**F12 (part 1 error and part 3 omission).** §12.3 Seam gap: "constructed-dev minus unedited-real AUROC per question". The ledger, D37, reads verbatim: "**Held out entirely:** TRACE, MALT reviewed runs, LLMBar and RewardBench 2, the 200 probe items, unedited real runs for constructed questions, and a reasoning-stripped copy of each."
- **Evidence:** §7.9 never defines the unedited-real set: which runs, how they are labelled, whether it sits in dev or held-out, or its positive floor. L2 has no natural source at all (§7.3 trajectory table), and G4 and L5 have few. With roughly zero real positives the AUROC interval is unbounded, so the gate can never flag.
- **Consequence:** the seam-learning instrument is inert for the questions built only from constructions.
- **Where it belongs:** §7.9.
- **Fix:** a decision on its sources and floor.

**F13 (part 1 error and part 3 omission).** Ledger D27 verbatim: "Dev and held-out sets use the real rate; instrument: on action-visible pairs the accuracy gap between the two copies stays near 0." §7.5 and §7.9 state no note rate for dev or held-out.
- **Evidence:** D42 rejected a flat 0.02 bound because it was "about one standard error at ~500 pairs". That count is the training note pairs. Dev at 1.1% notes on about 1,300 records gives about 14 note records, and only a few of those are action-visible pairs.
- **Consequence:** the note-crutch interval never clears 0, so the gate cannot fail. "Accuracy" also has no threshold.
- **Fix:** a decision. State the dev note rate and give the note-crutch gate its own pair set and threshold.

**F14 (part 1, error).** §7.2: negatives are cut so that "relative run position (k / run length, in deciles) matches that harness's positives".
- **Evidence:** the model cannot see run length. It sees absolute position, through the ledger size and the number of one-liners. Matching on relative position leaves the visible cue unmatched. The text also does not say whether event type and position are matched jointly or separately.
- **Consequence:** the cue the matching was meant to remove survives.
- **Fix:** a decision, but a small one. Match on absolute event index (or state length), jointly with event type.

**F15 (part 1, error; composition).** §7.8: "every positive row is kept and negative rows are sampled down to at most 3 per positive". §9.1: "S ≈ 763 at R = 12,200".
- **Evidence:**
  - Every agent record carries the full every-event set of 11 to 12 rows (D30).
  - My estimate from the §7.3 plan: about 3–4K positive rows against about 75–85K every-event rows, so roughly 80% of rows are dropped. A benign record keeps none of its 11 rows with probability about 0.9¹¹ ≈ 0.3.
  - The replay share, the benign share, R and S are all stated before the cap.
  - "A dropped row costs no teacher call" is true, but it means the teacher labels rows that are then discarded.
- **Consequence:**
  - The trained mix differs from the one decided, and replay is probably well above 25% of rows.
  - The D30 rationale ("one state answered differently across questions") is largely undone.
  - S is computed on the wrong R.
- **Fix:** a decision. Is the cap per row or per record? Is R counted before or after the cap? Is the mix re-checked after the cap?

**F16 (part 1, error, minor).** §7.1: "N_replay = 3,000 | ρ_replay · N with ρ_replay = 0.25".
- **Evidence:** 0.25 × 12,200 = 3,050. That gives s = 8,550 / 10,630, not 8,600 / 10,630.
- **Consequence:** a builder who follows the formula gets different quotas from the table.
- **Fix:** one correct answer. Fix ρ or the count (12,000 + 200 screen records was the ledger's history).

**F17 (part 1, error; train/runtime mismatch).** §6.1: "Tool names map to Claude Code names: Bash (any shell, including keystroke batches), Read, Write, Edit, Grep, Glob, WebFetch, TodoWrite, ExitPlanMode."
- **Evidence:**
  - CONTRACT.md §5: "Actions (Edit, Write, Bash, PowerShell)".
  - Ledger D12: "On Windows, shell actions may arrive through a PowerShell tool as well as Bash."
  - CONTRACT.md §1: the demo runs on Windows 11.
  - There is no rule for other tools, and no key argument is defined for WebFetch, TodoWrite or ExitPlanMode.
- **Consequence:** on the demo machine, shell events render as a tool name never seen in training.
- **Fix:** a small decision. Map PowerShell to Bash in the shared renderer, and set an unknown-tool rule.

**F18 (part 1, omission).** §6.3: `questions` is a JSON object keyed by ID ("M4", "M1", "D5"). §4.2: RF wraps "the judged sentence … in ⟦ ⟧, with up to two neighbouring sentences".
- **Evidence:**
  - Rows asked per requirement, per event or per section (G2, D1/D3, D2, RF, SCR, M8) collide on a single key.
  - RF's input form is undefined: is the ⟦⟧ window in the state or in the question, and what is RF's state? RF also runs at runtime (D20), so its form binds the runtime.
- **Consequence:** the builder fixes a runtime format on its own authority.
- **Fix:** key suffixes are one correct answer; the RF input layout is a decision.

**F19 (part 1, omission).** §6.5: "<question short name>". §4.2 D1/D3: "«short names of the questions that fired»". D2: "«summary»".
- **Evidence:**
  - No short names and no summary template are defined anywhere, yet they appear in trained D1/D3/D2 rows and in L7 correction-window text that is "identical to the runtime's".
  - G5 has a correction but is missing from the item order.
  - The "p = 0.87" value used inside constructions has no specified distribution, so a constant would be a cue.
- **Consequence:** runtime-binding strings get invented during the build.
- **Fix:** a small decision.

**F20 (part 1, omission).** §6.6: "Cap = (screen budget − instructions − ledger − event) / target sections". The state contains "RUN LEDGER <recent events only>". §7.4 Overflow screen: "A document split per 6.6".
- **Evidence:**
  - The screen ledger has no size rule, so the cap formula cannot be evaluated.
  - The pool of documents used for screen records is not named.
  - Sections "without one" are labelled no by construction, though a natural section can be relevant.
  - Instructions over 8,192 tokens make the cap negative.
- **Consequence:** the builder decides the screen format the runtime inherits.
- **Fix:** a decision.

**F21 (part 1, omission).** §7.9: "8K, 16K and 32K renderings of the same records with identical labels, plus start, middle and end placements of the deciding instruction".
- **Evidence:**
  - Under the fixed fill rule, changing the length changes which events appear in detail, and L1 is defined over "events shown in detail", so labels can change.
  - USER INSTRUCTIONS is always first (§6.4), so the deciding instruction cannot be moved unless it sits in a padded document.
  - No construction method is given.
- **Consequence:** the gate that sets the validated length cannot be built as stated.
- **Fix:** a decision (vary B_state or pad; which questions; where the instruction lives).

**F22 (part 1, error; gate cannot fail).** §12.3 Calibration: "per-question ECE on dev … ≤ stock Kev's … | refit; else serve that question uncalibrated".
- **Evidence:**
  - T_q and b_q are fitted on that same dev (§9.5), so the check is in-sample against an uncalibrated stock model. Kev's own pipeline keeps calibration and development as separate splits (research line 45).
  - "Refit" with the same procedure gives the same result.
- **Consequence:** the gate passes by construction, and its fallback is not a distinct action.
- **Fix:** a decision. Cross-fit on dev folds, or hold out a calibration slice.

**F23 (part 1, overreach).** §1: "the selected adapter's dev score is at least stock's minus one standard error". §12.3: "prefer α = 0.85; else the next candidate". §13: "moves selection to the next candidate in pick order".
- **Evidence:** the guarantee follows only within the kept set: best ≥ stock, so selected ≥ best − SE. "Pick order" is never defined, and "prefer α = 0.85" can pick a candidate outside the one-SE set.
- **Consequence:** the bounded-regression guarantee is not guaranteed.
- **Fix:** one correct answer. Pick order is intent-score rank within the kept set, then stock.

**F24 (part 1, gap).** §9.4: "intent score: mean AUROC on the intent slice over M1, M7, L4 and G1", drawn from SWE-chat pre-correction windows, HelpSteer3, Atlas, goal-flip pairs and IN3.
- **Evidence:** none of those sources is a goal-splice construction. Goal-flip pairs label only M1 and its twin (§7.4). L4 and G1 positives on about 200 records may be near zero, and the slice has no per-question floor.
- **Consequence:** the deciding score is noisy or undefined for half its components.
- **Fix:** a decision. Set a floor, or allow splice records into the slice.

**F25 (part 1, gate cannot be evaluated).** §12.2 Positive floor: "every question has its planned positive rows". Run yield: "low yield moves its share".
- **Evidence:** no positive-row plan per question exists anywhere (§7.3 plans records per source), and "low" is not quantified. The emergent test "the build stops on a shortfall" has no number to compare against.
- **Fix:** a decision.

**F26 (part 1, overreach).** §13 Residual "none" for "Secrets or personal data in records", "Forgetting general skill", "Saying yes everywhere" and licence breach.
- **Evidence:**
  - The secrets scan (§12.2) checks four strings. It misses GitHub, AWS and HF tokens, `sk-proj-` keys and private keys, all plausible in SWE-chat and TonyDzi real sessions.
  - Retention covers one suite.
  - The yes-rate instrument has no trigger.
- **Consequence:** an unsupported claim, in a public repo (CONTRACT §1).
- **Fix:** one correct answer. State the actual residuals; a broader pattern set is a builder detail.

**F27 (part 1, error, minor).** §6.1: "emits events with exactly these fields (the Claude Code Mod's schema)".
- **Evidence:** CONTRACT §3 also carries `schema_version`, `session_id` and `event_id`, accepts extra fields (`extra="allow"`), and calls the layout "provisional".
- **Consequence:** a strict Phase-1 "event schema validator" rejects real Mod fixtures.
- **Fix:** one correct answer. Accept a superset.

**F28 (part 1, minor).**
- §12.1 Serve-path parity: "max |Δp| ≤ 0.01 on dev (sourced: bf16 serving noise measured at 0.0055)". The statistic behind 0.0055 is not stated, and a maximum over about 20K dev rows can exceed it by chance. The fallback "inspect the merge and load path" has no end state.
- §12.1 Accelerated-kernel parity uses the same-seed noise floor. A deterministic reference gives a floor of 0, which no kernel change can meet. The impact is low because the reference path is the default.

**F29 (part 1, minor).** The ledger's D41 says "AUROC does not change under temperature or prior offset", and §9.4 selects before calibration. That holds for yes/no questions but not for choice and score questions: per-option offsets inside a softmax change the one-vs-rest rankings across records. The impact on selection is small.

**F30 (part 1, unsupported claim, minor).** §3 says "Sources are named where used", but §7.1, §7.7 and §7.8 cite "a narrow-data study", "the long-context research" and "the data-mixing research" without naming them.

**Claims I re-derived and verified (no finding):**
- s = 8,600 / 10,630 ≈ 0.809, with Σ n^plan = 10,630.
- f_note = 4 × 7 / 644 = 0.0435, about 530 records.
- S = ⌈12,200 / 16⌉ = 763, and 21 candidates.
- The vote-to-target mapping and the choice tie rule (§8.3).
- The label-resolution order (§8.4).
- The T ≥ 1 clamp is applied consistently.

---

## Part 2: Cost audit

- **Training run, 2–2.5 h (band 1.5–4 h): I defend this.**
  - My estimate is about 70–80M tokens per epoch before the cap: replay about 1.5K per record, long records about 24K, the rest about 5K.
  - LoRA with checkpointing costs roughly 2.4×10¹⁰ FLOPs per token, giving about 1.3 h at 40% MFU or about 2.1 h at 25% on an H100.
  - Kev's documented skills stage ran 1.4 h on an H200 (research line 84).
  - The F15 cap shrinks the run. The $10–13 cost at $3.95/h matches Kev's price table.
- **Missing cost: candidate scoring and evaluation. I challenge this.**
  - 21 candidates × the dev split (about 1,300 records plus top-ups), plus the long-gate renderings, Retention and the held-out pass, is roughly 200M forward tokens (estimate).
  - Through the serving path that is far worse: report 31 measured 3.6 s for one 32K state with 20 questions on an L40S, and about 27K state-scorings at around 1 s each is about 7.5 h.
  - The spec neither budgets this time nor says that scoring uses the batched training forward. It enters the 07:00 cut-off only as "measured".
- **Teacher, "18,000–20,000 calls": soften and relabel.**
  - That figure is items × votes, not calls. At 10–20 records per call it is about 1,300–2,000 calls.
  - The volume (my estimate) is about 10K items × about 7K tokens × 2 votes ≈ 140M input tokens plus raw reasoning, and a 20-record batch of long records reaches about 480K tokens in one call.
  - Batches should be bounded by tokens, not record count.
  - No dollar figure or plan quota is stated.
  - 1–2 h needs about 250 output tokens per second sustained per subagent at 15 parallel. I would carry 2–4 h until the first batch is measured.
- **Generation plus agent runs, $25–70: I challenge the estimate and defend the cap.**
  - I could not find Haiku 5.5 or Sonnet 5.5 prices, so this is an inference from the token profile of typical agentic runs, not a sourced figure.
  - About 300 headless Claude Code runs of tens of turns each plausibly cost $0.3–1+ each, so the runs alone could reach $100–300 before reruns for low yield. The 3,000–3,500 generations add tens of dollars.
  - In practice the $200 cap is the binding number, with run yield as the fallback.
  - Neither the wall-clock time nor the infrastructure for 300 runs inside task containers (where they run, how many in parallel, pulling SWE-Bench Pro images) is stated or estimated. That is a real overnight feasibility risk, noted here without recommending any cut.

---

## Part 3: Completeness against the ledger

These omissions are already given in full above as F12 (D37's unedited real runs) and F13 (D27's note rate in dev and held-out). Additional items:

- **O1 (D20, quoted verbatim):** "Instrument: filter recall needs one." / "Revisit if. Filter recall is low on held-out instructions." No RF recall measure appears in §12.3 or §12.4. Low severity: dev AUROC partly covers it.
- **O2 (D28, quoted verbatim):** "Terminal Wrench ~250 (red-team prompt stripped, down-weighted)". The §7.3 Terminal Wrench row has no down-weighting and the spec has no weighting mechanism. If "down-weighted" referred to the reduced quota, the spec carries it. It needs a one-line confirmation.
- **Ledger-internal notes, not spec omissions:**
  - D30's headline ("two Sol subagents … no tiebreak") contradicts its own later bullet ("one Sol vote and one Terra vote"). The spec follows the bullet.
  - D43's "base rates by position are restored by calibration" cannot hold for a scalar per-question offset; the spec rightly does not carry it.
  - The trace omits D45, although the spec does carry its values.

---

## Part 4: Spec/task boundary

These items belong in task.md or AGENTS.md and should leave the spec:

- **Cut-off scheduling:** §10 row "Stage cut-offs"; §13 row "Overnight time overrun"; §15's last line ("Every stage of phases 2–5 has a cut-off time computed backward from 07:00 EST…"); and §9.4's last sentence (the 07:00 pick timing). §9.4 should keep only the selection rule itself.
- **Subagent dispatch:** §8.3, "subagent thinking level is medium for labelling and low or none for mechanical checks". Batching by source can stay, because it affects labels.
- **Standing operational laws (AGENTS.md):** §7.3 "downloads land in their own empty directory, are read only with `python -I`…" and §8.7 "The API key comes from an environment secret…".
- **Process status in front matter:** "(pending adversarial review)".

---

## The three most likely failure points, by expected impact

1. **F1, the α and pointer-head identity.** It is certain to trigger: either identity parity blocks every candidate, or the builder improvises the interpolation and the 0.85 candidates become different objects.
2. **F7, gates that fail through noise.** Retention at n = 300 and an unsized long-context gate can push selection down to stock Kev and drop the validated length, with no real regression. F10, F13 and F22 are the opposite case: gates that cannot fail.
3. **Unbudgeted selection and evaluation compute, together with the teacher and agent-run wall-clock, against 07:00.** This is the cost audit plus F15: the post-training phase may not fit the window, and the post-cap training mix is not the one that was decided.

## Verdict

Not implementation-ready.

**Blocking questions that need a decision from David:**
1. F2: what the runtime path is for renderer parity and calibration, and where the Mod fixtures come from.
2. F3: the lift protocol (baseline calibration, TRACE and probe question mapping, how reasoning is rendered, pooled versus both, the overlap).
3. F4: whether the teacher sees outcome hints.
4. F5: what the fill rule cuts on overflow.
5. F6: the "priorities stated" predicate and the empty-section rendering.
6. F7: the sample size or decision rule for the Retention and long-context gates.
7. F8: the dev positive floor (30 or 60).
8. F10: the teacher-agreement statistic and its threshold.
9. F11: whether there is a retrain or report-only fallbacks, and the stratified surface test.
10. F12: the unedited-real set.
11. F13: the dev note rate and the note-crutch measurement set.
12. F15: whether the balance cap is per row or per record, and the R definition.
13. F17: the PowerShell and unknown-tool mapping.
14. F18: RF's input layout.
15. F19: short names and the D2 summary template.
16. F20: the screen ledger size and document pool.
17. F21: how the long-gate items are constructed.
18. F22: the calibration-gate split.
19. F24: the intent-slice floor.
20. F25: the positive-floor numbers and the yield threshold.
21. Cost audit: whether candidates are scored through the batched forward pass, and the time budgeted for it.

**One-correct-answer fixes that still need writing down:** F1 (weight-space interpolation including the head), F4 (filter source labels to seq ≤ k, notes from their own step only), F9 (formula order and the π definition), F14 (match absolute position jointly with event type), F16, F23, F26, F27, F28, F29 and F30, plus the Part 4 moves.