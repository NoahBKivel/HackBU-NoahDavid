# Runtime spec review: final round (`docs/RUNTIME-SPEC.md`)

I ran `date` first: Sun Nov 8 00:38:38 EST 2026. I read every mandated file in full, in order, in chunks of about 200 lines. The coverage ledger is at the end. Every shell command ran in the foreground and exited. I wrote no files.

## Summary

- All five fixes from the previous round landed. One fix (H1) introduced a small wording ambiguity, reported as F1.
- I found one older wording error in the "correction sent at" rule, which H4 restated (F2).
- Both findings are low severity, each has one correct answer, and neither blocks the build.
- Section 9's cost numbers check out against report 31.
- Nothing from the ledger is missing.
- No task-file material is in the spec, and no mechanism breaks the owner's rule.

---

## Part 1. Logic and contract audit

### Walks that found nothing

- **6.2 against the backend's `Result` model** (`Noah/backend/app.py` lines 60–73, 91–108). The model allows extra fields. Every result shape validates: scored, skipped, late, overflow, and a straggler that arrives after its turn. `drift`, `drift_rate` and `late_results` pass as extras, and `check_late_results` validates each late entry against the same model.
- **7.1 skip rule.** I checked it against the Mod (`register.tsx`):
  - `turn_completed` carries `turn = {reason, …}` and `agent_text = e.answer` (lines 202–204).
  - `seq` resets to 0 at session start and is incremented before use, so the first event is 1 (lines 226, 281).
  - `session_started` is sent once per session id (lines 88–91), so the duplicate-`event_id` row never drops a document update.
  - The Mod never retries a POST (lines 376–386).
- **7.3 question rows and 7.4 firing.** The H3 exception agrees with 7.1 and 7.8. G1 fires when p < 0.5. A G2 row whose top option is `broken` but whose p is below 0.5 does not fire, which is consistent with 7.7. Only the every-event set, G2, G5 and M8 fire.
- **7.5 diagnostics.** The trigger depends only on finding status, and with H2 in place the order is: status changes, then the trigger, then diagnostics, then the opening rules.
- **7.6 findings, walked on concrete sequences:**
  - **An instruction on a skipped event.** E5 is classified and the G1 finding is dismissed. E6 is a Read that carries the prompt for `[I2]`. At E7 the dismissed finding closes. If G1 fires at E7, a new finding opens, diagnostics run, and a correction can go out. This matches D72.
  - **A correction delivered late.** E5's result is late and stored. E6 runs on time and carries it in `late_results`, so F(E5) goes into `pending_correction_marks` when E6 returns. E7 sets "correction sent at E7", and L7 runs from E8. F(E5) stays out of OPEN FINDINGS until it has a mark. This matches 7.10.
  - **A minor finding upgraded.** G1 is minor at E5. At E6 G1 still fires, so the finding stays open; diagnostics run; D5 says significant; the finding is upgraded and its correction goes out.
  - **An action finding.** Each action has its own key, (question, seq), so a minor one closes once its notice is sent.
- **7.7 actions.** One severity per event, the notice texts match D76, and the action order matches CONTRACT §4.
- **7.8 Pane fields.** `risk` is the maximum over exactly the questions that can fire, G1 excluded, and each fires at ≥ 0.5. So `flagged` holds exactly when `risk` ≥ 0.5, on the overflow path too, where M8 is in that set and SCR is not.
- **7.9 overflow, 7.10 ordering and late results, 6.4 and 7.11 loading and fallback.** These are as the previous rounds verified. I found nothing new.
- **Section 5 lifecycle against section 7.** The H2 order agrees with 7.5 and 7.6.
- **Storage.** Modal Dict allows objects up to 100 MiB (modal.com/docs/guide/dicts). Whole events under the Mod's 5 MB cap (`MAX_EVENT_BYTES`, `register.tsx` line 9) fit.

### Findings

**F1. The H1 closure clause has a reading under which an instruction on a classified event never takes effect**

- **Part / kind:** Part 1 · error · created by the H1 amendment · one correct answer · low.
- **Spec text, 7.6:** "closes on the first classified event where its question is asked and does not fire, or on the first classified event after any event, classified or skipped, that added a user instruction (`[I_n]`) since the previous classified event."
- **Evidence:**
  - Take E6 as a classified event that carries a new prompt, for example the agent's first Edit after the prompt. This is common, because the Mod puts each prompt on the next event it builds (`register.tsx` lines 140, 282–283, 292).
  - At E6, nothing that added an instruction comes before E6.
  - At E7, the "previous classified event" is E6 itself. Read strictly, "since E6" leaves E6 out.
  - So the strict reading never closes the finding for a classified carrier. That contradicts the same sentence's "classified or skipped".
  - A looser reading gives E7, which is what D76 says: "on the first classified event after the event that carried it". A builder who sets a flag at intake gets E6 instead.
