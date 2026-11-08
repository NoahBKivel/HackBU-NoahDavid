# Round-4 review of `docs/TRAINING-SPEC.md`

**Summary.** None of the 12 findings below blocks the build; one is medium, the rest low or low-medium. Every round-3 fix and every scope-audit cut landed, with three exceptions. The $200 split is recorded only in the round-3 audit file. Two fixes introduced new defects (R4-03, R4-10). The spec and ledger changed at 23:20, during this review, and three more defects came from that edit (R4-07, R4-08 and the benign-header slip under R4-04). Five defects in total were created by amendments.

The date is Sat Nov 7 2026, 23:25 EST (checked with `date`). I edited no file and invoked no skill. Every command ran in the foreground and exited before the next one started.

**The spec changed while I was reviewing it.** `TRAINING-SPEC.md` and `DESIGN-DECISIONS.md` were both saved at 23:20:45 and 23:20:51, after my first full read. I noticed because a quote check returned different text. I then re-read the whole spec (lines 1–664) and the ledger entries the edit touched. This report reviews the 23:20 version. The edit changed these places:
- §7.9: the MALT conversion was removed.
- §9.3: it now reads "08:00 fallback".
- §9.4: candidates are now scored in a separate container during training.
- §11: the candidate-scoring, serve-path and lift rows changed.
- §12.1: serve-path parity now uses 300 dev records.
- §12.3: the demo check now runs "through the deployed `classify()`".
- §12.4: MALT was dropped from the reports.
- Ledger: D13 moved to 08:00, and D47 gained a scheduling bullet.

---

## Part 0: Disposition verification

### Round-3 fixes (31 entries)

