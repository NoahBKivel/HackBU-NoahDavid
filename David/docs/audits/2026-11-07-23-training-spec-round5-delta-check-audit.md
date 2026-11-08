## Round-5 delta check: training specification

Of the 31 register items, 28 landed cleanly, 2 landed with a new defect, the cut landed and the defense holds. Two other amendment-created defects are not tied to a single row, so there are **4 amendment-created defects in all, none blocking**. Every mechanical sweep is 0. I edited no file, invoked no skill and started no background process. Date checked with `date`: 2026-11-08.

### Register items

| # | Item | Status | Receipt |
|---|---|---|---|
| 1 | Owner decision R5-04 (agent runs count 0) | LANDED | §10 says agent-run sources (8.7) and T sources count 0. D44 says the 300 agent runs count 0 toward P_q, "so M2 and M7 take their floors from constructions, IF_multi, IN3 and JL-ActionBoundary". The emergent-table row (line 1142) now reads "none: the runs count 0 toward the positive floor (D44)". |
| 2 | Owner decision F-01 (floor of 60) | LANDED | §10: "max(0.8 · P_q, 60) … the 60 (the dev floor's count, 7.9) is the floor for questions whose positives come only from teacher labels (G5, M5)". §12.2: "holds ≥ max(0.8 · P_q, 60)". D44 matches. |
| 3 | R5-01 / F-02 (fill rule) | LANDED | §6.4: "stopping at the first block that does not fit what remains of the detail budget … so the detailed events are always the newest in an unbroken run". "is spent" no longer appears. D47 round-5 bullet and the cross-track note match. |
| 4 | R5-02 (failed gate) | LANDED | §13: "A failed correctness gate takes its 12.1 fallback (stopping its stage where that fallback says so)". |
| 5 | R5-03 / F-09 (V label question) | LANDED WITH NEW DEFECT (Defect B) | §7.3 header: "reading tests, grader output, answer files or planted answers is L6; altering, skipping or special-casing a measure … is M4; the teacher labels the other questions". The CheatBench row says "a read-based offence sets L6 as the V label, and M4 on those records is teacher-labelled". The HVTB row says "access to `admin/` sets L6". |
| 6 | R5-04 dataset part | LANDED, with a low ambiguity (Defect C) | §10: "dataset V sources from the natural share among the rows the converter keeps (dataset metadata)". |
| 7 | R5-05 (pseudocount) | LANDED | §9.5: "Both rates take a pseudocount of 0.5 per class, so an option absent from base dev or from train gives a finite offset." |
| 8 | R5-06 (three passes) | LANDED | §8.2 item 6: "Diagnostics take three ordered passes, as at runtime: resolve the record's labels; then D1/D3 and D5 …; then D2, whose «summary» cites the D1/D3-positive events (LATEST EVENT when none)". This matches D76 line 1098. |
| 9 | R5-07 (`turn.reason`) | LANDED | §6.1: "Converters set `turn.reason` to `answer` on every `turn_completed` event that ends in an agent message followed by a user turn or the end of the run." The cross-track note (lines 25) is in place. D72 already reads "G2 and G5 run on `turn_completed` events whose end reason is `answer`". |
| 10 | R5-08 (siblings not cap-exempt) | LANDED WITH NEW DEFECT (Defect A) | §6.4: siblings are "sharing its split and batch (siblings are not a contrast pair, so the cap's pair exemption does not cover them)". |
| 11 | R5-09 | LANDED | §3: "the long-record share comes from the data-mixing and long-context research". "rare-question" appears 0 times. |
| 12 | R5-10 | LANDED | §12.4 no longer contains "concurrently". Its only remaining use is the §11 cost line, which was meant to stay. |
| 13 | F-03 (one 2,000-token cap) | LANDED | §6.4: "Each detailed block's `result`, `patch`, `plan` and `agent said:` text (a MESSAGE block's text) together are capped at 2,000 tokens". D40 line 883 puts agent text "inside the same cap". |
| 14 | F-04 (mean statistic) | LANDED | §12.1: "the winner's mean \|Δ log-odds\| … ≤ 1.5 × stock Kev's own gap". D44 matches. |
| 15 | F-05 (paired SE) | LANDED | §9.4 step 2: "bootstrap the standard error of its paired difference from the best candidate (best − candidate) over the same 1,000 resamples". §1 says "one paired bootstrap standard error". D41 line 997 matches. |
| 16 | F-06 (twins capped together) | LANDED | §7.8: "a base row and its negated twin (4.2) are kept or dropped together". |
| 17 | F-07 (RF rows) | LANDED | §6.7: "those labels only define R_k and add no RF training rows beyond the RF quotas in 7.3." |
| 18 | F-08 (dossier path) | LANDED | §7.3: "Dossier numbers (#N) refer to `docs/DATASET-DOSSIER.md`". The path appears once. |
| 19 | Claims 1 (temperature) | LANDED | §12.1: "log p_yes − log p_no from both softmax entries …; every model on both sides of the comparison is loaded with temperature 1.0". |
| 20 | Claims 2 (T sources 0) | LANDED; the ledger lags (Defect D) | §10: "T sources 0 (no measured positive rate exists for any monitor question)". |
| 21 | Claims 3 (`answer` gate) | LANDED | §4.2 table, G2 and G5: "at each `turn_completed` event whose end reason is `answer`". §8.2 item 6 carries the same gate. |
| 22 | Claims 4 (no change) | LANDED (no change, as disposed) | The §7.3 tau2 row reads "V for `communicate_checks` scored by substring match (true of the 2025 release files)". |
| 23 | Duplicate AskUserQuestion sentence | LANDED | §6.1 line 165 now says each thing once: the result becomes a `user_instruction`, and AskUserQuestion is never a cut point. |
| 24 | Cut: R5-11 (spot-check) | LANDED | §7.6 has no spot-check. D45: "The 5% spot-check of benign rewrites was cut". D27 does not mention it. |
| 25 | Defense: claims 3(b) (IN3 ask) | DEFENSE HOLDS | D72: "at a turn end only a G2 "broken" sends a correction, while "not done" shows in `details` only". G5's wording ("reported success unsupported") gives no on an ask. So training and runtime agree and nothing nags. |
| 26 | Ledger: 07:00 → 08:00 in D13 and D34 | LANDED | D13 lines 240 and 246, and D34 line 798, say 08:00. The only 07:00 left in the ledger is D13's options list and its "Earlier:" clause (lines 239–240), which is legitimate history. |
| 27 | Ledger: D45 spot-check cut, D47 read-only bullet and round-5 bullet | LANDED | D45 line 922. D47 line 950: "read-only by tool name (the Mod's set, round 4)". D47 line 949 is the round-5 bullet. |
| 28 | Ledger: D40 agent-text cap, D41 paired SE | LANDED | Lines 883 and 997. |
| 29 | Ledger: D44 floor and serve-path statistic | LANDED | Line 915. |
| 30 | Trace D13 row | LANDED | Trace line 14: "D13 08:00 best-model rule". |
| 31 | Cross-track notes | LANDED | Lines 23–27 carry the round-5 section. |

