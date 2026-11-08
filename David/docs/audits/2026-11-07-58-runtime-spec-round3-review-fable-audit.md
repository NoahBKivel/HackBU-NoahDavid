# Round-3 review of `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\RUNTIME-SPEC.md`

Date from `date`: Sun Nov 8 00:03 EST 2026. Every mandated file was read in full, in order, chunked at about 200 lines (ledger at the end). Receipts beyond the mandated set: Kev `api.py` in full and `serve.py` 120–199 at `fc4a17e1` (never run), and report 31 in full. Shell commands run: `date`, `wc -l`; both foreground, both exited. No background processes, no files written.

**Headline.** All fifteen register entries landed in the text. The ordering rule re-derives cleanly on every walk I ran; the E1/E2 Kev claims match the source line for line; section 9 matches report 31. I found five issues with receipts, all amendment-created or amendment-adjacent, each with one correct answer and none adding a mechanism: one that matters (the diagnostics trigger sentence contradicts itself and, read literally, disables D72's upgrade path), two consistency lags left by E6 and E14, one unstated ordering of the renderer's input, and one mis-cited basis in section 9. No omission against the ledger. No task material. No mechanism fails the owner's rule.

---

## Part 1. Logic and contract audit

### Walks performed (no finding unless stated)

**7.10 ordering (E3), six walks.** (a) Slow head: E1 runs 10 s; E2–E6 wait; the timer never runs because `last_seq`+1 = 1 has arrived; every result is late by `backend_sent_at`, stored, and ridden out on the first on-time result. (b) Exception: E1 raises after its store; `last_seq` → 1; E2 proceeds. (c) Single gap: `last_seq` = 1, E2 missing, E3 arrives; timer runs (next due 2 missing, E3 waiting); at expiry `last_seq` → 2, E3 runs; E2 arriving later has `seq` ≤ `last_seq`, does not wait, and takes 7.1's last row. (d) Double gap: E2, E3 missing, E4 waiting; at expiry the lowest waiting is 4, so 2 and 3 are skipped, `last_seq` → 3. If E3 arrives mid-timer, the lowest waiting becomes 3; only 2 is skipped. (e) Running predecessor then gap: E2 running, E3 missing, E4 waiting; no timer while 2 is "arrived"; E2 finishes, `last_seq` → 2, the timer starts then. This is the right behaviour and the text excludes the wrong reading. (f) `last_seq` never decreases under any of these. Clean.

**7.6 lifecycle with the E9/E10 text.** Action finding (M4, 10) significant → correction, carrier E11, L7 from E12; a later M4 is key (M4, 15), a new finding (per-action identity). Run finding (G1) significant: repeat firings send nothing; "dismissed correctly" → `dismissed`; closes when G1 stops firing or a new instruction arrives; a later firing is a new finding. Open significant run findings close only through L7, as D72 states. Minor run finding upgraded on a later firing at significant: takes that event's citations, correction goes out. One message covering (M4, 40) and (L5): "dismissed correctly" closes the first, marks the second dismissed, L7 stops. All match D72 (line 1042, which now reads "the same issue"). The one defect is the trigger sentence that decides whether the upgrade path ever runs (F1).

**7.1 turn ends (E6).** Non-empty text + `answer`: every-event set + G2 + G5 on one state; non-empty text + other reason: every-event set only (the companion's rule, 4.2 line 106); empty text + `answer`: G2 and G5, `drift` null, `risk` defined from G2/G5; empty text + other reason: skipped. A `not done` G2 row can never fire (if `not done` is the argmax, p(`broken`) < 0.5), so 7.7's "sends nothing; its R_k text goes to `details.not_done`" is consistent with 7.4. Consistent with companion 4.2 and D72; 7.3 lags (F2).

**7.3/7.11 B_state (E7).** B_state = L − 1 gives the companion's 32,767 at L = 32,768; 8,191 for stock and for any model without a gate result; redeploy on the gate. The E8 arithmetic holds: 0.85 × 8,191 − (a 2,000-token LATEST EVENT + ~100 tokens of headings, EFFORT, OPEN FINDINGS, count line) ≈ 4.9K, so "roughly 5K" is the conservative figure.

**6.4 against Kev (E1, E2).** `to_record(req)` returns `({"state", "questions"}, meta)` (`api.py` 102–117); noul options are `[no, yes]` (line 110), choice in `criteria` order (112), score in level order (114); `Server.probs` returns `self.submit(rec).result()`, the future of `(probabilities, stats)` with `[q.tolist() for q in p]` unrounded (`serve.py` 133, 147–148, 189). `question_keys` returns the choice criteria names (the dict keys), `["false","true"]` for noul, `"0","1",…` for score (`api.py` 94–99), so "option keys as Kev reports them (choice option names; score levels "0", "1", "2")" is exact. The model thread takes one queued record then drains with `get_nowait` up to `MAX_BATCH` (153–160), so 7.2's "may split across a few batches" is right.

**6.2 against `Result`.** Every field validates under `extra="allow"` (`Noah/backend/app.py` 60–73); `check_late_results` validates each late entry (91–108).

**13 phase-1 independence (E14).** Phase 1's items (gate, store, intake, loading, calibration math, firing, findings, actions on fixture probabilities, late results) need nothing from training. The live path stays the placeholder's builder and question until phase 2 (line 351). One check clause leaks (F4).

### Findings

**F1 · Part 1 · amendment-created (E9) · error · one correct answer · medium.**
- Spec 7.5: "They run only when some fired row, under 7.6, would open a new finding or upgrade a minor one; a firing that maps to an open or dismissed finding needs no diagnostics." Spec 7.6 rule 1: "An `open` or `dismissed` finding with key K exists: if it is open, minor, and this event's severity is significant or serious, it is upgraded, takes this event's cited events, and its correction goes out (7.7); otherwise nothing is sent." Spec 7.5 step 1: "Second request: `D1#E<seq>` for each detailed event, and `D5`". Spec 7.7: "(D5 is asked once per event)".
- Evidence: "this event's severity" is D5's level, and D5 is produced by the diagnostics. So whether a fired row "would upgrade a minor one" cannot be known before the diagnostics run; the trigger must be a predicate on finding state alone. The sentence's second clause ("maps to an open or dismissed finding needs no diagnostics") includes an open *minor* finding, which is exactly the case the first clause requires diagnostics for. D72 (ledger line 1042): "if its question fires again while it is open at significant or serious, the correction goes out."
- Consequence: an implementer who follows the second clause never asks D5 on a repeat firing against a minor finding, so no run finding (L1, G1, L4, …) ever escalates from a notice to a correction. None of §10's checks exercises the upgrade path (`no-reopen-after-dismissal` tests dismissal, `turn-end-no-nag` tests G2), so the gap passes every check. An implementer who follows the first clause must invent the predicate.
- Answer: one correct answer. Diagnostics run when some fired row either has no `open` or `dismissed` finding with its key, or has an `open` finding that is minor; D5's level then decides the upgrade under rule 1. No mechanism is added; the sentence is rewritten.

**F2 · Part 1 · amendment-created (E6) · error (internal inconsistency) · one correct answer · low.**
- Spec 7.3, line 201: "at `turn_completed`: `G2#R<k>` for each R_k and `G5`." Spec 7.1, line 184: "plus G2 (once per R_k) and G5 when `turn.reason` is `answer` (a missing reason counts as `answer`)".
- Evidence: companion 4.2, G2 and G5 "When asked": "at each `turn_completed` event whose end reason is `answer`"; D72 as updated. 7.3 is the row list the question runner is built from and was not touched by E6.
- Consequence: built from 7.3 alone, the runner asks G2 and G5 on an aborted, refusal or error turn that carries text (7.1 only skips the empty-text case). §10's "Turn ends" check would catch it, so the cost is a failed check and a round trip, not a shipped defect.
- Answer: one correct answer: 7.3 reads "at an `answer` turn end (7.1)".

**F3 · Part 1 · omission (adjacent to E4/E5) · one correct answer · low.**
- Spec 6.5: "`event_ids: [event_id] # stored events, in processing order`". Spec 7.3: "The state for event k is the shared renderer's output on the session's instructions, documents, stored events up to k, and the OPEN FINDINGS lines". Spec 6.3: "the instruction-list builder, which numbers `[I_n]` from the event stream … in arrival order". Spec 7.1 last row: "an event whose `seq` ≤ `last_seq` and whose `event_id` is new … stored".
- Evidence: companion 6.4 labels blocks `[E<seq>]`, details "newest first", and LATEST EVENT is event k; training converters emit events in `seq` order, so the shared renderer and builder take an ordered stream and have no reason to sort. A late arrival (7.1 last row) is stored after later events, so processing order is not `seq` order, and its instruction would be numbered after later ones.
- Consequence: a runtime that hands the renderer `event_ids` order after a late arrival renders the late event as the newest block (or as LATEST EVENT, if the renderer takes the last element) and numbers `[I_n]` differently from what training produced on the same stream. Rare (an event delayed past 8 s), silent, and §10's shared-renderer check sees it only if its fixture contains a late arrival.
- Answer: one correct answer: events are passed to the builder and the renderer ordered by `seq`; "arrival order" in 6.3 means event order.

**F4 · Part 1 · amendment-created (E14) · error (phasing) · one correct answer · low.**
- Spec 13, phase 1: "Clears: … skipped events …" and "Depends on: none". Spec 10, Skipped events: "… an AskUserQuestion answer appears exactly once, as the next `[I_n]`". Spec 13, phase 2: "Builds: the shared module wired in: instruction list …". Spec 6.3: "the instruction-list builder".
- Evidence: the `[I_n]` numbering is produced only by the shared builder, which enters in phase 2; principle 2 and line 351 forbid a stand-in formatter.
- Consequence: phase 1 cannot clear the full "Skipped events" row; the builder either defers the clause silently or writes a stand-in numbering that 13 forbids.
- Answer: one correct answer: that clause clears in phase 2 beside "shared renderer".

**Considered and not raised.**
- L7 on an empty-text `answer` turn: 7.1 says "only G2 and G5", 7.3's L7 rule applies to every classified event. Asking L7 there is consistent with 7.3; skipping it delays one L7 answer by one event. No consequence worth a clause.
- M8 citations: 7.9 fixes them to LATEST EVENT while 7.5's D1 rows still run on the merged state for D5's request; the D1 answers are unused when only M8 fired. Harmless.
- Where the lateness check sits relative to the final Dict writes: E11's "tens of milliseconds" assumes it is the last step before return; checking before the header write widens the window by report 31 C3's ~50–100 ms of Dict I/O. Inside the stated exception's spirit; adding a rule would be a mechanism.
- `burst-backlog`'s "exactly once" against the E11 window: a few-percent flake per burst, owner-accepted.
- The L7 trimming rule's constant at runtime (training's 32,768 + 640 versus B_state + 640) decides whether a 6–7K message is trimmed at an 8K state; it is the shared module's call, and §9's figure is an upper bound either way.
- A (G2, R_k) finding whose unit is removed by a document replacement is never re-asked and so never closes by "does not fire"; D70 scoped out agent-edited documents.
- `details.open_findings` counts status `open` (dismissed excluded) and `details.fired` keys suffixed rows as `G2#R3`: one natural reading each, no contract impact.
- Phase 1's live path: the placeholder's builder and question stay deployed; the Kev-path checks run on a dev deployment. Not a product choice.

---

## Part 2. Cost and latency against report 31

| Spec 9 claim | Report 31 | Verdict |
|---|---|---|
| 1.2 s at 8K, 2.9 s at 32K, 12 rows, cache miss, model time | C2: 1,221 / 2,907 ms (lines 35, 39) | Holds |
| Modal + Dict 0.15–0.3 s | C3: ~100 ms Dict on a skipped event; round trip − `classify_ms` = 56 ms p50, 144 ms p95 (line 47); the design does three Dict operations per event | Holds |
| ~70 ms per diagnostic row above 4,096 tokens | C2 note (line 43) | Holds |
| 10–25 D1 rows, 0.7–1.8 s | 10 × 70 = 0.7 s, 25 × 70 = 1.75 s; at B_state 8,191 the detail budget admits fewer blocks, so the figure is conservative there | Holds |
| L7 row 0.3–0.5 s, labelled estimate | C2 q=1 miss: 107 ms at 2K, 470 ms at 8K, 2,056 ms at 32K ≈ 0.06 ms per token; 7K tokens ≈ 0.4 s | Number holds; basis mis-cited (F5) |
| RF ~0.1 s per unit | C2: 107 ms, 2,048 miss q=1 (line 33) | Holds |
| Overflow beyond 8 s | C2: 1,789 ms per 8K screen at q=20 (line 35); four screens + merged ≈ 8.4 s | Holds |
| $2.27/h | C5 (line 58) | Holds |

**F5 · Part 2 · unsupported claim (wording) · one correct answer · low.**
- Spec 9: "(estimated from report 31's long-row prefill, not measured)".
- Evidence: report 31 C2 varies state tokens (2,048–32,768) and question count (1–20) with short probe rows; it has no row-length axis. The only long-input prefill it measures is state prefill (q=1 column).
- Consequence: none on the build; the 0.3–0.5 s figure is consistent with the per-token state prefill, but the stated basis is a measurement the report does not contain.
- Answer: cite the C2 q=1 state-prefill rows as the basis.

---

## Part 3. Completeness against the ledger

Checked D70–D77 clause by clause, plus D13, D17, D19.G7, D19.L7, D20, D21.E5/E6/E7/U, D22, D23, D24, D25, D26, D29, D29.W, D35, D40, D71 and both CROSS-TRACK-NOTES sections. Every D70 cut is in §1's out list or absent from the mechanics (runtime eval metrics and the segment cache are absent). D71 is 7.8 and 6.2. Every D72 clause is in 7.1, 7.3, 7.6 or 7.7, including the `answer`-turn rule and `details.not_done`. D73 is 7.9 (its "highest-scoring first" equals 7.9's "drop the lowest-scoring"). D74 is §10's Done row and §12. D75 is 6.3 and 13. Every D76 bullet is carried, including both stock cases (picked stock served with the lift-baseline fit via `selected.json`; no `selected.json` served at the shipped temperature). D77 is §1, 6.1, 7.10, 11 and 12. **No omission.**

