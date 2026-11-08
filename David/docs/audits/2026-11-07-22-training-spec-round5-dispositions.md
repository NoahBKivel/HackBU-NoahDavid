# Round 5 dispositions: training specification (final full round)

Sources: external claims (`-19-`, Findings 1–4), Opus (`-20-`, R5-01…R5-11), Fable (`-21-`, F-01…F-09). Every kept finding passed the use test first. Spec 664 → 667 lines (the added lines state which question an M4/L6 V label covers).

**Owner decisions:**
- R5-04 (agent-run positive share): the 300 agent runs count 0 toward P_q; M2 and M7 take their floors from constructions, IF_multi, IN3 and JL-ActionBoundary (§10; D44). The ledger's emergent row claiming the floor catches non-misbehaving runs is withdrawn.
- F-01 (teacher-only questions): the floor is max(0.8 · P_q, 60), so G5 and M5 have a 60-positive floor (§10, §12.2; D44).

**Fixes (one correct answer):**
- R5-01 / F-02: the fill rule stops at the first detailed block that does not fit; "is spent" removed (§6.4).
- R5-02: a failed correctness gate takes its §12.1 fallback (§13).
- R5-03 / F-09: a V label covers the question its offence matches (a read of tests, grader output or answer files is L6; altering a measure is M4); the teacher labels the rest; CheatBench and HVTB rows say so (§7.3).
- R5-04 dataset part: dataset V sources take the natural share among kept rows (§10).
- R5-05: both calibration rates take a 0.5 pseudocount per class (§9.5).
- R5-06: diagnostics labelled in three ordered passes, mirroring D76 (§8.2 item 6).
- R5-07: converters set `turn.reason` = `answer` on every turn end followed by a user turn or the run's end (§6.1); cross-track note for D72.
- R5-08: siblings share split and batch, but only contrast pairs are cap-exempt (§6.4).
- R5-09: "the rare-question floor" removed from §3's sourced claims.
- R5-10: "scored concurrently" left §12.4 (task material).
- F-03: one 2,000-token cap names its members once: result, patch, plan, agent text (§6.4; D40).
- F-04: serve-path parity compares the mean |Δ log-odds| (§12.1; D44).
- F-05: the kept set uses the paired bootstrap SE of (best − candidate) (§9.4, §1; D41).
- F-06: a base row and its negated twin are kept or dropped together by the cap (§7.8).
- F-07: RF labels on G2/D2 records define R_k only and add no training rows (§6.7).
- F-08: the dossier path is named once (§7.3).
- Claims 1: every model on both sides of serve-path parity loads at temperature 1.0; log-odds from both softmax entries (§12.1).
- Claims 2: T sources contribute 0 to P_q (§10).
- Claims 3: see R5-07; the §4.2 table and §8.2 item 6 carry the `answer` gate.
- Claims 4: no change (the shipped 2025 tau2 files are substring-scored).
- Duplicate AskUserQuestion sentence in §6.1 removed.

**Cut (David's scope rule):** R5-11, the 5% spot-check of benign rewrites (§7.6; D27, D45).

**Defended:** claims 3(b) (an IN3 ask ends as an `answer` turn, so it carries G2 and G5): the teacher answers G5 no (no success is reported) and G2 per requirement, usually `not done`; the runtime asks the same questions on the same kind of turn, and D72 sends no correction for `not done` at a turn end, so training matches runtime and nothing nags.

**Ledger:** 07:00 → 08:00 in D13 and D34; D45's spot-check cut; D47's read-only bullet and a round-5 bullet; D40's agent-text cap; D41's paired SE; D44's floor and serve-path statistic; trace file D13 row; cross-track notes.

**Trajectory:** Opus/Fable/claims: round 4: 12 / 9 / 7; round 5: 11 / 9 / 4, none blocking, 5 amendment-created across both reviewers.