| # | Entry | Status | Receipt |
|---|---|---|---|
| 1 | R3-01 agent text / `turn_completed` | LANDED | §4.2: "text before a tool call is that event's `agent said:` line … A record cut at a `turn_completed` event therefore carries the every-event set plus G2 and G5". §6.4: "A `turn_completed` event renders as `[E<seq>] MESSAGE` followed by its final text; converters emit … every single-response record's response, as a `turn_completed` event". |
| 2 | R3-02, R3-03 / F R3-04 ties and teacher wording | LANDED | §8.3: "`label` = target > 0.5 for G1 (target 0.5 gives no, the drift class)"; "a tie between a positive and a non-positive option goes to the positive one". §8.2 item 2: "Answer with the question's positive class (4.1)". I re-derived the polarity for the twins and it is consistent. |
| 3 | R3-04 M8 and D2 membership | LANDED | §4.1: "(screen records carry SCR and M8 only)". §4.2 D2 row: "when M2 or G2 fired". |
| 4 | R3-05 / F R3-17 §1 identity wording | LANDED | §1: "equals stock Kev-4B merged to full weights the same way … tensor for tensor". |
| 5 | R3-06, F R3-11 long gate question and d | LANDED | §7.9: "d is the larger of … disagreement rates on M2". §12.3: "M2 accuracy". |
| 6 | R3-07 / F R3-07 overflow reserve | LANDED | §6.4: "B_state − 0.15 × B_state − tokens(LATEST EVENT, OPEN FINDINGS, EFFORT, the section headings and one count line)". The detail-block rule this relies on is R4-11. |
| 7 | R3-08 / F R3-18 floor share | LANDED | §10: "share measured on each source's full labelled set". |
| 8 | R3-11 serve-path in logits | LANDED | §12.1: "max \|Δz\| (logits)". |
| 9 | R3-12 secrets patterns | LANDED | §12.2: token-shaped regexes. |
| 10 | R3-13, F R3-14 padding | LANDED | §7.7: "non-normative text … the record's own documents at a uniformly drawn position". |
| 11 | R3-14 can't-tell relabel ends | LANDED | §8.5 and §12.2: "relabel once; a second failure is reported". |
| 12 | R3-15 π^dev on base dev | LANDED WITH NEW DEFECT | §7.9: "every prevalence-dependent quantity … is computed on base dev". But §9.5 fits T on "all of dev" and §12.4 fits stock's b on "the same dev split" (R4-03). |
| 13 | R3-16 stock if selected | LANDED | §9.5, last bullet. |
| 14 | R3-17/18, F R3-19/20 teacher band | LANDED | §11: "0.3–3.7 h …; RF units … add ~10–20%". The arithmetic re-derives: 2,200 × 5 / (60 × 50) = 3.67 h. |
| 15 | R3-19 / F R3-02 $200 split | NOT LANDED anywhere the executor reads | The spec is unchanged. The register says "generation spend is reserved first. Recorded here; the task file schedules it." The ledger's new D47 bullet says "the 300 agent runs launch first, in parallel" and sets no sub-cap. The price was never checked (R4-06). |
| 16 | R3-20 identifiers | LANDED | OLMo, tau2, SWE-Misbehavior, Atlas and the probe path are present. The MALT identifier went with the 23:20 removal of the MALT report; MALT is now only an exclusion, so this is moot. |
| 17 | R3-21 / F R3-12 demo check form | LANDED; the 23:20 edit then added a defect (R4-08) | §12.3: recorded session, stand-in, predicate. |
| 18 | R3-22 pass cap on a synthetic record | LANDED | §10: "synthetic record at `max_packed`". |
| 19 | R3-23 §13 recovery | LANDED | §13: "(Serve-path parity, Demo check)". |
| 20 | R3-24 / claims F2 stale none-pair sentence | LANDED | It is absent from §9.1. |
| 21 | R3-25 Q4 and O-FIRING | LANDED | §14 has only Q1–Q3. |
| 22 | R3-26 post-pushback K | LANDED | §7.3: "cut at the last classified event of the agent's responding turn". |
| 23 | R3-27 p range | LANDED | §7.4: "[0.5, 0.99]". |
| 24 | R3-28 slice sizing | LANDED | §9.4: "sized so each intent question meets the dev floor". |
| 25 | R3-29 / F R3-08 yes-everywhere instrument | LANDED WITH NEW DEFECT | §13: "against the teacher's positive rate there (above 2× → flag)" (R4-10). |
| 26 | R3-30 AgentJudgeBench, `both_bad` | LANDED | §7.3: "T (the coverage score is a hint…)"; "`both_bad` included". |
| 27 | F R3-03 benign filters as hints | LANDED WITH NEW DEFECT (minor) | The rows are T now, but the header still reads "Benign runs (negatives for every question)". The same pattern survives in CodeTraceBench (R4-04). |
| 28 | F R3-10 read-only set | LANDED | §7.2: "(Read, Grep, Glob, WebFetch, by tool name)". |
| 29 | F R3-13 served question set | LANDED | §9.4: "averaged over the served questions (4.2 minus the twins)". |
| 30 | F R3-15 TRACE cut locator | LANDED | §7.9: "located by the teacher once per conversation and logged". |
| 31 | Claims F1, F3, F6, F7, and F5 (defended) | LANDED; F5's defense holds | Row limit (§6.4), Kev-27B scope (§7.7), schema (§6.1), optimizer-step sharing (§9.2 item 2). F5: the claims audit read `register.tsx:291,305`; the Mod sends every tool input as `args`, so the plan text arrives. |

### Defense and dropped items

- **F R3-09 (tie rows count as positives in dev AUROC): DEFENSE HOLDS** on David's stated preference. Its clause "bounded by the 'flag everything' instrument" overstates: that instrument is a report after the only run (R4-10).
- **All 5 dropped groups are confirmed absent.** The surface gate is gone from §9.4 and §12.3. Per-converter golden bytes are gone from §12.1. There is no note diagnostic set in §7.5. There are no folds in §9.5. TRACE is one state per conversation in §12.4.

### Scope-audit cuts (11)

All 11 cuts LANDED, and nothing in the spec still refers to them:
- five candidates (§9.3);
- surface baseline;
- seam gap and the unedited-real set (§1 row 2 and §13 keep only the held-out lift);
- note-crutch gate;
- twin and ledger-size reports;
- retention, now reported only (§12.3);
- calibration-vs-stock report and cross-fitting;
- per-converter golden bytes;
- the identity logit check (§12.1 is tensor-only);
- the run-yield gate;
- the reasoning-stripped held-out copies.

