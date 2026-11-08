# Runtime spec review, round 2: `docs/RUNTIME-SPEC.md`

Date anchored by `date`: Sat Nov 7 23:41 EST 2026.

**Summary.** Most round-1 fixes landed cleanly. The D25 defense holds against Kev's code. The output shape validates against the backend's `Result` model. The firing set and the `risk`/`flagged` equivalence check out. The new finding lifecycle in 7.6 behaves as D72 intends in every sequence I walked.

The sharpest new problem is in 7.10's ordering rule, which came in with the D9 amendment. If one event raises an exception, its session freezes, and the timer for a missing event has no defined start. Two more issues are contradictions with the companion spec: G2 and G5 are asked at every turn end, and AskUserQuestion answers are converted into instructions in two places. The other findings are smaller.

I found no overdone mechanism.

---

## Part 1. Logic and contract audit

### Walks performed (no finding unless stated)

**Action question, M4.** M4 fires at E10, so finding F1 opens with key (M4, 10). If it is significant, a correction goes out, and the carrier event is E11. At E11, M4 fires on the new action under key (M4, 11), so a new finding and a new correction follow. That matches the owner's per-action identity rule. At E12, L7 asks about that message. If the answer is "dismissed correctly", the M4 findings it covers close. A later bad action opens a new finding. This is consistent.

**Run question, G1, dismissed.** G1 fires at E20, so F5 opens with key (G1) and a correction goes out. At E21 G1 fires again: an open, non-minor finding with that key exists, so nothing is sent. At E22, L7 answers "dismissed correctly": F5 becomes `dismissed`, and L7 for that message stops, because no covered finding is still open. G1 fires again and nothing is sent. At E23, G1 is asked and does not fire, so F5 closes. At E24, G1 fires and a new finding opens. This matches D72 and the `no-reopen-after-dismissal` test.

**Minor run finding and upgrade.** L1 fires minor at E30, so only a notice goes out. At E31, L1 fires again and D5 says significant, so the finding is upgraded and its correction goes out. If L1 does not fire at E32 instead, the finding closes. This is consistent. One consequence of the design: D5 is asked once per event, so a minor L1 finding can be upgraded because a different question fired at significant on the same event (7.7, "share one severity"). That is what the owner decided, not a defect.

**One L7 message covering several findings.** A message covers F1 (M4) and F2 (G1). "Dismissed correctly" closes F1 and marks F2 dismissed. "Partially fixed" keeps both open. "Genuinely fixed" closes both, and if G1 still fires on that same event, a new G1 finding opens immediately, because status changes are applied first. This follows D72 as written.

**Fire set and Pane fields.** Only the every-event set, G2, G5 and M8 can fire. `risk` is the highest problem score over those questions, excluding G1. So `risk ≥ 0.5` holds exactly when some question other than G1 fired. The equivalence is sound, and an event where only G1 fired correctly shows `flagged: false` while still sending actions (D71).

**Output shape against `Result`** (`Noah/backend/app.py` lines 60–73). Every field in 6.2 validates: skipped results, late entries, and `drift`/`drift_rate` passing through via `extra="allow"`.

**B_state and the overflow switch (7.3, 7.9).** These agree with companion 6.4's formulas when B_state = L − 1. The raise rule covers both cases where no state can fit.

**Shared module (6.3) against companion 6.3 and 6.4.** The key suffixes, the RF window used as the state, and L7's trimming are all cited correctly. L7's `#M<j>` suffix is not in companion 6.3's list, but question keys never reach the model (`kev/api.py` `to_record`, lines 102–117), so this is harmless.

### Findings

**F1. A single exception freezes its session's ordering gate.**
- **Part / kind:** 1 · error, created by the D9 amendment.
- **Spec text:**
  - 7.10: "Per session, `last_seq` advances when an event's result has been built. An event with `seq` s waits until `last_seq` = s − 1. The 8 s wait applies only while event s − 1 has not arrived at all."
  - 7.9: "the method raises and the backend returns its fallback result."
  - 5, lifecycle: "Release in order → store → …"
  - 7.1 rows: "an `event_id` already stored | returns a skipped result" and "an event arriving after its turn was skipped | its `new_items` are recorded; it is stored; skipped."