**Ledger note, not a spec finding.** D75 (line 1074): "it imports the training agent's state and screen renderer read-only and starts once that renderer exists." E14's disposition made phase 1 independent of the training build (§13 "Depends on: none"), so the runtime build now starts before the renderer exists and imports it in phase 2. The spec follows the owner's round-2 decision; D75 should carry that clause (ledger as current state).

---

## Part 4. Spec/task boundary and proportionality

Use test run over every mechanism in 6–8 and 10: the ordering gate and its 8 s skip (CONTRACT §3 says requests arrive out of order; history must be in order for the state); `last_seq` in the header (a scaledown restart mid-session); per-event Dict entries plus the header (the renderer's exact counts, D76); the per-session lock (concurrent threads); the duplicate-`event_id` skip (idempotency on a keyed store, one lookup); late results, `backend_sent_at` and `pending_correction_marks` (the contract and the shared "correction sent at E<m>" line); one L7 row per message and kind-based issue keys (D72); the diagnostics trigger (latency, D72's upgrade); the overflow screen, merge and clean raise (D73, D76); `selected.json` and the swap script (D76); the null-calibration fallback (the stock path); `_test_sleep_s` (an existing hook Noah's tests use); the fifteen §10 checks (each one cheap test of a decided behaviour). Each has a one-sentence use for this build; none guarantees beyond what was asked; none needs a further mechanism. §12's items define the done bar's input or name external dependencies; §10's `verify_deploy.py` reference defines the oracle. **No task material; zero findings.**

---

## Register verification

| Entry | Verdict |
|---|---|
| E1 | Landed (6.4 line 155). Verified against `api.py` 102–117 and `serve.py` 133, 147–148, 189. No new defect. |
| E2 | Landed (6.4 lines 153, 155). Verified against `api.py` 94–99 (`question_keys`). No new defect. |
| E3 | Landed (7.10 line 264). Six walks clean; `last_seq` monotone; timer start unambiguous. No new defect. |
| E4 | Landed (6.5 line 159, 7.1 line 186). Resolves audit 54's `…:e:None` collision. No new defect. |
| E5 | Landed (6.3 lines 142, 147; 6.5 line 168; 7.1 lines 181, 188). Residual: input order unstated (F3, low). |
| E6 | Landed (6.1 line 107, 7.1 line 184, 10 line 306, D72 line 1042). 7.3 line 201 not updated (F2, low). |
| E7 | Landed (7.3 line 196, 7.11 line 269). No new defect. |
| E8 | Landed (1 line 21); arithmetic verified against companion 6.4's switch. |
| E9 | Landed (7.5 line 211, 7.6 line 229). The trigger sentence contradicts itself on open minor findings (F1). |
| E10 | Landed (6.3 line 143, 7.6 line 232). No new defect. |
| E11 | Landed (1 line 17, 11 lines 327–328). Owner decision. |
| E12 | Landed (9 line 290; 7.2 line 192; 7.9 line 254). One basis mis-cited (F5, low). |
| E13 | Landed (11 line 324). |
| E14 | Landed (13 lines 346–351). One check clause leaks phase 2 into phase 1 (F4, low). |
| E15 | Landed (4 line 55). |

## The three most likely failure points

1. **The diagnostics trigger built literally (F1).** Both readings of 7.5 are plausible; one silently removes D72's upgrade path, and every §10 check stays green.
2. **The shared-module seam (6.3).** The module does not exist yet; the runtime relies on promises recorded only in CROSS-TRACK-NOTES (B_state as a parameter, fit flags, the exported builder, formatter and trimmer, USER INSTRUCTIONS rendered from the passed list). If the training build's interface differs, phase 2 stalls; F3 is one way the seam fails even when the interface matches.
3. **The stock-fallback demo.** At L = 8,192 the overflow switch sits near 5K tokens of instructions plus documents (a condition on Noah's repository, stated in §1), and stock Kev's lean on "still pursuing" (report 31 line 71: yes-rate 0.02) fires G1 on most events, so a drift correction arrives early unless D5 reads minor. Model behaviour under the accepted scope, but the live-catch bar is exposed on that path.

## Verdict

**Implementation-ready on the demo path once F1 and F2 are written down.** Each is one sentence with one correct answer and adds no mechanism; neither needs an owner decision. F1 is the single blocking item, because an implementer can build "findings" in phase 1 either way and only one way honours D72, with no check to tell them. F3, F4 and F5 are non-blocking, one correct answer each. No owner decision is open.

---

## Coverage ledger

| File | Lines read | Every line |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 (`date` run) | yes |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 | yes |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 | yes |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–606 | yes |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–134 | yes |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–207 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–261 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\backend\app.py` | 1–200, 201–394 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\classifier\app.py` | 1–161 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\RUNTIME-SPEC.md` (target) | 1–200, 201–351 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md` | 78–109 (4.2), 142–279 (6.1–6.7), 547–556 (9.5); headers located by one grep | every mandated section in full |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 201–400, 401–600, 601–800, 801–1000, 1001–1185 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\CROSS-TRACK-NOTES.md` | 1–30 | yes |
| `…\docs\audits\2026-11-07-54-runtime-spec-round2-external-claims-audit.md` | 1–98 | yes |
| `…\docs\audits\2026-11-07-55-runtime-spec-round2-review-opus-audit.md` | 1–200, 201–304 | yes |
| `…\docs\audits\2026-11-07-56-runtime-spec-round2-review-fable-audit.md` | 1–139 | yes |
| `…\docs\research\2026-11-07-31-stock-kev-modal-measurements-and-intent-probe-research.md` (receipt, Part 2) | 1–98 | yes |
| scratchpad `kev-verify\repo\kev\api.py` at `fc4a17e1` (receipt, E1/E2) | 1–165 | yes |
| scratchpad `kev-verify\repo\kev\serve.py` at `fc4a17e1` (receipt, E1/E12) | 120–199 | targeted by design |