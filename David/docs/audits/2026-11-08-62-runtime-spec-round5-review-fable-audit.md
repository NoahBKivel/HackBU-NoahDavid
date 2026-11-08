# Final-round review of `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\RUNTIME-SPEC.md`

`date` ran first: Sun Nov 8 00:38:59 EST 2026. Every mandated file was read in full, in the given order, in chunks of about 200 lines (coverage ledger at the end). Kev's clone at `fc4a17e1` and the Mod's `register.tsx` were read in targeted ranges only; nothing was run. Shell commands: `date` and one `wc -l`, both foreground, both exited. No background processes. No files written.

**Summary.** All seven register entries landed. Three findings remain, each with one correct answer and none needing an owner decision or a new mechanism:

- **F1 (amendment-created, from H1, medium-low):** 7.6's new-instruction exit closes a minor or dismissed run finding only on a classified event that comes *after* the event carrying the instruction. When the instruction rides on the classified event itself (the agent's first call after a prompt is an Edit or Bash), the literal text closes it one event late or never. The ledger's D76 bullet has the same gap.
- **F2 (pre-existing, low):** "the next event the session receives" (7.6) must mean arrival at the method, not release from the ordering gate; in a burst the two differ by several events, and the Mod's attach code shows arrival is the correct one.
- **F3 (pre-existing, low):** 7.1's "with empty text, only G2 and G5" omits the L7 rows 7.3 asks on every classified event.

No omission against the ledger. No task material. No mechanism fails the owner's rule. Section 9 holds against report 31 at every row; two figures are upper bounds I would soften, not errors.

---

## Part 1. Logic and contract audit

### Walks that found nothing

**Output shape (6.2) against `Result`** (`Noah/backend/app.py` 52–73, 91–108). Scored, skipped, late and overflow results all validate: `risk` is a probability or null under `ge=0, le=1`, `flagged` a bool, each action carries `type`/`level`/`text`, and `drift`, `drift_rate`, `late_results` and every `details` key pass under `extra="allow"`. `check_late_results` validates each late entry against the same model and keeps extras through `model_dump()`. Action order detected → inject → intervened matches CONTRACT §4 and D24. Notices carry no prefix (CONTRACT §7).

**Event table and skip rule (7.1).** The read-only set equals the backend's `READ_TOOLS` and companion 6.1. `session_started` is `seq` 1 (`register.tsx` 226, 246, 281: `seq` resets to 0 at session start and `baseEvent` increments before use), so 7.10's "numbers a session's events from 1" holds. The Mod sends `turn.reason` (204). The turn-end matrix (text × reason, missing reason = `answer`) matches companion 4.2's closing paragraph, D72 and D76. `toolEvent` always sets `action` (312–320), so the "no action but non-empty `agent_text`" row never arises from this Mod; harmless.

**Question rows (7.3) and firing (7.4).** The row list matches companion 4.2 and 6.3's key suffixes. "No limit on the rows of one request beyond each row's own length" holds: `admit` refuses only a state over `SERVE_MAX_STATE` or a row over `SERVE_MAX_BRANCH` (`serve.py` 132–145, `model.py` 18–19) and `rows_per_pass` splits passes without changing answers (`model.py` 41–47). G2's `not done` argmax implies p(`broken`) < 0.5, so 7.7's `details.not_done` rule never collides with firing.

**Diagnostics and findings (7.5, 7.6), walked.**

