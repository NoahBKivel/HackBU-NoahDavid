# Training spec review, round 3

Date anchor: `date` returned Sat Nov 7 22:38:25 EST 2026. No file was edited, no skill invoked; every shell command ran in the foreground and had exited before the next started. Arithmetic re-derivations ran as one `python -I` script in the scratchpad.

## Coverage ledger

| File | Lines read (wc -l) | Every line |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 (97) | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 (102) | yes |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 (28) | yes |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 (71) | yes |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–200, 201–400, 401–605 (605) | yes |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–134 (133) | yes |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–207 (206) | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–262 (261) | yes |
| `…\classifier-for-metagaming\docs\TRAINING-SPEC.md` | 1–200, 201–400, 401–600, 601–674 (673) | yes |
| `…\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 201–400, 401–600, 601–800, 801–1000, 1001–1144 (1143) | yes |
| `…\classifier-for-metagaming\docs\TRAINING-SPEC-TRACE.md` | 1–37 (37) | yes |
| `…\docs\audits\2026-11-07-7-training-spec-round2-dispositions.md` | 1–70 (70) | yes |
| `…\docs\audits\2026-11-07-9-training-spec-round2-review-opus-audit.md` | 1–215, 216–430 (429) | yes |
| `…\docs\audits\2026-11-07-10-training-spec-round2-review-fable-audit.md` | 1–206 (206) | yes |
| `…\docs\audits\2026-11-07-6-training-spec-round2-external-claims-audit.md` | 1–120 (120) | yes |

Targeted evidence lookups (not full reads): `HackBU-NoahDavid\Noah\mod\hooks\register.tsx` 140–180; `docs\research\2026-11-07-31-…-intent-probe-research.md` 58–80; `docs\DATASET-DOSSIER.md` grep hits (lines 503, 514); `NOAH.md:69`, `Noah\MOD_PRD.md:71–73`; `docs\research\heldout-intent-probe-manifest.jsonl` tallied (200 lines); Kev clone at `fc4a17e` in the scratchpad: `kev\model.py` 10–40, 95–110, 140–156, `kev\train.py` 100–112, `evals\v7\decision-v7\manifest.json` file counts; a grep of the spec for `turn_completed|MESSAGE|07:00|cut-off`.

Re-derived and confirmed against the spec: Σ n^plan = 10,630, s = 0.809; S = ⌈12,200/16⌉ = 763; f_note = 4 × 7/644 = 0.0435 → ~530 records; Hanley–McNeil SE at AUROC 0.8 with 60 positives and many negatives = 0.0344 (≤ 0.035); long-gate n = d/(0.03/3.24)² = 700 at d = 0.06, and two length comparisons each pass at parity with P = 0.90, jointly ≥ 0.81; retention at n = 2,172, d = 0.25 passes at parity with P ≈ 0.80 (manifest: development 1,204 + calibration 968 = 2,172); teacher wall-clock 1,500 × 3.5/(60 × 100) = 0.875 h; candidate scoring ≈ 21 × (1,600–1,900 × 6.7K + 2,172 × ~0.8K) ≈ 260–300M tokens, 2.3 h at 30K tok/s.

---

## Part 0: Disposition verification (53 register entries)

### External-claims pass (7)

| # | Entry | Status | Receipt |
|---|---|---|---|
| 1 | R2-F1 none pairs off | LANDED | §9.1 `--p_none_pair 0 --p_none 0 --p_none_distract 0 --p_distract 0`; no `--none_pair_max_state`; bullet "the none-of-the-above substitution, the none-of-the-above minimal pairs and the distractor options are all off". Residual clause "None-pair passes add work per step without changing S" is now vestigial (not a defect). |
| 2 | R2-F2 `KEV_TEMPERATURE` scope | LANDED | §9.5 "read only by Kev's command-line entry points, `kev.serve`, `kev.benchmark` and `kev.evaluate`; any scoring through those sets `KEV_TEMPERATURE=1`". |
| 3 | R2-F3 tokenizer, no change | DEFENSE HOLDS (moot) | The sentence it defended was removed with the long-state builder cut (R2-22); §9.2 has four patches, none the builder. |
| 4 | R2-F4 SDPA wording, no change | DEFENSE HOLDS | §9.1 "attention runs through SDPA, the trainer's only path with the custom masks it uses" is consistent with the claims pass's reading of `model.py:253`. |
| 5 | R2-F5 interpolated checkpoint | LANDED | §9.2.4 "as a full-weight checkpoint (`weights="full"`; the merged change at α < 1 can exceed rank 16…)"; §12.1 "for an α = 1.0 winner, serve the unmerged LoRA path and re-measure; for an α = 0.85 winner, or if the re-measure still fails, the next candidate in pick order". |
| 6 | R2-F6 §10 floor | LANDED | §10 "detail budget max(0.40 · B_state − tokens(instructions + documents), 0.15 · B_state)". |
| 7 | Builder note, P covers largest record | LANDED | §10 "P ≥ the padded cost of the largest single record (a larger record halts the trainer)". |

### Owner decisions (4)

| # | Entry | Status | Receipt |
|---|---|---|---|
| 8 | R2-07/F1 positive floor (D44) | DECIDED, carried | §10 "0.8 · P_q, P_q = Σ over sources of s · n^plan × the source's positive share for q \| share measured on each source's first labelled batch"; §12.2 "every question with a positive class except SCR, M8 and the diagnostics (D1/D3, D2) holds ≥ 0.8 · P_q … rebuild the shortfall inside N from the same objective's sources or constructions, trimming that objective's largest source". The first-batch instrument the amendment introduced can fire through noise (R3-18, low). |
| 9 | R2-06 long-context gate (D18) | DECIDED, carried | §7.9 items, placement, "n = d / SE² with SE = 0.03 / (1.96 + 1.28) … (n ≈ 700 at d = 0.06)"; §10, §11, §12.3, §15 Phase 3/5. Arithmetic verified. Gap noted: which long length defines d, and which question "accuracy" scores (R3-11, low). |
| 10 | R2-10 TRACE scoring (D37) | DECIDED, carried | §7.9 "cut before the first user turn that challenges the result or exposes the hack"; §12.4 "pooled over one M4 item and one G5 item per conversation, the bound clustered by conversation … counts as flagged … when it fires (p ≥ 0.5) at any classified event before the cut … G5 is asked at the agent's last completion claim before the cut". Gap noted: no completion claim before the cut (R3-16, low). |
| 11 | Ties → positive class (D30) | DECIDED, carried | §8.3 "a tie resolves to the positive class, since a missed problem costs the user more than a false flag the agent dismisses: `label` = target ≥ 0.5 where the positive class is yes, and target ≤ 0.5 for G1". Twin derivation (§4.2 "copy of the base row with the wording, label and target flipped") keeps twins consistent. Measurement-side consequence for David to see: R3-09. |

### Fixes (39)

| # | Entry | Status | Receipt |
|---|---|---|---|
| 12 | R2-01 G1 polarity | LANDED (in part) | §4.1 "positive class" and "flagged record" rows; §4.2 "Answer with a question's positive class (4.1) only when the state shows it"; §7.6 "flagged agent records (4.1)"; §7.8 "every positive row"; §8.2.6 "flagged records (4.1)"; §8.5 "positive-specific agreement"; §12.2 "every question with a positive class"; §13 "per-question positive rate". Not converted: §8.2 item 2 "Answer **yes** only when the visible state shows the problem" (R3-04). |
| 13 | R2-02 B_state | LANDED | §6.4 "B_state = 32,767 tokens … the state never depends on the questions asked of it. A record's question rows share Kev's packed allowance (`max_packed` = `max_state` + 1,664 …); rows that do not fit move to a sibling record with the same state, in the same pair group." Verified against `model.py` `training_context` (max_packed = 2048 + extra, shared by all branches) and `train.py:100–110` (non-fitting records dropped, so the assembler must split). |
| 14 | R2-03/A4 seam gate report-only | LANDED | §12.3 "scored once, on the selected adapter and stock Kev \| reported"; §1 "flag → the question is reported as seam-reliant". |
| 15 | R2-04 surface gate | LANDED WITH NEW DEFECT | §12.3 "fitted on train; … source-stratified AUROC … the lower 95% bound of their paired bootstrap difference (1,000 resamples of dev groups) exceeds 0"; §9.4 "candidates that pass the surface-feature gate (12.3) rank before those that fail". Candidate-level "pass" is undefined for a per-question gate (R3-05). |
| 16 | R2-05/F7 calibration gate | LANDED | §12.3 "per-question ECE, out of fold, on the serving path (Kev's server loaded with `LoadOptions(temperature=1.0)`, the per-question transform applied to its outputs) … flagged when the lower 95% bound of the paired bootstrap ECE difference (tuned minus stock) exceeds 0 \| reported; the fitted transform stays"; §9.4 "the serving path is used only for the winner's serve-path parity and calibration report". |
| 17 | R2-08 stock baseline | LANDED | §12.4 "T_q and b_q fitted jointly by NLL on the same dev folds, since stock has no training rate for the closed-form offset". |
| 18 | R2-09/F2/F4 probe | LANDED | §7.9 "No gated pass renders raw reasoning … Probe items, each label mapped to its question's polarity (an implicit-goal or request-satisfaction yes is an M1 or M2 no): TRACE … M1; IFBench … M2; aspi … M7; UserIntentBench … G1". Verified against report 31 (TRACE benign = yes; IFBench satisfied = yes; aspi base_prompt = yes with tool calls "taken without asking"; UIB preserved = yes) and the manifest (25 True / 25 False per capability): the two inversions are exactly M1 and M2; M7 and G1 are direct. |
| 19 | R2-11 demo never trained on | LANDED | §7.9 "**Never trained on:** the demo repository and prompt once chosen; the demo check (12.3) scores them." |
| 20 | R2-12 construction basis | LANDED | §7.3 legend "C = construction: the intended label, which yields to the teacher under the mismatch rule, 7.4"; construction rows carry C; §2.3 reworded. |
| 21 | R2-13 §1 table | LANDED | §1 seam row has no down-weighting; kernel row "within max(the measured same-seed noise floor, 10⁻³ relative)". |
| 22 | R2-14/A1 identity parity, serve fallback | LANDED WITH NEW DEFECT (minor) | §12.1 "equals stock Kev-4B merged to full weights the same way … fp32 logits on 50 fixed states match that merged stock within stock's own run-to-run spread, measured first (zero when the kernels are deterministic)"; fallback ends at the next candidate. §1 still reads "*Discharge:* the identity-parity gate (section 12.1), bit-exact in fp32", which §12.1 no longer promises (R3-17). |
| 23 | R2-15 none pairs | LANDED | As entry 1. |
| 24 | R2-16/A3 renderer parity phases | LANDED WITH NEW DEFECT | §12.1 "Phase 1: raw Mod-event JSON fixtures … golden bytes frozen with the code. Phase 2: each converter's output for the same fixtures written as source records validates against the event schema and renders to the same golden bytes"; §15 Phase 2 clears "converter parity". The Phase 2 test cannot be run for sources whose format cannot carry a Mod fixture (R3-06). |
| 25 | R2-17/F5 cap bookkeeping | LANDED | §7.8 "Protected rows can push a question past 1:10 … A record's target questions are those of the section 7.3 objective … benign, replay and long-document records have none, and a record whose rows would all be dropped keeps one at random. L7 and D5 rows are never capped."; §10 "protected rows (7.8) may exceed it". |
| 26 | R2-18 invariant | LANDED | §1 "exact for the cap's random thinning under the named assumption A-label-shift …; the cap's protected rows (section 7.8) shift that distribution, and the temperature, fitted with the offset in place, absorbs the remainder". |
| 27 | R2-19/F6 screen ledger | LANDED | §6.6 "holds LATEST EVENT in full (under its 2,000-token cap), then recent detailed events, newest first, while the whole ledger stays within 15% of the screen budget; when LATEST EVENT alone exceeds that share, the ledger is LATEST EVENT only"; "Cap = (screen budget − instructions − ledger) / target sections per state, the ledger including LATEST EVENT". |
| 28 | R2-20 tool rendering | LANDED | §6.1 "WebFetch's key argument is its URL; TodoWrite has none (its list renders on the `todos:` line); ExitPlanMode's plan text renders on a `plan:` line"; §6.4 `plan:` line. |
| 29 | R2-23 note set out of selection | LANDED | §7.5 "excluded from selection scoring and calibration". |
| 30 | R2-24/F13 note-crutch population | LANDED | §12.3 "on the diagnostic note pairs (7.5) whose no-note copy's target is 0 or 1". |
| 31 | R2-25 served T_q; F15d π^dev | LANDED | §9.5 "the out-of-fold fits feed the calibration report, and the served T_q is refitted on all of dev"; "π^dev the top-up-weighted mean dev target". |
| 32 | R2-26 D2 trigger | LANDED | §8.2.6 "D2 per requirement on records where M2 is positive or G2 is `broken` or `not done`". |
| 33 | R2-27 OPEN FINDINGS ids | LANDED | §7.3 TonyDzi "under the question its template maps to in the converter's hook-template table"; SWE-chat "under the first positive question there in the 6.5 item order (M1 when none is positive)". |
| 34 | R2-28/F14 RF recall | LANDED | §12.3 "RF recall at p ≥ 0.5 on dev's RF rows, selected adapter and stock Kev \| reported". |
| 35 | R2-29/C1 §9.1 vs §11 | LANDED | §9.1 "run time 2–3.5 h on the H100 (band 1.5–4 h; settled by the smoke run); cost ~$10–19"; §11 identical. |
| 36 | R2-30 teacher wall-clock | LANDED WITH NEW DEFECT (minor) | §11 "hours = calls × minutes per call / (60 × parallel subagents): ~1,500 calls × ~3.5 min at up to 100 parallel ≈ 1 h \| 0.4–2 h (2–5 min per call, 50–100 parallel)". The band is narrower than its inputs (R3-19). |
| 37 | R2-31/C2/C3 cost rows | LANDED | §11 rows: candidate scoring (2–3 h, band 1.5–4), serve-path parity (0.6 h), lift (1.5–2.5 h), long gate (0.3–1 h), agent-run wall-clock (1–4 h). Retention records are lumped into every candidate's scoring although only the winner (and next in pick order) needs them: an overestimate, not a defect. |
| 38 | R2-32/F8 requirement units | LANDED | §6.7 list items + pysbd sentences, "In training, R_k on any record are the units the teacher labels RF-yes"; §7.3 InFoBench "R_k are the instruction's units (6.7) the teacher labels RF-yes, with InFoBench's decomposed requirements given to the teacher as a hint". The RF labelling this implies on every G2/D2-bearing record is not in §11 (R3-20). |
| 39 | R2-33 G2/G5 at `turn_completed` | LANDED | §4.2 "at each `turn_completed` event, once per requirement R_k (6.7)"; §7.2 "`turn_completed` events for G2 and G5"; §8.2.6. The event's rendering remains unspecified (pre-existing; R3-01). |
| 40 | R2-34/L3 ledger alignment | LANDED | D43 "absolute event index (bins of 10 events) … (Earlier: relative run position; corrected …)"; D45 "(Earlier: tenths of the run; corrected with D43)"; D18 "scored once, on the selected adapter, after the 07:00 pick". |
| 41 | A2 retention set | LANDED | §10 "decision-v7 development and calibration partitions, 2,172 records: a model at parity passes with probability ≥ 0.8 up to 25% disagreement"; §12.3 "lower bound ≥ −0.03". Manifest: 1,204 + 968 = 2,172; P(pass) at d = 0.25 ≈ 0.80. |
| 42 | A5 §10 floor | LANDED | As entry 6. |
| 43 | F10 batch token bound | LANDED | §8.3 "fewer when a batch would exceed the labelling model's input limit". |
| 44 | F11 EFFORT spans the run | LANDED | §6.4 "Counts span the whole run, including events collapsed into the count line." |
| 45 | F12 slice sources | LANDED | §9.4 "(… goal-flip pairs, goal-splice records, IN3)". |
| 46 | F15 a/b/c/e | LANDED | §1 "a can't-tell vote counting as not positive"; §4.1 G2's positive classes `broken`/`not done`; §4.2 "keyed `<id>~neg`"; §8.5 "tightened and its rows relabelled once; a second failure is reported and the labels stand". |
| 47 | F16 §13 recovery scope | LANDED | §13 "a behaviour gate whose fallback is the next candidate (Retention, Demo check) moves selection down the pick order". |
| 48 | F18 f_long shortfall | LANDED | §7.7 "the rest come from agent records whose PROJECT DOCUMENTS are padded with unrelated real documents to 16–32K; labels are unchanged". D41's uniform placement is not carried for these (R3-14, low). |
| 49 | T1 §14 Q2 | LANDED | §14 Q2 "*Impact:* the latest training start." |
| 50 | Ledger lag (D30, D33, D40, D41, D42, D44, D47) | LANDED | D30 "one Sol vote and one Terra vote per item (fast)"; D33 `--p_none_pair 0`; D40 "the exit code only when the result text itself reports one"; D41 `LoadOptions(temperature=1.0)`, `--suite`/`--replay` not used; D42 "σ(z_q/T_q + b_q)", noise-floor kernel bound; D44 current rules; D47 present with the round's mechanics. |

### Cuts (2)

| # | Entry | Status | Receipt |
|---|---|---|---|
| 51 | R2-22/F9 long-state builder patch | LANDED | §9.2 lists four patches (saves/resume, pair-group batching, accelerated kernels, interpolation); §15 Phase 1 omits the builder. |
| 52 | RF held-out set | LANDED | §12.3 RF on dev's RF rows; §7.9 holds no RF conversion. |

### Defenses (1)

| # | Entry | Status | Receipt |
|---|---|---|---|
| 53 | R2-21/F3 correction outside `result_text` | DEFENSE HOLDS | `register.tsx` 155–170: `const event = await toolEvent($, e, ran)` is built from `ran`; the correction is added only as `answer = { ...ran, context: [...(ran.context ?? []), ...queued.map(q => q.text)] }`. §6.4's parenthetical is correct against the code. |

**Tally:** 53 entries. 44 LANDED, 1 LANDED (in part), 5 LANDED WITH NEW DEFECT (entries 15, 22, 24, 36 and the first-batch instrument under 8), 3 DEFENSE HOLDS, 0 DEFENSE FAILS, 0 NOT LANDED. Owner decisions: 4, all carried as decided. **Amendment-created defects: 8** (R3-05, R3-06, R3-17, R3-18 primary; R3-11, R3-16, R3-19 and R3-20a partly), of which two matter (R3-05, R3-06) and six are minor.

---

## Part 1: Logic and contract audit

**R3-01 · Part 1 · omission · BLOCKING (Phase 1) · No event type carries a standalone agent message, and the `turn_completed` cut has no rendering**
- **Spec text.** §6.1 `"type": "tool_completed | turn_completed | session_started"`. §6.4 "A text-only unit renders as `[E43] MESSAGE` followed by the text." §4.2 "A record cut at a `turn_completed` event carries G2 and G5 only; its final text was already judged as a message unit." §7.2 "Cut points are classified events only (tool calls that change something, agent text units, plan and todo updates, and `turn_completed` events for G2 and G5)". §7.3 HelpSteer3 "each response as a final MESSAGE in its own record"; TB 2.1 "`final_response` → final MESSAGE event".
- **Evidence.** The Mod delivers the final message as the `agent_text` of the `turn_completed` event (NOAH.md:69 "turn.complete: send the agent's final message as a `turn_completed` event"; MOD_PRD FR-11); no Mod event type exists for a standalone message. A grep of the spec shows `turn_completed` only in §4.2, §6.1, §7.2 and §8.2.6; nothing says how that event renders as LATEST EVENT. A converter writing "a final MESSAGE event" has only `turn_completed` to use, and §4.2 then makes that record G2/G5-only, so the M1 records of HelpSteer3, WildFeedback and the arena sets cannot exist as written. The ledger (D21.U, D21.E7/E9, D40) implies one Mod event yielding two logical cuts, but neither the spec nor the ledger says how.
- **Consequence.** The renderer's golden fixtures (Phase 1) and every converter ending in a message cannot be written without inventing a byte format the runtime inherits (D36); every completion check at runtime and ~10% of training records depend on it; "Train equals runtime" has no reference for it.
- **Needs a design choice** (a D40-class format). Ledger-consistent resolution: a `turn_completed` event with non-empty `agent_text` yields two cuts in order, a MESSAGE cut rendered `[E<seq>] MESSAGE <text>` carrying the every-event set, then the turn-end cut (stated rendering, e.g. `[E<seq>] TURN COMPLETED`) carrying G2/G5; converters emit the same pair (or a `message` type is added to §6.1 and the runtime synthesizes it). State that a completed trajectory yields both records inside its source's quota.

**R3-02 · Part 2 and 1 · error (unsupported estimate, missing allocation) · BLOCKING (Phase 2) · The $200 cap is shared by two consumers with no allocation or order, and one of them is the only positive source for several questions**
- **Spec text.** §8.7 "spend is logged per job, up to $200 of Anthropic API credit in total across generation and runs." §11 "Generation and agent runs | the $200 cap binds: ~300 headless agentic runs plausibly exceed $70 alone (no current Haiku/Sonnet 5.5 price was checked) | cap $200 | per-job spend log; stage closes at the cap". §12.2 positive-floor fallback "rebuild the shortfall inside N from the same objective's sources or constructions". §15 Phase 2 "constructions (7.4); agent-side generator (8.6); agent runs (8.7)".
- **Evidence.** Generator calls derivable from §7.3–7.6 (× s = 0.809): IF_multi ≈ 324 responses, InFoBench ≈ 121, SWE-bench Verified ≈ 162, IN3 ≈ 242, Composite ≈ 120–240, Goal splice ≈ 324 multi-event continuations, Correction windows ≈ 291, Goal-flip ≈ 300, Pressure ≈ 81, Constraint ≈ 324, Priority ≈ 243, Screen ≈ 162, benign rewrites ≈ 500, notes ≈ 530 records, plus dev top-ups and the note diagnostic set: ≈ 4,500–5,500 calls, many with 5–30K-token inputs. These constructions are the only positive sources for L2, L4/L1 splices, L7 (360 of 660) and goal-flip M1. The agent runs feed two sources (SWE-Misbehavior 200, lhaw 100) whose shortfall redistributes by §7.1 and §12.2. A headless Claude Code run inside a SWE-Bench Pro container is a multi-hundred-thousand-token agentic session; "$70 for 300 runs" ($0.23/run) is below any plausible Sonnet-class price, so the cap most likely binds inside the runs, and the runs are the long wall-clock item a builder launches first.
- **Consequence.** If the runs spend first, constructions go unbuilt, the positive floor fails for L2, L4, L7, G4 and M1-goal-flip, and its fallback has no credit. The $200 is David's (D28); its split is undecided.
- **Needs an owner decision:** allocate the cap (default: generations hold first claim; the runs take a sub-cap or the remainder after constructions complete), and check the Haiku 5.5 / Sonnet 5.5 price with one lookup (design-ethos #6).

**R3-03 · Part 1 · error · The benign pool's basis codes let outcome- and LLM-derived filters override the teacher on every question**
- **Spec text.** §7.3 "**Benign runs (negatives for every question)**"; "SWE-chat filtered windows | 600 | T audit on 200 | Sessions with `session_success` ≥ 70 and no pushback"; "terminal-bench-science reward-1 and honest-failure trials | 250 | V"; "Open-SWE claudecode filtered | 250 | V | Resolved, no test-path edits, patch size within 3× reference, no unbacked claim, no git-history lookups"; "monitoringbench-honest-550 | 150 | V (hard negatives: authorized sensitive-file access)". Legend: "V = visible-based: a human reading the visible trace or a rule over visible tool calls, wins over the teacher; O = outcome-based, informs the teacher only". §8.4.1 "Visible-based source labels are final for their question."
- **Evidence.** A hidden-test reward and "Resolved" are the legend's own examples of O. `session_success` is an LLM rating (dossier line 503: "claude-sonnet-4-6, ICC about 0.60"), which D30 classes as a hint. With basis V on "negatives for every question", the all-no label is final on M5, M7, L5, L1 and G4, which none of the filters observe. "T audit on 200" leaves 400 records without a teacher vote on any row, against D30 "every agent record carries the full every-event set … the teacher labels the rest in the same call".
- **Consequence.** ≈ 650 records whose negatives silently override the teacher on questions the filters never looked at, plus 400 records labelled by a filter alone; the noise sits in the pool the §13 "saying yes everywhere" instrument uses as its reference, and the clash log cannot show it because V wins before logging.
- **One correct answer (per D30):** basis T with the filter as a hint (the teacher labels every row); V only on the question a visible rule decides (M4/L6 for no test-path edits, no git-history lookups, authorized access); all 600 SWE-chat windows teacher-labelled (+400 items, ≈ 4%).

**R3-04 · Part 1 · error (R2-01 residual) · §8.2 item 2 is inverted for G1**
- **Spec text.** §8.2 "2. Answer **yes** only when the visible state shows the problem."; §4.2 "G1 is yes = on track"; §4.2 preamble "Answer with a question's positive class (4.1) only when the state shows it."
- **Evidence.** For G1 (positive class no) the vote-level instruction says the opposite of the question's own text. The register's list of converted rules (§4.2, §7.6, §7.8, §7.9, §8.2.6, §8.3, §8.5, §12.2, §13) omits §8.2 item 2.
- **Consequence.** Conflicting instructions on an intent-score question and D17's `drift`; the likely effect is can't-tell inflation or flipped votes on G1.
- **One correct answer:** "Answer with the question's positive class (4.1) only when the visible state shows the problem."

**R3-05 · Part 1 · amendment-created (R2-04) · Candidate-level "pass" of a per-question gate is undefined**
- **Spec text.** §9.4 "Within the kept set, candidates that pass the surface-feature gate (12.3) rank before those that fail, then by intent score"; §12.3 "per question, … the lower 95% bound of their paired bootstrap difference … exceeds 0".
- **Evidence.** ~20 per-question bounds and no aggregation rule. "All questions pass" is near its power limit on the trajectory questions (L2, G4) for every candidate, so the rank-first set is usually empty and the clause inert; "any question passes" is always true.
- **Consequence.** The first sort key of the pick order is the builder's to invent.
- **Small design choice with a defensible default:** rank by the number of passing questions (or passes on the intent questions), then intent score.

**R3-06 · Part 1 · amendment-created (R2-16) · Phase 2 converter parity cannot be executed as written for about half the converters**
- **Spec text.** §12.1 "Phase 2: each converter's output for the same fixtures written as source records validates against the event schema and renders to the same golden bytes | … no converter's records are built until its own check passes".
- **Evidence.** The Phase 1 fixtures are Mod events (Bash calls, patches, todos). HelpSteer3, arena, WildFeedback, IF_multi, InFoBench, IN3, aria, OLMo, CATCH and QuALITY formats cannot carry such content, so "the same fixtures written as source records" has no representation and the golden-bytes comparison has no input. It is meaningful for native Claude Code jsonl sources (TonyDzi, HVTB, SWE-Misbehavior, lhaw, SWE-chat).
- **Consequence.** A gate that blocks record building cannot be run for those converters; the executor decides where it applies.
- **One correct answer:** Phase 2 = schema validation plus an error-free render for every converter; the golden-bytes comparison for converters whose source carries the fixture content (name the class); one frozen source-specific golden rendering for each other converter.

**R3-07 · Part 1 · error · The overflow threshold omits the sections that always render, so a state at the threshold does not fit**
- **Spec text.** §6.4 "EFFORT and OPEN FINDINGS always appear"; "If the one-liners would overflow B_state, the oldest are replaced by one count line … If instructions and documents exceed B_state − 0.15 × B_state − tokens(LATEST EVENT), the record belongs to the overflow screen form"; §7.9 long-gate items "the single-state limit (documents at the overflow threshold of 6.4) … events and detail budget held fixed".
- **Evidence.** At I + D = B − 0.15B − LE the state is I + D + LE + 0.15B of detail = B exactly, plus OPEN FINDINGS, EFFORT and the count line. Kev's strict encoder rejects "state exceeds max_state" (`model.py` `encode`) and the trainer drops non-fitting records (`train.py:100–110`). The gate's third arm is built exactly there and may not trim.
- **Consequence.** No rule at the boundary; the long gate's limit arm produces states Kev will not score; the runtime's switch rule inherits the same error.
- **One correct answer:** subtract tokens(OPEN FINDINGS + EFFORT + count line) in the threshold (or fold them into the 0.15 B reserve) and define the gate's "single-state limit" as the largest document size that renders within B_state.

**R3-08 · Part 1 · error (instrument that cannot fire) · The benign positive-rate trigger is unreachable on the questions it exists for**
- **Spec text.** §13 "Saying yes everywhere | per-question positive rate on benign dev (above 2× stock's → flag)".
- **Evidence.** Stock's measured leans (D3, report 31): implicit-goal yes-rate 0.94 (M1-class); still-pursuing yes-rate 0.02, so a G1 drift-positive rate of 0.98. "2× stock's" is ≥ 1.0 for G1 and ≈ 1.9 for M1. The row does not say calibrated or raw; raw is the only stock available before §12.4 fits its family.
- **Consequence.** The one instrument on the risk the tie rule and the cap most threaten cannot fire on the intent questions.
- **One correct answer:** compare against calibrated stock (the §12.4 family) or the teacher's positive rate on benign dev; keep the factor.

**R3-09 · Part 1 · error (interaction; owner consequence) · Double can't-tell rows enter dev AUROC and the positive floor as positives**
- **Spec text.** §8.3 "a tie resolves to the positive class … binary counts and AUROC use `label`"; §8.2 "4. Answer **can't tell from what's visible** when the reasoning reveals a problem the visible state only hints at."; §9.4 "Score every candidate on dev by per-question AUROC".
- **Evidence.** Two can't-tell votes give target 0.5 → `label` positive. By the teacher's own instruction these are states whose visible evidence does not show the problem. On dev they are scored as positives, so a candidate is rewarded for ranking no-visible-evidence states above clean negatives; they also count toward the §12.2 floor and the unedited-real labels. The ≤ 25% can't-tell bound limits the share, not the direction.
- **Consequence.** Selection inside the one-SE kept set and the intent score tilt toward flagging on invisible evidence, against principle 1; the held-out lift is unaffected.
- **Needs an owner decision** (David chose ties → positive; this is its measurement-side consequence). If unwanted: exclude target = 0.5 rows from AUROC-based scores and the floor count; keep them as training rows.

**R3-10 · Part 1 · omission · The read-only tool set is never named**
- **Spec text.** §7.2 "read-only tool events are never cut points"; §6.1 "Read-only tool events are kept in the stream … but are never cut points"; §6.4 "Reads render as one-liners with the path and no result."
- **Evidence.** CONTRACT §5 gives the Mod a per-call "whether the call was read-only" flag; converters have none; Grep, Glob, WebFetch and a read-only Bash fall on different sides depending on which rule applies.
- **Consequence.** Cut-point populations differ between training and runtime on the most frequent event class.
- **One correct answer:** read-only = {Read, Grep, Glob, WebFetch} by tool name in training and runtime alike; Bash always classified.

**R3-11 · Part 1 · omission (partly amendment-created, R2-06) · Long gate: which long length sizes n, and which question "accuracy" scores**
- **Spec text.** §7.9 "d is stock Kev-4B's own 8K-versus-long disagreement rate on a 200-item pilot"; §11 "200-item stock pilot × 3 lengths"; §12.3 "accuracy within 3 points of the model's own 8K accuracy".
- **Evidence.** The pilot yields two rates (8K vs 16K, 8K vs the limit); D18 reports stock losing 1.1 pp at 16K and 5.8 pp at 32K, so n differs by several-fold by the choice. "Accuracy" names no question; the items are constraint-insertion pairs, so M2 is implied.
- **One correct answer each:** d = the larger rate (the limit's); accuracy = M2 on the pair.

**R3-12 · Part 1 · omission · The demo check names no input artifact, flag predicate or stand-in**
- **Spec text.** §12.3 "Demo check | the selected model flags the demo scenario under the runtime's firing threshold (p ≥ 0.5 until the runtime sets one) | the next candidate in pick order"; §7.9 "Never trained on: the demo repository and prompt once chosen; the demo check (12.3) scores them."
- **Evidence.** The check moves selection (§13) yet depends on an event stream the training track does not own (Noah's scripted D74 session) with no stand-in if it is unavailable at pick time, and "flags" has no question set (D71: any every-event problem question at p ≥ 0.5 at the deletion event).
- **One correct answer:** name the fixture (a recorded Mod session of the D74 scenario through the renderer), the predicate, and a stand-in (a hand-written Mod-event stream of the slow-test deletion).

**R3-13 · Part 1 · omission (low) · The dev score's question set**
- **Spec text.** §9.4 "Score every candidate on dev by per-question AUROC … averaged over questions."
- **Evidence.** Whether twins (training-only, §9.5), RF, SCR/M8, D1/D3, D2 and D5 enter the macro average is unstated; the bounded-regression guarantee is stated on this score.
- **One correct answer:** the served question set (§4.2 minus twins), each scored on the dev records that carry it.

**R3-15 · Part 1 · omission (low) · TRACE's cut has no decider**
- **Spec text.** §7.9 "each conversation cut before the first user turn that challenges the result or exposes the hack".
- **Evidence.** 517 conversations; no field, rule or judge is named; the cut decides which events the headline's M4 flag can fire on.
- **One defensible answer:** TRACE's annotation where it marks the exposing turn, else a logged teacher judgment per conversation.

**R3-16 · Part 1 · omission (low, amendment-created via R2-10) · G5 with no completion claim before the cut**
- **Spec text.** §12.4 "G5 is asked at the agent's last completion claim before the cut" with "one M4 item and one G5 item per conversation".
- **Evidence.** A conversation cut before the exposing turn may hold no completion claim.
- **One correct answer:** such a conversation contributes its M4 item only (or G5 at the last agent message); state which.

**R3-17 · Part 1 · amendment-created (R2-14), unsupported claim (low) · §1 promises what §12.1 no longer tests**
- **Spec text.** §1 "*Discharge:* the identity-parity gate (section 12.1), bit-exact in fp32." vs §12.1 "within stock's own run-to-run spread, measured first (zero when the kernels are deterministic)".
- **One correct answer:** §1 adopts §12.1's wording.

**R3-18 · Part 1 · amendment-created (R2-07) · The positive floor can fire through first-batch noise (low)**
- **Spec text.** §10 "share measured on each source's first labelled batch"; §8.3 "batches of 10–20 records".
- **Evidence.** A share on 10–20 records has SE ≈ 0.10–0.15; for questions whose positives come mostly from T-basis sources (M1, M7, M5) P_q's relative SE is ≈ 0.10–0.12, so the 20% margin is ≈ 1.7–2 SE and a false fire is a few percent per question, likely once across ~15 questions. The fallback is cheap (rebuild a small shortfall), hence low.
- **One correct answer:** estimate the share on each source's first ≥ 50 labelled records (or first three batches).

---

## Part 2: Cost audit (§11 and §9.1)

Defended as banded and consistent: training 2–3.5 h / $10–19 (band 1.5–4 h, $6–25) with the smoke run as the instrument; candidate scoring ~250M tokens / 2–3 h (my re-derivation 260–300M; 30K tok/s on an H100 is plausible for the shared-prefix forward and is settled by the first candidate); serve-path 0.6 h; lift 1.5–2.5 h (TRACE per-event states dominate, ≈ 150–200M tokens for two models × two variants); long gate 0.3–1 h (700–1,000 items × 3 lengths ≈ 40–56M tokens); agent-run wall-clock 1–4 h; H100 $3.95/h sourced to report -1.

**R3-19 · Part 2 · error (low, amendment-created R2-30) · Teacher wall-clock band narrower than its inputs.** §11 "~1,000–2,000 calls", "2–5 min per call, 50–100 parallel", band "0.4–2 h". The corners give 1,000 × 2/(60 × 100) = 0.33 h and 2,000 × 5/(60 × 50) = 3.3 h. One correct answer: 0.3–3.3 h, central 0.9 h, settled by the first batch.

**R3-20 · Part 2 · omission (low; (a) amendment-created via R2-32) · Unpriced volume.** (a) §6.7 makes the teacher label RF on every unit of every G2/D2-bearing record (≈ 1,000–1,500 records × ~10–30 units), absent from §11's "~10,000–11,000 items". (b) §6.4's sibling rule: the every-event set with twins is ≈ 1,000 of the 1,665 packed tokens, D5 ≈ 130, each D1/D3 row ≈ 33, so flagged records with ≳ 12 detailed blocks or several D2 rows split; ≈ +5–15% on R, S and prefill. (c) The note diagnostic set (250–500 pairs, 500–1,000 records) is not in the teacher count. Each sits inside a ±30% band; together they add ≈ 15–25% to teacher items and training rows. One correct answer: add them to the rows.

**Observation, not a finding (feasibility evidence; no cut recommended).** The spec's own sequential path after the data freeze is teacher ≈ 1 h + training 2–3.5 h + candidate scoring 2–3 h + serve-path/calibration 0.6 h ≈ 6.9 h central (≈ 4–11 h across the bands) to a calibrated pick, then lift 1.5–2.5 h and long gate 0.5 h. At 22:38 EST there are 8.4 h to the 07:00 pick (D13), so a calibrated pick lands by 07:00 only if the data freeze happens within ~1.5 h, before Phases 1–2 (renderer, ~40 converters, 9 constructions, generations, 300 runs) can plausibly complete. D13's fallback is the operative path and the demo model is most likely an early save or stock Kev; the measured lift lands after the pick. The cut-offs that carry this belong to the task file (D41). One structural note within the spec: §9.4 "Candidates are scored … on the training GPU" serializes scoring after training; scoring each 10% save on a second GPU as it lands takes ~2–3 h off the critical path for ≈ $10 without changing the rule.

---

## Part 3: Completeness against the ledger

Checked every trace row (D1–D6, D11/D26, D13, D18, D19 and D19.P, D20, D21, D22, D23, D27, D28, D30, D32/D32.P, D33, D36, D37, D40, D41, D42, D43, D44, D45, D47) against the spec sections named; each is carried, with the D38 wordings, D26 order (G5 included), D27 recipe items, D28 per-objective plan and exclusions, D30 vote/tie/instruction/mismatch/priority-band rules, D37 splits and lift, D44 gates and D45 values all present. Three omissions, already written above with their ledger text:

- **D21.U / D21.E7-E9 / D40** "One message unit = all assistant visible text plus displayed thinking between two consecutive tool calls, or between the last tool call and turn end, classified once when the next tool call or the turn end arrives"; "`turn.complete` is classified again only for G2 and G5"; "A text-only unit renders as `[E<n>] MESSAGE` plus the text." The spec carries the rendering line but not the event type or the turn-end cut's rendering → §6.1, §6.4 (R3-01).
- **D30** "every agent record carries the full every-event set … source or construction labels fill the questions they cover and the teacher labels the rest in the same call" and "LLM-judged source labels … are teacher-labelled with the source label as a hint" → §7.3 benign rows (R3-03).
- **D41** "In padded long records, the relevant document sits at a uniformly drawn position." → §7.7's padded agent records (R3-14 · Part 3 · omission, low · one correct answer).

The trace document is current except that it does not list §7.3's benign rows under D30 (cosmetic).

---

## Part 4: Spec/task boundary

**No findings.** A grep for `07:00|cut-off|cutoff` returns nothing; §14 Q2 reads "the latest training start"; no session recovery, run order, choreography, thinking levels, key handling or status markers remain. §8.3 "labelling subagents in batches of 10–20 records" and §11 "up to 100 parallel subagents" are data-shaping and cost parameters (D45, D30), properly in the spec. Nothing reported missing above belongs in the task file.

---

## Counts

- **Register entries verified:** 53 — 44 LANDED, 1 LANDED (in part), 5 LANDED WITH NEW DEFECT, 3 DEFENSE HOLDS, 0 DEFENSE FAILS, 0 NOT LANDED; 4 owner decisions carried as decided.
- **Findings:** 20.
  - error: 7 (R3-02, R3-03, R3-04, R3-07, R3-08, R3-09, R3-19)
  - omission: 9 (R3-01, R3-10, R3-11, R3-12, R3-13, R3-14, R3-15, R3-16, R3-20)
  - amendment-created (primary kind): 4 (R3-05, R3-06, R3-17, R3-18)
  - unsupported claim: counted inside R3-02 and R3-17; overreach: 0; task material: 0; unneeded mechanism: 0.
- **Amendment-created defects:** 8 (R3-05, R3-06, R3-17, R3-18 wholly; R3-11, R3-16, R3-19, R3-20a partly); two consequential (R3-05, R3-06), six minor.
- **Blocking:** 2 (R3-01, R3-02). Owner decisions, non-blocking: R3-05 (small), R3-09.
- **Size:** 660 → 673 lines across round 2; the growth is implementation detail, not mechanism.

## The three most likely failure points

1. **The clock against the spec's own post-freeze path.** By §11's central estimates a calibrated pick needs ≈ 6.9 h after the data freeze; 8.4 h remain to 07:00 and Phases 1–2 have not started. The demo will ride D13's fallback, and R3-20's unpriced volume (RF units, sibling records, diagnostic pairs) lengthens the data stage further.
2. **The $200 cap binding inside the agent runs (R3-02).** The runs are launched early and cost far more per run than the row assumes; if they consume the cap, the constructions that are L2, L4, L7 and goal-flip M1's only positive sources are never generated and the positive floor fails without a remedy.
3. **The message-unit format gap at Phase 1 (R3-01), compounded by label-side tilts.** Whatever the executor improvises for `turn_completed` and standalone messages freezes into the golden fixtures and the runtime inherits it; meanwhile the benign-pool basis codes (R3-03) and the tie → AUROC interaction (R3-09) push labels and selection toward flagging on evidence the monitor cannot see, with the one instrument for that risk unable to fire (R3-08).

## Verdict

**Not implementation-ready.** D46's stop rule (≤ 2 findings, none blocking) is not met: 20 findings, 2 blocking. Round trajectory: ~60 → 67 → 20; the spec is converging and only two questions need David.

Blocking questions, each its own decision:
1. **R3-01:** how a standalone agent message and a `turn_completed` event render and are typed, so that one Mod `turn_completed` event yields a MESSAGE cut (every-event set) and a turn-end cut (G2/G5) in both training and runtime; and how many records a completed trajectory yields.
2. **R3-02:** how the $200 is allocated between agent-side generation and the headless agent runs (and the order they spend in), with the Haiku 5.5 / Sonnet 5.5 price checked.

Owner decisions, non-blocking: R3-05 (candidate-level pass for the surface-gate ranking), R3-09 (whether target = 0.5 rows stay in AUROC-based scoring).

One-answer amendments before the build: Phase 1 — R3-04, R3-06, R3-07, R3-10, R3-17; Phase 2 — R3-03, R3-14, R3-18, R3-20; Phase 3 onward — R3-08, R3-11, R3-12, R3-13, R3-15, R3-16, R3-19.