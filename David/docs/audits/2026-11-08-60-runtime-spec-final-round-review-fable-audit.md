# Round-4 (final, full-scope) review of `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\RUNTIME-SPEC.md`

`date` ran first: Sun Nov 8 00:21:09 EST 2026. Every mandated file was read in full, in the given order, in chunks of about 200 lines (coverage ledger at the end). Kev's clone at `fc4a17e1` was read in targeted ranges only and never run. Shell commands: `date` and one `wc -l`, both foreground, both exited. No background processes; no files written.

**Summary.** All seven register entries landed and none created a new defect. Every 6.4 claim about Kev's loader and serving path checks against the source line for line, including three claims no earlier round had verified (`LoadOptions.temperature`, `Checkpoint.meta.temperature`, and a local directory as a `Checkpoint` argument). Section 9 matches report 31. No omission against the ledger. No task material. No mechanism fails the owner's rule. Two low findings remain, both with one correct answer and neither blocking: a pre-existing seam in 7.3's row list that contradicts 7.1 on empty-text `answer` turn ends, and a session-header field (6.5) the document never defines.

---

## Part 1. Logic and contract audit

### Walks that found nothing

**Contract (6.1, 6.2 against CONTRACT.md §3–4 and `Noah/backend/app.py` 60–73, 91–108).** Every result shape in 6.2 (scored, skipped, late, overflow) validates under `Result` with `extra="allow"`: `risk` is a probability or null, `flagged` a bool, `actions` entries carry `type`/`level`/`text`, `drift`, `drift_rate`, `late_results` and the `details` keys pass as extras; `check_late_results` validates each late entry with the same model and `model_dump()` keeps extras. Action order (detected, inject, intervened) matches CONTRACT §4 and D24. Notices carry no prefix (CONTRACT §7). `backend_sent_at` matches CONTRACT §7's proposal and D77. `warmup()` matches the backend's `/health` path (lines 300–309, 375–382).

**Shared module (6.3 against companion 6.1, 6.3–6.7).** Every export the runtime names (question wordings, row fillers, instruction-list builder, OPEN FINDINGS formatter, state and screen renderers, splitters, correction builder) is either in the companion or in CROSS-TRACK-NOTES' "what the shared module must expose" list; the key suffixes (`G2#R3`, `D1#E41`, `D2#R3`, `SCR#S2`, `M8#S2`) match companion 6.3; the `[I_n]` arrival-order rule matches companion 6.4; B_state as a parameter matches the notes.

**Model loading and probability reading (6.4 against Kev at `fc4a17e1`).**
- `LoadOptions(... temperature=1.0)`: the field exists, "None = the temperature the checkpoint carries ...; 1.0 = raw logits" (`checkpoint.py` 105).
- "T = the checkpoint's shipped temperature (`Checkpoint.meta.temperature`, since the loaded head reads 1.0)": `load` sets `m.head.temperature = meta.temperature if opts.temperature is None else opts.temperature` (241), so `meta.temperature` is the shipped value and is readable after an override.
- The fallback reproduces Kev's own behaviour: the head applies temperature as `z / self.temperature` (`model.py` 218, 223), so σ(z/T_ship) over `z = log p_yes − log p_no` read at T = 1 equals Kev's default p, and softmax(log p_o / T) equals its choice p up to the constant softmax ignores.
- `selected.json`'s `"checkpoint": "<directory or hub id@revision>"`: `resolve_run` returns a directory as given and otherwise `snapshot_download`s `repo@revision` (`checkpoint.py` 38–45).
- `rec, meta = kev.api.to_record(request)`: returns `({"state": render(req.state), "questions": qs}, meta)`; noul options `[no, yes]`, choice in `criteria` order, score in level order with a legend (`api.py` 102–117); `question_keys` gives `["false","true"]`, the criteria names, or `"0","1",…` (94–99). `render(req.state)` adds nothing to a string state; `with_date_facts` is opt-in (`KEV_DATE_FACTS=1`, `serve.py` 225) and not on this path, so the state Kev reads is the renderer's bytes.
- `ps, stats = server.probs(rec)`: `probs` is `self.submit(rec).result()`, a Future of (probabilities, stats) with `[q.tolist() for q in p]` unrounded (`serve.py` 147–148, 189); `Server.answer` is a separate method (200).
- 7.3's "no limit on the rows of one request beyond each row's own length": admission refuses only a state over `SERVE_MAX_STATE` (65,536) or a row over `SERVE_MAX_BRANCH` (73,728) (`serve.py` 136–142; `model.py` 18–19); `rows_per_pass` is `max(1, …)` (`model.py` 47). 7.2's "may split across a few batches": the model thread takes one queued record then drains with `get_nowait` up to `MAX_BATCH = 64` (`serve.py` 153–160).