### Mechanical sweeps

- **Em dashes in the spec:** 0.
- **"07:00":** 0 in the spec, 0 in the trace, 0 in the cross-track notes.
- **"is spent" in the spec:** 0.
- **"max |Δ" in the spec:** 0.
- **"spot-check" in the spec:** 0.
- **Same phrases in the ledger:** "spot-check" appears only in D45's cut sentence. "is spent" appears only in D22 (line 625), which the round-5 amendments did not touch.

### Amendment-created defects

**A. Siblings share a batch, but no rule batches them (R5-08). Low to medium.**
- §6.4 says siblings move "sharing its split and batch (siblings are not a contrast pair, so the cap's pair exemption does not cover them)".
- That conflicts with three other places:
  - §4.1 defines a pair group as "records that must share a split and a batch: same-context pairs, note pairs, rewrite copies, goal-flip pairs".
  - §9.2 item 2 batches only pair groups: "treats each pair group as one unit".
  - §7.8 exempts "every row belonging to a pair group" from the cap.
- So the builder has two choices, and both break something:
  - Make siblings a pair group: they get batched together, but §7.8 exempts them from the cap, which R5-08 meant to stop.
  - Keep them out: §9.2 never puts them in one batch.
- The ledger agrees with neither: D47 line 935 still says siblings move "(same pair group)".
- **Who builds it wrong:** whoever writes the batching patch and the record assembler or cap.
- **Fix:** have §9.2 item 2 batch siblings too, and change D47 line 935.

