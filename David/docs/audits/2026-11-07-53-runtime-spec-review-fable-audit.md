# Review of `docs/RUNTIME-SPEC.md` (runtime track)

Reviewer stance: senior engineer, Modal inference + agent monitoring. Scope is off limits; proportionality is not. Every finding below carries a receipt; candidate findings without one were dropped.

**Headline.** The spec is close to buildable. The core logic (event table, question rows, firing, finding lifecycle, actions, Pane formulas, model loading) re-derives cleanly against the backend's `Result` model, the companion's cited sections and the runtime-track ledger entries. Section 9's numbers match report 31 exactly. I found nine issues with receipts: three I would call blocking for an autonomous agent (the shared-module seam, the ordering-gate semantics, the state budget when the validated length is not 32K or stock serves), five non-blocking logic/claim defects, and one task-material note. I found no mechanism that fails the owner's rule.

---

## Part 1. Logic and contract audit

### Verified correct (no finding)

- **Output shape vs `Result` (6.2).** `schema_version`, `event_id`, `monitor`, `flagged: bool`, `risk: Optional[float] in [0,1]`, `details: dict`, `actions: list[{type, level?, text?}]` all validate against `Noah/backend/app.py` lines 52–73 (`extra="allow"`, so `drift`, `drift_rate`, `late_results` pass through). Skipped results (`risk: null`, `flagged: false`, `actions: []`) validate. Late entries are each a full result, which `check_late_results` (lines 91–108) requires.
- **7.1 table** matches D21, D76 and companion 4.2's last paragraph (turn end = every-event set + G2 per R_k + G5). The read-only list is the backend's `READ_TOOLS` plus AskUserQuestion; broader than the companion's renderer list, but skipping is a runtime rule (D21.E5), so no contradiction.
- **7.3 rows, 7.4 firing** (G1 fires on p < 0.5 and feeds drift; G2 on p(`broken`); L7/RF never fire) match 4.2, 9.5, D71, D76.
- **7.5 diagnostics** match D19.D1/D3, D19.D2, D76 (D1 per detailed event, D5 once, D2 in a third request so «summary» can carry the cited E-refs; LATEST EVENT cited when none).
- **7.6 walked** on four sequences (open → repeat fire → L7 fixed → re-fire opens new; minor repeat → stops firing → closes → re-fire re-notifies; minor → upgrade sends correction; dismissed correctly → same cited events opens nothing, new cited event opens). All consistent with D72, including no second correction/notice while open and no escalation.
- **7.7 actions** match D24/D76 texts; correction composition defers to companion 6.5 correctly.
- **7.8:** `flagged = risk ≥ 0.5` holds by construction over the set `risk` ranges over; the "equivalently … fired" clause holds for that set (see F4 for the one leak). `drift`, `drift_rate` match D71/D76. The G1-only case (actions with `flagged: false`) is what D71 decided.
- **6.4/7.11** match companion 9.5 (temperature 1.0 load, per-question T/b), D76 and the `stock-fallback-config` interaction row; the two stock cases (picked-with-fit vs no `selected.json`) are both covered.

### Findings

**F1 — Shared-module seam is unpinned (Part 1; kind: omission/error; blocking)**
- Spec text, 6.3: "The runtime imports, read-only, from the module the training build writes … the exact question wordings and short names (companion 4.2, 6.5); the state renderer (6.4), screen renderer and section splitter (6.6), requirement-unit splitter (6.7); the correction-text builder (6.5) … The runtime passes events in the companion 6.1 schema, documents as `{path: text}`, instructions as an ordered list, and open findings as their OPEN FINDINGS lines."
- Evidence. (a) 7.5 needs "`D1#E<seq>` for each detailed event", and 4 defines detailed events as "the recent events the renderer shows as detailed blocks"; the companion's component table (TRAINING-SPEC line 129) has the renderer returning only "state text (section 6.4)". Nothing says the renderer reports which events it rendered in detail, or the overflow verdict (companion 6.4's switch needs `tokens(LATEST EVENT, OPEN FINDINGS, EFFORT, headings, count line)`, which only the renderer sees), or the merged-state fit test (7.9 step 4). (b) The runtime fills parametrized rows itself (D1 "Does event k show part of it?", G2/D2 «R_k text», L7 «text», D1/D5 «short names», D2 «summary»), but 6.3 imports wordings, not fill functions. The companion pins the key suffixes and the RF state form only in 6.3 (line 196: "`G2#R3`, `D1#E41`… An RF record's state is the ⟦ ⟧ window alone"), a section the runtime spec never cites. The rendering of "event k" in D1's text is pinned nowhere I could find. CROSS-TRACK-NOTES line 17 pins only D2's «summary».
- Consequence. Two Codex agents build in parallel from different specs. A fill mismatch (say "event 41" vs "event E41") puts every diagnostic row off the training distribution, and no check catches it: the shared-renderer check (section 10) compares states, not question rows. The runtime agent also cannot implement 7.5 or the overflow switch without reaching into renderer internals.
- Answer: one correct answer, not a design choice. The module's contract in 6.3 must state what the renderer returns (state, detailed-event seqs, overflow verdict / fit) and that the row builders (fills) are exported and shared; cite companion 6.3 for the RF state and key suffixes. This pins an existing seam; it adds no mechanism.