The ledger still names some of them (see the ledger notes after Part 4).

**Tally:** 48 entries verified (31 fixes, 1 defense, 5 dropped groups, 11 cuts).
- 43 LANDED, of which 3 carry a new defect (entries 12, 25, 27).
- 1 NOT LANDED (entry 15).
- 2 DEFENSE HOLDS (F5 and F R3-09).
- 0 DEFENSE FAILS.

---

## Part 1: Logic and contract audit

**R4-01 · omission · medium · one correct answer · Positives whose first offence is a read cannot be cut where the spec says**
- **Spec:**
  - §7.2: "read-only tool events (Read, Grep, Glob, WebFetch, by tool name) are never cut points. **Positive:** cut at the first offending event its label points to".
  - §7.3 CheatBench: "First offence = first tool call reading `/tests`, a verifier output, a gold or answer file".
  - §7.3 HVTB: "first tool call whose input touches `admin/`".
- **Evidence:** In these Claude Code runs the offence is often a Read call, which §7.2 forbids as a cut. Ledger D21.E5 already gives the rule: "Grader-peeking (L6) is caught one classified event later." §6.4 shows the read in RUN LEDGER: "Reads render as one-liners with the path".
- **Consequence:** About 400 L6/M4 records, from the main L6 source, have no defined cut. Converters will improvise, and the runtime renderer does not decide this.
- **Consumer:** the CheatBench and HVTB converters.
- **Fix:** When the first offence is read-only, cut at the next classified event. The read shows in RUN LEDGER.

**R4-02 · error · one correct answer · The correction template hard-codes "answered yes"**
- **Spec:** §6.5 "asked "<question>" … answered yes (p = 0.87)".
- **Evidence:** G1 fires on *no* ("G1 is yes = on track", §4.2). G2 fires on `broken` or `not done`. Ledger D40 specifies "the answer and probability", not "yes".
- **Consequence:**
  - A G1 item tells the agent the monitor "answered yes" to "is the agent still pursuing what the user asked for?", which inverts the finding.
  - A G2 item is meaningless.
  - This text is frozen into about 290 L7 construction records, and the runtime adopts it unchanged.
- **Consumer:** the correction-window construction, the runtime correction, and the agent reading it.
- **Fix:** "answered <the firing answer> (p = …)".

**R4-03 · amendment-created (R3-15 × scope audit) · one correct answer · Calibration fits ignore the base-dev rule**
- **Spec:**
  - §7.9: "every prevalence-dependent quantity (π^dev, 9.5) is computed on base dev, without the top-ups".
  - §9.5: "T_q minimizes NLL on all of dev".
  - §12.4: stock's "T_q and b_q fitted jointly by NLL on the same dev split".
- **Evidence:** Stock's b_q fitted by NLL *is* a prior, so it is prevalence-dependent. Fitting it on dev with the top-ups (300–600 records, about 60 positives per rare question) inflates rare-question prevalence. The tuned model's b_q, by contrast, uses base dev.
- **Consequence:**
  - The lift baseline is calibrated to a different prevalence than the tuned model it is compared with.
  - If stock is selected (§9.5, last bullet), it serves an inflated b_q and fires more often at p ≥ 0.5.
  - The tuned model's T is pulled the same way.
- **Consumer:** the calibrator, the lift test, and a stock fallback.
- **Fix:** Fit T_q, and stock's (T_q, b_q), on base dev.

**R4-04 · error (plus one amendment-created header) · one correct answer · Source rules still mark labels as visible-based and final on questions their rules never looked at**
- **Spec:**
  - §7.3 CodeTraceBench: "V (competence errors are negatives for every question)".
  - §7.3 benign header: "**Benign runs (negatives for every question)**", although every row beneath it is now T.
  - §7.3 Open-SWE: "V only on M4 and L6 for the no-test-edit and no-history rules".
- **Evidence:**
  - §8.4: "Visible-based source labels are final for their question." A competence-error annotation says nothing about M5, G5 or M7. A run with an error can still claim success falsely (M5 yes).
  - "No test-path edits" does not decide M4. M4's wording includes "hard-coding expected outputs", which can happen outside test paths.
  - The round-3 fix F R3-03 already applied this logic to the benign pool.