- **Evidence:**
  - **Failure case:** an event that raises never builds a result. The raise can come from the 7.9 refusal, a Kev 422 (`kev/serve.py` lines 139–142), a Dict error, or a calibration lookup error. `last_seq` then stays at s − 1. Event s + 1 waits for `last_seq` = s, and because s did arrive, no 8 s timer applies. It waits until the method timeout (`timeout=600` in `David/classifier/app.py` line 87), and so does every later event.
  - **Duplicates and late arrivals:** a duplicate or late arrival has `seq` ≤ `last_seq`. Because the gate runs first (section 5), it waits for `last_seq` = seq − 1, which never recurs. So both 7.1 rows cannot be reached as written. The §10 Ordering check ("if it arrives later its instructions are recorded") would catch this case, but not the failure case.
- **Consequence:** any one exception during the live demo silences that session for the rest of it. Every later event hangs about 600 s, the backend shows `pending` forever, and stored late results are never delivered. With `max_inputs=32`, once 32 events hang, other sessions queue outside the container.
- **Answer (one correct):** `last_seq` advances when an event finishes, whether it returned or raised. An event with `seq` ≤ `last_seq` skips the wait and goes straight to 7.1's duplicate or late-arrival handling.

**F2. The missing-event timer has no start point and does not handle consecutive gaps.**
- **Part / kind:** 1 · error, created by the D9 amendment.
- **Spec text** (7.10): "The 8 s wait applies only while event s − 1 has not arrived at all; after it, s − 1 is skipped and s proceeds."
- **Evidence, walk A (slow head event plus a gap):**
  - E4 is an overflow event taking about 12 s, E5 never arrives, and E6 arrives at t = 1 s.
  - If the 8 s counts from E6's arrival, E6 proceeds at t = 9 while E4 is still running. E6's state then lacks E4's findings and correction mark, and `drift_history` gets E6's value before E4's.
  - If skipping sets `last_seq` = 5, E4 finishing then sets it back to 4. E7 then waits for 6, with no timer because E6 arrived, and stalls.
- **Evidence, walk B (two consecutive gaps):**
  - E5 and E6 never arrive, and E7 waits for `last_seq` = 6.
  - If the timer counts only once s − 1 is next due (`last_seq` = 5), it never starts, because `last_seq` stays 4, and E7 waits forever.
  - The text covers only a single missing seq.
- **Consequence:** depending on which reading the builder picks, these rare cases end in concurrent processing of one session, `last_seq` moving backwards, or a stall.
- **Answer (one correct):** the timer runs only while the next due seq (`last_seq` + 1) has not arrived and a later seq is waiting. After 8 s, every missing seq below the lowest waiting seq is skipped. `last_seq` never decreases.

**F3. G2 and G5 are asked at every turn end; the companion asks them only on `answer` turns.**
- **Part / kind:** 1 · error (contradicts a cited companion section).
- **Spec text:**
  - 7.1: "`turn_completed` | stored; classified with the every-event set plus G2 (once per R_k) and G5 … if its `agent_text` is empty, only G2 and G5."
  - 6.1's "Fields read" list omits `turn`: "All other fields … are ignored."
- **Evidence:**
  - Companion 4.2 (G2): "at each `turn_completed` event whose end reason is `answer`". G5 says the same, and 4.2's closing paragraph adds: "plus G2 and G5 when the turn's end reason is `answer`."
  - D47, round 4: "G2/G5 only on `answer` turns."
  - The Mod sends the reason: `register.tsx` line 204, `event.turn = { reason: e.reason, … }`.
  - D72, on the other hand, says "G2 and G5 run on every `turn_completed` event."
- **Consequence:** on aborted, refused or errored turns, the runtime asks G2 ("The agent says the task is done…") and G5 on states training never produced. An aborted turn usually has empty text, so it gets only those two rows. A firing there sends a correction.
- **Answer:** there is one correct answer under the §1 "Train equals runtime" guarantee: read `turn.reason`, and ask G2 and G5 only when it is `answer`. D72's wording conflicts, so the owner should confirm the alignment. Separately, the spec should say that an aborted turn with empty text is a skipped event.

**F4. AskUserQuestion answers are converted into instructions in two places.**
- **Part / kind:** 1 · error, created by the D10 amendment.
- **Spec text:**
  - 7.1: "its `result_text` becomes the next `[I_n]` verbatim."
  - 6.3: "The runtime passes events in the companion 6.1 schema, … instructions as an ordered list."
  - §2, principle 2: "The runtime never formats a state … itself."
