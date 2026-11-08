# Round 3 dispositions: training specification

Sources: Opus (`-12-`, R3-01…R3-31), Fable (`-13-`, R3-01…R3-20, numbered independently; "F" below), external claims (`-11-`, Findings 1–7). Both reviews read the spec before the scope audit (`-7-`, last section); findings about mechanisms cut there are dropped. Every kept finding passed the use test first: the mechanism it touches has a named consumer. Spec 664 → 664 lines.

**Dropped (mechanism cut in the scope audit):** Opus R3-09, F R3-05 (surface-gate pass); Opus R3-10, F R3-06 (per-converter parity); Opus R3-28 note-set part, F R3-20c; Opus R3-05 cross-fit part; Opus R3-31, F R3-16 (TRACE now one state per conversation, both asked at the last classified event before the cut).

**Fixes (one correct answer):**
- Opus R3-01 / F R3-01 (agent text and `turn_completed`): the Mod has no message event; agent text is judged with the event that carries it; a `turn_completed` cut renders `[E<seq>] MESSAGE` + final text and carries the every-event set plus G2/G5, so the final text is judged once (D21.E7/E9 under the real schema); converters emit final messages and single responses as `turn_completed` (§4.2, §6.4, §7.2).
- Opus R3-02, R3-03 / F R3-04: G1 `label` = target > 0.5; G2 positive-vs-non-positive ties to the positive option; teacher instruction 2 uses the positive class (§8.2, §8.3).
- Opus R3-04: M8 out of "flagged record"; D2 row "when M2 or G2 fired" (§4.1, §4.2).
- Opus R3-05 / F R3-17: §1 identity wording matches §12.1 (tensor equality).
- Opus R3-06, F R3-11: long gate scores M2; d = the larger of the two disagreement rates (§7.9, §12.3).
- Opus R3-07 / F R3-07: overflow threshold reserves OPEN FINDINGS, EFFORT, headings and a count line; the gate's limit arm is the largest document load that renders (§6.4, §7.9).
- Opus R3-08 / F R3-18: positive-floor share measured on each source's full labelled set (§10).
- Opus R3-11: serve-path parity compares logits (§12.1).
- Opus R3-12: secrets scan uses token-shaped patterns (§12.2).
- Opus R3-13, F R3-14: padding uses non-normative articles only, the record's own documents at a uniform position (§7.7, §7.9).
- Opus R3-14: can't-tell relabel once, then reported (§8.5, §12.2).
- Opus R3-15: π^dev computed on base dev, without top-ups (§7.9, §9.5).
- Opus R3-16: stock, if selected, is served with its lift-baseline fit (§9.5).
- Opus R3-17, R3-18 / F R3-19, F R3-20a-b: teacher band 0.3–3.7 h, relabel and RF/sibling volume noted (§11).
- Opus R3-19 / F R3-02 ($200 split): no new rule needed beyond D28: agent runs already redistribute on shortfall (§7.1), generations have no substitute, so generation spend is reserved first. Recorded here; the task file schedules it.
- Opus R3-20: source identifiers added (AISI OLMo, tau2, SWE-Misbehavior, Atlas, SWE-bench annotations, MALT, the probe manifest path) (§7.3, §7.9).
- Opus R3-21 / F R3-12: demo check on a recorded Mod session of the demo scenario (stand-in: a hand-written Mod-event stream of the slow-test deletion), predicate any every-event problem question at calibrated p ≥ 0.5 at the offending event (§12.3).
- Opus R3-22: pass cap measured on a synthetic record at `max_packed` (§10).
- Opus R3-23: serve-path parity listed among gates that move the pick (§13).
- Opus R3-24 / claims Finding 2: stale none-pair sentence removed (scope audit).
- Opus R3-25: Q4 and O-FIRING-THRESHOLD removed; screen values stated as decided (§10, §14).
- Opus R3-26: SWE-chat post-pushback record cut at the last classified event of the responding turn (§7.3).
- Opus R3-27: correction-window p drawn from [0.5, 0.99] (§7.4).
- Opus R3-28 slice part: intent slice sized so each intent question meets the dev floor (§9.4).
- Opus R3-29 / F R3-08: "flag everything" instrument compares calibrated positive rate with the teacher's benign positive rate (§13).
- Opus R3-30: AgentJudgeBench coverage and arena `both_bad` become teacher hints, since both contradicted G1's and M1's wording (§7.3; D30, D45 updated).
- F R3-03: benign-pool filters are teacher hints; V only for the rules over visible calls (§7.3).
- F R3-10: read-only tools named (§7.2).
- F R3-13: dev score averages the served questions, twins excluded (§9.4).
- F R3-15: TRACE cut located by the teacher once per conversation, logged (§7.9).
- Claims Findings 1, 3, 5, 6, 7: applied in the scope audit (row limit, Kev-27B precedent, schema, pair groups per step); Finding 5 (ExitPlanMode field name) is left to the recorded Mod session, which carries every tool input as `args`.

**Defense:**
- F R3-09 (tie rows count as positives in dev AUROC): consistent with David's stated preference (a missed problem costs more than a false flag); selection rewarding ambiguity-flagging is the intended direction, bounded by the "flag everything" instrument.

**Trajectory:** round 2: 34 / 27 / 6 findings; round 3: 31 / 20 / 7, of which 14 / 8 amendment-created; blocking 1 / 2, all resolved without new owner decisions.