**Session store (6.5).** Per-event entries plus a header carry everything a rebuild needs (documents, units, event ids, `last_seq`, findings, drift history, late results); instructions derive from stored events through the single builder. One field is undefined (F2).

**Events (7.1), units (7.2), state and rows (7.3), firing (7.4).** The skip rule matches D21 and the companion's read-only set; RF runs on skipped events too (the 5 lifecycle puts the filter before the skip), so `session_started` and AskUserQuestion answers feed R_k. The turn-end table: non-empty text + `answer` → every-event set + G2 per R_k + G5; non-empty text + other reason → every-event set; empty text + `answer` → G2 and G5, `drift` null; empty text + other reason → skipped; missing reason → `answer`. Matches companion 4.2, D72 and D76. The fire set and problem scores match D71; a G2 row whose argmax is `not done` has p(`broken`) < 0.5 and cannot fire, so 7.7's `details.not_done` rule is consistent with 7.4.

**Diagnostics and findings (7.5, 7.6), walked.**
- *Action question.* E10 Bash deletes tests; M4 fires; key (M4, 10) has no finding → diagnostics → D5 significant → F1 opens; detected, inject, intervened. The result returns on time, so the correction "counts as reaching the agent"; E11 arrives and is the first event received after that response → "correction sent at E11"; L7#M1 asked from E12. On E11, M4 firing again has key (M4, 11), a new finding; a second correction can go (D72's per-action identity). On E12, `genuinely fixed` closes F1; `dismissed correctly` closes it too (action finding). Correct.
- *Run question.* E5: G1 fires (p(G1) < 0.5), key (G1), no finding → diagnostics → D5 minor → F3 opens, one `potential` notice, never in OPEN FINDINGS. E6: status pass first: G1 is asked and fires, so F3 stays; then the fired row maps to an open minor finding → diagnostics run (7.5's second clause) → D5 significant → F3 upgraded, takes E6's citations, correction out; D5 minor → nothing sent. E7: F3 open non-minor → no diagnostics, nothing sent. E8: L7 `dismissed correctly` → F3 `dismissed`; G1 still firing → nothing. E9: G1 does not fire → F3 closes. E10: G1 fires → new finding F4. Every step matches D72, including the no-reopen rule and the upgrade path round 3 restored.
- *G2 at a turn end.* E20 `answer` turn with text: every-event set + G2#R1..R3 + G5 + any L7 rows. G2#R2 = `broken` at 0.6 fires, key (G2, R2), new → second request (D1 per detailed event, D5) → third request (D2 per R_k, «summary» from the cited E-refs) → significant → correction. G2#R3 = `not done` → nothing sent, R3's text in `details.not_done`. A later `answer` turn where G2#R2 does not fire closes a dismissed or minor (G2, R2); an open significant one closes only through L7. Correct.
- *A late-delivered correction.* E5's result finishes late, is stored, rides on E6's response; the correction counts as reaching the agent then; E7 is the first event received after that response → "correction sent at E7"; L7 from E8. Consistent with 7.6, 7.10 and the OPEN FINDINGS line.

**Actions (7.7), Pane fields (7.8).** One severity per event; notice texts match D76; `risk` excludes G1 and `flagged` = `risk` ≥ 0.5 holds exactly when a non-G1 question fired; `drift_rate` matches D76 and D17.

**Overflow (7.9).** Screen packing, picking, M8 findings citing LATEST EVENT, the merged state's `<path> › <heading>` documents, dropping lowest-scoring until fit (equivalent to D73's highest-first), diagnostics on the merged state, and the clean raise all match D73 and D76. 7.5's "or on the merged state when only a screen M8 fired" reads oddly in isolation but 7.9 step 5 fixes every diagnostic on the merged state.