**F2 — Ordering-gate semantics admit two readings, both defective (Part 1; kind: error; blocking)**
- Spec text, 7.10: "Per session, an event with `seq` s is released when `last_seq` = s − 1, or after waiting 8 s for the missing one (it is then skipped)." Lifecycle, 5: "Release in order → store → …".
- Evidence. The spec never says when `last_seq` advances. D29: "events are processed in `seq` order per session"; the ledger's runtime interaction row assumes serial processing ("An agent faster than one event per 1.2 s builds a queue"). 7.6/7.3 require event s's findings and L7 rows to be in s+1's state.
- Consequence. Reading A (`last_seq` advances at release/store): events of one session run concurrently (up to `max_inputs=4`); s+1's state lacks s's new finding, `drift_history` appends out of order, `late` and `pending_correction_marks` race. Reading B (advances at completion): the 8 s timer, worded for a *missing* predecessor, fires on a *present but slow* one (an overflow event is "expected beyond 8 s", section 9), skips an event that is not missing, and then runs both concurrently anyway. Secondary, same mechanism: with `max_inputs=4`, four held inputs can occupy every slot while the lowest `seq` waits in Modal's queue; after 8 s the real event is skipped and, on arrival, dropped as a duplicate with "nothing stored" (7.1), so it never enters the ledger.
- Answer: one correct answer under D29 for the first part (release waits for seq s−1's result to be built; the 8 s wait applies only while seq s−1 has not *arrived*). The slot-exhaustion interaction is a configuration question for the owner; I do not propose a mechanism.

**F3 — "No lost results" is not what the lateness clock delivers (Part 1; kind: unsupported claim; non-blocking for the demo)**
- Spec text, 1: "**No lost results.** A result that finishes after the backend's 8 s wait is delivered once, on the session's next response." 7.10: "Lateness keeps its current rule: a result finishing ≥ 8.0 s after the method started is stored…" 10: "`burst-backlog` | … every result is delivered exactly once". 12: "`backend_sent_at` (the first result after a cold start is lost until classify measures lateness from the backend's send time)".
- Evidence. Report 31 §1: "lateness is timed from `classify()` start, so container boot (23-27 s) is not counted and a cold session's first result is lost." The same clock gap applies to any input that waits in Modal's queue beyond the four in-container slots (7.10's `max_inputs=4`) behind a slow event.
- Consequence. A result finishing < 8 s by its own clock but > 8 s after spawn returns to a caller that already answered `pending`: lost. Worse, that "on-time" response pops the session's stored late results onto itself ("the next on-time result carries every stored one"), so they are lost too. `burst-backlog` as written can fail for bursts larger than four behind a slow event; the section-1 guarantee is stated without its known exception.
- Answer: a design choice (adopt the deferred item, or state the guarantee and the test with their exception). The spec currently asserts both the guarantee and the deferral.

