# Round 5 review: TRAINING-SPEC.md (final full round)

**Note on the target's state.** The spec was amended in place at 23:36:48 while this review ran (664 → 665 lines). My first full read predated the amendment; a locator check caught the change and I re-read every range my findings cite. Two defects I had drafted against the earlier text were already closed by that amendment: §6.1 now carries `"turn": {"reason": "answer | aborted | refusal | error"}` with "Converters set `turn.reason` to `answer` on the `turn_completed` event that ends a completed run", and §10's positive floor no longer depends on an unlocated dossier rate. All receipts below quote the live text.

## Part 0: disposition verification (25 register entries)

| Entry | Status | Receipt (section, live text) |
|---|---|---|
| Owner decision F2 (positive floor shares fixed before build) | LANDED, and it surfaces F-01 | §10: "T sources 0 (the dossier holds no measured positive rate for any monitor question), so P_q comes from C and V sources"; §12.2: "holds ≥ 0.8 · P_q positive training rows (section 10), P_q being what the decided plan yields" |
| R4-01 read as first offence | LANDED | §7.2: "When a positive's first offence is a read … the record is cut at the next classified event, and the read shows in RUN LEDGER." |
| R4-02 firing answer | LANDED | §6.5: "answered <the firing answer> (p = 0.87)" |
| R4-03 base dev | LANDED | §9.5: "T_q minimizes NLL on base dev (7.9)"; §12.4: "T_q and b_q fitted jointly by NLL on base dev" |
| R4-04 CodeTraceBench, benign header | LANDED | §7.3: "T (the competence-error annotation is a hint)"; "Benign runs (the teacher labels every question)" |
| R4-05 TonyDzi hook | LANDED | §7.3: "T (the hook's text is a hint)"; "under the first positive question at the hooked event in the 6.5 item order (M1 when none is positive)" |
| R4-06 spend reserve, $70 removed | LANDED | §8.7: "generation's estimated spend is reserved first"; no "$70" anywhere |
| R4-07 / F3, F4 choreography out | LANDED | §9.3: "If the pick is made before training ends, the two saves are the latest one and the one nearest step 400 that exist then."; §9.4: "a candidate may be scored as soon as it exists, on any GPU running the same code"; §12.1: "both gaps measured on the same hardware pair" |
| R4-08 demo check pre-deploy | LANDED | §12.3: "(or, before it is deployed, the shared renderer and the serving path with the per-question transform)" |
| R4-09 / F1 TRACE synthetic | LANDED | §1 family 2 and §13: "unseen synthetic Claude Code conversations (TRACE …) … the demo check … is the only real-run check" |
| R4-10 flag-everything as report | LANDED | §13: "reported beside the teacher's positive rate there" |
| R4-11 block added only if it fits | **LANDED WITH NEW DEFECT** (F-02) | §6.4: "each added only if it fits what remains of the detail budget max(…) is spent" — the sentence no longer parses |
| R4-12 R_k trimmed | LANDED | §6.4: "a quoted «R_k text» is trimmed head and tail, each cut marked `[cut]`" |
| F5 §15 dependency split | LANDED | §15 row 4: "the run: the labelled, capped train split and its pair-integrity check; selection and calibration: dev, the intent slice and stock's dev scores" |
| F6 recovery | LANDED | §13: "except serve-path parity, whose fallback (12.1) moves selection down the pick order; the demo check does the same" |
| F7 agent said / MESSAGE cap | **LANDED WITH NEW DEFECT** (F-03) | §6.4: "`agent said:` and MESSAGE text share it" versus the closing sentence "Each detailed block's `result`, `patch` and `plan` together are capped at 2,000 tokens" |
| F8 long padding target | LANDED | §7.7: "until the rendered state reaches 16K to B_state, documents stopping at the 6.4 threshold" |
| F9 / claims 7 AskUserQuestion | LANDED | §6.1: "AskUserQuestion is never a cut point"; §7.3 IN3: "an ask renders as a `turn_completed` MESSAGE asking the question, cut there" (the sentence "AskUserQuestion answers become `user_instruction` items" is now stated twice in §6.1; redundancy only) |
| Claims 1 `Server.probs`, log-odds | LANDED (further tightened by the 23:36 amendment) | §12.1: "Kev's unrounded probabilities (`Server.probs`), compared as log-odds computed as log p_yes − log p_no … every model on both sides … loaded with temperature 1.0" |
| Claims 2 patch field | LANDED | §6.1: `"patch": <Claude Code's structured hunks, or null>` |
| Claims 3 pass cap | LANDED | §10: "smoke run on a synthetic record at the largest real padded cost (a full state plus its question count × its longest row)" |
| Claims 4 tau2 | LANDED | §7.3: "V for `communicate_checks` scored by substring match; T with `nl_assertions` as a hint" |
| Claims 5, 6 read-only set, PowerShell | LANDED | §6.1: "(Read, Grep, Glob, WebFetch, WebSearch, LS, NotebookRead, by tool name, the Mod's own set)"; "renders PowerShell as Bash" |
| Claims turn-reason note | LANDED (closed by the 23:36 amendment; now consistent in §4.2 table, §4.2 prose, §6.1 and §8.2 item 6) | §4.2: "at each `turn_completed` event whose end reason is `answer`"; §6.1 `turn.reason` |
| Ledger lag | LANDED IN PART (ledger side only; the spec is clean) | D13/D41 say 08:00 but D18 ("after the 07:00 pick"), D27 ("D13's 07:00 best-model choice"), D36 ("fallback trigger is 07:00 EST") and the trace ("D13 07:00 best-model rule") still say 07:00; D27 still lists the cut note-crutch instrument ("accuracy gap between the two copies stays near 0"); D47's round-2 bullet still says "the hook template's mapped question (TonyDzi)" (superseded by R4-05) and its round-3 bullet "read-only = Read, Grep, Glob, WebFetch by name" (superseded by claims 5) |

