All reads are complete and current. Here is the round-4 report.

# Round 4 review: `docs/TRAINING-SPEC.md`

Date registered by `date`: 2026-11-07 23:18 EST. Spec version reviewed: mtime 23:13:34 (664 lines). Ledger version: mtime 23:13:47 (1,166 lines). Both files changed during this review; the spec was re-read in full after the change and the ledger's changed regions were located and re-read (coverage ledger at the end).

## Part 0: Disposition verification

### Round-3 register: fixes (31 entries)

| Entry | Status | Receipt |
|---|---|---|
| Opus R3-01 / F R3-01 (agent text, `turn_completed`) | LANDED | §4.2 "A record cut at a `turn_completed` event therefore carries the every-event set plus G2 and G5 … so the final text is judged once"; §6.4 "A `turn_completed` event renders as `[E<seq>] MESSAGE` followed by its final text; converters emit a run's final message, and every single-response record's response, as a `turn_completed` event"; §7.2 cut points include `turn_completed`. |
| Opus R3-02, R3-03 / F R3-04 (ties; G1; instruction 2) | LANDED | §8.3 "`label` = target ≥ 0.5 where the positive class is yes, and `label` = target > 0.5 for G1 (target 0.5 gives no, the drift class)"; "a tie between a positive and a non-positive option goes to the positive one; other ties go to the Sol vote"; §8.2.2 "Answer with the question's positive class (4.1)". Twin derivation (§4.2 "label and target flipped") keeps twins consistent at 0.5. |
| Opus R3-04 (M8 out of flagged; D2 row) | LANDED | §4.1 "flagged record … (screen records carry SCR and M8 only)"; §4.2 D2 "per requirement, when M2 or G2 fired". |
| Opus R3-05 / F R3-17 (identity wording) | LANDED | §1 "tensor for tensor"; §12.1 "equals stock Kev-4B merged to full weights the same way (base plus merged LoRA, plus head), tensor for tensor". |
| Opus R3-06, F R3-11 (long gate scores M2; d) | LANDED | §7.9 "d is the larger of stock Kev-4B's own 8K-versus-16K and 8K-versus-limit disagreement rates on M2"; §12.3 "M2 accuracy within 3 points". Arithmetic re-derived: SE = 0.03/3.24 = 0.00926; n = 0.06/0.00926² = 700. The 3.24 = 1.96 + 1.28 gives per-length power 0.90, so both lengths pass with ≈ 0.81 ≥ 0.8. Holds. |
| Opus R3-07 / F R3-07 (overflow threshold) | LANDED | §6.4 "exceed B_state − 0.15 × B_state − tokens(LATEST EVENT, OPEN FINDINGS, EFFORT, the section headings and one count line)"; §7.9 "the single-state limit (the largest document load that renders within B_state under 6.4)". Re-derived: at the threshold the state fits exactly with the count line absorbing all one-liners. |
| Opus R3-08 / F R3-18 (positive-floor share) | LANDED WITH NEW DEFECT | §10 "share measured on each source's full labelled set (the gate runs after labelling)". Landed as dispositioned; the consequence is finding F2 below (the gate can no longer detect the yield shortfall it exists for). |
| Opus R3-11 (serve-path compares logits) | LANDED | §12.1 "max \|Δz\| (logits)". |
| Opus R3-12 (secrets patterns) | LANDED | §12.2 token-shaped pattern list. |
| Opus R3-13, F R3-14 (non-normative padding) | LANDED | §7.7 "non-normative text (long articles of the QuALITY kind, never agent documents or policies …), the record's own documents at a uniformly drawn position"; §7.9 "padded by non-normative articles". |
| Opus R3-14 (can't-tell relabel once) | LANDED | §8.5 and §12.2 "relabelled once; a second failure is reported". |
| Opus R3-15 (π^dev on base dev) | LANDED | §7.9 "computed on base dev, without the top-ups"; §9.5 "π^dev the mean target on base dev (7.9)". |
| Opus R3-16 (stock served with lift fit) | LANDED | §9.5 last bullet. |
| Opus R3-17, R3-18 / F R3-19, F R3-20a-b (teacher band) | LANDED | §11 "0.3–3.7 h (2–5 min per call, 50–100 parallel, 1,000–2,200 calls); a relabel pass … ; RF units on G2/D2 records and sibling records add ~10–20%". Arithmetic: 1,000×2/(60×100) = 0.33 h; 2,200×5/(60×50) = 3.67 h. Holds. |
| Opus R3-19 / F R3-02 ($200 split) | LANDED as dispositioned (no spec change) | §8.7 "$200 … in total across generation and runs"; §11 "stage closes at the cap". Note: the register's rule "generation spend is reserved first" exists in the register only; the ledger's new D47 scheduling bullet ("the 300 agent runs launch first, in parallel, under a hard cut-off") does not carry it. The task file will be built from the spec and ledger, so the reservation has no home. See failure point 1. |
| Opus R3-20 (source identifiers) | LANDED | §7.3 AISI OLMo, tau2, SWE-Misbehavior (#45), Atlas, SWE-bench annotations (#46); §7.9 `metr-evals/malt-public`, `docs/research/heldout-intent-probe-manifest.jsonl`. |
| Opus R3-21 / F R3-12 (demo check) | LANDED | §12.3 Demo check row. |
| Opus R3-22 (pass cap on synthetic record) | LANDED | §10 "smoke run on a synthetic record at `max_packed`". |
| Opus R3-23 (serve-path moves the pick) | LANDED WITH NEW DEFECT | §13 names Serve-path parity among "behaviour gate[s] whose fallback is the next candidate", while §12.1 lists it as a correctness gate and §13 opens "A failed correctness gate stops its stage". Finding F6. |
| Opus R3-24 / Claims 2 (stale none-pair sentence) | LANDED | grep: `none` appears only in `--p_none_pair 0 --p_none 0 …` (§9.1) and "the none-of-the-above substitution, the none-of-the-above minimal pairs and the distractor options are all off". |
| Opus R3-25 (Q4, O-FIRING-THRESHOLD removed) | LANDED | §14 holds Q1–Q3 only; §10 "screen budget 8,192 tokens … 10 sections per state"; §6.6 "floor = cap / 4 (named, overridable factors)". |
| Opus R3-26 (post-pushback cut) | LANDED | §7.3 "cut at the last classified event of the agent's responding turn". |
| Opus R3-27 (p in [0.5, 0.99]) | LANDED | §7.4 Correction window. |
| Opus R3-28 slice part | LANDED | §9.4 "sized so each intent question meets the dev floor"; §7.9 "with the same floor per intent question". |
| Opus R3-29 / F R3-08 ("flag everything") | LANDED | §13 "against the teacher's positive rate there (above 2× → flag)". |
| Opus R3-30 (AgentJudgeBench, `both_bad` as hints) | LANDED | §7.3 rows for repochat, arena-140k, AgentJudgeBench. |
| F R3-03 (benign filters are hints) | LANDED | §7.3 benign table: "T (the filter is a hint)", "T (the reward is a hint)", "T (filters are hints; V only on M4 and L6 …)". |
| F R3-10 (read-only tools named) | LANDED | §7.2 "(Read, Grep, Glob, WebFetch, by tool name)". |
| F R3-13 (served questions, twins excluded) | LANDED | §9.4 "averaged over the served questions (4.2 minus the twins)". |
| F R3-15 (TRACE cut by teacher, logged) | LANDED | §7.9 "(located by the teacher once per conversation and logged)". |
| Claims 1, 3, 5, 6, 7 | LANDED | §6.4 `max_branch` = `max_state` + 640; §7.7 "Kev-27B built 3,200 of its long records this way"; §6.1 `file_changes` only on Edit/Write with structured hunks; §9.2 "share an optimizer step (they may sit in different passes)". |

### Round-3 register: defense (1)

F R3-09 (tie rows count as positives in dev AUROC): DEFENSE HOLDS. §8.3 "binary counts and AUROC use `label`" with ties to the positive class is consistent with D30's recorded preference; it handicaps every candidate equally and the "flag everything" instrument bounds it.

### Round-3 register: dropped (5 groups)

All five dropped mechanisms are absent or changed as stated: no surface gate (grep: "surface" appears only in the §13 risk name "Surface shortcuts"); no per-converter golden bytes (§12.1 "every converter's output validates against that event schema"); no note diagnostic set (§7.5); no cross-fitting (§9.5 "T_q minimizes NLL on all of dev"); TRACE is one state per conversation (§12.4).

### Scope-audit cuts (11)

All eleven are gone from the spec: five candidates (§9.3, §11); no surface-feature baseline; no seam gap or unedited-real set (§1 family 2 "none measured in training"); no note-crutch gate (§1 family 3 "none measured"); no twin-consistency or ledger-size report; retention reported only (§12.3, §13); no calibration-vs-stock report or 5-fold cross-fitting; no per-converter golden bytes; no identity logit check (§12.1 tensor equality only); no run-yield gate (§12.2); no reasoning-stripped held-out copies (§7.9 "No held-out pass renders raw reasoning"). Grep for `cross-fit|fold|ECE|crutch|seam gap|unedited|twin-consisten|ledger-size|logit check|run.yield|stripped copies|21 candidates|every save` returns no spec residue (the only `fold` hit is "scaffold"; `stripped` hits are Terminal Wrench's source variants and SWE-chat path scrubbing).

**Ledger still refers to cut mechanisms** (not spec defects; recorded because the instruction asks that nothing still refer to them): D27 line 687 "calibration cross-fitted over five dev folds"; D27 line 686 "instrument: on action-visible pairs the accuracy gap … stays near 0"; buy/spend row for D27 "~20 candidate scorings"; D42 line 896 "an fp32 logit check" and 899 "cross-fitted for the report"; D44 line 915 "logits within stock's run-to-run spread on 50 fixed states", "calibration is checked out of fold", "run yield"; D45 line 922 "identity parity on 50 fixed states"; D28 line 697 "down-weighted" and "reasoning-stripped copies". Also: D13 now says 08:00 but D3 (127), D13 revisit (246), D18 (323), D27 (687), D34 (798), D36 (819), D41 (989, 1000) and the emergent-interactions row (1123) still say 07:00; and D47 line 937 ("which carry only those two") contradicts D47 line 947 (every-event set plus G2/G5). The spec carries the later decision in each case.

**Part 0 counts.** 48 entries verified (31 fixes, 1 defense, 5 dropped groups, 11 cuts). LANDED 29; LANDED WITH NEW DEFECT 2 (R3-08, R3-23); DEFENSE HOLDS 1; dropped and cuts all confirmed absent; NOT LANDED 0; DEFENSE FAILS 0.

---

## Part 1: Logic and contract audit (§1, §6, §7, §8, §9, §12)

Re-derived and holding: the bounded-regression guarantee (§1, §9.4: if stock is best the kept set is within 1 SE of stock; if a tuned candidate is best at B > stock, the kept set is within 1 SE of B > stock − SE); the prior-shift formula (§9.5 b_q = logit π^dev − logit π^train is the exact label-shift correction for random thinning; applied after temperature as stated); the composition arithmetic (§7.1 Σ n^plan = 1,750 + 870 + 1,500 + 850 + 1,750 + 1,750 + 660 + 1,500 = 10,630; s = 0.809); f_note = 4 × 0.011 = 0.044 → 537 records; S = ⌈12,200/16⌉ = 763; the Hanley–McNeil floor (at AUROC 0.8, n_p = 60, n_n = 600: SE = 0.0351); the long-gate n (above); the fill rule's threshold (above); the tie rules across base rows and twins; the §9.2 rank argument for full-weight checkpoints (B′A′ − BA has rank ≤ 32, so θ(α) at α < 1 is not rank-16).

Findings:

**F1 · Part 1 · unsupported claim · §1 family 2 and §13**
- Spec text: §1 "Converted and constructed records | deployment states | none measured in training | the held-out lift on real Claude Code runs (TRACE) is the check"; §13 "Learning the construction seam | held-out lift on real runs".
- Evidence: the project's own dossier (`docs/DATASET-DOSSIER.md` line 132) classifies TRACE as "Synthetic Claude Code reward-hack conversations, human-verified … Synthetic (scripted hacks)"; line 1765 "hackbench and TRACE have no clean negatives (hackbench) or are synthetic (TRACE)"; line 1782 lists TRACE under "Synthetic or scripted demonstrations"; line 1822 records TRACE's own shortcut leakage ("pressure framing and user-turn keyword leakage, 99 of 268 hacked vs 62 of 249 benign").
- Consequence: the family-2 instrument is described as a real-run check when its source is scripted; a reader of the lift report takes a pass as evidence that the construction→deployment gap is small, which no held-out set here measures. The only real-run check in the spec is the demo check on a recorded Mod session (§12.3).
- Consumer: whoever reads the lift report as evidence (the writeup; the owner's done bar).
- One correct answer: reword family 2's instrument and the §13 row to "the held-out lift on unseen Claude Code conversations (TRACE, scripted, human-verified)" and state that the recorded demo session is the sole real-run check. No new mechanism; scope unchanged.

**F2 · Part 1 · amendment-created (R3-08) · gate that cannot fail in its intended dimension · §10, §12.2**
- Spec text: §10 "Positive floor | 0.8 · P_q, P_q = Σ over sources of s · n^plan × the source's positive share for q | share measured on each source's full labelled set (the gate runs after labelling)"; §12.2 "holds ≥ 0.8 · P_q positive training rows … P_q being what the decided plan yields | rebuild the shortfall inside N from the same objective's sources or constructions".
- Evidence: with the share measured on the same labelled set that supplies the actual positives, actual positives A_q = Σ n_actual × share and P_q = Σ s·n^plan × share. The gate fails only when sources with positives deliver > 20% fewer records than planned, which §7.1 already redistributes before labelling. A source that delivers no records (a construction the generator could not make, an agent-run source whose runs never misbehave) has share undefined or 0 and contributes 0 to P_q, so the gate passes. The ledger's emergent-interactions table names this gate as the catch for "a question with very few positives silently under-trains" and "Runs that never misbehave yield only negatives for M2 and M7 → `positive-floor` (D44) catches it"; as written it catches neither.
- Consequence: the one data gate guarding positive yield passes by construction; a question that lost its positive source trains on negatives alone with no rebuild triggered.
- Consumer: the executor deciding whether to rebuild before the data freezes.
- Needs a design choice (how the data gate judges): either define the share from a reference the build cannot move (each source's intended positive share: V sources from their conversion rule, C sources from the construction, T sources from a declared expectation such as the dossier's measured rate) and keep 0.8 as the margin; or accept the gate as a record-count gate and drop the ledger's claim that it catches yield loss. Not blocking the build start; it must be settled before Phase 3's data gates run.

**F3 · Part 1 / Part 4 · amendment-created (23:13 edit) · §9.3**
- Spec text: §9.3 "If training has not ended by the 08:00 fallback, the pick uses the saves that exist then."
- Evidence: "the 08:00 fallback" is defined nowhere in the spec (grep: the only `0[78]:00` hit is this line); it is D13's deadline, which the ledger's D47 bullet assigns to the task file. The previous wording, "the two saves are the latest one and the one nearest step 400 that exist then", named which saves; the new wording "the saves that exist then" admits the reading "every existing save", which re-expands the candidate set the scope audit cut to five.
- Consequence: an agent reading only the spec cannot resolve the reference and may score up to ten saves × two α values on a deadline.
- Consumer: the executor performing the early pick.
- One correct answer: "If the pick is made before training ends (the task file sets the deadline), the two saves are the latest one and the one nearest step 400 that exist then."

**F4 · Part 1 · amendment-created (23:13 edit) · §9.3, §9.4, §12.1, §11**
- Spec text: §9.3 "Stock Kev is scored on dev before training ends, so only the trained candidates are scored after it"; §9.4 "Candidates are scored with the batched training forward (shared prefix) on the training GPU"; §9.1 "P = the largest per-pass token count whose smoke-run peak memory is ≤ 0.9 × GPU memory"; §12.1 "stock Kev's own gap on the same records (measured before training ends)".
- Evidence: the ledger's new D47 bullet puts dev construction and stock's scoring during the run, so stock cannot be scored before the run starts; the training GPU is sized to 0.9 of its memory by P, leaving no room for a second Kev-4B forward at 32K states. The previous §12.1 text "measured the same way" (same hardware pair for both gaps) was dropped in the edit.
- Consequence: the agent either OOMs the training run or stalls stock's scoring; the serve-path ratio compares gaps measured on different hardware pairs.
- Consumer: the executor scheduling stock's dev scoring and serve-path parity.
- One correct answer: name a second GPU container running the training-forward code for stock's dev scoring and training-forward logits, and require both serve-path gaps to be measured with the same training-forward and serving hardware; add the second container (~10–15 min) to the §11 candidate-scoring row.

**F5 · Part 3 · amendment-created (ledger D47, 23:13) · §15**
- Ledger text (D47 line 947): "Scheduling for the task file (partner-confirmed …): training starts once the train split is labelled, and the dev split, long-context items, held-out conversions and stock's scoring are built and run during the run; the 300 agent runs launch first, in parallel, under a hard cut-off, unfinished shares going to the same objective's other sources."
- Spec text: §15 "4. Training and selection | the run (9.1); candidates; selection; calibration | … | Depends on 3", where Phase 3 is "teacher labelling (8); label resolution; balance cap; splits; intent slice; long-gate items and their stock pilot".
- Evidence: the template makes inter-phase dependencies spec material ("nothing in Phase 2 secretly needs something only built in Phase 3"). As written, the run depends on all of Phase 3, including dev, the intent slice and the long-gate items, which the owner has now decided are built during the run.
- Consequence: §15 forbids the schedule the ledger decided; an agent following §15 waits for dev before starting the run, costing the hours the decision was made to save.
- Consumer: the executor ordering Phase 3 and 4 work.
- One correct answer: split the dependency: the run depends on the labelled, capped train split and the pair-integrity check over the groups it holds; selection and calibration depend on dev, the intent slice and stock's dev score. Where the schedule itself lives is the task file's; the dependency is the spec's.

**F6 · Part 1 · amendment-created (R3-23) · §13**
- Spec text: §13 "A failed correctness gate stops its stage; a behaviour gate whose fallback is the next candidate (Serve-path parity, Demo check) moves selection down the pick order"; §12.1 lists Serve-path parity under "Correctness gates".
- Evidence: the same gate is a correctness gate in §12.1 and a behaviour gate in §13; the two sentences prescribe different outcomes for its failure (stop vs. move down).
- Consequence: a reader of §13 alone stops the stage on a serve-path failure instead of taking the §12.1 fallback.
- Consumer: the executor handling a serve-path failure.
- One correct answer: §13 "A failed correctness gate stops its stage, except Serve-path parity, whose fallback (12.1) moves selection down the pick order; the Demo check does the same."

**F7 · Part 1 · omission · §6.4, §6.6**
- Spec text: §6.4 "Each detailed block's `result`, `patch` and `plan` together are capped at 2,000 tokens" and "LATEST EVENT is a detailed block under the same 2,000-token cap"; §6.6 "The screen ledger holds LATEST EVENT in full (under its 2,000-token cap)".
- Evidence: `agent said:` text and a `turn_completed` MESSAGE's final text are outside the stated cap, yet §6.6 treats the whole LATEST EVENT as capped. A final message of several thousand tokens makes LATEST EVENT exceed the detail budget and the overflow threshold's reserved term, and the screen form's "LATEST EVENT in full" can exceed the screen budget.
- Consequence: a rare but unhandled render failure at both forms; two readings of what "the 2,000-token cap" covers.
- Consumer: the renderer builder.
- One correct answer: cap `agent said:` and MESSAGE text with the same head-and-tail rule inside the block's 2,000 tokens (or state a separate cap), and make §6.6 refer to that rule.

**F8 · Part 1 · error (ambiguity with a wrong reading) · §7.7**
- Spec text: §7.7 "f_long = 0.10 of all records render at 16–32K tokens … agent records whose PROJECT DOCUMENTS are padded with non-normative text … to 16–32K".
- Evidence: §6.4 sends any record whose instructions plus documents exceed ≈ 0.85 × B_state − tokens(LATEST EVENT, OPEN FINDINGS, EFFORT, headings, count line) (≈ 25–26K) to the overflow screen form, which trains SCR and M8 only. Documents padded to 26–32K flip the record out of the single-state form and lose its labels.
- Consequence: if the builder pads documents (not the rendered state) to 16–32K, roughly a third of padded records become screen records and the long single-state share falls short of f_long.
- Consumer: the long-record builder.
- One correct answer: the pad target is the rendered state (16K to B_state), so documents stop at the §6.4 threshold.

**F9 · Part 1 · omission · §6.1, §7.2, §7.3 IN3**
- Spec text: §6.1 "AskUserQuestion answers become `user_instruction` items"; §7.2 "Cut points are classified events only (tool calls that change something, plan and todo updates, and `turn_completed` events); read-only tool events (Read, Grep, Glob, WebFetch, by tool name) are never cut points"; §7.3 IN3 "Generator writes a guess and an ask continuation per task".
- Evidence: an AskUserQuestion call is a `tool_completed` event under a name on neither list; whether it is a cut point decides where the IN3 "ask" negatives for M7 are cut, and the spec does not say how an "ask continuation" is rendered.
- Consequence: converter-dependent cuts for the M7 negatives that carry the "asked" carve-out.
- Consumer: the IN3, Ambig-SWE and lhaw converters.
- One correct answer: AskUserQuestion events are not cut points (D21.E6's reading); an ask continuation renders as a `turn_completed` MESSAGE whose text asks the question, cut there.

No overreach or unneeded mechanism found in §1, §6, §7, §8, §9 or §12 beyond F2's gate, which the use test now fails in its current form.

## Part 2: Cost audit (§11, run time in §9.1)

Every row recomputed from its stated inputs:
- Training run: $3.95 × 2–3.5 h = $7.9–13.8 plus trials → $10–19 within $6–25. The 2–3.5 h estimate is consistent with ≈ 82M state tokens at 4B with checkpointing on an H100 at ≈ 300 TFLOP/s effective (≈ 2.4 h); labeled estimate, settled by the smoke run. Holds.
- Candidate scoring: dev ≈ 1,750 records × 6.7K = 11.7M tokens; 4 trained candidates = 47M ≈ 50M; at 30K tok/s = 26 min ≈ 25 min. Holds. Nit: after the 5→4 change the point estimate sits on the band's lower edge (25–60 min); the band was not rescaled (≈ 20–50 min). The 30K tok/s is an estimate the first candidate settles, as stated.
- Serve-path parity: 300 records × ≈ 1–1.5 s ≈ 5–7 min; band 3–15 min. Holds, subject to F4's hardware question.
- Lift and held-out: RewardBench 2's ≈ 7,500 short states dominate at ≈ 7.5M tokens ≈ 4 min; 15–30 min for two models concurrently holds.
- Long-context gate: 1,000 × 3 × ≈ 17K = 51M tokens ≈ 28 min; pilot 10M ≈ 6–17 min depending on GPU; band 0.3–1 h holds.
- Agent runs: 300 × 3–10 min / 20 = 45–150 min; "1–2.5 h" holds.
- Teacher items: 8,800 non-replay train + ≈ 1,750 dev + 900–1,200 long-gate ≈ 11,450–11,750; the row's 10,000–11,000 is slightly low but inside ±30%. Calls 1,100–2,200 holds; wall-clock band verified above.
- Generation and agent runs: the row states that no Haiku/Sonnet 5.5 price was checked and the cap binds; honest labeling. The reservation rule from R3-19 is in no spec or ledger text (see Part 0 and failure point 1).
- Irreducible floor: correctly named (state tokens; shared prefix the only lever).

No cost finding beyond the nit and F4's missing second-GPU line item.

## Part 3: Completeness against the ledger

Every training-bearing decision traces to spec text: D27 (recipe, cap, rewrites, notes, twins, goal-flips, interpolation set, pick rule, calibration → §7.5–7.8, §9.1–9.5), D28 (composition, sources, exclusions, agent runs → §7.1, §7.3, §7.9, §8.7), D30 (teacher input, instructions, votes, ties, resolution, mismatch, priority band, batches → §7.4, §8.1–8.6), D33 (host, flags, pins, Unsloth gate, saves, resume → §9.1–9.2, §12.1), D37 (grouping, dev floor, held-out list, lift → §7.9, §12.4), D38 (wordings → §4.2, verified verbatim for M7, L5, G1, D5, L7, RF, SCR, M8), D40 (formats → §6.4–6.5), D41 (every forced mechanic → §6.4, §7.1, §7.5, §9.1, §9.5, §10, except stage cut-offs, which are task material), D42–D45 (guarantees, architecture, gates, build values → §1, §5, §6.2–6.3, §7.2, §12), D47 (every mechanic incl. the round-3 list), D18, D19.P, D20, D21, D22. The sole omission is F5 (the new D47 scheduling bullet's dependency change, which §15 does not carry). The ledger-lag items listed in Part 0 are ledger-side and do not affect the spec.

## Part 4: Spec/task boundary

The spec carries no session-recovery, run-order, status-doc or completion-checklist material. The one leakage is F3 (§9.3's reference to "the 08:00 fallback", a task-file deadline). §14 Q2's "Impact: the latest training start" references scheduling but states a legitimate open question. §8.3's batch size and §7.6's 5% spot-check are build values with data-quality consequences and belong in the spec. Nothing task-file-bound was reported as missing.

---

## Close

**Counts.** Register entries verified: 48 (31 fixes, 1 defense, 5 dropped groups, 11 scope-audit cuts): 29 LANDED, 2 LANDED WITH NEW DEFECT (R3-08, R3-23), 1 DEFENSE HOLDS, 16 cuts/drops confirmed absent, 0 NOT LANDED, 0 DEFENSE FAILS. Findings: 9 (unsupported claim 1 [F1]; amendment-created 5 [F2, F3, F4, F5, F6]; omission 2 [F7, F9]; error 1 [F8]; overreach 0; task material 0 beyond F3's reference; unneeded mechanism 0). Amendment-created defects: 5, of which 2 from round-3 fixes (F2, F6) and 3 from the 23:13 edits (F3, F4, F5). Blocking findings: 0. Design choice needed: 1 (F2). The rest have one correct answer.

**Three most likely failure points.**
1. The shared $200 cap with agent runs launched first (D47's new bullet) and no reservation for generations anywhere in the spec or ledger: if the runs consume the cap, the constructions that are the only positive sources for L2, L4, L7, G4 and goal-flip M1 are never generated, and the positive floor as written (F2) passes with those sources at zero.
2. The early-pick path. At 23:18 Phases 1–3 have not started; with the teacher band 0.3–3.7 h, agent runs 1–4 h, a 2–3.5 h run and ≈ 35–45 min after it, the 08:00 pick before training ends is the path most likely to be exercised, and it is the path F3 (which saves) and F4 (where stock is scored) leave ambiguous.
3. The lift test's TRACE half. TRACE is scripted (dossier) and M4 is asked at the last classified event before the cut, usually a final MESSAGE, where M4's "latest action" wording may not see the hack; both endpoints are required, so a genuinely better model can fail endpoint (2) through dilution. This is the owner's decided protocol (D37), not a finding; it is where a true lift is most likely to go unreported.

**Verdict on implementation-readiness.** Ready to start Phase 1 and 2 with no blocking question: every finding except F2 has one correct answer an implementer can apply, and F2's gate is implementable as written. Questions that must be answered before the phase that uses them, named individually: (1) F2, before Phase 3's data gates: does the positive floor measure yield against a fixed reference, or is it accepted as a record-count gate with the ledger's claim withdrawn (owner choice); (2) F4, before Phase 4: where stock's dev scoring and training-forward logits run during the training run; (3) F3 and F5, before the task file is written: the early-pick wording and §15's dependency split; (4) F1, F6, F7, F8, F9: wording and edge fixes with one answer each, none gating a phase.

---

## Coverage ledger

| File | Lines read | Covered |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 (EOF) | every line |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 (EOF) | every line |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–30 (EOF) | every line |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 (EOF) | every line |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–606 (EOF) | every line |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–134 (EOF; steps 4 and 6 at 51–53, 64) | every line |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–207 (EOF) | every line |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–262 (EOF) | every line |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md` | first pass 1–220, 221–440, 441–664 (EOF) at ≈ 23:08; full re-read 1–220, 221–440, 441–664 (EOF) at 23:18 after the 23:13:34 edit | every line, current version |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 201–400, 401–600, 601–800, 801–1000, 1001–1158 (EOF) at ≈ 23:10 (pre-edit, 1,158 lines); after the 23:13:47 edit (1,166 lines): decision index and entry headings re-listed (unchanged set), changed regions located by grep and re-read: line 240 (D13), lines 945–960 (D47 incl. the new scheduling bullet at 947) | every line of the pre-edit version; changed regions of the current version |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC-TRACE.md` | 1–37 (EOF) | every line |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-14-training-spec-round3-dispositions.md` | 1–43 (EOF) | every line |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-7-training-spec-round2-dispositions.md` | 1–75 (EOF; scope audit 72–75) | every line |
| `…\docs\audits\2026-11-07-12-training-spec-round3-review-opus-audit.md` | targeted: 18–26, 149–157, 328–334 (R3-08 text) | partial, by design |
| `…\docs\audits\2026-11-07-13-training-spec-round3-review-fable-audit.md` | targeted: 49–52, 111, 117–118, 206–209, 249–258 (F R3-18 text) | partial, by design |
| `…\docs\DATASET-DOSSIER.md` | grep hits only: 132, 154, 1613, 1751–1872 (TRACE entries) | partial, for F1's receipt |