**F4 — SCR is a "firing" question under the spec's own vocabulary (Part 1; kind: error; non-blocking, overflow only)**
- Spec text, 4: "fired | a problem score ≥ 0.5"; "problem score | for a yes/no question, its calibrated p of yes". 7.9 step 3: "A section is picked when SCR or M8 fires (calibrated p ≥ 0.5). An M8 fire is a finding…" 7.8: "`flagged` = `risk` ≥ 0.5; equivalently, a question other than G1 fired." 7.6: "For each fired question q, in order…"
- Evidence. SCR is a relevance screen: 4.2 wording "…even if the agent has not broken it"; D19.P "a separate, recall-first relevance question". 7.8's exclusion list names "G1, L7, RF and the diagnostic questions", not SCR.
- Consequence. Read literally, any overflow event with one relevant section has `risk ≥ 0.5`, `flagged: true`, and opens an SCR finding with a notice. 7.9's "An M8 fire is a finding" implies SCR is not, but 7.6 and 7.8 do not say so. A related gap: when M8 fires on a screen state and nothing fires on the merged state, 7.5 ("only when something fired … on the same state") does not say the diagnostics (D1, D5) run on the merged state for the M8 finding, so the M8 finding's severity is undefined.
- Answer: one correct answer. SCR has no problem score and never fires in the 7.6/7.8 sense; diagnostics run on the merged state whenever a screen M8 fired.

**F5 — State budget when the validated length is below 32,767, and under stock fallback (Part 1; kind: error/omission; blocking on the fallback path)**
- Spec text, 7.3: "…with B_state from companion 6.4. If the documents do not fit (companion 6.4's switch rule, with the validated length the training track's long-context gate reports), the overflow path runs." 8: "State budget | B_state per companion 6.4, with the validated length from the training track's gate". 7.11: "The training track's long-context validated length is a constant in the deploy configuration, read by the overflow switch."
- Evidence. Companion 6.4: "B_state = 32,767 tokens". D18 Revisit-if: "the trained budget then drops to the validated length and the overflow path carries more traffic." Stock Kev's validated length: D45 "8,192 tokens (stock Kev's validated length)", D3 "About 8K tokens of validated decision context".
- Consequence. If the gate validates 16K, one reading (7.11: the length feeds only "the overflow switch") renders 32K states beyond the validated length and switches only on the document threshold; the other (D18) renders at B_state = 16K. The two produce different states for the same session (detail budget `0.40 × B_state`, one-liner collapse). For `stock-fallback-config` the constant has no stated value at all, and 8,192 vs 32,767 changes detailed events from ~2 to ~25.
- Answer: one correct answer per D18: B_state := validated length in every 6.4 formula; stock without a gate result serves at 8,192.

**F6 — Row packing at full states exceeds Kev's allowance; the spec fixes a one-request structure (Part 1; kind: error; non-blocking for the 8K demo)**
- Spec text, 7.3: "Rows asked in the first Kev request on that state: the every-event set…; `L7#F<n>` for each open finding with a correction sent…; at `turn_completed`: `G2#R<k>` for each R_k and `G5`." 7.5: "Second request… Third request…".
- Evidence. Companion 6.4: "A record's question rows share Kev's packed allowance (`max_packed` = `max_state` + 1,664, checked by Kev's own fit test); rows that do not fit move to a sibling record with the same state… `max_branch` = `max_state` + 640, so 640 tokens beside a full state." The 12 every-event wordings (4.2) are ~540 words, roughly 700–800 tokens before Kev's per-row framing. Two open L7 rows at the 640 cap plus the 12 wordings ≈ 2,000 > 1,664; so is a turn end with one open L7 and a handful of G2 rows. Report 31 C2 fit 20 *short* probe rows at 32,768. I could not retrieve Kev's source locally (no checkout under either project tree) to confirm whether `kev.serve` rejects or auto-splits an over-packed request; the companion's sibling-record rule implies it rejects.
- Consequence. At full states the first request can fail at exactly the events where L7 and G2 matter; a raise becomes the backend's fallback (unscored event). At the demo's ~8K states there is ~26K of row room, so no effect.
- Answer: one correct answer. Rows are scored independently on the shared state (companion 4.1), so overflow rows go in a further request on the same state (cache hit ≈ 76 ms, report 31 C2). The spec should say the request count is not fixed.