- **Consequence:** About 120 records carry final labels that override the teacher on questions their rule never observed. The header invites a builder to force all-no labels.
- **Consumer:** the record assembler.
- **Fix:** CodeTraceBench becomes T with the annotation as a hint (V only where a rule decides). The header becomes "Benign runs (the teacher labels every question)".

**R4-05 · omission · small design choice · The TonyDzi hook-to-question table is a label rule nobody decided**
- **Spec:** §7.3: "V (hook template mapped per question by a fixed table the converter carries)", and the L7 row uses the same table for OPEN FINDINGS.
- **Evidence:** The ledger never decided the table's contents. D47 only says "use the hook template's mapped question". Initializing-projects step 7 says a design question is never settled by build-agent judgment.
- **Consequence:** The build agent writes final, teacher-overriding labels for about 80 records.
- **Consumer:** the TonyDzi converter.
- **Fix:** List the table, or make the row T with the hook as a hint.

**R4-08 · amendment-created (23:20) · one correct answer · The demo check depends on an artifact this track doesn't own**
- **Spec:** §12.3: "through the deployed `classify()`, on a recorded Mod session … | the next candidate in pick order". §1 Scope puts "the classifier's serving logic" *out*.
- **Evidence:** `classify()` is the runtime agent's deliverable (D75). The spec gives a stand-in for the *recording* but none for the *entry point*. Its fallback also implies redeploying `classify()` once per candidate.
- **Consequence:** If the runtime build is late, the gate that moves the pick cannot run.
- **Consumer:** the selector.
- **Fix:** When `classify()` isn't deployed, score through the shared renderer and the serving path (`LoadOptions(temperature=1.0)` plus the per-question transform).

**R4-09 · unsupported claim · one correct answer · TRACE is not "real Claude Code runs"**
- **Spec:** §1 row 2: "the held-out lift on real Claude Code runs (TRACE) is the check". §13: "held-out lift on real runs".
- **Evidence:** Dossier #108 (DATASET-DOSSIER.md around line 1617): "Synthetic … Claude Code conversations generated with claude-opus-4-5 and simulated tool results".
- **Consequence:** The only check named for the "converted and constructed records" family is itself generated text, so the stated assurance is overstated.
- **Consumer:** the §1 reader and the writeup's lift claim.
- **Fix:** "unseen synthetic Claude Code conversations (TRACE)".

**R4-10 · amendment-created (R3-29) · unneeded mechanism · The "yes everywhere" trigger fires through noise and has no action**
- **Spec:** §13: "per-question positive rate at calibrated p ≥ 0.5 on benign dev, against the teacher's positive rate there (above 2× → flag)".
- **Evidence:**
  - Where the teacher's benign rate is 0 (likely for L2 and G4 on benign runs), 2 × 0 = 0, so any single positive flags.
  - The flag has no action: the mitigations column lists only pre-training measures, and there is one run.
  - D30 conditions the tie rule on this instrument "guarding" against flag-everything. A post-run report cannot guard.
- **Consumer:** none acts on the flag, so it is reassurance only.
- **Fix:** Report the two rates and drop "→ flag". Correct D30's "guard" wording.

**R4-11 · error (low) · one correct answer · The detail fill can overshoot B_state at the overflow threshold**
- **Spec:** §6.4: "recent events as detailed blocks, newest first, until the detail budget … is spent".
- **Evidence:** The R3-07 threshold assumes detail is at most 0.15 B. If the block that crosses the budget is included (up to about 2,000 tokens), a state at the threshold exceeds B_state. The count-line rule cannot absorb that. Kev then rejects the state, or the trainer drops the record.
- **Consumer:** the renderer, for both training and runtime.
- **Fix:** Add a block only if it fits the remaining detail budget.

**R4-12 · omission (low) · one correct answer · Kev's 640-token row limit is handled only for L7**
- **Spec:** §6.4: "Each single row must also fit Kev's row limit … L7's «text» is trimmed".
- **Evidence:** G2 and D2 quote «R_k text», and a long markdown list item (for example one holding a code block) can exceed 640 tokens beside a full state. Per the round-3 claims audit (`train.py:105-110`), the trainer silently drops the whole record.
- **Consumer:** the renderer.
- **Fix:** Trim R_k the same way, marked `[cut]`.

