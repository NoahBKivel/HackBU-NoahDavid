Two of the seven dispositions have a new defect, both from the H4 wording. Neither needs a design choice, and both are low severity. The other five landed as written and create nothing new. The spec and the ledger agree on every item.

## Disposition table

| Disposition | Landed | New defect |
|---|---|---|
| H1/I1 (7.6 line 225; D76 line 1099) | Yes, word for word. D76 says the same thing: "on the classified event that carries it, or on the first classified event after a skipped one that carried it". | None. The fix fits the three rules it touches. Section 5 puts "fire" before the status changes, so the first exit, "asked and does not fire", can be evaluated. 7.1 loads `new_items` before the state, so the instruction on the event that carries it counts at that event. 7.5 then works: after the finding closes, the fired row has no open or dismissed finding with its key, so diagnostics run and "a firing on that event is then a new issue" holds. The earlier strict reading that never closed the finding is gone. |
| H2 (section 5, line 99) | Yes, word for word | None. It agrees with 7.5 and 7.6. |
| H3 (7.3, line 199) | Yes, word for word | None |
| I3 (7.1, line 184) | Yes, word for word | None. 7.1, 7.3 and 7.8 now agree on an empty-text turn end: G2, G5 and the L7 rows run there, G1 is not asked, `drift` is null, and `risk` comes from G2 and G5. |
| H4/I2 (6.5 line 166; 7.6 line 232; D76 line 1099) | Yes. 6.5 has `pending_correction_marks`, 7.6 has the arrival rule, and D76 matches. It agrees with 7.10: a mark is set only after the result is returned, on time or inside `late_results`. The Mod applies `inject_agent` from `late_results` too (`register.tsx` 362–363, 404–406). | **Yes, two (N1, N2).** |
| Section 9 wording (line 290) | Yes. The arithmetic holds: 10–25 × 70 ms = 0.7–1.75 s, and 3–8 × 70 ms = 0.21–0.56 s. | None. It agrees with 6.5, which keeps the header in memory. |
| H5 (ledger) | Yes. D10 at line 204 no longer lists `correction_message`. The D23 and D25 index rows (lines 60, 62) match those entries' current decisions (lines 633, 652). The D76 State budget bullet (line 1094) matches the disposition, and also matches 7.3 and section 8. | None |

## Findings

**N1. The mark is stamped on arrival, before earlier queued events are processed, so their states can name a later event. Created by H4. One correct answer. Low.**
- **Text:**
  - 7.6: "'Correction sent at E<m>' is the `seq` of the first `tool_completed` event to arrive at `classify()` (counted on arrival, before the ordering gate)…"
  - 7.6: "OPEN FINDINGS lists findings with a correction sent whose status is `open` or `dismissed`".
  - 7.3 and 7.6: L7 is "asked from the first classified event after the correction reached the agent".
- **Evidence:** take the `burst-backlog` case.
  - E11 and E12 are waiting at the gate when E10's response returns with a correction.
  - The Mod attaches the correction to the next tool result (`register.tsx` 174–186), which is E13. E13 arrives while E11 is still running, which takes at least 1.2 s.
  - The arrival rule sets the mark to E13 before E12's state is built.
  - Nothing in 7.3 or 7.6 limits the line or the L7 row to marks at or before the event being rendered.
  - Read literally, E12's state shows "correction sent at E13". A builder who keys L7 on "a mark is set" asks L7 at E11 or E12.
  - Training never produces this. Its state is built from "events ≤ k, open findings" (TRAINING-SPEC line 129), and its example line puts the mark after the flagged event, not after the current one ("[F3] M4 at E41 · correction sent at E42", line 216).
  - Before H4, a builder who stamped at release could not produce this. The H4 text now requires stamping on arrival.
- **Consequence:** in every backlog, the queued events' states carry a line that points at an event the model cannot see. That breaks train-equals-runtime. L7 rows may also be asked early: each costs about 0.3–0.5 s and answers about actions chosen before the correction. Status is not harmed, because "any other answer keeps them open".
- **Answer:** add one clause to 7.6. At event k, a finding's OPEN FINDINGS line appears only when E<m> ≤ k, and its L7 row is asked only when k > E<m>. This is the behaviour the release-time stamp gave.

**N2. The first `tool_completed` after the response may be a denied call, which does not carry the correction. Created by H4's claim about the Mod. One correct answer. Low.**
- **Text:** 7.6: "the first `tool_completed` event to arrive … the Mod attaches a correction only to the next tool result".
- **Evidence:**
  - The Mod attaches queued corrections only when the call was not denied: `if (ran.deny === undefined)` (`register.tsx` 175–183).
  - It still sends that call as a `tool_completed` event (301), with `action.denied` set (315).
  - The correction stays queued and goes out with the next call that is not denied.
- **Consequence:** when the first call after a correction is denied, E<m> is set one event or more too early. The OPEN FINDINGS line names the wrong event, and the first L7 rows judge actions taken before the correction arrived. Status is not harmed, for the same reason as in N1.
- **Answer:** in 7.6, count only "the first `tool_completed` event whose `action.denied` is null". Add `denied` to the fields 6.1 lists as read. Accepting this as an edge case is also defensible, since denials are rare.

## Considered and not raised

- **A late straggler that carries an instruction.** For 7.6's "since the previous classified event", it counts in processing order. The other reading needs a skip after an 8 s gap plus a prompt on that event, so it is an edge case.
- **Who owns the arrival stamp.** No component in section 5 owns it. That is an omission, not a contradiction, and 7.6 states the stamp explicitly.
- **Locking for the stamp.** The stamp must record arrival order outside the per-session lock that is held while an event is processed. That is an implementation detail with one meaning in the text.
- **A finding dismissed and closed on the same event.** When L7 dismisses a finding on the event that carries a new instruction, it closes there. That follows from 7.6's listed order.

## Coverage ledger

| File | Lines read | Every line |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 | yes |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\RUNTIME-SPEC.md` | 1–200, 200–353 | yes |
| `...\docs\audits\2026-11-08-61-runtime-spec-round5-review-opus-audit.md` | 1–174 | yes |
| `...\docs\audits\2026-11-08-62-runtime-spec-round5-review-fable-audit.md` | 1–170 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | index 21–70 (D10, D23, D25 rows); D10 196–210; D23 627–635 and D25 649–656 (to check the index rows); D72 1039–1054; D75 1071–1077; D76 1079–1105 | every mandated entry in full |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\mod\hooks\register.tsx` | 120–300, 380–420 as mandated; also 299–322 and 355–366 and one grep, for the N2 and `late_results` receipts | targeted |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\docs\TRAINING-SPEC.md` | one grep, plus lines 129, 215–216, 236, 242, 387–388 (receipt for N1 only) | receipt only |

Shell commands ran in the foreground only: `wc`/`grep` and one `sed`. I wrote no files.