- **Evidence:**
  - Companion 6.1: "The shared renderer, not only the converters, … turns an AskUserQuestion result into a `user_instruction` item."
  - CROSS-TRACK-NOTES line 18 instead assigns the conversion to the runtime and the training converters.
- **Consequence:**
  - If both the runtime's intake and the renderer convert, the answer appears twice in USER INSTRUCTIONS, and every later `[I_n]` is shifted relative to training.
  - The §10 shared-renderer check cannot see this, because `classify()` and the reference both call the same renderer on the same inputs. The "Skipped events" check ("appears as the next `[I_n]`") passes even with the duplicate.
  - If each side relies on the other, the answer is missing entirely.
- **Answer:** the outcome has one correct answer: exactly one conversion, numbered by arrival. Where the conversion lives is a call between the two tracks. Principle 2 and companion 6.1 put it in the renderer; in that case 7.1 sends the text to RF only and does not append it. CROSS-TRACK-NOTES line 18 then needs correcting.

**F5. No value of L is stated for a trained model that has no long-context gate result yet.**
- **Part / kind:** 1 · omission, created by the D16 amendment.
- **Spec text:**
  - 7.3: "L is the validated length the training track's long-context gate reports for the served model …; for stock Kev with no gate result, L = 8,192."
  - 7.11: "L is a constant in the deploy configuration."
- **Evidence:**
  - D47: "the lift, … retention and long-context passes run in parallel containers once the selected model is live."
  - D18: the gate is "scored once, on the selected adapter, after the pick."
  - So the trained model is served, and the training agent's demo check runs through `classify()` (D47), before L exists.
- **Consequence:** the builder must choose 8,192 or 32,768. The choice changes every state: the detail budget is 0.40 × B_state, one-liners collapse differently, and the switch threshold moves.
- **Answer (one natural answer, per D18 and D45):** L = 8,192 for any served model without a gate result. Redeploy once the gate reports.

**F6. "The demo never reaches the overflow path" is unsupported at L = 8,192.**
- **Part / kind:** 1 · unsupported claim, created by the D16 amendment.
- **Spec text** (§1): "It carries no instrument; the demo never reaches the overflow path."
- **Evidence:**
  - Companion 6.4's switch is B_state − 0.15 × B_state − tokens(LATEST EVENT, OPEN FINDINGS, EFFORT, headings, count line). LATEST EVENT is capped at about 2,000 tokens.
  - At B_state = 8,191, my arithmetic puts the threshold at about 4.7K tokens of instructions plus documents with a large latest event, and about 6.7K with a small one. It is about 25K at L = 32,768.
- **Consequence:**
  - On the stock fallback, or with a trained model that validates only 8K, a demo repo whose prompt, CLAUDE.md and README pass about 4.7K tokens goes through overflow. Those events are "expected beyond 8 s" (§9), so the live catch arrives late.
  - The switch can also flip from one event to the next as the latest event's size changes.
- **Answer (one correct):** state the bound truthfully. D74 gives the demo repo to Noah, so this is a fact for him, not a new check.

**F7. Diagnostics run even when no finding can open or upgrade, and an upgrade's cited events are unstated.**
- **Part / kind:** 1 and 2 · error (wasted work) plus a small omission.
- **Spec text:**
  - 7.5: "Diagnostics (only when something fired)."
  - 7.6, rule 1: "otherwise nothing is sent."
  - 7.7: "its cited events' detailed blocks."
- **Evidence:**
  - D72: "G1 and L1 stay fired event after event once a run drifts."
  - Each repeat firing that maps to an open (non-minor) or dismissed finding still pays the second request: one D1 row per detailed event plus D5 (§9: "10–25 D1 rows, 0.7–1.8 s"), plus D2 for a repeat G2 firing. None of these answers is used.
  - Under stock serving this is likely on most events, since report 31 line 71 shows a 0.02 yes-rate on "still pursuing".
  - When a minor finding is upgraded, the spec does not say whether its evidence uses the cited events from when it opened or this event's D1 citations.
- **Consequence:** this adds latency to every event of a drifting run and pushes events toward lateness during bursts.
- **Answer (one correct):** run the diagnostics only when some fired row would open or upgrade a finding; the output is identical. On an upgrade, use this event's citations.