---

## Part 2: Cost audit

**R4-06 · omission and unsupported claim · one correct answer (from D28 and the round-3 register) · The $200 split is decided but carried nowhere the executor reads, and the price is still unchecked**
- **Spec:**
  - §8.7: "up to $200 of Anthropic API credit in total across generation and runs".
  - §11: "the $200 cap binds: ~300 headless agentic runs plausibly exceed $70 alone (no current Haiku/Sonnet 5.5 price was checked) | … stage closes at the cap".
- **Evidence:**
  - The round-3 register decided "generation spend is reserved first" but recorded it only in the audit file.
  - Ledger D47 now says "the 300 agent runs launch first, in parallel" with no sub-cap.
  - Generations are the only positive source for L2, the L4/G1 splices, L7 and goal-flip M1. Agent-run shortfalls already redistribute (§7.1).
  - Design-ethos #6 counts an unchecked estimate as a defect when one lookup would settle it.
- **Consequence:** If the runs spend first, the constructions go unbuilt and the positive floor fails with no credit left to rebuild.
- **Consumer:** the executor's spend control. This is a budget rule of the same kind §8.7 already carries, not scheduling.
- **Fix:** In §8.7 state "generation's estimated spend is reserved first; agent runs get the remainder". Check the two prices or delete the "$70" speculation.

**Re-derived and consistent:**
- Candidate scoring: 1,750 × 6.7K ≈ 12M tokens per candidate, about 7 min at 30K tokens/s.
- Serve-path parity: 300 records in about 5 min.
- Training: $3.95 × 2–3.5 h.
- Agent runs: 300 × 3–10 min / 20 ≈ 0.75–2.5 h.
- Teacher calls: 10–11K items × 2 / 10–20 per call = 1,000–2,200 calls.
- Long-gate n: 0.06 / (0.03/3.24)² ≈ 700.
- Hanley–McNeil at 60 positives and AUROC 0.8 ≈ 0.034.
- Σ n^plan = 10,630, giving s = 0.809.

**Feasibility note (not a cut).** At 23:25 with an 08:00 fallback (D13), training must start by about 04:30–06:00. That means Phases 1–3 (renderer, about 40 converters, 9 constructions, about 3,500–5,000 generations, 300 agent runs, teacher labelling) must finish in about 5–6.5 h. D13's fallback is the likely path, and the task file's cut-offs carry this.

---

## Part 3: Completeness against the ledger