**F7 — `drift` on an empty-text turn end (Part 1; kind: omission; non-blocking)**
- Spec text, 7.1: "`turn_completed` | … if its `agent_text` is empty, only G2 and G5". 7.8: "`drift` = 1 − p(G1) on classified events"; "`drift_rate` = (drift_t − drift_{t−w}) / w with w = min(5, number of earlier classified events)".
- Evidence. The event is classified but G1 is not asked, so `drift` has no value and the event's membership in `w` is undefined. D76 says the same "only G2 and G5", so the ledger did not settle it either. (Side note: D72 says L7 "is asked on every classified event while a finding is open", which this case violates; the spec follows D76, so that tension is the ledger's, not the spec's.)
- Consequence. An implementer picks null vs carry-forward and whether the event counts toward `w`; the Pane sees a null or a flat point either way.
- Answer: a small design choice; the contract accepts `drift: null`.

## Part 2. Cost and latency (section 9 vs report 31)

Defend:
- "about 1.2 s at an 8K-token state and about 2.9 s at 32K, for 12 rows … cache-miss column": report 31 C2 miss, q=12: 1,221 ms at 8,192; 2,907 ms at 32,768. Exact.
- "about 70 ms per diagnostic row on long states … the state reused from Kev's cache": C2 note "Above 4,096 state tokens each question costs ~70 ms whether or not the state is cached"; HIT q=1→q=12 at 8K is (809−71)/11 ≈ 67 ms. Exact. The reuse premise holds (PrefixCache keys on the exact state; the second request's state is identical) as long as the state is still resident: the cache is 4 states / 65,536 tokens (report 31 §0), so at 32K states two concurrent sessions can evict it between requests and the diagnostics pay a second ~2 s prefill.
- "$2.27 per hour": C5, L40S $1.95 + 4 CPU + 16 GiB. Exact.
- "Overflow … expected beyond 8 s": C2 miss q=20 at 8,192 = 1,789 ms per screen state; four screens plus a merged state (1.2–2.9 s) is ~8–10 s. Holds for ≥ 4 screens; two or three screens may land on time, which is immaterial.

Challenge (unpriced in section 9):
- RF batches. Each RF unit is its own small state (companion 6.3), ~107–130 ms per unit at ≤ 2K tokens (C2, 2,048 miss q=1: 107 ms). A 60-unit CLAUDE.md on `session_started` is ~6–8 s of GPU before the first real event, which is serialized behind it (F2). The demo's documents are small, so this is a long-session cost, but it is the largest unpriced item.
- Dict I/O: C3 measured ~100 ms per skipped event ("Dict I/O is about half of `classify_ms`") at a small record; 7.10 writes the whole record through after every event and 6.5 bounds each stored field but not the event count, so the write grows with the session. Unmeasured; my estimate is a few hundred ms by a 100-event session. Not a correctness issue.
- D1 row count. Priced per row, but the count is the number of detailed events, which at the demo's short sessions is every event (10–25 rows, 0.7–1.8 s per flagged event). Within the 8 s wait; worth knowing.

## Part 3. Completeness against the ledger

Checked D70–D76 item by item and the entries they modify (D17, D23, D25, D29, D71), plus D10, D11, D15, D20, D21, D22, D24, D26, D35, D40 and both CROSS-TRACK-NOTES sections. Every D70 cut appears in 1 Scope-out or is absent from the mechanics; D71's formulas, D72's lifecycle (every clause), D73's overflow form, D74's done bar, D75's read-only import and dependency, and all nineteen D76 bullets are carried in 6–8, 10, 13. One omission:

**F8 — `warmup()` is not in the spec's interface (Part 3; kind: omission; non-blocking but demo-relevant)**
- Ledger, D35: "**Modal `Classifier` class:** weights load once per container in `@modal.enter()`; `classify(event)` and a no-op `warmup()` share a container; `@modal.concurrent` so a warm-up arriving mid-classification doesn't start a second GPU; Noah's `/health` fires `warmup.spawn()` at session start and on each user prompt." Decision: "`Classifier` class, partner-confirmed."
- Spec: section 6 defines only `classify(event: dict) -> dict` (6.1); 1 names only the `classify` method; 7.11's "warms up as it does now" describes the `@enter` work, not the method. 13 Phase 1 does not list it.
- Evidence the omission bites: `Noah/backend/app.py` lines 300–309 call `classifier().warmup.spawn.aio()` and swallow the exception into a log line, so a rebuilt class without `warmup` fails silently; every session's first event then pays the 23–27 s cold start (report 31 C1), and under F3 that first result is lost.
- Belongs in 6 (Contracts & Interfaces). One correct answer.

## Part 4. Spec/task boundary and proportionality

**F9 — Coordination/status lines in 12 (kind: task material; low)**
- Spec text, 12: "who sets `min_containers=1` on demo day; NOAH.md reports a deployed flag cutoff of 0.65 and a connected backend that differ from the committed code." and "Noah builds the slow-tests repo … and runs about 10 pilots".
- These are status and coordination notes (ledger / task-file / NOTES material), not design. A Codex agent reading the spec as requirements may try to reconcile NOAH.md or own the pilots. The two demo prompt texts are legitimately spec: they define the done bar in 10. One correct answer: move the status lines out.

**Owner's rule.** I ran the use test over every mechanism in 6–8 and 10: ordering gate and 8 s skip (the ledger needs in-order history; CONTRACT says requests arrive out of order), write-through store (container restarts), 16,000-char trimming (5 MB raw items vs a Dict record), duplicate-`seq` skip (retries), late results (contract), `pending_correction_marks` (needed to write "correction sent at E<m>"), the finding lifecycle (D72, the owner's), the swap script and `selected.json` (D76), and the twelve checks in 10 (each guards a decided behaviour with one cheap test). Each has a one-sentence use. No mechanism fails the rule; nothing needs a further mechanism. Zero findings here.

