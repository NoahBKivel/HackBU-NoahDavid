# Round 2 dispositions: training specification

## External-claims pass (`2026-11-07-6-…`)
Part 0: all 13 round-1 claims findings landed; C-F5 and C-F6 landed with new errors, fixed below.
- R2-F1 (none pairs re-add a "none" answer to G2/L7): **fix**, `--p_none_pair 0`, `--none_pair_max_state` dropped; ledger D33 updated.
- R2-F2 (`KEV_TEMPERATURE` also read by kev.benchmark and kev.evaluate): **fix**, wording corrected.
- R2-F3 (builder tokenizer is already Kev-4B's): **no change**; the spec's text is correct.
- R2-F4 (SDPA wording): **no change**; the check is correct.
- R2-F5 (interpolated checkpoint format): **fix**, full-weight checkpoint; serve-path fallback per α.
- R2-F6 (§10 detail budget lacked the floor): **fix**.
- Builder note (P must cover the largest record): **fix**, added to §10.

## Opus (`-9-`, R2-01…R2-34) and Fable (`-10-`, A1–A5, F1–F18, C1–C3, T1) round-2 reviews
Each finding was checked against the spec, the ledger and the cited source before disposition. Spec 660 → 674 lines (new rows: positive class and flagged record, §6.7, cost rows; implementation-crucial detail).

**Owner decisions (asked one at a time):**
- R2-07 / F1 positive floor: **decided** (D44). Floor = 0.8 × the positives the decided plan yields per question (P_q, from each source's measured positive share); shortfalls rebuilt inside N from the same objective, trimming its largest source; SCR, M8, D1/D3, D2 reported. §10, §12.2.
- R2-06 long-context gate: **decided** (D18). Overall accuracy per length decides; one uniformly drawn placement per item, placement reported; items = constraint-insertion records with the constraint in a project document, padded to 8K, 16K and the single-state limit (docs at the overflow threshold); n = d / (0.03/3.24)² from stock's own 8K-vs-long disagreement on a 200-item pilot; scored once on the selected adapter after the pick. §7.9, §10, §11, §12.3, §15.
- R2-10 TRACE scoring: **decided** (D37). Cut before the first user turn exposing the hack; M4 (and M1 for probe TRACE items) flags the conversation if it fires at any classified event before the cut; G5 at the last completion claim; M4 and G5 pooled into one paired test clustered by conversation. §7.9, §12.4.
- David's stated preference (overflagging costs less than underflagging, short of flagging everything): **ties now resolve to the positive class** (D30). §8.3.

**Fixes (one correct answer):**
- R2-01 G1 polarity: "positive class" and "flagged record" defined (§4.1); every rule that said "yes"/"positive" uses them (§4.2, §7.6, §7.8, §7.9, §8.2.6, §8.3, §8.5, §12.2, §13); twins derived from base rows, key `<id>~neg`.
- R2-02 B_state: fixed at 32,767, independent of questions; overflowing question rows go to a sibling record (§6.4, §10).
- R2-03 / A4 seam gate: report-only, scored once on the winner and stock; "selection prefers" removed (§12.3, §1).
- R2-04 surface gate: fitted on train, source-stratified AUROC, paired bootstrap difference lower bound > 0; passing candidates rank first in the pick order (§12.3, §9.4).
- R2-05 / F7 calibration: out-of-fold ECE on the serving path (LoadOptions(temperature=1.0) + transform), flagged on the paired difference vs stock; report-only, transform stays (§12.3); §9.4 serving-path sentence aligned.
- R2-08 stock baseline: T and b fitted jointly by NLL (§12.4).
- R2-09 / F2 / F4 probe: polarity mapping and IFBench, aspi, UIB conversions written; no gated pass renders raw reasoning (§7.9).
- R2-11 demo: moved to "never trained on" (§7.9).
- R2-12 construction basis: code C, yields to the teacher (§7.3 legend and rows); §2.3 reworded.
- R2-13: §1 table drops "down-weighted"; kernel bound matches §12.1.
- R2-14 / A1: full-weight checkpoint (claims-pass fix); identity parity compares against stock merged the same way within stock's run-to-run spread (also F17); serve fallback ends at the next candidate (§12.1).
- R2-15: landed via claims pass (`--p_none_pair 0`).
- R2-16 / A3 renderer parity: Phase 1 golden Mod-event fixtures; each converter re-checked in Phase 2 (§12.1, §15).
- R2-17 / F5: protected rows may exceed 1:10; target questions defined per §7.3 objective; benign/replay/long have none; a record keeps at least one row; L7/D5 uncapped (§7.8, §10).
- R2-18: invariant reworded (exact for the random thinning; temperature absorbs the protected rows) (§1).
- R2-19 / F6 screen ledger: LATEST EVENT in full, then recent events within 15%; cap formula counts the event once (§6.6, §10).
- R2-20: WebFetch URL, TodoWrite none, ExitPlanMode `plan:` line (§6.1, §6.4).
- R2-23: note diagnostic set excluded from selection too (§7.5).
- R2-24 / F13: note-crutch population = pairs whose no-note target is 0 or 1 (§12.3).
- R2-25: served T_q refitted on all of dev; cross-fit for the report (§9.5). F15d: π^dev = mean dev target.
- R2-26: D2 asked when M2 positive or G2 broken/not done (§8.2.6).
- R2-27: OPEN FINDINGS id for hook (template table) and pushback (first positive question, else M1) (§7.3).
- R2-28 / F14 RF: recall on dev's RF rows (no extra labelling) (§12.3).
- R2-29 / C1: §9.1 aligned with §11.
- R2-30 teacher wall-clock: formula and band; with up to 100 parallel subagents ≈ 1 h, band 0.4–2 h (§11).
- R2-31 / C2 / C3: cost rows added (candidate scoring 2–3 h corrected, serve-path, lift incl. TRACE per-event, long gate, agent-run wall-clock) (§11).
- R2-32 / F8: requirement units §6.7 (list items + pysbd sentences); R_k = teacher RF-yes units; InFoBench decompositions become hints (§7.3).
- R2-33: G2/G5 at `turn_completed` events, which carry only those two (§4.2, §7.2, §8.2.6).
- R2-34 / L3: absolute-bin matching is the correct implementation of the decided policy (the model sees absolute position, never run length); D43/D45 updated with an "Earlier:" clause. D18 long-gate items: scored once on the winner, never selected or calibrated on.
- A2 retention: set = decision-v7 development + calibration (2,172), parity passes ≥ 0.8 up to 25% disagreement (§10, §12.3).
- A5: landed via claims pass.
- F10: batches fewer when over the labelling model's input limit (§8.3).
- F11: EFFORT counts span the whole run (§6.4).
- F12: goal-splice records added to §9.4's slice list.
- F15 a/b/c/e: can't-tell counts as not positive in agreement; positive class defines G2's classes; twin key; agreement failure → tighten and relabel once, second failure reported (§1, §8.5, §12.2).
- F16: §13 recovery scoped to Retention and Demo check.
- F18: f_long shortfall filled by padding PROJECT DOCUMENTS with unrelated real documents (Kev-27B's method) (§7.7).
- T1: §14 Q2 impact reworded.
- Ledger lag (D30 header, D33, D40, D41, D42, D44): updated in place; D47 records the round's mechanics; D26 (runtime-owned) and D20 noted in `docs/CROSS-TRACK-NOTES.md`.

**Cuts (no consumer, by David's use-test rule):**
- R2-22 / F9: long-state builder patch deleted (§9.2, §15).
- RF held-out recall set replaced by dev's RF rows (no extra labelling).

**Defenses:**
- R2-21 / F3 (correction outside `result_text`): the Mod's code builds the event from the tool result and puts the correction only into `answer.context` (`Noah/mod/hooks/register.tsx:158-168`, verified in the round-2 claims pass). CONTRACT.md's wording is less specific than the code; the code is authority.

**Trajectory:** round 1: ~60 findings; round 2: 34 (Opus) + 27 (Fable) + 6 (claims), of which 16 (Opus) and 5 (Fable) were amendment-created; blocking 4 + 2, all now decided.

## Scope audit after round 2 (David's rule: a mechanism giving more assurance than a reasonable engineer asks for is cut; signed off)
**Cut from the spec (verify absence, and that nothing still refers to them):** 21-candidate scoring (now five: final save and the save nearest step 400, × {1.0, 0.85}, plus stock; §9.3, §11); surface-feature baseline (§12.3; §9.4 pick order back to intent rank); seam gap and unedited-real set (§1 family 2, §7.9, §12.3, §13); note-crutch gate and its diagnostic set (§1 family 3, §7.5, §12.3); twin-consistency and ledger-size reports; retention as a pick gate (now reported, §12.3, §13); calibration-vs-stock report and 5-fold cross-fitting (§1, §9.5, §12.3, §12.4); per-converter golden bytes (§12.1, §15); identity logit check (§12.1); run-yield gate (§12.2); reasoning-stripped held-out copies (§7.9, §12.4).
**Round-3 claims fixes (`-11-`):** event schema follows the Mod code (file_changes only on Edit/Write, op edit/write, structured patches; §6.1, §6.4 example; fixtures from a recorded Mod session or corrected samples, §12.1); L7 «text» trimmed to Kev's 640-token row limit (§6.4); stale none-pair sentence removed (§9.1); Kev-27B precedent narrowed to its 3,200 embedded long states (§7.7); pair groups share an optimizer step, not a pass (§9.2).
Spec 674 → 664 lines.