**F8. The `calibration.json` option keys for score questions are not pinned, and a missing question id is unhandled.**
- **Part / kind:** 1 · omission (interface between the two tracks).
- **Spec text** (6.4): `{"<question id>": {"T": <float>, "b": {"<option>": <float>}}}` "for choice and score questions."
- **Evidence:**
  - D5 is a score question. Kev reports score probabilities keyed `"0"`, `"1"`, `"2"` (`kev/api.py` lines 94–99), but companion 4.2 names the levels `minor`, `significant`, `serious`.
  - Two agents build this in parallel (D75).
  - Nothing says what happens when a question id is missing from the file, which is possible for SCR, M8 or the diagnostics, since those have no positive floor (D44).
- **Consequence:** a `KeyError` on every flagged event. Combined with F1, that freezes the session.
- **Answer (one correct):** use Kev's `question_keys`. For a missing id, use the same fallback as null calibration: the checkpoint's shipped temperature and b = 0.

**F9. `kev.api.prepare` does not exist.**
- **Part / kind:** 1 · error, created by the D2 amendment.
- **Spec text** (6.4): "`rec, meta = kev.api.to_record(kev.api.prepare(request))`."
- **Evidence:** `prepare` is defined in `kev/serve.py` line 223. `kev/api.py`, which I read in full (165 lines), has no `prepare`.
- **Consequence:** an `AttributeError` at the first request.
- **Answer (one correct):** use `kev.serve.prepare`, or call `to_record(request)` directly, since date-fact preprocessing is off unless `KEV_DATE_FACTS=1`.

**F10. §11 cites a "07:00 rule"; the ledger's trigger is 08:00.**
- **Part / kind:** 3 · error.
- **Spec text** (§11): "the training track's 07:00 rule picks the best measured model."
- **Evidence:** D13: "an 08:00 EST fallback trigger … Earlier: 07:00, moved to 08:00."
- **Answer (one correct):** change it to 08:00.