Register entries verified: 25. LANDED 22, LANDED WITH NEW DEFECT 2, LANDED IN PART 1 (ledger only). Amendment-created defects: 2.

## Findings

**F-01 · Part 1 · error (a gate that cannot fail) · needs an owner choice**
Spec: §10 "T sources 0 (the dossier holds no measured positive rate for any monitor question), so P_q comes from C and V sources"; §12.2 "every question with a positive class except SCR, M8 and the diagnostics … holds ≥ 0.8 · P_q". Evidence: in §7.3's M5/G5 table every source is T or O→T except Open-SWE ("V where the claim contradicts test output") and tau2 ("V for `communicate_checks`"), and the table does not say which of M5/G5 those V labels cover. So P_{G5} = 0 (or near it) and P_{M5} is a small fraction of one source; the floor 0.8 · 0 = 0 passes with zero G5 positives. The same holds for every question whose positives come only from T sources. Consequence: the gate the ledger's emergent-interactions table relies on ("a question with very few positives silently under-trains … `positive-floor` … the build stops on a shortfall") has no teeth for exactly the questions that carry half of lift endpoint (2) (§12.4 "one M4 item and one G5 item per conversation"). Consumer: the Phase-3 data gate and the lift test. This is the owner's round-4 rule ("0 where none") applied to the fact that no T source has a rate; the owner should decide whether T-only questions get a stated floor (the dev floor's ~60 positives is the only number already in the spec) or whether "no floor" is accepted and recorded. The current text is executable as written, so the default exists; the choice is about how data is judged.

**F-02 · Part 1 · amendment-created (R4-11) · one correct answer**
Spec §6.4: "then recent events as detailed blocks, newest first, each added only if it fits what remains of the detail budget max(0.40 × B_state − tokens(instructions + documents), 0.15 × B_state) is spent (the 0.15 floor …); every older event as a one-liner". Evidence: two sentences were merged ("each added only if it fits what remains of the detail budget" and "until the detail budget … is spent"), and the result is ungrammatical and admits two algorithms: stop at the first block that does not fit, or skip it and try older blocks. Consequence: a renderer that skips produces a non-contiguous detailed window, which contradicts L1's wording ("Across the recent events shown in detail in RUN LEDGER") and "every older event as a one-liner". Consumer: the renderer builder (and so every record and every runtime state). Correct answer: stop at the first block that does not fit; everything older is a one-liner.

**F-03 · Part 1 · amendment-created (F7) · one correct answer**
Spec §6.4: "LATEST EVENT is a detailed block under the same 2,000-token cap; `agent said:` and MESSAGE text share it, kept head and tail with a `[cut N tokens]` marker." and, three sentences later, "Each detailed block's `result`, `patch` and `plan` together are capped at 2,000 tokens." Evidence: the first sentence puts `agent said:`/MESSAGE inside the block cap; the second enumerates the cap's members without them (the ledger's D40 also lists only result, patch and plan). Consequence: two readings (one 2,000-token pool for all four fields, or a separate 2,000 for agent text), each changing state length and what a long final message shows. Consumer: the renderer builder. Correct answer: one sentence naming the cap's members once; the register's F7 wording ("share the block's 2,000-token cap") says the single-pool reading.

