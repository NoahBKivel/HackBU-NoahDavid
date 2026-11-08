# Round-2 review: `docs/TRAINING-SPEC.md`

Date anchor: `date` → Sat Nov 7 21:51 EST 2026. No file edited; no skill invoked; three foreground shell commands (`date`/`wc`, `wc`, one `python -I` arithmetic script in the scratchpad), each exited before the next.

## Coverage ledger

| File | Lines read | wc -l | Every line |
|---|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 | 97 | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 | 102 | yes |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 | 28 | yes |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 | 71 | yes |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–200, 201–400, 401–605 | 605 | yes |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–134 | 133 | yes |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–207 | 206 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–262 | 261 | yes |
| `…\classifier-for-metagaming\docs\TRAINING-SPEC.md` | 1–200, 201–400, 401–600, 601–660 | 660 | yes |
| `…\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 201–400, 401–600, 601–800, 801–1000, 1001–1077 | 1076 | yes |
| `…\classifier-for-metagaming\docs\TRAINING-SPEC-TRACE.md` | 1–35 | 35 | yes |
| `…\docs\audits\2026-11-07-4-training-spec-round1-dispositions.md` | 1–74 | 74 | yes |
| `…\docs\audits\2026-11-07-2-training-spec-review-opus-audit.md` | 1–170, 171–329 | 329 | yes |
| `…\docs\audits\2026-11-07-3-training-spec-external-claims-audit.md` | 1–210 | 210 | yes |
| `…\docs\audits\2026-11-07-5-training-spec-review-fable-audit.md` | 1–208 | 208 | yes |

(Where a read ends one past `wc -l`, the file lacks a trailing newline.)

---

## Part 0: Disposition verification

**Headline fixes**

| Register entry | Status | Receipt |
|---|---|---|
| O-F1/C-F2 α and pointer head | **LANDED WITH NEW DEFECT** (A1 below) | §1: "θ(α) = θ_kev + α(θ_tuned − θ_kev) over every trained tensor (the LoRA taken as its merged product)"; §9.2.5 interpolation tool; §9.3 "At α = 0 the tool must reproduce stock Kev's tensors exactly". |
| C-F3 kernel check | LANDED | §9.1 "fla's Triton kernels must run the DeltaNet layers (no torch fallback); attention runs through SDPA"; §12.1 Kernel check row. |
| C-F4/O-F5 B_state and one-liner overflow | LANDED (one clause short) | §6.4 "B_state = 32,768 − (tokens of that record's questions) − 1 … oldest are replaced by one count line (`[E1–E120: 120 earlier events]`)". The register's "EFFORT still counts them" is not in the spec (see F11). |
| C-F1 replay via `--data` | LANDED | §7.3 replay table "Pre-built … (not the trainer's `--replay` sampler) … passed through `--data`"; §9.1 command has no `--suite`/`--replay`. Ledger D41 still says the opposite (Part 3, L2). |
| C-F5 `LoadOptions(temperature=1.0)` | LANDED | §9.5 Serving bullet. |
| C-F6 none/distractor flags off | LANDED | §9.1 `--p_none 0 --p_none_distract 0 --p_distract 0` and the bullet explaining it. |
| O-F7 retention n; long-gate n sized | **LANDED WITH NEW DEFECT** (A2) | §12.3 "decision-v7 dev (all 1,204 records)"; §7.9 and §10 "sized by formula from measured discordance so a model at parity passes with probability ≥ 0.8". |
| O-F22 cross-fitted calibration | LANDED | §1, §9.5 "cross-fitted over five dev folds"; §12.3 "ECE, out of fold". |
| O-F9 offset form, π, invariant | LANDED | §1 "σ(z_q/T_q + b_q) … corrects the balance cap; it does not claim to reach deployment prevalence"; §9.5 "π^train is the mean training target after the cap and π^dev the top-up-weighted dev rate". |
| O-F2 renderer parity fixtures | **LANDED WITH NEW DEFECT** (A3) | §12.1 Renderer parity row. |
| O-F3 (part) stock gets the calibration family | LANDED | §12.4 "Baseline: stock Kev-4B given the same calibration family (offset and temperature, cross-fitted on the same dev folds)". |
| Cost: scoring via training forward | LANDED | §9.4 last paragraph; §11 Candidate scoring row. |
| O-F28/C-F7 serve-path relative rule | LANDED (fallback undefined for α = 0.85, see A1) | §12.1 "≤ 1.5 × stock Kev's own gap measured the same way \| serve the unmerged LoRA path and re-measure". |

**Remaining fixes (grouped)**

| Entry | Status | Receipt |
|---|---|---|
| Leakage O-F4 | LANDED | §8.1 "source labels whose `event_seq` ≤ k … Outcome-based source labels are the one exception"; §7.5 "Each note is written only from its own step's raw reasoning". |
| Matching O-F14 | LANDED | §7.2 "joint distribution of event type … and absolute event index (in bins of 10 events…)". Ledger D43/D45 still say relative tenths (Part 3, L3). |
| Arithmetic O-F16 | LANDED | §7.1 "ρ_replay = 3,000 / 12,200 ≈ 0.25". |
| Steps O-F15 part | LANDED | §9.1 "R the train-split record count after the balance cap, replay included". |
| Pick order O-F23 | LANDED | §9.4 "The pick order is the intent-score rank within the kept set, then stock Kev"; §1 Bounded regression. |
| Schema O-F27/17/18 | LANDED | §6.1 "at least these fields … accepts extra fields", "including keystroke batches and PowerShell", "A tool outside this list renders under its own name with its first string argument"; §6.3 key suffixes and "An RF record's state is the ⟦ ⟧ window alone". |
| Strings O-F19 | LANDED | §6.5 short-name table, D2 summary, "M2, M4, L6, M5, L5, G2, G5, …"; §7.4 "p values drawn uniformly from [0.6, 0.99]". Ledger D26 order still lacks G5 (L2). |
| Labels C-F10/11 | LANDED | §7.3 terminal-wrench "T (`key_hack_steps` and the judge's labels are LLM judgements, given as hints)"; Goodfire "T"; eungyeuk "T (no shipped label; a 258-run sample found no hacks)". |
| Rewording C-F8 | LANDED, role gap remains (F9) | §9.2.3 "effective cap (7,488 tokens), its 8K dev-fit check and its hard-wired decision-v7 input are lifted". |
| C-F9, C-F12, C-F13 | LANDED | §9.1 "(triton 3.9.0 fails fla 0.5.2 at import; these pins were measured in the serving image…)"; §7.3 "up to 15 near-duplicates per task: 5 per task and model"; §12.3 "a 3-point tolerance this spec borrows from Kev's context-validation rule". |
| O-F26 residuals, secrets | LANDED | §13 Residual column (four honest residuals); §12.2 Secrets scan pattern list. |
| O-F29 | LANDED | §9.5 "per-option offsets can reorder one-vs-rest rankings, so selection scores uncalibrated logits for every candidate alike". |
| O-F30 | LANDED | §3 names arXiv 2610.02076, ProLong 2410.02660, Kev-27B model card, Kev's README. |
| Floors O-F24/25 | LANDED (new infeasibility, F1) | §7.9 "the intent slice … with the same floor per intent question; goal-splice records may enter it"; §12.2 "≥ 300 positive training rows"; Run yield defined. §9.4's slice source list omits goal splices (F12). |
| Long-gate items O-F21 | LANDED | §7.9 long-context gate items bullet. |
| Note-crutch set O-F13 | LANDED ("action-visible" still undefined, F13) | §7.5 "a separate dev diagnostic set of note pairs, sized so the paired-difference standard error is ≤ 0.02 and excluded from calibration". |
| Instruments O1 | LANDED (set unnamed, F14) | §12.3 "Requirement filter \| RF recall on held-out instructions \| reported". |
| Boundary moves | LANDED | No cut-off row in §10, no overrun row in §13, §15 closes on the phase table, §9.4 has no 07:00, §8.3 has no thinking levels, §7.3 preamble has no download rule, §8.7 has no key rule, front matter reads "Status: Implementation-ready". |

**Defenses**

| Entry | Status | Receipt |
|---|---|---|
| O2 Terminal Wrench down-weight = quota | DEFENSE HOLDS | §7.3: 250 of the 1,750 M4/L6 plan. |
| O-F11 report-only + selection preference; per-source surface baseline | DEFENSE HOLDS for the surface baseline; the seam-gap half **creates a conflict** (A4) | §12.3 "within each source: a logistic model … \| reported as shortcut-reliant; selection prefers a candidate that passes". |
| O-F4 outcome hints | DEFENSE HOLDS | §8.1 states the exception explicitly. |

**Decisions David made (carried as decided)**

| Decision | Spec receipt |
|---|---|
| O-F15 cap 1:10, pairs exempt, no record vanishes (D27) | §7.8 verbatim. Carried. |
| O-F8 dev floor SE ≤ 0.035 (~60) (D37) | §7.9 "SE … ≤ 0.035, about 60 positives at AUROC 0.8". Carried; arithmetic re-derived: SE(60 positives, 600 negatives) = 0.0351, (60, many) = 0.0344. |
| O-F10 positive-specific agreement 2a/(2a+b+c) ≥ 0.70 (D30) | §1, §8.5, §12.2. Carried (can't-tell handling unstated, F15). |
| O-F3 lift protocol (D37) | §12.4 two endpoints, question mapping. Carried. |
| O-F12 unedited-real set (D37) | §7.9 bullet. Carried (but see A4). |
| O-F6 G4 every event, EFFORT always (D19.G4) | §4.2 last paragraph; §6.4 "EFFORT and OPEN FINDINGS always appear". Carried. |
| O-F20 screen pool and ledger (D19.P) | §7.4 Overflow screen row; §6.6 "up to 15% of the screen budget". Carried (see F6). |
| V-F7b 0.15 floor (D22) | §6.4 max(…, 0.15 × B_state). Carried; §10 not updated (A5). |
| V-F9 OPEN FINDINGS line only (D40) | §6.4. Carried; premise unverified (F3). |

**Fable fixes:** V-F3 (§8.3 "`label` = target > 0.5, so a tie is no"), V-F4 (§7.8), V-F5 (§7.6), V-F6 (§8.4 item 1), V-F7d (§6.4 "LATEST EVENT is a detailed block under the same 2,000-token cap"), V-F8 (§6.4 exit code; §6.1 PowerShell; todos), V-F9 (§6.4), V-F10 (§7.3 L7 rows), V-F13 (§7.9 Held-out conversions, partial: F2), V-F18 items (§6.4 `[I_n]`, §7.2 cut indices, §7.3 QuALITY, §9.1 head LR/anchoring), V-O6 (§7.9 last sentence), Cost (§11): all LANDED. One Fable item the register never disposed: `build_long_states.py` without a stated role (F9).

**Register totals:** 52 entries verified (13 headline, 16 grouped, 3 defenses, 9 David decisions, 11 Fable). 47 LANDED/HOLDS cleanly; 4 LANDED WITH NEW DEFECT (A1–A4); 1 defense partly fails (O-F11 seam half). Amendment-created defects: **5** (A1–A5).

---

## Amendment-created defects

**A1 · Part 1 · amendment-created · the interpolated candidates have no representation or serve fallback.** §1: "the LoRA taken as its merged product"; §9.2.5: "writes θ(α) … as a loadable checkpoint"; §12.1 fallback: "serve the unmerged LoRA path". Evidence: at α = 0.85, θ_kev + α(B′A′ − BA) = base + [(1−α)B | αB′][A; A′], rank 32, not Kev's rank-16 adapter; it is loadable only as merged full weights or a rank-32 LoRA with scaling adjusted. The spec names neither, and "the unmerged LoRA path" does not exist for such a candidate. Consequence: the builder picks a representation that decides whether serve-path parity's fallback is possible and whether `--init_from`-style loading works. One correct answer (state the representation; give the α = 0.85 fallback). Non-blocking.

**A2 · Part 1 · amendment-created · §10 and §12.3 disagree on retention sizing, and 1,204 only suffices under an unstated discordance.** §10: "Long-gate and retention item counts | n such that a model at parity passes with probability ≥ 0.8, from measured discordance"; §12.3: "(all 1,204 records)". Re-derived (pass iff diff − 1.96·SE ≥ −0.03, SE ≈ √(d/n)): at n = 1,204 a parity model passes with P = 0.91 at 10% discordance, 0.80 at 13.8%, 0.64 at 20%, 0.48 at 30%; the §10 rule needs n ≥ 436 at d = 0.05, 872 at 0.10, 1,744 at 0.20. A continuation run that flips ≥ 15% of decision-v7 answers fails retention through noise, and since retention is applied down the pick order, the cascade to stock Kev that O-F7 described survives above d ≈ 0.14. Needs a design choice (tolerance, rule, or an explicit "retention is capped by the dev set; above d = 0.14 it is report-only"). Non-blocking but likely to fire.

**A3 · Part 1 · amendment-created · renderer parity is cleared before the thing it tests exists.** §12.1: "fixtures written both as source records and as raw Mod-event JSON … through the converter path and the direct Mod-event path"; §15 Phase 1 clears it, Phase 2 builds "source converters (7.3)". Evidence: in Phase 1 the only "converter path" is a hand-written §6.1 stream, which is the Mod schema itself, so the two paths coincide and the gate cannot fail; it is never re-run when the ~40 converters land. Consequence: the "Train equals runtime" discharge has no teeth where mismatches arise. One correct answer: per-converter schema validation plus parity on fixtures re-run in Phase 2 (or move the gate). Non-blocking.

**A4 · Part 1 · amendment-created · the seam gate makes a held-out set a selection input.** §7.9: "Unedited-real set (held out) … never trained on; the seam gate's reference"; §12.3 Seam gap: "selection prefers a candidate that passes"; §2 principle 5: "No held-out item reaches training, selection or calibration"; §5 Lifecycle: "The evaluator reads the held-out sets once, for the selected adapter and stock Kev only". Evidence: a selection preference requires scoring candidates on the unedited-real set, and a fallback down the pick order re-reads it. Consequence: either the principle or the gate is violated; the builder must choose. One correct answer consistent with D37 (held out): seam gap is report-only on the winner; drop "selection prefers" from that row. Non-blocking.

**A5 · Part 1 · amendment-created · §10 formula omits the 0.15 floor.** §10: "detail budget 0.40 · B_state − tokens(instructions + documents)"; §6.4: "max(0.40 × B_state − tokens(instructions + documents), 0.15 × B_state)". One correct answer: make §10 match. Non-blocking (the §6.4 rule is the one the renderer follows).

---

## Part 1: Logic and contract audit

**F1 · error · the 300-positive floor is unreachable for several questions under the §7.3 plan, and the top-up's effect on N is unstated.** §12.2: "every question has ≥ 300 positive training rows … | top up from the same objective's sources or constructions"; §7.1 N_screen = 200; §7.4 overflow screen: "one sentence inserted into one section that bears on (SCR yes) or contradicts (SCR yes, M8 yes)". Evidence (estimate; n^plan × s = 0.809, half of each construction's records positive): Omission → ~140 L5 positives; Composite → ~120 L2; Goal splice → ~160 L4; Priority → ~120 G4 (positive only where "≥ 5 / 0" holds, so fewer); screen → ≤ 200 SCR and ≤ 200 M8 positives by construction (≈ 100 if the two insertion kinds split). L2, G4 and M8 have no natural source that yields positives in volume. Consequence: the data gate fails for at least L2, L4, L5, G4, M8 at freeze; the authorized fallback is to build more constructions, which either grows N past 12,200 or displaces other quotas through s, and the spec says which nowhere. Needs a design choice (where top-ups come from; whether N grows). **Blocking:** the agent cannot pass the data gate without choosing.

**F2 · omission · 150 of the 200 probe items have no conversion rule.** §12.4: "on the 200 intent-probe items … Items are rendered through the state renderer like any record"; §7.9 Held-out conversions list TRACE, MALT, LLMBar, RewardBench 2 only. Evidence: the manifest's sources are TRACE, aspi, UserIntentBench and IFBench (Opus report, "Leads I dropped"). No row says how an aspi/UserIntentBench/IFBench item becomes `[I1]` plus events, nor how its label becomes the yes/no for M1, M2, M7, G1. Consequence: the headline lift is adjudicated on renderings and label mappings the builder invents. One correct answer per source, but it must be written. **Blocking** (it decides how success is judged).

**F3 · unsupported claim · the Mod attaches corrections "outside the reported `result_text`".** §6.4: "(the Mod attaches its text to the agent's next tool result outside the reported `result_text`)". Evidence: CONTRACT.md §4 says only "Attaches `text` to the agent's **next** tool result"; nothing in §3–5 says the reported `result_text` excludes it, and CONTRACT §7 lists no such agreement. Consequence if false: every post-correction runtime state carries text training never shows. One correct answer independent of Noah: the shared renderer strips any `result_text` segment beginning with the §6.5 header "Intent monitor:". Non-blocking.

**F4 · error · the lift's gated endpoint may render raw reasoning.** §12.4: "Also reported, not gated: each held-out source … and each again with reasoning stripped" (implying the gated pass includes reasoning); §2.1: evidence the monitor cannot see "never becomes the evidence for a yes"; §7.5: notes exist only in training records at f_note. Consequence: if TRACE's CoT is rendered into the state, the headline measures a condition deployment never has (r = 0.011). One correct answer: the gated pass renders no raw reasoning; the "with reasoning" variant is the diagnostic. Non-blocking but headline-affecting.

**F5 · error · a benign source's "target questions" is undefined, and one reading makes the cap self-contradictory.** §7.8: "other negative rows are sampled down to at most 10 per positive; no record loses its source's target questions, so no record vanishes"; §7.3 heading: "Benign runs (negatives for every question)". Evidence: if every question is a benign record's target, ~1,500 benign records × 12 rows are uncappable and L2 (~120 positives) cannot reach 10:1; if none is, the "so no record vanishes" clause has no mechanism for benign records. Needs a decision (small): the benign target set, or a "keep ≥ 1 row per record" rule. Non-blocking.

**F6 · error · the screen ledger cannot hold LATEST EVENT.** §6.6: "The screen ledger holds LATEST EVENT plus recent detailed events up to 15% of the screen budget"; §14 Q4 stand-in 8,192 → 1,229 tokens; §6.4: LATEST EVENT's result plus patch alone may reach 2,000 tokens. Also "Cap = (screen budget − instructions − ledger − event)" subtracts the event twice if the ledger includes it. One correct answer each (LATEST EVENT outside the 15%, or a tighter screen cap; fix the formula). Shared format, so write it. Non-blocking.

**F7 · omission · the calibration gate still runs "through the runtime classifier's path".** §12.3: "per-question ECE, out of fold, through the runtime classifier's path"; §1 Scope: serving logic is out. Round-1 O-F2/V-F11 fixed renderer parity but not this row. One correct answer: through the serving load used for serve-path parity (`LoadOptions(temperature=1.0)` plus the per-question transform). Non-blocking.

**F8 · omission · how R_k are produced for natural-run G2/D2 training records.** §4.2 G2 "once per requirement"; §8.2.6 "G2 per requirement only at a completion claim"; §7.3 gives R_k only for IF_multi, AgentIF, InFoBench and constraint insertion. For SWE-chat/Open-SWE/TB-science completion claims no splitter or filter is named (teacher marks sentences? stock Kev RF?). Different choices give different R_k sets and a train/runtime mismatch. Needs a decision (small). Non-blocking.

**F9 · unneeded mechanism or omission · `build_long_states.py` is patched but never used.** §9.2.3 lists three lifted limits and re-rendering; §7.3 QuALITY/long_policy rows and §7.7 never name the script. Either state its job (the padding for the two long-document sources) or delete the patch. One correct answer. Non-blocking.

**F10 · error · teacher batches are bounded by count, not tokens.** §8.3: "batches of 10–20 records from one source per call"; §11 assumes "50–100K+ input tokens". Evidence: 20 long records (16–32K each, plus raw reasoning) is 400–700K tokens in one call. One correct answer: add a token bound. Non-blocking.

**F11 · omission · collapsed events and EFFORT.** §6.4 count line replaces old one-liners; EFFORT's counts are "per area, counts of edits, writes and shell commands" with no statement that collapsed events still count. G4 reads those counts. One correct answer (counts span the whole run). Non-blocking.

**F12 · error · §9.4 and §7.9 disagree on the intent slice's sources.** §9.4: "(SWE-chat pre-correction windows, HelpSteer3 code items, Misalignment Atlas intention episodes, goal-flip pairs, IN3)"; §7.9: "goal-splice records may enter it". One correct answer. Non-blocking.

**F13 · omission · "action-visible" note pairs undefined.** §12.3 Note crutch: "on action-visible note pairs"; §7.5 same phrase; no predicate. One correct answer (e.g. the no-note twin's target ∈ {0, 1}). Non-blocking.

**F14 · omission · RF's held-out set unnamed.** §12.3: "RF recall on held-out instructions". No held-out conversion for RF exists in §7.9 (IFEval is held out and is the natural candidate). One correct answer. Non-blocking.

**F15 · omission · small undefined terms in label rules.** (a) §8.5 agreement 2a/(2a+b+c): how a can't-tell vote counts in b, c. (b) §4.1 "non-default class / default class" for G2, L7, D5: the default is never named, yet the cap and floor depend on it. (c) Twin question keys are absent from §6.3's suffix convention. (d) §9.5 π^dev: `label` rate or mean target (π^train is the mean target). (e) §1 Family 1 trigger "reviewed before the data freezes" has no end state. Each one correct answer. Non-blocking.

**F16 · error · §13 recovery contradicts §12.3's per-row fallbacks.** §13: "a failed behaviour gate on the selected candidate moves selection to the next candidate in pick order"; §12.3: only Retention and Demo check say "the next candidate"; Twin, Ledger strata, Note crutch, Surface, Seam say flag/report. Read as written, any flagged question moves selection and can cascade to stock. One correct answer: scope §13's sentence to the rows whose fallback is "next candidate"; define "selection prefers" or delete it. Non-blocking.

**F17 · overreach (low) · identity parity assumes stock is bit-reproducible.** §12.1: "logits equal stock's bit-exactly in fp32 on 50 fixed states". If the fla Triton path is not run-to-run bit-exact, stock fails against itself and no candidate is scored. One correct answer: the tensor equality is the identity test; the logit test is judged against stock's own run-to-run spread, measured first (verifier verified). Non-blocking.

**F18 · omission · f_long has no instrument or fallback.** §7.7: "f_long = 0.10 of all records render at 16–32K … from source runs with a long real history kept up to the cut, plus the long-document records". ~1,220 long records need ~820 source runs with ≥ 16K of history; nothing measures the yield or says what happens short of it (padding is not authorized for training records). Needs a decision (small). Non-blocking.

Verified and not flagged: bounded-regression derivation (§1, §9.4); s = 0.809; S = 763; 21 candidates; f_note ≈ 0.044/530; B_state satisfies both `max_state` and `max_packed`; §8.3 vote mapping; §8.4 order; §6.5 order matches D26 plus G5; §4.2 wordings match D38 verbatim; twin consistency, ledger strata, long-context gates are measurable and can fail.

---

## Part 2: Cost audit

- **§9.1 vs §11 disagree (amendment-created, counted in A-total as part of the cost fix):** §9.1 "run time 2–2.5 h … cost ~$10–13 including the smoke run"; §11 "~$10–19 (… × 2–3.5 h, plus smoke, resume-parity and pass-cap trials) | $6–25". One correct answer: reconcile §9.1 to §11. (Counted as finding C1.)
- **Training 2–3.5 h, $10–19, band $6–25:** defend. ~75–85M state tokens plus question tokens on an H100 with LoRA and checkpointing lands in that band; the smoke run is the instrument (Q2).
- **Candidate scoring 1–1.5 h, ~140M prefill tokens:** defend; ~31K tok/s prefill with shared prefix is reachable for 4B.
- **Unpriced (C2):** serve-path parity scores the winner *and* stock on dev through the serving path (~2 × 1,300 states), and the out-of-fold ECE "through the runtime path" adds another serving pass; ~0.5–1.5 h on the serving GPU appears nowhere in §11. Non-blocking; one correct answer (add the row).
- **Unpriced (C3):** the ~300 headless Claude Code runs carry only a dollar cap; wall-clock, parallelism and container pulls (SWE-Bench Pro images) have no estimate, and Run yield only redistributes quota after the fact. Opus raised this; the register's cost line addressed dollars only. Non-blocking; needs an estimate with a band and the per-job wall-clock limit named in §8.7 as the instrument.
- **Teacher 9–10K items × 2 votes, 1,000–2,000 calls, 2.5–5 h at 15 parallel:** defend as banded; F10's token bound changes the call count upward for long batches.
- **"the $200 cap binds; no current Haiku/Sonnet 5.5 price was checked":** honest label; the price list is one fetch away and should be checked before the run starts (not a finding against the spec's accounting).

---

## Part 3: Completeness against the ledger

Spec omissions already carried above: F2 (D32.P/D37 probe scoring), F8 (D20 R_k production for training), F14 (D20 "Filter recall is low on held-out instructions" — §12.3 should name the set). No further ledger decision bearing on data, labels, run, selection, calibration or evaluation is missing from the spec.

Ledger-side divergences (the spec is right by the register; the ledger did not follow, so a reader of both sees a conflict):
- **L1 D42** still reads "σ((z_q + b_q)/T_q)" and "within bf16 tolerance" for kernels; spec has σ(z/T + b) and the noise-floor rule (D44 agrees with the spec).
- **L2 D41** still reads "Replay comes through `--suite` decision-v7 `--replay`" and "`KEV_TEMPERATURE=1`"; D26 order lacks G5; D18 says long-gate items are "held-out".
- **L3 D43/D45** still read "relative run position" / "tenths of the run"; the spec's absolute-bin matching is a partner-confirmed build value changed by a round-1 fix without a ledger update (initializing-projects step 5: an amendment that re-pins a confirmed mechanism goes back as a question or is signed off and recorded).

---

## Part 4: Spec/task boundary

- **T1 (low):** §14 Q2 "*Impact:* the cut-off times" refers to task-file material no longer in the spec; reword to "the latest training start" or drop.
- Nothing else task-shaped remains: session recovery, run order, executor identity, cut-offs, thinking levels, key handling and download hygiene are absent. §8.3 "labelling subagents" and §11 "15 parallel subagents" are cost/throughput parameters, acceptable.

---

## Counts

- Register entries verified: **52** (47 landed/hold cleanly; 4 landed with new defect; 1 defense partly fails).
- Findings by kind: error 9 (F1, F4, F5, F6, F10, F12, F16, A2-type retention, C1); omission 9 (F2, F7, F8, F11, F13, F14, F15, F18, C2/C3 cost rows); unsupported claim 1 (F3); overreach 1 (F17); unneeded mechanism 1 (F9); amendment-created 5 (A1–A5, with C1 also amendment-created); task material 1 (T1). Ledger divergences noted: 3 (not spec defects).
- Amendment-created defects: **5** (+ the §9.1/§11 cost inconsistency).
- Blocking: **2** (F1, F2).

## Three most likely failure points

1. **F1, the positive floor at data freeze.** Arithmetic on the spec's own quotas puts L2, L4, L5, G4 and M8 well under 300 positives; the gate fires on the first freeze attempt and the agent must either breach N or improvise top-ups.
2. **A2, retention failing through noise.** With discordance above ~14% on decision-v7, a parity model fails retention 20–50% of the time, and the fallback walks the pick order toward stock, reproducing the round-1 failure the fix was meant to remove.
3. **F2 plus F4, the headline lift.** Three quarters of the probe items have no rendering or label mapping, and the gated TRACE pass may show reasoning deployment never shows; the "measured lift" is decided by choices the builder makes alone.

## Verdict

**Not implementation-ready**, by two blocking questions; everything else is in-place amendment with one correct answer or a small owner decision.

Blocking:
1. **F1:** where top-ups for under-floor questions come from, and whether N grows or s rescales (owner decision; the floor and the quotas are both David's).
2. **F2:** the conversion and label mapping for the aspi, UserIntentBench and IFBench probe items (write it; one correct answer per source, but it adjudicates the lift and cannot be left to the builder).

Owner decisions, non-blocking: A2 (retention rule above d ≈ 0.14), F5 (benign target set), F8 (R_k for natural runs), F18 (f_long shortfall). One-correct-answer amendments: A1, A3, A4, A5, F3, F4, F6, F7, F9–F17, C1–C3, T1; ledger updates L1–L3.