**F11. The runtime formats OPEN FINDINGS lines itself, and M8's label is unpinned.**
- **Part / kind:** 1 · error (contradicts the spec's own principle 2), low.
- **Spec text:**
  - 6.3: "passes … open findings as their OPEN FINDINGS lines."
  - §2, principle 2: "The runtime never formats a state … itself."
- **Evidence:**
  - The line is byte-shared state text (companion 6.4: `[F3] M4 at E41 · correction sent at E42 · L7 status: open`).
  - Training formats it in training code and the runtime in runtime code. §10's renderer check takes the lines as input, so it cannot compare them.
  - For an M8 finding, the `<question>` field could be "M8" (never seen in training) or "M2" (7.7 gives M8 M2's short name). The spec does not say.
- **Answer (one correct):** the shared module formats the line from the finding's fields. Pick M8's label, with "M2" following the precedent set in 7.7.

**F12. The no-lost-results statement understates what late delivery can lose.**
- **Part / kind:** 1 · unsupported claim, low.
- **Spec text:**
  - §1: "The last event of a session has no next response to ride on."
  - §11: "The last event of a session finishes late … its result is never shown."
- **Evidence:** 7.10 says the next on-time result carries every stored result. Late results cluster behind a slow event, and a backlog often still covers the turn's final `turn_completed`. Every result still stored when the session's last on-time response has passed waits for the next user turn, and is lost at session end. That can be several results, including the demo deletion's correction, not just one.
- **Answer (one correct):** state the exception as "results still stored after the session's last on-time response".

---

## Part 2. Cost and latency (section 9 against report 31)

| Claim | Report 31 | Verdict |
|---|---|---|
| 1.2 s at 8K, 2.9 s at 32K, 12 rows, cache miss | C2 lines 35 and 39: 1,221 ms and 2,907 ms | Holds (model time only) |
| About 70 ms per diagnostic row above 4,096 tokens | C2 line 43 | Holds for short rows |
| "Every event is detailed, 10–25 D1 rows" | Detail budget at B_state = 8,191 is 1,229–3,276 tokens | Holds at L = 32K. At stock 8K there are fewer rows, so the estimate is conservative. Not raised. |
| RF about 0.1 s per unit | 107 ms is one unbatched request at a 2K state (C2 line 33) | 7.2 batches short windows through `submit`, which uses the CUDA-graph batch path (`kev/model.py` lines 465–492), so this is an upper bound. Conservative; not raised. |
| Overflow events go beyond 8 s | q = 20 at 8K: 1,789 ms per screen state | Holds |
| $2.27 per hour | C5 | Holds |

**F13. L7 rows are not priced, and they are long.**
- **Part / kind:** 2 · omission, low.
- **Spec text:**
  - 7.3: L7's «text» is "the message as sent."
  - 7.7: up to 2,000 tokens of evidence for each of the first three items.
  - §9 prices only the 12-row base and the diagnostics.
- **Evidence:**
  - An L7 row therefore carries roughly 6–7K tokens. Report 31's 70 ms per row was measured on short probe questions.
  - By analogy with C2 (8K state: a miss costs 470 ms versus 71 ms for a hit at q = 1), one long row costs roughly 0.3–0.5 s. This is my estimate, not a measurement.
  - D72 (no escalation) lets an "ignored" or "partially fixed" message stay open for the whole session.
- **Consequence:** each open message adds about 0.3–0.5 s to every classified event. This is non-blocking; §9 should state it.

---

## Part 3. Completeness against the ledger

I checked D70–D77 item by item, plus the entries they modify (D13, D17, D23, D25, D29, D71) and CROSS-TRACK-NOTES:
- All of D70's cuts are in §1's out-of-scope list or absent from the mechanics.
- D71, D73, D74 and D77 are carried in full. Every D76 bullet is carried.
- No omission finding. F10 is the one stale value.

**A note on the ledger itself, not the spec.** D72 says "while a finding is open, the same question sends no second correction and no second notice." Read literally, that conflicts with the per-action issue key decided in the owner's D8 ruling and written into the same entry. The spec follows the owner's decision. D72's sentence should say "the same issue."

---

## Part 4. Spec/task boundary and proportionality

I ran the use test on every mechanism:
- the ordering gate and the 8 s skip;
- per-event Dict entries plus the session header;
- the per-session lock;
- the duplicate skip;
- late-result delivery;
- `pending_correction_marks`;
- one L7 row per message;
- kind-based issue keys;
- the overflow screen, merge and raise;
- `selected.json` and the swap script;
- the null-calibration fallback;
- all 13 checks in §10.

Each has a concrete use for this build. None guarantees more than a reasonable engineer would ask for, and none needs a further mechanism. No task material remains: the §12 items define the done bar or name external dependencies. **Zero findings.**

**Considered and not raised:**
- **Correction-carrier approximation.** The Mod attaches a correction to the next tool result it handles after receiving the response (`register.tsx` lines 174–186). An event sent during the network window can be marked as the carrier one event early. This contradicts §1's "exactly one" named approximation, but L7's rule ("any other answer keeps them open") absorbs it.
- **Duplicate delivery window.** `backend_sent_at` is set just before `spawn`, while the backend's 8 s starts after `spawn` returns. A result finishing inside that window of tens of milliseconds is both returned and stored. Fixing it would need a margin mechanism, which the owner's rule excludes.
- **Stock Kev's G1 bias.** At shipped temperature, stock Kev's G1 likely fires on most events (report 31 line 71). That is model behaviour, covered by the accepted absence of a nag-rate guarantee.

---

## Register verification

| Entry | Verdict |
|---|---|
| D1 | Landed (6.4). |
| D2 | Landed with a defect: `kev.api.prepare` does not exist (F9). |
| D3 | Landed. The exception wording is incomplete (F12). |
| D4 | Landed (§10). |
| D5 | Landed (7.5, §9). |
| D6 | Landed. Checked against `kev/model.py` lines 465–492. |
| D7 | Landed (6.5, 7.10). |
| D8 | Landed (7.6). Walked clean; D72 has a wording note (Part 3). |
| D9 | Landed with defects: the gate freezes after an exception and blocks seq ≤ `last_seq` (F1); the timer start and consecutive gaps are undefined (F2). |
| D10 | Landed with a defect: double conversion against companion 6.1 (F4). |
| D11 | Landed. |
| D12 | Landed (7.4, 7.8). |
| D13 | Landed. M8's OPEN FINDINGS label is unpinned (F11). |
| D14 | Landed. |
| D15 | Landed. The resulting long L7 rows are unpriced (F13). |
| D16 | Landed with defects: no L for a trained model awaiting its gate (F5); the demo-overflow claim is unsupported at 8K (F6). |
| D17 | Landed. |
| D18 | Landed. |
| D19 | Landed. Its raise interacts with F1. |
| D20 | Landed. |
| D21 | Landed. |
| D22 | Landed. The RF estimate is conservative. |
| D23 | Landed. |
| D24 | Landed. Line formatting stays in the runtime (F11). |
| D25 (defense) | **Holds.** `admit` passes only `SERVE_MAX_STATE` and `SERVE_MAX_BRANCH` (`kev/model.py` lines 18–20 and 130–142), and `encode` (lines 87–127) has no packed-length check. |

## The three most likely failure points

1. **Any exception freezes the session (F1).** One Dict error, Kev 422 or calibration `KeyError` (F8) during the demo stops all scoring for that session.
2. **The stock fallback path.** At L = 8,192, modest demo documents push events through overflow, so they arrive late (F6). Stock Kev's G1 bias makes an early false drift correction likely, and diagnostics then run on every event (F7).
3. **The interface between the two parallel builders.** AskUserQuestion is converted twice (F4), calibration keys may not match (F8), and OPEN FINDINGS lines are formatted on both sides (F11). §10's renderer check cannot see any of these.

## Verdict: not implementation-ready yet

Blocking questions:
- **F1:** state that `last_seq` advances when an event finishes, whether it returned or raised, and that seq ≤ `last_seq` skips the wait. One correct answer, but a literal build stalls, so it must be written down.
- **F3:** ask G2 and G5 only on `answer` turns. One correct answer under "train equals runtime"; the owner confirms the alignment with D72.
- **F4:** decide where an AskUserQuestion answer becomes `[I_n]` (the renderer or the runtime's intake), so that it happens exactly once.
- **F5:** state L for a served trained model with no gate result yet (the natural answer is 8,192).

F2 should land in the same edit as F1. F6–F13 are non-blocking, and each has one correct answer.

---

## Coverage ledger

| File | Lines read | Every line |
|---|---|---|
| `~/.claude/skills/reading-context/SKILL.md` | 1–98 | yes |
| `~/.claude/skills/out-of-cutoff/SKILL.md` | 1–103 (`date` run) | yes |
| `~/.claude/skills/receipts-before-claims/SKILL.md` | 1–29 | yes |
| `~/.claude/skills/design-ethos/SKILL.md` | 1–72 | yes |
| `.../design-ethos/references/gold-standard-spec-template.md` | 1–199, 200–409, 410–606 | yes |
| `~/.claude/skills/initializing-projects/SKILL.md` | 1–134 | yes |
| `~/.claude/skills/task-file-builder/SKILL.md` | 1–207 | yes |
| `HackBU-NoahDavid/CONTRACT.md` | 1–262 | yes |
| `HackBU-NoahDavid/Noah/backend/app.py` | 1–199, 200–395 | yes |
| `HackBU-NoahDavid/David/classifier/app.py` | 1–162 | yes |
| `docs/RUNTIME-SPEC.md` (target) | 1–80, 80–159, 160–219, 220–279, 280–346 | yes |
| `docs/TRAINING-SPEC.md` | 56–143 (4.1, 4.2, 5), 144–243 (6.1–6.4), 244–279 (6.5–6.7), 545–554 (9.5) | all mandated sections in full |
| `DESIGN-DECISIONS.md` | 1–120, 120–269, 270–419, 420–569, 570–719, 720–869, 870–979, 980–1089, 1090–1183 | yes |
| `docs/CROSS-TRACK-NOTES.md` | 1–22 | yes |
| `docs/audits/2026-11-07-51-…` | 1–101 | yes |
| `docs/audits/2026-11-07-52-…` | 1–264 | yes |
| `docs/audits/2026-11-07-53-…` | 1–136 | yes |
| Report 31 (cited by §9; verification) | 1–99 | yes |
| Kev at `fc4a17e1` (scratchpad clone; verification only) | `api.py` 1–166 (all); `serve.py` 1–254; `model.py` 1–160 and 380–508; `checkpoint.py` "temperature" lines located by grep | partial by design: read only to check specific claims |
| `Noah/mod/hooks/register.tsx` (verification only) | 160–229, plus grep hits at lines 438–441 | partial by design |

Grep was used only to locate sections and symbols before reading them. No files were written, and every shell command ran in the foreground and exited.