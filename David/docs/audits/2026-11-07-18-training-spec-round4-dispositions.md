# Round 4 dispositions: training specification

Sources: Opus (`-17-`, R4-01…R4-12), Fable (`-16-`, F1–F9), external claims (`-15-`, Findings 1–7 and the turn-reason note). Every kept finding passed the use test first. Spec 664 → 664 lines.

**Owner decision:** Fable F2 (positive floor): the expected share per source is fixed before the build (constructions' intended labels, V conversion rules, the dossier's rate for T sources; 0 where none), so a source yielding nothing shows as a shortfall (§10; D44, D47).

**Fixes (one correct answer):**
- R4-01: a positive whose first offence is a read is cut at the next classified event; the read shows in RUN LEDGER (§7.2).
- R4-02: correction text states the firing answer, not "yes" (§6.5).
- R4-03: T_q, and stock's (T_q, b_q), fitted on base dev (§9.5, §12.4).
- R4-04: CodeTraceBench is T with its annotation as a hint; benign header "the teacher labels every question" (§7.3).
- R4-05: TonyDzi Stop-hook rows are T with the hook as a hint; the L7 hook row's OPEN FINDINGS question = first positive question at the hooked event, else M1 (§7.3). No undecided table remains.
- R4-06: generation spend is reserved before agent runs; the "$70" speculation is removed (§8.7, §11).
- R4-07 / F F3, F4: the clock and the container choreography left the spec; §9.3 names the two saves an early pick uses; §9.4 lets any candidate be scored once it exists, on any GPU running the same code; serve-path gaps measured on the same hardware pair (§9.3, §9.4, §12.1).
- R4-08: the demo check runs through the shared renderer and the serving path when `classify()` is not yet deployed (§12.3).
- R4-09 / F F1: TRACE described as unseen synthetic Claude Code conversations; the demo check is the only real-run check (§1, §13).
- R4-10: the "flag everything" instrument is a report beside the teacher's rate (§13).
- R4-11: a detailed block is added only if it fits the remaining detail budget (§6.4).
- R4-12: quoted «R_k text» is trimmed to the row limit (§6.4).
- F F5: §15's dependency split: the run needs the capped train split and its pair-integrity check; selection and calibration need dev, the intent slice and stock's scores.
- F F6: §13 recovery: serve-path parity's fallback moves the pick; the demo check does the same.
- F F7: `agent said:` and MESSAGE text share the block's 2,000-token cap (§6.4).
- F F8: long-record padding targets the rendered state (16K to B_state), documents stopping at the 6.4 threshold (§7.7).
- F F9 / claims 7: AskUserQuestion is never a cut point; the renderer turns its result into a `user_instruction`; an IN3 ask renders as a `turn_completed` MESSAGE (§6.1, §7.3).
- Claims 1: serving outputs are Kev's unrounded probabilities (`Server.probs`), compared as log-odds (§12.1).
- Claims 2: the patch field is the structured hunks or null (§6.1).
- Claims 3: the pass cap is measured on a synthetic record at the largest real padded cost (§10).
- Claims 4: tau2 `communicate_checks` V (substring scoring), `nl_assertions` T hints (§7.3).
- Claims 5, 6: read-only set = the Mod's (Read, Grep, Glob, WebFetch, WebSearch, LS, NotebookRead); the shared renderer maps PowerShell to Bash (§6.1).
- Claims turn-reason note: G2 and G5 only on turns whose end reason is `answer` (§4.2).
- Ledger lag (cross-fitting, logit check, run yield, 07:00, D47 contradiction): corrected in D27, D41, D42, D44, D47.

**Trajectory:** round 3: 31 / 20 / 7 findings; round 4: 12 / 9 / 7, none blocking.