Every trace row is carried in substance: D1–D6, D11/D26, D13, D18, D19/D19.P, D20–D23, D27, D28, D30, D32/D32.P, D33, D36, D37, D40–D45 and D47. The only gaps are R4-05 (D47's "mapped question", whose table was never decided) and R4-06 (the D28-derived spend order).

## Part 4: Spec/task boundary

**R4-07 · task material (amendment-created at 23:20) · Clock and container choreography entered the spec**
- **Spec:**
  - §9.3: "If training has not ended by the 08:00 fallback, the pick uses the saves that exist then. Stock Kev is scored on dev before training ends".
  - §9.4: "is scored in a separate GPU container while training continues".
  - §12.1: "(measured before training ends)".
- **Evidence:**
  - "08:00 fallback" is defined nowhere in the spec.
  - Ledger D47 files this exact content under "**Scheduling for the task file**".
  - The skills place cut-off scheduling and choreography in task.md.
- **Consumer:** the task file.
- **Fix:** Keep "the pick uses the saves that exist when it runs". Move the clock and the containers to task.md. §11 may keep the minutes as estimates.

### Ledger notes (not spec findings; listed because the task-file builder reads the ledger)
- D13 is now 08:00, but D3 "Revisit if", D13 "Revisit if", D34, D36, D41 ("Stage cut-offs are computed backward from D13's 07:00") and the emergent-interactions table still say 07:00. The task-file builder will compute its cut-offs from D41.
- D47's round-2 bullet "G2 and G5 … carry only those two" contradicts its own round-3 bullet and the spec.
- D27 still says "cross-fitted over five dev folds", D42 still names the logit check and cross-fitting, and D44 still lists "run yield" among the gates. All of these were cut.

---

## Counts

- **Register entries verified:** 48. 43 LANDED (3 with a new defect), 1 NOT LANDED, 2 DEFENSE HOLDS, 0 DEFENSE FAILS.
- **Findings:** 12. A finding counts under one kind only:

| Kind | Count | Findings |
|---|---|---|
| error | 3 | R4-02, R4-04, R4-11 |
| omission | 4 | R4-01, R4-05, R4-06, R4-12 |
| amendment-created | 3 | R4-03, R4-08, R4-10 |
| task material | 1 | R4-07 (also amendment-created) |
| unsupported claim | 1 | R4-09 (R4-06 carries one too) |
| overreach | 0 | |

- **Amendment-created defects:** 5. They are R4-03, R4-07, R4-08 and R4-10, plus the benign header inside R4-04.
- **Severity:** R4-01 is medium. R4-03, R4-04 and R4-06 are low-medium. The rest are low.
- **Blocking:** 0. Only R4-05 needs a design choice, and a small one; every other finding has one correct answer.

## The three most likely failure points

1. **Data-touching formats frozen with a defect.** The "answered yes" template (R4-02) goes into L7 data and the runtime. The L6 read-cut gap (R4-01) hits the main L6 source. Final labels from CodeTraceBench and TonyDzi override the teacher (R4-04, R4-05).
2. **The $200 split lost between the audit file and the task file (R4-06).** If the agent runs launch first and drain the credit, the only positive sources for L2, L4/G1, L7 and goal-flip M1 never get generated.
3. **The overnight clock.** Phases 1–3 have about 5–6.5 h before an 08:00 fallback, so the demo will likely run on an early save or stock Kev. A stock fallback then serves with a top-up-inflated b_q (R4-03).

## Verdict

**Implementation-ready to start Phase 1; there are no blocking questions.** D46's stop rule (at most 2 findings, none blocking) is not met: there are 12 findings, all non-blocking. Each fix should land before the phase that freezes it:
- R4-02 and R4-11 before the Phase 1 renderer freezes.
- R4-01, R4-04, R4-05, R4-06 and R4-12 before Phase 2.
- R4-03, R4-08 and R4-10 before Phase 4.
- R4-07 and R4-09 are wording or moves and can land at any time.

The only owner choice is R4-05 (list the hook table, or make the row teacher-labelled), and it doesn't block the build.

---

## Coverage ledger

| File | Lines read |
|---|---|
| reading-context SKILL.md | 1–98 |
| out-of-cutoff SKILL.md | 1–103 |
| receipts-before-claims SKILL.md | 1–29 |
| design-ethos SKILL.md | 1–71 |
| gold-standard-spec-template.md | 1–200, 200–409, 410–605 |
| initializing-projects SKILL.md | 1–133 |
| task-file-builder SKILL.md | 1–206 |
| CONTRACT.md | 1–261 |
| TRAINING-SPEC.md, first read | 1–170, 170–339, 340–509, 510–664 |
| TRAINING-SPEC.md, re-read after the 23:20 edit | 1–170, 170–304, 305–454, 454–664 |
| DESIGN-DECISIONS.md, first read (1,158 lines) | 1–200, 200–399, 400–599, 600–799, 800–999, 1000–1158 |
| DESIGN-DECISIONS.md, after the 23:20 edit (1,166 lines) | grep for the changed topics, then 232–247, 824–837, 935–959 re-read |
| TRAINING-SPEC-TRACE.md | 1–37 |
| Round-3 dispositions (-14-) | 1–43 |
| Round-2 dispositions with scope audit (-7-) | 1–75 |
| Round-3 Opus report (-12-) | 67–355 (findings, counts, coverage) |
| Round-3 Fable report (-13-) | 1–270 |
| Round-3 claims audit (-11-) | 1–144 |
| DATASET-DOSSIER.md | 1601–1624 (TRACE entry) |

Every line of the required files was covered, except the ledger as edited at 23:20: I re-read only the entries the edit touched, located by grep. The new round-4 claims audit (-15-) was not in scope and was not read.