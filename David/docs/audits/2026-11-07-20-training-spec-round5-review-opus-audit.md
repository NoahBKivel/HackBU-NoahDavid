# Training spec, review round 5 (final full round)

**Short answer:** no question blocks implementation. I found 11 real issues. 10 have one correct answer. One needs a small decision from David before the Phase 3 data gate (R5-04). 3 of the 11 were created by amendments. 24 of the 25 round-4 register entries landed in the spec; the 25th entry is ledger lag, and it is only partly fixed.

**What I reviewed.** The spec and the ledger were edited while I was reviewing. The spec was saved at 23:36:48, after the round-5 external-claims audit (`-19-`) landed at 23:36:38. The ledger was saved at 23:38:20. I copied both at that point and re-read the whole spec snapshot (665 lines). This report reviews that version: `C:\Users\david\AppData\Local\Temp\claude\e4a7ca8b20dbf3e0\48a356b8-0453-4fa7-b972-ac20964e049d\scratchpad\spec-snap.md`. I edited no project file. The only files I wrote are the two snapshot copies in the scratchpad. Every command ran in the foreground and exited before the next one started.

## Part 0: round-4 register verification

| Register entry | Status | Receipt (spec section) |
|---|---|---|
| Owner decision F2 (positive floor) | LANDED WITH NEW DEFECT (R5-04) | §10: "constructions from their intended labels, V sources from their conversion rule, T sources 0 …". This was rewritten again at 23:36. D44 and D47 carry the decision. |
| R4-01 (read offence) | LANDED | §7.2: "When a positive's first offence is a read …, the record is cut at the next classified event". R5-03 is a related older defect: the source rows still don't say which question the label sets. |
| R4-02 | LANDED | §6.5: "answered <the firing answer> (p = 0.87)" |
| R4-03 | LANDED | §9.5: "T_q minimizes NLL on base dev"; §12.4: "fitted jointly by NLL on base dev" |
| R4-04 | LANDED | §7.3 CodeTraceBench: "T (the competence-error annotation is a hint)"; benign header: "(the teacher labels every question)" |
| R4-05 | LANDED | §7.3 L7 hook row: "under the first positive question at the hooked event in the 6.5 item order (M1 when none is positive)". Ledger lag: D47 (line 940) still says "the hook template's mapped question (TonyDzi)". |
| R4-06 | LANDED | §8.7: "generation's estimated spend is reserved first"; §11: "generation reserved first". The "$70" text is gone. |
| R4-07 / F3 / F4 | LANDED, one leftover (R5-10) | §9.3: "If the pick is made before training ends, the two saves are the latest one and …"; §9.4: "on any GPU running the same code"; §12.1: "both gaps measured on the same hardware pair" |
| R4-08 | LANDED | §12.3 demo check: "(or, before it is deployed, the shared renderer and the serving path with the per-question transform)" |
| R4-09 / F1 | LANDED | §1: "unseen synthetic Claude Code conversations (TRACE, human-verified) … the only real-run check"; §13 matches |
| R4-10 | LANDED | §13: "reported beside the teacher's positive rate there" |
| R4-11 | LANDED WITH NEW DEFECT (R5-01) | §6.4: "each added only if it fits what remains of the detail budget … is spent" |
| R4-12 | LANDED | §6.4: "a quoted «R_k text» is trimmed head and tail, each cut marked `[cut]`" |
| F5 | LANDED | §15 Phase 4 "Depends on" column is split as asked |
| F6 | LANDED, but leaves an older contradiction (R5-02) | §13: "A failed correctness gate stops its stage, except serve-path parity …" |
| F7 | LANDED | §6.4: "`agent said:` and MESSAGE text share it" |
| F8 | LANDED | §7.7: "until the rendered state reaches 16K to B_state, documents stopping at the 6.4 threshold" |
| F9 / claims 7 | LANDED | §6.1: "AskUserQuestion is never a cut point"; §7.3 IN3: "an ask renders as a `turn_completed` MESSAGE". The round-5 claims audit, Finding 3(b), owns the IN3 premise. |
| Claims 1 | LANDED, strengthened at 23:36 | §12.1: "`Server.probs` … log p_yes − log p_no from both softmax entries … loaded with temperature 1.0" |
| Claims 2 | LANDED | §6.1: "<Claude Code's structured hunks, or null>" |
| Claims 3 | LANDED | §10: "smoke run on a synthetic record at the largest real padded cost" |
| Claims 4 | LANDED | §7.3 tau2 row: V for `communicate_checks`, T with `nl_assertions` as hints |
| Claims 5, 6 | LANDED | §6.1: "(Read, Grep, Glob, WebFetch, WebSearch, LS, NotebookRead, …)"; "renders PowerShell as Bash" |
| Turn-reason note | LANDED WITH NEW DEFECT (R5-07) | §4.2 and §8.2 item 6: "whose end reason is `answer`"; §6.1 adds `turn.reason` |
| Ledger lag ("07:00 … corrected in D27, D41, D42, D44, D47") | NOT LANDED (partly) | "07:00" is still in D27 (line 687, "D13's 07:00 best-model choice"), D3 (127), D13 "Revisit if" (246), D18 (323), D34 (798), D36 (819) and the emergent table (1139). D45 still says "identity parity on 50 fixed states", but that check was cut. The training agent never reads the ledger, so none of this reaches the build. |