**Ordering, concurrency, late results (7.10).** Walked a slow head, an exception, a single gap, a double gap, a gap with a running predecessor, and a straggler: `last_seq` is monotone, the timer starts only when the next due seq is absent and a later one waits, and a straggler takes 7.1's last row. A waiter that spends the 8 s is itself late and recovers on the next event (E6 arriving at t = 3 s runs at 9.2–10.4 s, on time). The lateness check and the two stated exceptions match D77. Modal's thread-per-input model under `@modal.concurrent` with sync methods makes the per-session lock the right primitive; with `max_containers=1` the in-memory state is authoritative and the Dict is for restarts.

**Loading and swapping (7.11).** Matches D76 and the handoff notes; the adapter directory loads through the same `Checkpoint` path as the hub id (above).

### Findings

**F1 · Part 1 · error (pre-existing seam between 7.3 and 7.1) · one correct answer · low.**
- Spec 7.3: "Rows asked in the first Kev request on that state: the every-event set, positive wordings only; …". Spec 7.1, `turn_completed` row: "classified with the every-event set when its `agent_text` is non-empty … with empty text, only G2 and G5, and its `drift` is null". Spec 7.8: "`drift` = 1 − p(G1) on classified events where G1 is asked; null where it is not (an empty-text turn end)".
- Evidence: 7.3 is the list the question runner is built from and states no exception; 7.1 and 7.8 both exclude the every-event set on an empty-text `answer` turn; D76 says the same ("a `turn_completed` asks the every-event set when its text is non-empty, plus G2 and G5 when `turn.reason` is `answer`"). Round 3 corrected 7.3's third bullet for the `answer` gate but not the first bullet. Section 10's "Turn ends" check tests only G2/G5 presence, and "Skipped events" tests the empty *aborted* turn, so an empty-text `answer` turn is untested.
- Consequence: a runner built from 7.3 asks twelve questions on a state whose LATEST EVENT is `[E<n>] MESSAGE` with no text, returns a `drift` value where 7.8 says null (feeding `drift_rate`), and lets M1/M2/M4 fire on an empty message. Empty-text `answer` turn ends are not rare: a turn that ends on AskUserQuestion or ExitPlanMode has no final text.
- Answer: one correct answer; 7.3's first bullet reads "the every-event set, positive wordings only (not on an empty-text turn end, 7.1)".

**F2 · Part 1 · error (undefined term) · one correct answer · low.**
- Spec 6.5, header fields: "`pending_correction_marks: [finding id]`". The term occurs once in the document (grep). Spec 7.6: "'Correction sent at E<m>' is the `seq` of the first event the session receives after the response that carried the correction". Spec 7.10: "A correction counts as reaching the agent only once its result has been returned (on time, or inside `late_results`)".
- Evidence: 7.6 and 7.10 define two moments (the result returned; the next event received) but never say what state is held between them or that this field holds it. The design-ethos language rule requires every internal reference to resolve within the document.
- Consequence: the builder infers the field's meaning from its name, and most will infer correctly; the one inference that matters is unstated: for a correction delivered inside `late_results`, the mark is set when the late result is attached to a response, not when it is stored. Getting that wrong stamps "correction sent at" with an event before the agent could have seen the message and starts L7 early.
- Answer: one correct answer, one sentence in 7.6 or 7.10: findings whose correction message has been returned (on time or inside `late_results`) and whose "reached the agent at" event has not yet arrived are held in `pending_correction_marks`; the next event the session receives sets E<m> for all of them and empties the list.