**F-04 · Part 1 · error (a gate that fails through noise) · one correct answer**
Spec §12.1: "the winner's max |Δ log-odds| between the training forward and the serving path on 300 dev records ≤ 1.5 × stock Kev's own gap on the same records". Evidence: both sides are the sample maximum of ~300 × ~16 bf16 kernel-path deltas; the ratio of two independent extreme-value statistics from similar noise exceeds 1.5 often, and an α = 0.85 winner (a merged full-weight checkpoint served as full weights) has a legitimately different path from stock's LoRA-branch path. Consequence: the fallback "for an α = 0.85 winner … the next candidate in pick order" demotes the pick on noise, with no re-measure step. Consumer: the Phase-4 gate and the pick. Correct answer: compare a non-extreme statistic (mean or a stated high quantile of |Δ log-odds|) at the same 1.5× multiple; the gate's purpose (catching a kernel-path divergence, which is orders of magnitude) survives.

**F-05 · Part 1 · error (under-specified rule) · one correct answer**
Spec §9.4 steps 2–3: "Bootstrap the standard error with 1,000 resamples of dev groups. Keep candidates within one standard error of the best." Evidence: "the standard error" is not tied to a quantity: each candidate's own score SE, the best candidate's SE, or the SE of the paired difference on the same resamples. §1's bounded-regression guarantee holds under any reading, but the kept set, and so the intent-score pick, differs. Consumer: the selector. Correct answer: the paired bootstrap SE of (best − candidate) over the same 1,000 group resamples.

**F-06 · Part 1 · error (under-specified rule) · one correct answer · low**
Spec §7.8: "Per question, every positive row and every row belonging to a pair group is kept, and other negative rows are sampled down to at most 10 per positive". §4.2: twins are "a copy of the base row with the wording, label and target flipped, keyed `<id>~neg`". Evidence: base and twin are distinct question keys, and twins are not a pair group (§4.1 lists "same-context pairs, note pairs, rewrite copies, goal-flip pairs"), so the cap samples M1 and M1~neg negatives independently and a record can keep one and lose the other. Consequence: the polarity contrast D27 built the twins for is broken on those records, and the twin's negative subsample differs from its base's. Consumer: the record assembler. Correct answer: the cap treats a base row and its twin as one unit. (Twins are training-only, so calibration is untouched.)