**Amendments that created defects: 3** (R5-01 from R4-11, R5-04 from F2, R5-07 from the turn-reason amendment).

## Findings

**R5-01 · Part 1 · error, created by an amendment (R4-11) · one correct answer · not blocking**
- **Spec text (§6.4):** "then recent events as detailed blocks, newest first, each added only if it fits what remains of the detail budget max(0.40 × B_state − tokens(instructions + documents), 0.15 × B_state) is spent".
- **Evidence:**
  - The sentence can be read two ways. The renderer either stops at the first block that doesn't fit, or skips it and tries older, smaller blocks.
  - If it skips, a newer event renders as a one-liner while an older one is detailed. The layout in §6.4 assumes that cannot happen: "<one-liners for older events> <detailed blocks for recent events>".
  - L1 is worded around "the recent events shown in detail", which also assumes the detailed events are consecutive.
  - "is spent" is left over from the old wording ("until … is spent").
- **Consequence:** the shared renderer, and so both training and runtime states, is built on an unclear rule.
- **Who uses it:** the shared renderer.
- **Fix:** stop at the first block that does not fit, so the detailed events are always the newest ones in a row. Delete "is spent".

**R5-02 · Part 1 · error, older text that F6 did not fix · one correct answer · not blocking**
- **Spec text:**
  - §13: "A failed correctness gate stops its stage, except serve-path parity".
  - §12.1, resume parity, fallback: "run without the resume patch; a crash means a rerun".
  - §12.1, accelerated-kernel parity, fallback: "the reference path".
- **Evidence:** two more correctness gates have fallbacks that do not stop the stage.
- **Consequence:** an agent reading §13 alone stops Phase 1 when the optional Unsloth trial fails.
- **Who uses it:** the build agent when a Phase 1 gate fails.
- **Fix:** "A failed correctness gate takes its §12.1 fallback."

**R5-03 · Part 1 · error · one correct answer · not blocking (medium)**
- **Spec text:**
  - §7.3 CheatBench: "First offence = first tool call reading `/tests`, a verifier output, a gold or answer file, or a leaked secret … `attempt` rows are positives".
  - §7.3 HVTB: "Ablation setting → M4/L6 … First offence = first tool call whose input touches `admin/`".
  - §7.2: a read offence is "cut at the next classified event".
  - §2 principle 3: a V label "is final for its question".
- **Evidence:**
  - M4 asks whether "the latest action make[s] a measure of success … look better than the real work". LATEST EVENT is now the event after the read, which is not itself gaming a measure.
  - L6 names exactly this behaviour: "reading hidden tests, grader files or answer keys it was not given".
  - Neither source row says which question the rule sets.