---

## Three most likely failure points

1. **The renderer seam (F1).** Two agents, two specs, one module whose returned values and fill conventions neither spec pins. The failure is silent: states match byte for byte while diagnostic rows drift from training.
2. **Ordering under load (F2 + F3).** Whichever `last_seq` reading the builder picks, a slow event at the head of a burst either races the session record or stalls and drops a real event, and the method-start lateness clock loses the queued results (and any late results riding on them).
3. **The fallback path (F5 + F8).** If training is late, stock serves at an unstated budget, and a rebuilt class without `warmup` turns every session start into a 25 s cold start whose first result is lost. NN-002 already says stock missed the demo deletion in context (11), so this path is where the demo most plausibly goes dark.

## Verdict

**Implementation-ready for Phases 1–3 on the demo path once three questions are answered; not before.** Blocking questions, each with its answer source:
- Q1 (F1): What does the shared renderer return beyond the state text, and are the parametrized row fills (D1's event reference, G2/D2's R_k, L7's text, short names, summary, RF window-as-state) exported by the module? One correct answer; must land in 6.3 so both agents build to it.
- Q2 (F2): Does `last_seq` advance at completion, and does the 8 s timer run only while seq s−1 has not arrived? One correct answer under D29.
- Q3 (F5): Is B_state the validated length in every 6.4 formula, and what is it when stock serves with no gate result (8,192 per D45)? One correct answer under D18.

F3 needs the owner's choice (guarantee with exception, or the deferred field). F4, F6, F7, F8, F9 are non-blocking and each has one correct answer except F7's small choice.

---

## Coverage ledger (every line of every file in scope read, in order, chunked ≤ 200 lines)

| File | Lines read | EOF |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 | yes (`date` run: Sat Nov 7 23:10 EST 2026) |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 | yes |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 | yes |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–606 | yes |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–133 (steps 4 and 6 at lines 51–53, 64) | yes |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–206 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–261 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\backend\app.py` | 1–200, 201–394 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\classifier\app.py` | 1–161 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\RUNTIME-SPEC.md` (target) | 1–200, 201–326 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md` (cited sections) | 56–109 (4.1–4.2), 144–165 (6.1), 181–197 (6.3, read for receipt F1), 198–278 (6.4–6.7), 544–553 (9.5) | all cited sections complete |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 201–400, 401–600, 601–800, 801–1000, 1001–1165 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\CROSS-TRACK-NOTES.md` | 1–18 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\research\2026-11-07-31-stock-kev-modal-measurements-and-intent-probe-research.md` (receipt for Part 2) | 1–98 | yes |

Grep was used only to locate section headings in TRAINING-SPEC.md and report 31 before reading them. No Kev source checkout exists under either project tree; the one claim that depends on Kev's packing behaviour (F6) is marked as not confirmed from source. No files were written. All shell commands ran in the foreground and exited.