- **Consequence:**
  - The builder has to pick E6, E7 or never.
  - "Never" brings back the failure the previous round's R1 fixed: on stock Kev, G1 fires on most events (report 31, line 71), so a dismissed G1 finding would stay silenced across new user requests.
  - Section 10's `no-reopen-after-dismissal` check does not say where the instruction arrives, so it would not catch this.
- **Answer (one correct, per D76):** delete "since the previous classified event". The rule then reads "on the first classified event after any event, classified or skipped, that added a user instruction". That gives E7 for a classified carrier and is unambiguous.

**F2. A correction's "sent at" mark can land on a turn end, which never carries a correction**

- **Part / kind:** Part 1 · error · older wording that H4 restated · one correct answer · low.
- **Spec text, 7.6:** "'Correction sent at E<m>' is the `seq` of the first event the session receives after the response that carried the correction (the Mod attaches it to that tool result)." H4 adds: "the next event the session receives sets their E<m> and empties the list."
- **Evidence:**
  - The Mod attaches queued corrections only inside its tool-call hook (`register.tsx` lines 174–183).
  - The turn-end handler (lines 198–211) and `startSession` attach nothing.
  - A Read does carry the correction, so skipped tool events are correct as written.
- **Consequence:**
  - When the next event is a turn end, the mark names that event. The correction actually reaches the agent on the first tool call of the next turn.
  - L7 then starts on an event whose action was chosen before the agent saw the correction. It answers `ignored` or `acknowledged only`, so the finding stays open and nothing closes wrongly.
  - The only lasting effect is a wrong E<m> in the OPEN FINDINGS state text.
- **Answer (one correct):** in 7.6, change "the first event the session receives" to "the first `tool_completed` event the session receives", and "the next event" to "the next `tool_completed` event". No new mechanism is needed.

### Considered and not raised

- **L7 on an empty-text `answer` turn end.** 7.1 says "only G2 and G5", while 7.3's L7 bullet has no exception. 7.3 is the row list, and asking L7 there is harmless.
- **Two status changes on the same event.** If L7 answers "dismissed correctly" at E7 and a skipped E6 added an instruction, the result depends on which rule runs first. Building in 7.6's listed order (L7 first) gives one answer.
- **D5's «short names».** D5 is asked with the short names of all fired questions, including ones tied to a dismissed finding. That matches how training labelled D5 on flagged records.
- **Stragglers taking the "sent at" mark, and the attach-to-next-result race.** The previous round already considered and accepted both.
- **The CONTRACT §4 item the previous round left alone.** CONTRACT §4 says the container "takes up to 4 calls at a time"; 7.10 sets 32. The previous round's reasoning still holds:
  - The backend uses its own `max_inputs=50` and `spawn` (`app.py` lines 321, 370). It depends on nothing in that sentence.
  - The sentence describes the container rather than defining an interface field, so updating it is a documentation task, not a spec defect.

---

## Part 2. Cost and latency (section 9 against report 31)

| Claim | Report 31 | Verdict |
|---|---|---|
| 1.2 s at 8K, 2.9 s at 32K, 12 rows, cache miss | C2: 1,221 and 2,907 ms (lines 35, 39) | I would defend it |
| Modal and Dict add 0.15–0.3 s | C3: 56 ms p50 overhead; about 100 ms of Dict I/O on a skipped event (line 47) | I would defend it. "Reads the header" overstates a little, because the session is held in memory |
| About 70 ms per diagnostic row above 4,096 tokens | C2 note (line 43) | I would defend it |
| 10–25 D1 rows, 0.7–1.8 s | At B_state = 8,191 the detail budget is about 1.2–3.3K tokens, so only about 2–6 events get detailed blocks | I would challenge it as overstated. It errs on the conservative side, so nothing in the build depends on it |
| L7 row adds 0.3–0.5 s | q = 1 miss column gives 0.052–0.063 ms per token | I would defend it |
| RF about 0.1 s per unit | 107 ms is one row on a 2K state | It is an upper bound. RF windows are short and batched |
| Overflow takes longer than 8 s | 1,789 ms per 8K screen at q = 20 | I would defend it for four or more screen states |
| $2.27/h | C5 (line 58) | I would defend it |