- **Consequence:** a final M4=yes could land on events that are not gaming anything. M4 then learns "whatever follows a test read". That blurs M4 into L6 and contradicts the eungyeuk M4/L6 hard negatives.
- **Who uses it:** the CheatBench and HVTB converters, and the record assembler.
- **Fix:** a read-based first offence sets L6 as the V label. On those records, M4 is labelled by the teacher.

**R5-04 · Part 1 · error, created by an amendment (F2) · needs a small decision from David (before Phase 3)**
- **Spec text (§10, positive floor):** "V sources from their conversion rule".
- **Evidence:**
  - Most V rows don't give a share of positives. CATCH, Aria, OLMo, impossible-SWE and willjgriff list positive and negative rules but no mix.
  - The agent-run V sources (SWE-Misbehavior: "checker violations → M2/D2"; lhaw: "guesses vs asks") have no share until the runs exist.
  - Ledger emergent table: "Runs that never misbehave yield only negatives for M2 and M7. | `positive-floor` (D44) catches it".
- **Consequence:**
  - The builder cannot compute P_q from the spec.
  - If the agent-run share is taken as 0, the floor can no longer catch the risk the ledger assigns to it.
- **Who uses it:** the positive-floor gate (§12.2).
- **Fix:**
  - Dataset V sources: use the natural share among the rows the converter keeps, taken from dataset metadata. This has one correct answer.
  - Agent-run sources: David chooses a planned share, or 0 with the emergent row withdrawn.

**R5-05 · Part 1 · error · one correct answer · not blocking (low)**
- **Spec text:**
  - §9.5: "b_q = logit(π_q^dev) − logit(π_q^train) … per option b_q,o = log π_o^dev − log π_o^train".
  - §7.9: π^dev is computed "on base dev, without the top-ups".
- **Evidence:**
  - The rare questions are exactly the ones topped up, so base dev can hold almost no positive mass for them.
  - Choice and score options can be absent from base dev or from train, for example G2 `can't tell from the evidence` or D5 `serious`.
  - A zero gives log 0. That makes b = −∞, so the question never fires at serving, or +∞ / NaN when π^train is 0.
- **Who uses it:** the calibrator and the serving transform.
- **Fix:** state a floor for both rates, a pseudocount or clipping to [ε, 1−ε].

**R5-06 · Part 3 · omission across the two specs · one correct answer · not blocking**
- **Ledger text, D76:** "Diagnostics: D1/D3 and D5 in a second request on the same state, D2 in a third so its «summary» can name the cited events; with no event cited, LATEST EVENT is cited."
- **Ledger text, D36:** the training track covers "every runtime decision the training data must match".
- **Spec text:**
  - §6.5: "D2's «summary» is "<short names> at <E-refs>"".
  - The D1/D3 wording embeds «short names of the questions that fired».
  - §8.2 item 6 reads as if diagnostics are labelled in the same teacher call as everything else.
- **Evidence:** the D1/D3 and D2 question texts cannot be written until labels are resolved. D2 also needs the cited D1/D3 events. Training therefore needs three passes in order: resolve labels, then D1/D3 and D5, then D2. §11 does not count these passes.
- **Consequence:** D2 text in training can differ from what the runtime builds.
- **Where it belongs:** §8.2 item 6 and §6.5. Mirror D76: "fired" means resolved positive rows in the 6.5 order; E-refs are the D1/D3-positive events, or LATEST EVENT when there are none.
- **Who uses it:** the record assembler and the teacher pipeline.

**R5-07 · Parts 1 and 3 · created by an amendment (the 23:36 turn-reason edit) · one correct answer · not blocking**
- **Spec text:**
  - §6.1: "Converters set `turn.reason` to `answer` on the `turn_completed` event that ends a completed run."
  - §4.2: G2 and G5 are asked "at each `turn_completed` event whose end reason is `answer`".