- *Action question.* E10 Bash deletes tests; M4 fires; key (M4, 10) new → D1 per detailed event + D5 → significant → F1 opens; detected, inject, intervened. E11 arrives after the response → "correction sent at E11"; L7#M1 from E12. M4 firing again on E11 is key (M4, 11), a new finding (D72's per-action identity). `genuinely fixed` or `dismissed correctly` at E12 closes F1. Correct.
- *Run question.* E5: G1 fires, minor → F3 opens, one `potential` notice, not in OPEN FINDINGS. E6: status pass first (G1 asked and fires: F3 stays); fired row maps to an open minor finding → diagnostics → significant → F3 upgraded, takes E6's citations, correction out. E7: open non-minor → nothing. E8: L7 `dismissed correctly` → `dismissed`; G1 still firing → nothing. E9: G1 does not fire → closes. E10: G1 fires → F4, new. Matches D72, including no reopen.
- *Instruction on a skipped event (H1's case).* F3 dismissed at E8. E9 is a Read carrying `[I2]` (the Mod drains `pending` into whatever event comes next, `register.tsx` 140, 282–283, 301). E10 (Edit): status pass closes F3 because E9 added an instruction since the previous classified event; G1 firing opens a new finding. Correct. The classified-carrier case is F1.
- *Late correction.* E10's result finishes at 9 s → stored. E11 waits at the gate until E10 finishes, runs, returns on time carrying `late_results[E10]`; the correction now counts as returned (7.10) and F1 enters `pending_correction_marks`. E12 arrives → E<m> = 12, list emptied; the state at E12 shows "correction sent at E12"; L7 from E13. Consistent with the Mod, which queues the correction at `applyResult` (404–406) and attaches it to the result of the next `tool.call` that completes (174–183).
- *G2 at a turn end.* `answer` turn with text: every-event set + G2#R<k> + G5 + open L7 rows; G2#R2 `broken` at 0.6 → key (G2, R2) new → second and third requests → correction; G2#R3 `not done` → `details.not_done` only. Correct.

**Actions (7.7), Pane fields (7.8).** One severity per event; notice texts match D76; `risk` excludes G1, so `flagged` = `risk` ≥ 0.5 holds exactly when a non-G1 question fired (D71); `drift_rate` matches D76.

**Overflow (7.9).** Packing, picking, M8 findings, the `<path> › <heading>` documents, lowest-first dropping (D73's highest-first, inverted), diagnostics on the merged state and the clean raise match D73 and D76. At L = 8,192 the switch sits near 8,191 − 1,229 − tokens(LATEST EVENT + headings) ≈ 4.9–6.8K tokens, so section 1's "roughly 5K" holds.

**Ordering and late results (7.10).** Walked a slow head (waited, never skipped), an exception (`last_seq` advances), one and two gaps (8 s each), a straggler (7.1's last row), and a waiter that spends the 8 s (itself late; recovers on the next on-time result). Kev's single model thread with its lock serializes GPU work (`serve.py` 150–167). The late rule and both stated exceptions match D77.

**Model loading (6.4, 7.11) against Kev.** `LoadOptions.temperature` exists: "None = the temperature the checkpoint carries; 1.0 = raw logits" (`checkpoint.py` 105, 125). `load` sets `m.head.temperature = meta.temperature if opts.temperature is None else opts.temperature` (241), so `Checkpoint.meta.temperature` is the shipped value after the override. `to_record` returns `({"state", "questions"}, meta)` with noul options `[no, yes]`, choice in criteria order, score in level order with keys `"0","1",…` (`api.py` 94–117). `Server.probs` is `self.submit(rec).result()`, a Future of (probabilities, stats) (147–148); `answer` is separate (200–203). 7.2's "may split across a few batches" is exactly `_work`'s one blocking `get` then `get_nowait` up to `MAX_BATCH = 64` (153–160). The stock fallback reproduces Kev's default: σ(z/T_ship) over z read at T = 1.

**Lifecycle (section 5) against section 7.** The order "fire → status changes → diagnostics when the trigger holds → open or upgrade → compose actions" is the only order under which 7.5's trigger and 7.6's rules compose; the RF step before the skip lets AskUserQuestion answers and `session_started` documents feed R_k (D21.E6).

### Findings

**F1 · Part 1 · error, amendment-created (H1's new text) · one correct answer · medium-low.**

- Spec 7.6 (line 225): "A run-question finding that is minor or `dismissed` closes on the first classified event where its question is asked and does not fire, or on the first classified event after any event, classified or skipped, that added a user instruction (`[I_n]`) since the previous classified event."
- Spec 7.1 (line 188): "`new_items` on any event update the session before the state is built".
- Evidence. The Mod puts a prompt on the next event it builds, whatever its type (`register.tsx` 140, 282–283, 301). When the agent's first call after a prompt is an Edit or Bash, the instruction rides on a classified event E. The agent acted after reading the prompt, so E's own G1 answer judges the run against the new instruction. Under the text, E is not "after" itself, so the exit does not fire at E. At E+1 (the next classified event), "since the previous classified event" is E; whether E's own instruction counts depends on reading that span as inclusive or exclusive. Two literal readings: close at E+1, one event late; or never. The pre-H1 text ("or when the event brings a new user instruction", audit 59 R1 quote) covered this case and not the skipped-carrier case; the amendment covers the skipped carrier and drops this one. D76 (line 1099) has the same wording: "on the first classified event after the event that carried it, skipped events included".
- Consequence. On the stock path G1 fires on nearly every event (report 31 line 71: yes-rate 0.02 on "still pursuing"). A dismissed G1 finding survives the user's new request whenever that request arrives on a classified event (one event late, or for the rest of the session under the exclusive reading), and the firing at E maps to the dismissed finding, so "nothing is sent". The natural implementation (an instruction count that rose since the last classified event, including this event's `new_items`) is correct; the text is not. No section 10 check exercises the classified-carrier case.
- Answer: one correct answer. "on the first classified event at or after any event, classified or skipped, that added a user instruction (`[I_n]`) since the previous classified event" (and the same word in D76).

**F2 · Part 1 · error (an undefined moment, pre-existing; H4 reuses it) · one correct answer · low.**

- Spec 7.6 (line 232): "'Correction sent at E<m>' is the `seq` of the first event the session receives after the response that carried the correction (the Mod attaches it to that tool result). … the next event the session receives sets their E<m> and empties the list."
- Spec section 5 (lines 68–70): the ordering gate precedes event intake; 7.10: "events waiting their turn hold a thread each".
- Evidence. The Mod queues a correction at `applyResult` (`register.tsx` 404–406) and attaches it to the result of the first `tool.call` whose `next(e)` returns afterwards (174–183); `toolEvent` then builds and sends that tool's event (185–186). So the event carrying the correction is the first event the Mod *sends* after the response, which is the first to *arrive* at the method. In a burst (the `burst-backlog` scenario), E11 and E12 have already arrived and are waiting at the gate when E10's response returns; the Mod attaches to E13. Stamping at arrival gives E13; stamping at release from the gate gives E11.
- Consequence. Built at release (the natural place: inside the per-session lock, after the gate), the OPEN FINDINGS line reads "correction sent at E11" while the agent reads the correction after E13; L7 starts at E12 and its first two answers are about actions that predate the correction (likely `ignored`). "Any other answer keeps them open", so status is unharmed; the state line and two L7 rows (about 0.4 s each) are wrong. No section 10 check sees E<m>.
- Answer: one correct answer. The stamp is set when the event arrives at `classify()`, before the ordering gate; one clause in 7.6 ("the next event to arrive at the method, before the ordering gate").

**F3 · Part 1 · error (contradiction between 7.1 and 7.3, pre-existing) · one correct answer · low.**

- Spec 7.1 (line 184): "with empty text, only G2 and G5, and its `drift` is null".
- Spec 7.3 (line 200): "`L7#M<j>` for each correction message j still covering an open finding, asked from the first classified event after the correction reached the agent (7.6)", with no exception for turn ends. D72: "L7 is asked on every classified event while a correction is open".
- Evidence. An empty-text `answer` turn end is a classified event (G2 and G5 run on it). 7.3's list and D72 include L7; 7.1's "only" excludes it.
- Consequence. A builder who implements the empty-text branch from 7.1's table omits L7 there, so a `genuinely fixed` reading is delayed one event on turns that end on AskUserQuestion or ExitPlanMode. Low.
- Answer: one correct answer. 7.1: "with empty text, only G2, G5 and any L7 rows (7.3)".

### Considered and not raised

- **"The first classified event after the correction reached the agent" (7.3, 7.6).** 7.10's "counts as reaching the agent only once its result has been returned" is a precondition, and 7.6's parenthetical ("the Mod attaches it to that tool result") places the reading at E<m>; so L7 starts after E<m>, as both prior rounds read it. One natural reading.
- **Skipped results and `late_results`.** Section 5's arrows could be read as skipping "build the result"; 7.10's "the next on-time result" and 6.2's general `late_results` clause cover skipped results, as the deployed code already does. One correct answer.
- **Which items quote D2's R_k (7.7).** D2 is asked once per R_k for the event's whole problem, so its positives attach to every item of that event; the shared builder renders items (principle 2). One natural reading.
- **M8's cited events on overflow.** 7.9 fixes LATEST EVENT for the M8 finding while 7.5's D1 also runs; the fixed rule wins for M8 (an action question) and D1 serves D5 and the other fired questions. Overflow is off the demo path.
- **Where correction messages are stored.** 7.7 says "stored once"; 6.5's header has no field. Storing the text with each finding or a `messages` list is one obvious answer (raised and passed in round 3).
- **A straggler or duplicate arriving in the correction-mark window** would be stamped as E<m>: an edge of an edge, and a rule for it would be a mechanism.
- **The L7 trimmer's limit at L = 8,192.** Companion 6.4 states the row limit in `max_state` (32,768 + 640), not B_state; 7.3's substitution leaves it, so the whole message rides on an 8K state, as section 9 assumes. Train-matching; a seam to watch at the module boundary.
- **D76 "B_state is the long-context gate's validated length" versus the spec's "L − 1".** One token; the spec follows companion 6.4's B_state = `max_state` − 1 convention. A ledger wording note, not a defect.
- **CONTRACT §4 "takes up to 4 calls at a time" versus 7.10's 32.** Concurrency is not an interface field; the previous round's reasoning still holds: a documentation item on the shared file.
- **An instruction arriving on an AskUserQuestion event** is covered by F1's "at or after" wording and by the shared builder's conversion.

---

## Part 2. Cost and latency (section 9 against report 31)

| Section 9 claim | Report 31 | Verdict |
|---|---|---|
| 1.2 s at 8K, 2.9 s at 32K, 12 rows, cache miss, model time | C2: 1,221 and 2,907 ms (lines 35, 39) | Defend |
| Modal and Dict 0.15–0.3 s; "~100 ms of Dict I/O on a skipped event" | C3 (line 47): skipped event ~100 ms; round trip − `classify_ms` 56 ms p50, 144 ms p95 | Defend the band; challenge the basis: 6.5 holds the header in memory, so each event does two writes and no read; "reads the header" is wrong in words and the band is an upper bound |
| ~70 ms per diagnostic row above 4,096 tokens | C2 note (line 43) | Defend |
| "every event is detailed, about 10–25 D1 rows, 0.7–1.8 s" | Companion 6.4's detail budget at B_state 8,191 = max(3,276 − tokens(instructions + documents), 1,229); with README + CLAUDE.md of 2–3K tokens the budget is the 1,229 floor | Challenge: at L = 8,192 a few hundred-token blocks fill the floor, so 3–8 D1 rows (0.2–0.6 s) is the realistic figure; the stated range is an upper bound reached only at the full validated length |
| L7 row 0.3–0.5 s from "about 0.06 ms per token across 2K to 32K states" | C2 q = 1 miss: 107/2,048 = 0.052, 470/8,192 = 0.057, 942/16,384 = 0.057, 2,056/32,768 = 0.063 ms per token; 6–7K tokens → 0.36–0.44 s | Defend; the caveat "row length itself was not measured" is the honest label |
| RF ~0.1 s per unit; "a 60-unit document costs several seconds" | C2: 107 ms is a 2,048-token q = 1 miss; RF windows are ~100–200 tokens, under `BANK_WIDTH` 4,096 (graphed) and batched up to 64 | Upper bound; defensible as stated, likely 2–3× lower in practice |
| Overflow "expected beyond 8 s" | C2: 1,789 ms per 8K screen at q = 20; plus ~1.2 s merged state | Holds from about four screens up; one or two screens near the switch finish on time. Informational |
| $2.27/h | C5 (line 58) | Defend |

No findings. Unpriced but consistent: one G2 row per R_k at an `answer` turn end (~70 ms each above 4,096 tokens), and a rebuild after a scaledown pays about one Dict read per stored event on top of the 23–27 s cold start (C1).

---

## Part 3. Completeness against the ledger

Checked D70–D77 clause by clause, the entries they modify (D13, D17, D23, D25, D29, D29.W, D71), the runtime-bearing entries they rest on (D10, D11, D19.G7, D19.L7, D19.D1–D5, D19.P, D20, D21.*, D21.U, D22, D24, D26, D35, D40, D47) and all four CROSS-TRACK-NOTES sections.

- D70: every cut appears in section 1's out list or is absent from the mechanics; its consequences (documents as last sent; contradicting answers both reach the correction) are 7.1 and principle 4.
- D71: 7.8 and 6.2. D72: 7.1, 7.3, 7.6, 7.7, every clause; F1 is the one place the mechanics under-deliver the decision ("after which a firing is a new issue"), and D76 carries the same wording. D73: 7.9. D74: section 10's Done row and section 12. D75: 6.3 and 13. D76: every bullet carried in 6.1–7.11, both stock cases included. D77: sections 1, 6.1, 7.10, 11, 12.
- The handoff section (module `David/monitor_format/`, runtime `David/classifier/`, volume `intent-monitor-training` with `selected/`, `calibration.json`, `long_context.json`) is in 6.3, 6.4, 7.11.

**No omission.** Two ledger notes, not spec findings: D76's new-instruction bullet needs F1's "at or after" too, and D76's "B_state is the validated length" is one token off the spec's and companion's convention.

---

## Part 4. Spec/task boundary and proportionality

Use test run over every mechanism in sections 5–11: the ordering gate and its 8 s skip (CONTRACT §3: requests arrive out of order; D29 decided in-order processing); `last_seq`, `drift_history` and `pending_correction_marks` in the header (a scaledown restart mid-session; the shared "correction sent at" line); per-event Dict entries (exact renderer counts, D76); the per-session lock (threads under `@modal.concurrent`); the duplicate-`event_id` skip (one keyed lookup); `backend_sent_at` (D77); kind-based issue keys and one L7 row per message (D72); the diagnostics trigger (D72's upgrade and latency); the screen, merge and clean raise (D73, D76); `selected.json` and the swap (D76); the null-calibration fallback (the stock path); `_test_sleep_s` (Noah's existing test hook); the 32-slot sizing (stated basis); the seventeen section-10 checks (each one cheap test of a decided behaviour, the five named tests from D72's interaction table among them). Each has a one-sentence use in this build, none guarantees beyond what the owner asked for, and none needs a further mechanism. Section 1's two accepted exceptions are statements, not guards. Sections 12 and 13 hold external dependencies and phase order; the Done row is D74's bar. The document is 353 lines after landing seven dispositions, against 351 in round 3.

**No task material; no overdone mechanism; zero findings.**

---

## Register verification

| Entry | Verdict |
|---|---|
| H1 (7.6, D76) | Landed verbatim at line 225 and D76 line 1099. The amendment created F1: the classified-carrier case the old text covered is now outside the literal rule. |
| H2 (section 5) | Landed at line 99. The order is the one 7.5 and 7.6 require. No new defect. |
| H3 (7.3) | Landed at line 199. Consistent with 7.1 and 7.8. No new defect; F3 is the pre-existing seam in 7.1's own wording. |
| H4 (6.5, 7.6) | Landed at line 232; the field now resolves, and the late-correction walk above is consistent. It reuses the pre-existing "receives", which is F2. |
| H5 (ledger) | D10 no longer lists `correction_message` (line 204: "the correction travels in `inject_agent`"); the D23 and D25 index rows state the current decisions (lines 60, 62); D75 is current (line 1074). |
| Not acted on (CONTRACT §4 "4 calls") | Reasoning holds: concurrency is David's internals, not a contract field; a documentation item on the shared file. |

---

## The three most likely failure points

1. **The shared-module seam (6.3).** The module does not exist yet; the runtime relies on exports promised only in CROSS-TRACK-NOTES (B_state as a parameter, the fit flags, the instruction-list builder, the line formatter, the L7 trimmer). The two interface points most likely to diverge silently are the trimmer's limit (`max_state` constant versus B_state) and the merged-state fit check; the byte-for-byte check runs the same module on both sides, so it cannot see an interface misuse.
2. **The stock path at L = 8,192 in the live demo.** The Mod sends CLAUDE.md, AGENTS.md and README.md at session start (`register.tsx` 236–244), so RF judges every README sentence before the first scored event and instructions plus documents sit near the ~5K switch; stock Kev's 0.02 yes-rate on "still pursuing" fires G1 on nearly every event, so a drift finding opens early, diagnostics run on every event while it is minor, and F1 decides whether a dismissal of it survives the user's next request.
3. **Correction-delivery timing versus L7.** F2's burst case and the Mod's attach-to-next-result timing both move "correction sent at E<m>" off the event the agent read it on; the correction still lands and status is unharmed, but the OPEN FINDINGS line and the first L7 readings wobble, and no check in section 10 observes E<m>.

## Verdict

**Implementation-ready. No blocking question is open, and nothing needs an owner decision.** F1 should land before the task.md: it is one word ("at or after") in 7.6 and D76, and a literal build departs from D72 in the common case with no check to catch it. F2 and F3 are one-sentence clarifications with one correct answer each; a builder who reads the Mod's attach code and 7.3 alongside 7.1 builds the decided behaviour without them.

---

## Coverage ledger

| File | Lines read | Every line |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 (EOF) | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 (EOF); `date` run | yes |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 (EOF) | yes |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 (EOF) | yes |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–606 (EOF), returned whole in one read, no truncation | yes |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–134 (EOF) | yes |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–200, 200–206 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–262 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\backend\app.py` | 1–200, 200–395 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\classifier\app.py` | 1–162 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\RUNTIME-SPEC.md` (target) | 1–200, 200–354 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\docs\TRAINING-SPEC.md` | headings located by one grep; 56–109 (4.1–4.2), 142–279 (6.1–6.7), 547–556 (9.5) | every mandated section in full |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 200–400, 400–600, 600–800, 800–1000, 1000–1186 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\CROSS-TRACK-NOTES.md` | 1–36 (EOF) | yes |
| `…\docs\audits\2026-11-08-59-runtime-spec-final-round-review-opus-audit.md` | 1–171 (EOF) | yes |
| `…\docs\audits\2026-11-08-60-runtime-spec-final-round-review-fable-audit.md` | 1–155 (EOF) | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\docs\research\2026-11-07-31-stock-kev-modal-measurements-and-intent-probe-research.md` | 1–99 (EOF) | yes |
| Kev clone at `fc4a17e1` (receipts only) | `kev\checkpoint.py` 85–129, 232–245; `kev\serve.py` 128–167, 196–207; `kev\model.py` 38–49; `kev\api.py` 92–121; two greps (`temperature`/`to_record`/`LoadOptions`; `submit`/`probs`/`answer`/`MAX_BATCH`/`SERVE_MAX`/`rows_per_pass`) | targeted, by design |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\mod\hooks\register.tsx` | 18–47, 86–127, 128–252, 274–413, 570–608; one grep | targeted, for the `seq`, prompt-attachment, `turn.reason`, document and injection claims |

Shell commands, all foreground and exited: `date`, `wc -l`.