---

## Part 3. Completeness against the ledger

I checked D70–D77 clause by clause, plus the entries they modify or rest on: D10, D11, D17, D19.G7, D19.L7, D19.D1/D3, D20, D21.*, D23–D26, D29, D29.W, D35, D40 and D47, and all four sections of CROSS-TRACK-NOTES.

- Every D76 bullet appears in 6.4–7.11, including the new pending-marks bullet and the "skipped events included" bullet.
- D71 is in 7.8. D72 is in 7.1, 7.3, 7.6 and 7.7. D73 is in 7.9. D74 is in sections 10 and 12. D75 is in 6.3 and section 13. D77 is in sections 1, 6.1, 7.10, 11 and 12. D70's cuts are in section 1's out-list.

**No omissions.**

---

## Part 4. Spec/task boundary and proportionality

I ran the use test over every mechanism in the spec:
- the ordering gate and its 8 s skip;
- the per-session lock;
- the duplicate-`event_id` skip, a one-line idempotency check on a keyed store;
- the per-event Dict entries;
- `pending_correction_marks`, which the shared "correction sent at E<m>" state line needs;
- `backend_sent_at`;
- the issue keys by question kind;
- the diagnostics trigger;
- the overflow screen and its clean raise;
- `selected.json`, the swap, and the fallback when no calibration exists;
- the 17 checks in section 10.

Each has a one-sentence use in this build, and none needs a further mechanism. Sections 12 and 13 hold dependencies and phase order, which belong in a spec. **Zero findings.**

---

## Register verification

| Entry | Landed | New defect |
|---|---|---|
| H1 | Yes (7.6 line 225; D76 line 1099) | Yes: the "since the previous classified event" clause is F1 |
| H2 | Yes (line 99) | None |
| H3 | Yes (line 199) | None |
| H4 | Yes (6.5 line 166; 7.6 line 232) | It defines the field correctly. It restates the older turn-end wording error (F2) |
| H5 | Yes: D10 no longer lists `correction_message` (line 204); the D23 and D25 index rows are current (lines 60, 62); D75 is current | None |
| CONTRACT "4 calls" (not acted on) | Reasoning still holds (see Part 1, "Considered and not raised") | Not applicable |

## The three most likely failure points

1. **The shared-module seam (6.3).** Phase 2 depends on exports that are promised only in CROSS-TRACK-NOTES.
2. **The stock path at L = 8,192.** G1 fires on almost every event (still-pursuing yes-rate 0.02). While that finding is minor, diagnostics run on every event and add 0.7–1.8 s, which pushes fast bursts into late delivery. The README sent at session start also puts the overflow switch (about 5K tokens) within reach.
3. **Correction delivery at turn ends (outside the spec).** The Mod delivers corrections only on the next tool call. If the flagged deletion is the agent's last action before its turn ends, the correction waits for the next turn. That puts "the agent receives the correction" in the done bar at risk.

## Verdict

**Implementation-ready.** No blocking question is open, and nothing needs an owner decision. F1 and F2 are one-clause edits with one correct answer each. F1 should land before the task.md: a literal build could silently skip D72's re-arming on new instructions, and no check in section 10 would catch it.

---

## Coverage ledger

| File | Lines read | Every line |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–97 | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–102 (`date` run) | yes |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–28 | yes |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–71 | yes |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–200, 200–404, 405–605 | yes |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–133 | yes |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–206 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–261 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\backend\app.py` | 1–200, 200–394 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\classifier\app.py` | 1–161 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\RUNTIME-SPEC.md` (target) | 1–120, 120–239, 240–353 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\docs\TRAINING-SPEC.md` | 56–110 (4.1–4.2), 142–281 (6.1–6.7), 545–558 (9.5); headings located by one grep | every mandated section in full |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 200–399, 400–599, 600–799, 800–999, 1000–1185 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\CROSS-TRACK-NOTES.md` | 1–35 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-08-59-runtime-spec-final-round-review-opus-audit.md` | 1–170 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-08-60-runtime-spec-final-round-review-fable-audit.md` | 1–154 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\docs\research\2026-11-07-31-stock-kev-modal-measurements-and-intent-probe-research.md` | 1–99 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\mod\hooks\register.tsx` | 80–119, 120–349, 349–478, plus two greps | targeted, by design |
| Modal docs (Context7, `/websites/modal`) | the Dict size-limit passage | receipt only |
| Kev clone | not re-read; the previous rounds' line-level verification of 6.4 stands, and no new claim needed it | not applicable |