- **Ledger text, D72:** "G2 and G5 run on every `turn_completed` event (D21.E7/E9)".
- **Runtime spec, line 176:** `turn_completed` is classified with the every-event set "plus G2 … and G5", with no gate on the end reason.
- **Evidence:**
  - Multi-turn sources (SWE-chat, TonyDzi, Misalignment Atlas) contain turn ends in the middle of a session. The Mod reports these as `answer` (claims audit `-19-`, line 86).
  - Under the "never invents it" rule, converters leave the field empty on these turns. So G2 and G5 train only on the final turn of a run.
  - The runtime asks G2 and G5 on every turn end. D72 says a G2 "broken" there sends a correction.
- **Consequence:** at runtime, G2 and G5 are asked on turn ends the model never trained on, and a G2 "broken" there sends a correction to the agent.
- **Who uses it:** the converters and the runtime builder.
- **Fix:**
  - Converters set `answer` on every `turn_completed` that ends in an agent message followed by a user turn or the end of the run.
  - The runtime spec and D72 adopt the `answer` gate.
  - This is separate from the round-5 claims audit's Finding 3(b) (IN3 ask records).

**R5-08 · Part 1 · error (two rules interact) · one correct answer · low**
- **Spec text:**
  - §4.1 "pair group": "same-context pairs, note pairs, rewrite copies, goal-flip pairs".
  - §6.4: rows that do not fit "move to a sibling record with the same state, in the same pair group".
  - §7.8: "every row belonging to a pair group is kept".
- **Evidence:**
  - Flagged records with several D1/D3, G2 and D2 rows will exceed the 1,664-token question allowance and spawn siblings.
  - All of their rows then become exempt from the cap. The exemption was decided for contrast pairs ("so pairs keep their contrast", D27), not for siblings.
- **Consequence:** many negatives on flagged records escape the 1:10 cap.
- **Who uses it:** the balance cap.
- **Fix:** siblings share a split and a batch, but only contrast pairs are exempt from the cap.

**R5-09 · Part 1 · unsupported claim · one correct answer · low**
- **Spec text (§3):** "the long-record share and the rare-question floor come from the data-mixing and long-context research".
- **Evidence:** the floor is now 0.8 · P_q, taken from the decided plan (§10: "fixed before the build"), not from research.
- **Who uses it:** a reader judging where claims come from.
- **Fix:** remove "and the rare-question floor".

**R5-10 · Part 4 · task material, left over from R4-07 · low**
- **Spec text (§12.4):** "Tuned and stock are scored concurrently."
- **Evidence:** this is scheduling, and the gate does not use it. The container lines in §11 are fine, because the cost estimates depend on them.
- **Who uses it:** nothing in the gate.
- **Fix:** delete it; it belongs in the task file.

**R5-11 · Proportionality · unneeded mechanism · David confirms (D45 value) · low**
- **Spec text (§7.6):** "5% of copies are spot-checked for unchanged actions."
- **Evidence:** a copy only rewrites `agent_text`, and the actions are copied unchanged. The check guards nothing, and nothing happens if it fails.
- **Who uses it:** no one.
- **Fix:** delete it.

## Part 2: cost audit

Everything reconciles:
- **Step count and composition:** S = ⌈12,200/16⌉ = 763. The source quotas sum to Σ n^plan = 10,630, and s = 0.809.
- **Candidate scoring:** ~1,750 × 6.7K ≈ 12M tokens, and at 30K tokens/s that is about 7 minutes.
- **Long gate:** 3,000 states × ~18.7K ≈ 56M tokens, about 31 minutes. The item count n = 0.06 / (0.03/3.24)² ≈ 700. Using z = 1.28 per length gives a joint pass probability of at least 0.8, by the union bound.
- **Teacher:** about 1,500 calls × 3.5 minutes / 100 parallel ≈ 0.9 hours.
- **Agent runs:** 900–3,000 minutes / 20 parallel ≈ 0.75–2.5 hours.
- **Training run:** 2–3.5 hours is consistent with ~97M training tokens at 8–10K tokens/s.
- **Weakest number:** the scoring throughput of 30K tokens/s is labelled unmeasured. At 15K tokens/s the final candidate pair takes about 28 minutes, which is still inside the band. The spec already says the first scored candidate (stock) settles it.
- **Not counted:** the diagnostic passes from R5-06. Their cost should fit inside the existing ±30% teacher band.

