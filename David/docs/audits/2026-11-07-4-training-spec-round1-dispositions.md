# Round 1 dispositions: training specification

Sources: Opus review (`2026-11-07-2-…`, findings O-F1…O-F30, O1, O2), external-claims check (`2026-11-07-3-…`, C-F1…C-F13), Fable review (pending). Each finding was checked against the spec, the ledger and the cited source before disposition.

## Headline fixes (one correct answer)

| Finding | Disposition |
|---|---|
| O-F1, C-F2: α = 0 identity breaks (the pointer head trains; Kev's `lora_scale` scales the whole adapter) | **Fix.** Interpolate in weight space over every trained tensor: θ(α) = θ_kev + α(θ_tuned − θ_kev), LoRA taken as its merged product, pointer head included; a new trainer-side tool in §9.2. Δ becomes "the LoRA and head change". At α = 0 the tensors equal stock's, so identity parity holds. |
| C-F3: FlashAttention cannot run in Kev's trainer | **Fix.** Kernel check becomes "fla Triton kernels active for the DeltaNet layers; SDPA for attention". The ledger's D33 line naming FlashAttention is corrected the same way. |
| C-F4, O-F5: a 32,768-token state is rejected; questions share 1,664 tokens; one-liners can overflow | **Fix.** B_state per record = `--max_state` − (that record's question tokens) − 1, counted with Kev's tokenizer on Kev's rendering. When one-liners overflow, the oldest are replaced by one count line ("[E1–E120: 120 earlier events]"); EFFORT still counts them. |
| C-F1: `--replay` cannot rebalance or keep pairs | **Fix.** The 2,000 decision-v7 records are pre-built (rebalanced, pair groups kept) and passed through `--data` with their source names; `--replay` and `--suite` are dropped from the command. |
| C-F5: `KEV_TEMPERATURE` is ignored by the project's Modal class | **Fix.** Serving passes `LoadOptions(temperature=1.0)`; per-question T and b are applied after. |
| C-F6: default none-of-the-above augmentation relabels G2 and L7 rows | **Fix.** `--p_none 0 --p_none_distract 0 --p_distract 0`: the question set fixes those option sets (G2 already has "can't tell"); a substituted "none" would teach a label outside them. |
| O-F7: Retention at n = 300 fails through noise; the long gate's n is unsized | **Fix.** Retention uses all 1,204 decision-v7 dev records; the long-gate item count is sized by formula from measured discordance so that a model at parity passes with probability ≥ 0.8. |
| O-F22: calibration gate is in-sample | **Fix.** T_q and b_q are cross-fitted over 5 dev folds; ECE is measured out of fold. |
| O-F9: prior offset placement and π | **Fix.** p = σ(z/T_q + b_q) (offset after temperature, T fitted with the offset in place); π^train = mean target after the cap; dev top-up records are weighted back to their question's pre-top-up rate. The invariant is reworded: the offset corrects the balance cap to the collected pool's prevalence, not to deployment prevalence. |
| O-F2: renderer parity before a runtime exists | **Fix.** The renderer is one module the runtime imports; the gate compares the converter path against direct Mod-event JSON on fixtures written in both forms (Noah's sample events plus recorded Mod sessions when available). |
| O-F3 (part): stock baseline denied the bias offset | **Fix.** Stock gets the same calibration family (offset and temperature, cross-fitted on dev). |
| Cost audit: candidate scoring through the serving path would take hours | **Fix.** Candidates are scored with the batched training forward (shared prefix) on the training GPU; the serving path is used only for serve-path parity on the winner. |
| O-F28, C-F7: serve-path threshold unsupported | **Fix.** Relative rule: the winner's serve-path gap ≤ 1.5 × stock Kev's own train-forward vs serve-path gap on the same dev. Fallback: serve unmerged LoRA and re-measure. |

## Remaining fixes (grouped)

- **Leakage (O-F4):** source labels filtered to `event_seq ≤ k`; each note written only from its own step's reasoning; §8.1 states the decided exception: outcome-based labels reach the teacher as hints.
- **Matching (O-F14):** negatives matched jointly on event type and absolute event index (in bins of 10 events), the cue the model can see.
- **Arithmetic (O-F16):** replay stated as 3,000 = 2,000 + 500 + 500; ρ_replay = 3,000 / 12,200.
- **Steps (O-F15 part):** S counts records after the cap.
- **Pick order (O-F23):** candidates ranked by intent score within the kept set, then stock; every fallback moves down that order.
- **Schema (O-F27, O-F17, O-F18):** events accept a superset of fields; PowerShell renders as Bash; an unknown tool renders under its own name with its first string argument; repeated questions take key suffixes (`G2#R3`, `D1#E41`, `SCR#S2`); RF's state is the ⟦ ⟧ window alone.
- **Strings (O-F19):** a short-name table for every question; D2 summary = "<short names> at <E-refs>"; G5 placed after G2 in the item order; construction p values drawn uniformly from [0.6, 0.99].
- **Labels (C-F10, C-F11):** Terminal Wrench `key_hack_steps`, Goodfire flags and eungyeuk negatives are LLM judgements or sample checks, so they become T with the label as a hint.
- **Rewording (C-F8, C-F9, C-F12, C-F13, O-F26, O-F29, O-F30):** the long-state builder's real limits; triton evidence scoped to 3.9.0; up to 15 near-duplicates per task; the 3-point tolerance as the spec's own choice borrowed from Kev's context rule; honest residuals and broader secret patterns (`ghp_`, `AKIA`, `hf_`, `sk-proj-`, private-key headers); selection on uncalibrated logits stated precisely; the cited studies named.
- **Floors (O-F24, O-F25):** the intent slice takes the dev floor per intent question and may include splice records; positive floor = 300 positive training rows per question (sourced: the data-mixing research's rare-question floor); low yield = a source that leaves its objective under that floor.
- **Long-gate items (O-F21):** M2 records whose deciding requirement lives in a project document; PROJECT DOCUMENTS padded with unrelated real documents to 8K/16K/32K; the requirement document at start, middle or end; events and detail budget held fixed so labels are unchanged.
- **Note-crutch set (O-F13 part):** a separate dev diagnostic set of note pairs, sized so the paired-difference SE ≤ 0.02, excluded from calibration; dev otherwise at the real rate.
- **Instruments (O1):** RF recall on held-out instructions reported in §12.
- **Boundary (Part 4):** cut-off scheduling, the 07:00 timing, subagent thinking levels, download handling and the API-key rule move to the task file; "(pending adversarial review)" leaves the front matter.

## Defenses

- **O2 (Terminal Wrench "down-weighted"):** the ledger's down-weighting is its reduced quota (250 of 1,750 in its objective); the spec carries it.
- **O-F11 (fallbacks need a second run):** the one-run constraint is the owner's; post-run fallbacks are report-and-select by design. The fix is wording (report-only, plus selection-time preference), and the surface baseline is computed within each source so it measures shortcuts, not source composition.
- **O-F4 (outcome hints):** the owner decided outcome-based labels inform the teacher; the spec's "never receives outcomes" sentence is the error, not the design.

## Decisions for David (asked one at a time)

1. O-F15: the balance cap drops ~80% of question rows and changes the decided mix.
2. O-F8: the dev floor's SE threshold (0.05 ≈ 33 positives; ~60 positives needs ≈ 0.035).
3. O-F10: the teacher-agreement statistic and threshold.
4. O-F3: the lift protocol (which question scores each probe capability; pooled or both).
5. O-F12: the unedited-real set for the seam gate.
6. O-F6: how "the user stated priorities" is decided (it gates G4 and EFFORT).
7. O-F20: the overflow-screen document pool and screen ledger size.

## Fable review (`2026-11-07-5-…`, findings V-F1…V-F18, V-O1…O6, V-T1…T8)

Overlaps with the Opus review and claims check (V-F1, V-F2, V-F7a/c, V-F11, V-F12, V-F13 baseline, V-F14, V-F15, V-F16, V-F17 floor/yield/agreement/down-weight, V-F18 EFFORT/RF/G5, V-O1, V-O6 partly, V-T1–T8) were already disposed above.

**New fixes (one correct answer):**
- V-F3 ties: `label` = target > 0.5, so a tie is no; soft target unchanged.
- V-F4 pairs vs cap: pair-group rows are exempt from the cap.
- V-F5 rewrite copies: copies are teacher-labelled records; text-borne questions (M5, M7, M1) take the copy's own labels; action labels carry over.
- V-F6: constructions yield to the teacher (8.4 corrected to match 7.4 and the ledger).
- V-F7d: LATEST EVENT under the same 2,000-token cap.
- V-F8: exit code shown only when the result text reports one; PowerShell renders as Bash; `todos` from TodoWrite's content and status.
- V-F9: a sent correction appears in the state only as its OPEN FINDINGS line (the Mod attaches the text outside `result_text`); initial L7 status `open`; construction p values uniform in [0.6, 0.99].
- V-F10: natural L7 sources render the hook or pushback text as L7's «text» with an OPEN FINDINGS line (pushback as `[I_n]`).
- V-F13: held-out conversions written for TRACE, MALT, LLMBar, RewardBench 2.
- V-F18: `[I_n]` renumbered in arrival order; cut indices for goal splice and priority; QuALITY target at a uniform position (V-O5); head LR and anchoring stated (V-O2, V-O3).
- V-O6: long-gate items stay in dev but are excluded from selection and calibration.
- Cost: training run $10–19 (2–3.5 h); candidate scoring 1–1.5 h; teacher wall-clock 2.5–5 h at 15 parallel; the $200 cap binds generation and runs.

**Fixes that change shared formats (put to David):** the detail-budget floor of 0.15 × B_state (V-F7b), and the correction's rendering as an OPEN FINDINGS line only (V-F9).