### Considered and not raised
- **A G2 item's quoted requirement.** 7.7 says items quote "the R_k quoted by D2"; a (G2, R_k) finding carries R_k in its key and the G2 wording itself quotes it, so the shared builder lists it from the finding (companion 6.5: "fix the broken ones (listed)"). The builder owns item rendering under principle 2.
- **"When the event brings a new user instruction" (7.6)** on an AskUserQuestion answer, which arrives on a skipped event: with one instruction-list builder, "a new `[I_n]` since the last classified event" is the natural implementation.
- **Stale `source` on stored units after a late instruction renumbers `[I_n]`**: the `source` field is used only to remove a replaced document's units by path.
- **Which clock "receives" uses for "correction sent at E<m>"** when a skipped straggler arrives right after a correction: an edge of an edge; adding a rule would be a mechanism.
- **The Mod's attach-to-next-result race**: if E11's result is produced before E10's response arrives, the agent reads the correction at E12 while the state says E11; L7's first answer may be `ignored` one event early and the finding stays open until a later answer. Inherent to D11's delivery, not the spec.
- **The per-item 2,000-token evidence cap (7.7)** is unassigned between runtime and shared builder; principle 2 assigns it to the builder.
- **A session whose instructions alone exceed the switch threshold** raises on every later classified event, so its stored late results never deliver. D76 accepts the clean raise; section 11's "that event unscored" understates the duration but adds no defect.
- **CONTRACT §4 still says the container "takes up to 4 calls at a time"**; 7.10 raises it to 32. A documentation cascade item on Noah's shared file, not a spec defect.
- **`source` on a skipped result** is not listed among the always-present `details` keys; harmless either way.
- **A brief two-container window during redeploy** (old container finishing in-flight inputs) with independent `last_seq`: the swap precedes the demo; the Dict rebuild heals it.

---

## Part 2. Cost and latency (section 9 against report 31)

| Section 9 claim | Report 31 | Verdict |
|---|---|---|
| 1.2 s at 8K, 2.9 s at 32K, 12 rows, cache miss, model time | C2: 1,221 / 2,907 ms at q = 12 miss (lines 35, 39) | Holds |
| Modal + Dict 0.15–0.3 s; ~100 ms Dict I/O on a skipped event | C3: skipped event ~100 ms; round trip − `classify_ms` 56 ms p50, 144 ms p95 (line 47) | Holds; with the header in memory the design does two writes per event, so the figure is an upper bound |
| ~70 ms per diagnostic row above 4,096 tokens | C2 note (line 43) | Holds |
| 10–25 D1 rows, 0.7–1.8 s, "every event is detailed" | 70 ms × rows; at B_state 8,191 the detail budget is 1.2–3.3K tokens, so fewer events are detailed | Arithmetic holds; the row count is an upper bound at L = 8,192, and the section is labelled estimated |
| L7 row 0.3–0.5 s from "report 31's state-prefill cost at one question, about 0.06 ms per token across 2K to 32K states" (G6) | C2 q = 1 miss: 107/2,048 = 0.052, 470/8,192 = 0.057, 942/16,384 = 0.057, 2,056/32,768 = 0.063 ms per token; 6–7K tokens × 0.06 = 0.36–0.42 s | Holds; basis now correctly cited |
| RF ~0.1 s per unit | C2: 107 ms, q = 1, 2K miss (line 33) | Upper bound (short windows, graphed, batched) |
| Overflow beyond 8 s | C2: 1,789 ms per 8K screen at q = 20; four screens + merged ≈ 8.4 s | Holds for four or more screens |
| $2.27/h | C5 (line 58) | Holds |