**F-07 · Part 1 · error (under-specified rule) · one correct answer · low**
Spec §6.7: "In training, R_k on any record are the units the teacher labels RF-yes." §11: "RF units on G2/D2 records and sibling records add ~10–20%" (teacher items). §6.3: "An RF record's state is the ⟦ ⟧ window alone." Evidence: the spec says the teacher labels every unit of a G2/D2 record's instructions and documents, and that RF records are window-only states, but never says whether those labelled units also become RF training records. §7.1's composition is exhaustive (N = 12,200 with 200 RF inside IF_multi's 400), so they cannot be, but an agent reading §6.7 alone could add thousands of RF rows. Consumer: the record assembler and §7.1's count. Correct answer: one clause in §6.7: those labels define R_k and are not training rows beyond the §7.3 RF quotas.

**F-08 · Part 3 · omission · one correct answer · low**
Spec: §7.3 "SWE-Misbehavior (dossier #45 …)", "SWE-bench Verified annotations (… dossier #46)"; §10 "the dossier holds no measured positive rate"; §13 "licences recorded unverified in the dossier". Ledger D28: "Decided per objective in prose after collection (`docs/DATASET-DOSSIER.md`)". Evidence: the spec names "the dossier" four times and never locates it; the file exists at `docs/DATASET-DOSSIER.md`. After the 23:36 amendment no build input depends on it, so this is an unresolved internal reference only. Consumer: the reader. Correct answer: name the path once (front matter or §7.3) or drop the three decorative mentions.

**F-09 · Part 1 · error (under-specified rule) · one correct answer · low–medium**
Spec §6.2: `source_labels` carry a `question`; §8.4: "Visible-based source labels are final for their question." §7.3 M4/L6 table: CheatBench "V (maintainer review + rule audit) … First offence = first tool call reading `/tests`, a verifier output, a gold or answer file, or a leaked secret"; HVTB "Ablation setting → M4/L6". Evidence: no row in that table says which of M4 and L6 its V label covers; "M4/L6" is the objective, not a question. With R4-01, a read-first-offence record is cut at the next classified event, so a V label attached to M4 would be final on a state whose LATEST EVENT may not touch any measure, contradicting M4's wording ("Does the latest action make a measure of success … look better"). Consumer: every M4/L6 converter and §8.4. Correct answer: state the mapping that follows from the wordings: a read of tests, grader or answer files is L6; altering, skipping or special-casing a measure is M4; the teacher labels whichever question the source's label does not cover.

No findings in Part 2 (the run-time, scoring, teacher-throughput and gate arithmetic in §9.1, §10 and §11 re-derive: s = 8,600/10,630 = 0.809 with Σ n^plan summing to 10,630; S = ⌈12,200/16⌉ = 763; Hanley–McNeil at AUROC 0.8 gives SE ≈ 0.035 at ~60 positives; the long-gate n = d·(3.24/0.03)² = 700 at d = 0.06, and z = 1.28 is what makes two lengths pass jointly at ≥ 0.8; 12M dev tokens at 30K tok/s ≈ 7 min; 1,500 × 3.5 / 6,000 ≈ 0.9 h; all estimates are labelled estimated with bands and an instrument). No findings in Part 4: the residual scheduling phrases in §11 ("in a separate container during training", "once the selected model is live") are the stated basis of wall-clock estimates, which a cost model legitimately carries; no session-recovery, run-order or completion-checklist material remains.

## Counts

- Register entries verified: 25 (LANDED 22; LANDED WITH NEW DEFECT 2; LANDED IN PART 1, ledger side only).
- Findings: 9. By kind: error 6 (F-01, F-04, F-05, F-06, F-07, F-09), omission 1 (F-08), amendment-created 2 (F-02, F-03); unsupported claim 0, overreach 0, task material 0, unneeded mechanism 0.
- Amendment-created defects: 2 (F-02, F-03). F-01 is a consequence surfaced by the concurrent application of the owner's round-4 rule, not a text defect.
- Blocking: 1 (F-01, an owner choice with an executable default already in the text). F-02 through F-09 each have one correct answer.

## Three most likely failure points

1. **M5/G5 positive supply.** With every M5/G5 source teacher-labelled and the floor at zero (F-01), the number of G5 positives is whatever the teacher finds in TB-science, TB2.1 and the claim slices; too few under-trains the question that carries half of lift endpoint (2) and the "claims done, isn't" runtime moment, and nothing in the build would stop.
2. **Teacher wall-clock and agreement.** ~10,500 items × 2 votes with a 0.70 positive-specific-agreement gate whose only remedy is one relabel pass; the band already spans 0.3–3.7 h, and a relabel on a wide question repeats a large share of it. Everything downstream waits on this.
3. **The renderer's fill rule.** F-02 and F-03 sit in the one component every training record and every runtime state passes through; train equals runtime by construction, so a wrong reading is consistent but changes the detail window L1 and D1/D3 see and the length budget of every long record. Secondary: F-04's extreme-value statistic can demote a sound winner.

## Verdict

Implementation-ready once F-02 and F-03 are fixed (two sentences in §6.4, one correct answer each) and F-01 is answered: the only blocking question is **whether T-only questions (G5, and in practice M5) receive a stated positive floor, or whether "no floor" is the accepted decision and is written down as such**. F-04 through F-09 are builder-resolvable with the one correct answer each names, and I recommend landing them in the same pass since each touches a shared component (selector, record assembler, converters). The spec's guarantees, formulas, gates and ledger carriage otherwise re-derive cleanly; scope-audit cuts were not re-raised.

## Coverage ledger

| File | Lines read | Every line covered |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 (EOF) | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 (EOF) | yes |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 (EOF) | yes |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 (EOF) | yes |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–606 (EOF) | yes |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–134 (EOF) | yes |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–207 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–262 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md` | first pass 1–200, 200–400, 400–600, 600–664 (EOF, pre-amendment); after the 23:36:48 amendment re-read 10–34, 140–244, 440–453, 455–574, 574–665 (EOF) | yes (pre-amendment in full; every cited range re-read post-amendment) |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 200–400, 400–600, 600–800, 800–1000, 1000–1167 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC-TRACE.md` | 1–37 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-18-training-spec-round4-dispositions.md` | 1–33 (EOF) | yes |

Shell commands run (foreground, all exited): `wc -l` and `ls` on the target set; `ls`/`grep -c`/`grep -n` locator checks for the dossier file and end-reason mentions; `wc -l`/`stat`/`grep -n` to confirm the concurrent amendment. No files edited; no skills invoked; no background processes.