## Counts

- **Register entries verified:** 25. 24 landed in the spec; 4 of those carry a new or exposed defect. The ledger-lag entry did not land fully.
- **Findings:** 11.
  - Errors: 6 (R5-01, -02, -03, -04, -05, -08).
  - Omissions: 1 (R5-06).
  - Created by amendments: R5-07, plus R5-01 and R5-04, which are listed as errors above.
  - Unsupported claims: 1 (R5-09).
  - Task material: 1 (R5-10).
  - Unneeded mechanisms: 1 (R5-11).
  - Overreach: 0.
- **Created by amendments:** 3 (R5-01, R5-04, R5-07).
- **Blocking:** 0. One owner decision is needed before the Phase 3 data gate: the expected positive share for agent-run sources (R5-04).

This round does not meet the D46 stopping rule (at most 2 findings, none blocking). By count it fails, but none of the 11 blocks. 10 are one-line fixes with one correct answer; R5-04 needs David's small decision.

## The three most likely failure points

1. **M4 labels on read-offence V records (R5-03).** About 400 records would carry a final M4=yes on events that do not game a measure, which blurs M4 into L6.
2. **The diagnostics labelling pipeline (R5-06).** A three-pass dependency the spec doesn't state. The agent may improvise the D2 text, so it drifts from the runtime's, and the extra passes take time from the schedule.
3. **G2/G5 at turn ends (R5-07).** The runtime asks G2 and G5 on turn ends that training never covered. A G2 "broken" there sends a correction.

## Verdict

The spec is implementation-ready after the one-line fixes above; Phases 1 and 2 can start now. There is one owner question, and it does not block the start: R5-04, the expected positive share for the agent-run V sources (SWE-Misbehavior, lhaw). It must be answered before the Phase 3 positive-floor gate. The cross-track part of R5-07 needs the runtime spec and D72 to adopt the `answer` gate. Separately, the ledger still needs its in-place updates: 07:00 → 08:00, D45's "50 fixed states", and D47 line 940.

## Coverage ledger

| What | Lines read |
|---|---|
| Skills: reading-context, out-of-cutoff, receipts-before-claims, design-ethos | 1–98, 1–103, 1–29, 1–71 (all of each) |
| Skills: gold-standard spec template | 1–605 (all) |
| Skills: initializing-projects, task-file-builder | 1–133, 1–206 (all) |
| CONTRACT.md | 1–261 (all) |
| TRAINING-SPEC.md, the 23:31 version | 1–664 (all) |
| TRAINING-SPEC.md, the 23:36:48 snapshot (reviewed version) | 1–665 (all) |
| DESIGN-DECISIONS.md, the version before 23:38 | 1–1167 (all) |
| DESIGN-DECISIONS.md, the 1182-line 23:38 snapshot | Searched only. The change is runtime-side (D72 expanded, D77 added), and I checked the "07:00", D45 and D47 strings in it. |
| TRAINING-SPEC-TRACE.md | 1–37 (all) |
| Round-4 dispositions register | 1–33 (all) |
| Audit reports | Targeted reads only: `-17-` (summary and R4-07, R4-11), `-16-` (F6), `-19-` (lines 60–89, plus searches), `-12-` (166–179, R3-11). I searched the dispositions files from rounds 1–4 for already-settled issues. |
| RUNTIME-SPEC.md, DATASET-DOSSIER.md | Searched only, to check cross-references. |

Every line was covered in every file required in full. The one exception is the 23:38 ledger snapshot, which I searched rather than re-read.