Unpriced but consistent: a turn end with many R_k adds one G2 row each (~70 ms above 4,096 tokens), and a rebuild after a restart pays roughly one Dict read (~50 ms) per stored event on top of the 23–27 s cold start (C1). Neither is a ledger requirement. **No findings.**

---

## Part 3. Completeness against the ledger

Checked D70–D77 clause by clause, plus the entries they modify (D13, D17, D23, D25, D29, D29.W, D71), D10, D11, D19.G7, D19.L7, D20, D21.E1/E2/E8, D21.E5/E6/E7/E9, D21.U, D22, D24, D26, D35, D40, D47, and all three CROSS-TRACK-NOTES sections.

- D70's cuts are in section 1's out-list or absent from the mechanics (segment cache, runtime eval metrics, the overflow union); its consequences (documents as last sent; contradicting answers both reach the correction) are in 7.1 and principle 4.
- D71 is 7.8 and 6.2. D72 is carried in 7.1, 7.3, 7.6 and 7.7, every clause, including per-action versus run identity, no second correction or notice while open, no escalation, the minor-upgrade rule, L7 one row per message from the first classified event after delivery, G2/G5 on `answer` turns, and `not done` to `details` only. D73 is 7.9. D74 is section 10's Done row and section 12. D75 is 6.3 and 13. Every D76 bullet is carried in 6.4–7.11, including both stock cases (picked stock served with its lift-baseline fit through `selected.json`; no `selected.json` served at the shipped temperature). D77 is sections 1, 6.1, 7.10, 11 and 12.
- D29's "a final late result with no following event waits" is section 1's first exception. D13's 08:00 rule is in section 11. D21.E6's "AskUserQuestion answers re-run D20's filter" is met by the lifecycle running RF before the skip.
- The handoff section of CROSS-TRACK-NOTES (module `David/monitor_format/`, runtime `David/classifier/`, volume `intent-monitor-training` with `selected/`, `calibration.json`, `long_context.json`) is carried verbatim in 6.3, 6.4 and 7.11.

**No omission.** Two stale clauses sit in the ledger, not the spec: D10 still lists `correction_message` as a result field (superseded by `actions[]`), and D75 still says the runtime build "starts once that renderer exists" (phase 1 now depends on nothing).

---

## Part 4. Spec/task boundary and proportionality