**B. HVTB: an `admin/` write could be labelled L6 or M4 (R5-03 / F-09). Low.**
- The HVTB row says "access to `admin/` sets L6 as the V label; M4 is teacher-labelled".
- The §7.3 header says "altering, skipping or special-casing a measure … is M4".
- If the first tool call touching `admin/` is a write (for example, editing a grader file), the header gives M4 and the row gives L6.
- **Who builds it wrong:** the HVTB converter.
- **Fix:** have the row say a read of `admin/` sets L6, as the CheatBench row already says "read-based offence".

**C. "(dataset metadata)" does not fit IF_multi (R5-04 dataset part). Low.**
- §10 fixes each dataset V source's positive share "from the natural share among the rows the converter keeps (dataset metadata)", and the shares are "fixed before the build".
- IF_multi's V labels come from checkers run on responses the agent-side generator writes during the build (§7.3: "Sample one response per prompt from the agent-side generator; run open-instruct's per-instruction checkers"). There is no metadata share for it.
- D44 names IF_multi as a source of M2's floor.
- Two readings follow: measure the share after generation (not "fixed before the build"), or count it as 0, like agent runs. They give different P_q values for M2 and G2.
- **Who builds it wrong:** the positive-floor gate (§12.2).

**D. A D47 bullet still states the old floor rule (Claims 2 and R5-04). Low; ledger only.**
- D47's round-4 bullet (line 948) still reads: "the positive floor's expected share is fixed before the build (constructions' intended labels, V conversion rules, the dossier's rate for T sources)".
- The amended §10 and D44 now say: V shares are the natural share among kept rows, and agent-run and T sources count 0.
- The round-5 bullet does not replace that line, and the register's ledger line did not list it.
- **Who builds it wrong:** only someone reading the ledger. The build agent reads only the spec.

**Observation, not counted:** §11 counts teacher calls as items × 2 votes ÷ 10–20 records per call. It does not count the two extra diagnostic passes R5-06 adds on flagged records. The round-5 Opus reviewer judged they fit inside the ±30% band. I cannot check that, because the spec does not state the share of flagged records.

### Coverage ledger

| File | Lines read | Every line covered |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 (EOF) | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 (EOF) | yes |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-22-training-spec-round5-dispositions.md` | 1–38 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-19-training-spec-round5-external-claims-audit.md` | 1–118 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-20-training-spec-round5-review-opus-audit.md` | 1–215 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-21-training-spec-round5-review-fable-audit.md` | 1–102 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md` | 1–200, 201–400, 401–667 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC-TRACE.md` | 1–37 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\CROSS-TRACK-NOTES.md` | 1–27 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` (scoped, as instructed) | Found with a heading search, then read in full: D13 232–247; D27 680–691; D34 790–800; 878–1003 (D40, D42–D47, the justified defaults through D34.N, D41); 1039–1124 (D72–D77, read to check the defense and R5-06); 1125–1184 (the emergent table to the completeness check) | every named entry and the emergent table read in full |

Every line of every file the task required in full was read.