Use test run over every mechanism in sections 5–11: the ordering gate and its 8 s skip (CONTRACT §3 says requests arrive out of order; the state needs in-order history; D29 decided the order); `last_seq` and `drift_history` in the header (a scaledown restart mid-session); per-event Dict entries (exact renderer counts, D76); the per-session lock (threads under `@modal.concurrent`); the duplicate-`event_id` skip (one lookup on a keyed store); late results, `backend_sent_at` and the correction marks (the contract and the shared "correction sent at E<m>" line); one L7 row per message and kind-based keys (D72); the diagnostics trigger (latency and D72's upgrade); the screen, merge and clean raise (D73, D76); `selected.json` and the swap (D76); the null-calibration fallback (the stock path); `_test_sleep_s` (Noah's existing test hook); the 32-slot sizing (stated basis); the seventeen section-10 checks (each one cheap test of a decided behaviour, the five named tests from D72's interaction table among them). Each has a one-sentence use for this build, none guarantees beyond what the owner asked for, and none needs a further mechanism. Section 1's two exceptions are owner decisions. Sections 12 and 13 hold the done bar's inputs, external dependencies and phase order; section 10's `verify_deploy.py` reference defines the oracle. The document is 353 lines against 351 in round 3 while landing seven dispositions.

**No task material; no overdone mechanism; zero findings.**

---

## Register verification

| Entry | Verdict |
|---|---|
| G1 (7.5) | Landed. The trigger is now a predicate on finding state alone; walked minor → significant upgrade, dismissal with no reopen, and close-on-not-firing; matches D72 and D76. No new defect. |
| G2 (7.3) | Landed in the third bullet ("at a `turn_completed` whose reason is `answer` (7.1)"). No defect created by the fix; the first bullet's pre-existing seam with 7.1 is F1. |
| G3 (6.3) | Landed. Consistent with 6.5's processing-order storage and 7.1's straggler row; `[I_n]` renumbering after a late instruction is what training produces on the same stream. No new defect. |
| G4 (10, 13) | Landed. "Instruction numbering" is its own row, cleared by phase 2; "Minor upgrade" is a row cleared by phase 1; phase 1's remaining checks run on fixture probabilities and need nothing from the shared module. No new defect. |
| G5 (8) | Landed; the sizing row matches 7.3 and 7.11. |
| G6 (9) | Landed; the C2 q = 1 column gives 0.052–0.063 ms per token, and the stated 0.3–0.5 s follows. |
| G7 (header, 3, 6.3, 6.4, 7.11) | Landed. Both cited team-repo files resolve (`David/docs/TRAINING-SPEC.md`, `David/docs/research/2026-11-07-31-…`); module path and volume names match the notes' handoff section. No new defect. |

## The three most likely failure points

1. **The shared-module seam (6.3).** The module does not exist yet; the runtime relies on exports promised only in CROSS-TRACK-NOTES (B_state as a parameter, fit flags, the exported builder, formatter and trimmer). The byte-for-byte check runs the same module on both sides, so only the instruction-numbering check can catch an interface mismatch.
2. **The stock path at L = 8,192 in the live demo.** README, CLAUDE.md and AGENTS.md at session start sit near the ~5K-token switch; RF on every README sentence delays the first scored events into late results; and stock Kev's 0.02 yes-rate on "still pursuing" (report 31, line 71) fires G1 on nearly every event, so a drift finding opens early and, while it is minor, diagnostics run on every event (0.7–1.8 s each), pushing bursts late.
3. **Correction delivery timing versus L7.** The Mod attaches a correction to the next tool result, which may already be in flight when the response lands; "correction sent at E<m>" then precedes the event the agent actually read it on, L7's first answer can be `ignored` a turn early, and the finding stays open until a later answer. The correction still lands; the OPEN FINDINGS line and the first L7 reading are what wobble.

## Verdict

**Implementation-ready.** No blocking question. F1 and F2 are one-sentence edits with one correct answer each and no owner decision; a builder who reads 7.1 and 7.8 alongside 7.3, and 7.6 and 7.10 alongside 6.5, builds the decided behaviour without them, which is why neither blocks.

---

## Coverage ledger

| File | Lines read | Every line |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 (`date` run) | yes |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 | yes |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 | yes |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–605 | yes |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–134 | yes |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–207 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–261 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\backend\app.py` | 1–394 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\classifier\app.py` | 1–161 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\RUNTIME-SPEC.md` (target) | 1–200, 201–353 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\docs\TRAINING-SPEC.md` | 56–109 (4.1–4.2), 142–279 (6.1–6.7), 547–556 (9.5); headings located by one grep | every mandated section in full |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 201–400, 401–600, 601–800, 801–1000, 1001–1185 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\CROSS-TRACK-NOTES.md` | 1–35 | yes |
| `…\docs\audits\2026-11-07-57-runtime-spec-round3-review-opus-audit.md` | 1–206 | yes |
| `…\docs\audits\2026-11-07-58-runtime-spec-round3-review-fable-audit.md` | 1–154 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\docs\research\2026-11-07-31-stock-kev-modal-measurements-and-intent-probe-research.md` | 1–98 | yes |
| Kev clone at `fc4a17e1` (receipts only): `kev\checkpoint.py` 30–50, 85–110, 169–260; `kev\model.py` 15–60 and its `temperature` lines 212–223 (grep); `kev\serve.py` 128–200; `kev\api.py` 94–125; greps for `SERVE_MAX_*`, `rows_per_pass`, `MAX_BATCH`, `submit`/`probs`/`answer`, `with_date_facts`/`to_record` | targeted, by design |