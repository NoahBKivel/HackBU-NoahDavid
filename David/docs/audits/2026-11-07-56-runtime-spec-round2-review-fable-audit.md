# Round-2 review of `docs/RUNTIME-SPEC.md`

Date from `date`: Sat Nov 7 23:42 EST 2026. Every mandated file was read in full, in order, chunked at about 200 lines; the ledger is at the end. For receipts I also read report 31, `verify_deploy.py`, Kev's `serve.py` and `api.py` in full and targeted ranges of `model.py`, `checkpoint.py` and the Mod's `register.tsx` (the Kev clone from audit 51 is still in my scratchpad at commit `fc4a17e1`). All shell commands ran in the foreground and exited; nothing was written.

**Headline.** The round-1 amendments landed, and the logic re-derives cleanly: the 7.6 lifecycle survives every sequence I walked, the 7.10 gate behaves under a slow head and a missing event, the 7.4/7.8 fire set and `risk`/`flagged` equivalence hold, B_state and the overflow switch are consistent, the output validates against Noah's `Result`, and the D25 defense holds against Kev's source. I found six issues with receipts: one build-breaking typo from an amendment, one boundary race in the "no lost results" guarantee, one contradiction with the companion on when G2/G5 are asked (needs the owner), two small seam pins, and one unpriced cost. No omission against the ledger. No task material. No mechanism fails the owner's rule.

## Part 1. Logic and contract audit

### Verified (no finding)

- **7.6 walked.** (a) Action question M4, minor: opens at (M4, 10), notice sent, closes at once; a later M4 at (M4, 11) is a new finding — matches D72. (b) Run question L1 minor → stays open while firing, nothing re-sent; at significant it upgrades and the correction goes out; while open and not minor, later firings send nothing. (c) Dismissed run finding: G1 fires at E30 (correction), `dismissed correctly` at E32 → `dismissed`; G1 keeps firing at E33 → nothing sent; stops firing at E34 → closes; fires at E35 → new finding, new correction. Exactly D72. (d) One message covering (M4, 40) and (L5): `dismissed correctly` closes the action finding and marks the run finding dismissed; L7 stops being asked since no covered finding is `open`. (e) G2 per R_k: a second requirement found broken at a later turn end is a new key and corrects. One harmless consequence of the key design: for action questions rule 1's "exists" branch is unreachable (the key carries the current `seq`), so the upgrade path is run-question only, which is what the rules want.
- **7.10 walked.** Slow head E1 (10 s) with E2–E6 behind: no timer (E1 has arrived); all finish late by `backend_sent_at`, are stored, and ride the next on-time result. Missing E2: E3 waits 8 s, E2 is skipped, E3 runs; E2 arriving later has `seq` < `last_seq` and an unseen `event_id`, so its `new_items` are recorded and it is skipped (7.1). Slot exhaustion with a predecessor outside the container resolves within the 8 s skip.
- **7.4/7.8.** The questions that can fire other than G1 all have a problem score, so `risk ≥ 0.5` iff one fired; G1's special rule and `drift` match D71. The notation table still defines "fired" by problem score and says G1 "has none"; 7.4 resolves it. A nit, not a finding.
- **7.3/7.9.** B_state = L − 1 reproduces the companion's 32,767 at L = 32,768; serving accepts up to `SERVE_MAX_STATE` = 65,536 (`model.py` 18), so the budget never hits a serving limit. The overflow steps and both raise conditions match D73/D76. On the overflow path diagnostics run on the merged state in every case.
- **6.3 vs companion 6.3/6.4.** Key suffixes (`G2#R3`, `D1#E41`, `L7#M<j>`) never reach the model: `to_record` puts `qid` only into `meta` (`api.py` 105–117), so the runtime's `L7#M<j>` needs no training twin. What matters, the «event k» fill, is an exported row builder (D24).
- **6.2 vs `Result`.** All fields validate (`Noah/backend/app.py` 52–73, `extra="allow"`); skipped and late shapes validate; `check_late_results` validates each late entry (91–108).
- **Kev claims.** `Server.probs` returns unrounded `q.tolist()` (`serve.py` 147–148, 189); `Server.answer` rounds through `round_prob` (`api.py` 143–159). `Server.submit` queues a Future and the model thread takes up to `MAX_BATCH` = 64 (`serve.py` 132–145, 158–160). The prefix cache is LRU over 4 states / 65,536 tokens (`serve.py` 27–29, 39–87). One model thread holds `lock` around every batch (95–100, 162). `LoadOptions` has `dtype`, `temperature`, `cuda_graphs`, `fused` (`checkpoint.py` 121–128) and line 241 sets `head.temperature` from `opts.temperature` when given; `ck.meta.temperature` is the shipped value (16, 61).

### Findings

**F1 · Part 1 · amendment-created (D2) · error · one correct answer.**
- Spec 6.4: "Probabilities are read unrounded through `Server.probs(rec)` with `rec, meta = kev.api.to_record(kev.api.prepare(request))`".
- Evidence: `kev/api.py` at `fc4a17e1` (read in full, 165 lines) defines `to_record` (line 102) and no `prepare`. `prepare` is defined in `kev/serve.py` line 223 (`def prepare(req)`), and `serve.py` line 22 imports from `.api` only `SystemOneRequest, to_record, to_answers, output_tokens, with_date_facts`.
- Consequence: the call as written raises `AttributeError` on the first request; a Codex agent copying it literally stalls Phase 1 until it reads Kev.
- Answer: `kev.serve.prepare`, or drop the call: it returns the request unchanged unless `KEV_DATE_FACTS=1` (`serve.py` 31, 223–225).

**F2 · Part 1 · amendment-created (D3) · error / unsupported claim · design choice (small).**
- Spec 1: "**No lost results.** A result that finishes 8 s or more after the backend sent its event is delivered once"; 7.10: "a result is late when `time.time() − backend_sent_at ≥ 8.0`"; 6.1: "`backend_sent_at` (Unix seconds, set by the backend just before `spawn`)"; 10: "`burst-backlog` | … every result is delivered exactly once".
- Evidence: Noah's `app.py` 321–328 starts the 8 s after `spawn.aio` returns, so the backend's deadline is `backend_sent_at + s + 8` (s = spawn latency), and the classifier's return reaches it r later. Report 31 C3: round trip p50 239 ms against `classify_ms` 183 ms, so s + r is about 50–60 ms. The two deadlines differ by |s − r|. If r > s, a result finishing in (8 + s − r, 8) is "on time" by the classifier yet arrives after the backend answered `pending`: lost. If s > r, a result finishing in [8, 8 + s − r] is stored as late and also returned to a backend still waiting: delivered twice, and the Mod applies late results "exactly like a normal result" (CONTRACT section 4), so an `inject_agent` correction can be attached twice unless the Mod dedupes, which the contract does not require.
- Consequence: in a backlog exactly one event per burst crosses 8 s; at 1.2 s per event about |s − r| / 1.2 s, a few percent, of such bursts hit the window. `burst-backlog` flakes at that rate; the section-1 guarantee has an unstated exception.
- Answer: the owner's constant (D77). Either state the edge, or set the lateness threshold inside the backend's wait by the measured overhead. I propose no value.

**F3 · Part 1 · contradiction with companion 4.2 · error · owner decision.**
- Spec 7.1: "`turn_completed` | stored; classified with the every-event set plus G2 (once per R_k) and G5, all on one state"; 6.1 "Fields read" lists no `turn`.
- Evidence: companion 4.2, "When asked": G2 "at each `turn_completed` event whose end reason is `answer`", G5 the same; 4.2's closing paragraph: "plus G2 and G5 when the turn's end reason is `answer`"; companion 6.1 carries `"turn": {"reason": "answer | aborted | refusal | error"}`; D47 round 4: "G2/G5 only on `answer` turns". The Mod sends it: `register.tsx` 204 `event.turn = { reason: e.reason, duration_ms: e.durationMs, is_aborted: e.isAborted }`. D72 says "G2 and G5 run on every `turn_completed` event", so the ledger's runtime entry and the companion the spec declares authoritative disagree.
- Consequence: on an aborted or error turn (the user presses Esc; an API error) the runtime asks "The agent says the task is done. … what is the status of this requirement" per R_k, and G5, on rows the model saw only on answer turns; a `broken` at p ≥ 0.5 opens a (G2, R_k) finding and sends a correction at the moment of interruption.
- Answer: the owner chooses between D72 and companion 4.2. If answer-only, 6.1 adds `turn.reason` to the fields read and states the default when it is absent.

**F4 · Part 1 · amendment-created (D10 with D24) · omission in the 6.3 contract · one correct answer · low.**
- Spec 6.3: "The runtime passes events in the companion 6.1 schema, documents as `{path: text}`, instructions as an ordered list"; 7.1: AskUserQuestion "its `result_text` becomes the next `[I_n]` verbatim".
- Evidence: companion 6.1: "The shared renderer, not only the converters, renders PowerShell as Bash and turns an AskUserQuestion result into a `user_instruction` item".
- Consequence: a renderer that derives instructions from the events it is handed, as the companion says it does, and also receives the runtime's list renders the answer twice, or numbers `[I_n]` differently from the runtime's `units.source` (6.5), so R_k quotes point at the wrong `[I_n]`.
- Answer: 6.3 states that USER INSTRUCTIONS renders from the passed list only, and that the events' `new_items` and AskUserQuestion results are not re-derived by the renderer on this path.

**F5 · Part 1 · omission · one correct answer · low.**
- Spec 7.10: "An event with `seq` s waits until `last_seq` = s − 1." The initial value is unstated.
- Evidence: the Mod resets `seq` to 0 in `startSession` (`register.tsx` 226) and increments before building each event (281, 289), so a session's first event is `seq` 1 and numbers are contiguous.
- Consequence: `last_seq` starting anywhere but 0 (or first arrival − 1) either waits 8 s on every session's first event or treats it as a late arrival and skips it.
- Answer: `last_seq` starts at 0.

## Part 2. Cost and latency against report 31

Defend: 1.2 s at 8K and 2.9 s at 32K for 12 rows (C2 miss q=12: 1,221 / 2,907 ms); about 70 ms per diagnostic row above 4,096 tokens (C2 note; (809 − 71)/11 ≈ 67 ms at 8K hit); RF about 0.1 s per unit (C2 2,048 miss q=1: 107 ms; batching through `Server.submit` with CUDA graphs below 4,096 tokens can only make it cheaper); overflow beyond 8 s (C2 8K miss q=20: 1,789 ms per screen; four screens plus a merged state is 8–10 s); $2.27/h (C5). The 10–25 D1 rows figure is a rough middle: at a stock 8K budget the detail budget is about 2.3K tokens after small documents, so 5–10 detailed blocks; at 32K, 25–60.

**F6 · Part 2 · unpriced cost · no design choice · low.**
- Spec 9: "Modal and Dict add about 0.05–0.15 s"; 6.5: "A fresh container rebuilds its in-memory session from the header and the event entries".
- Evidence: report 31 C3 measured about 100 ms of Dict I/O on a skipped event with one or two operations on a tiny record. The design does one header read, one event write and one header write (the header carries every document) per event, and one read per stored event on the first event after a container start.
- Consequence: the per-event band is more likely 0.15–0.3 s; a 100-event session rebuilt after a scaledown restart adds seconds to its first event (which already follows a 23–27 s boot and is late regardless).

## Part 3. Completeness against the ledger

Checked D70–D77 clause by clause and the entries they modify (D17, D23, D25, D29, D71), plus D10, D11, D15, D19.G7, D19.L7, D20, D21.E5/E6/E7, D22, D24, D26, D35, D40 and both CROSS-TRACK-NOTES sections. Every D70 cut is scoped out in section 1 or absent from the mechanics; D71's formulas are 7.8; every D72 clause is in 7.3, 7.6 or 7.7; D73 is 7.9; D74 is 10 and 12; D75 is 6.3 and 13; all D76 bullets are carried (the `drift_rate` window in 7.8 is D76's refined by the D18 fix; B_state = L − 1 against D76's "validated length" is a one-token convention matching the companion's 32,767); D77 is 7.10, 6.1 and 12. D10's `correction_message` field is superseded by CONTRACT section 4's `inject_agent`, so its absence is correct. No omission found.

## Part 4. Spec/task boundary and proportionality

No task material remains after D23; section 12's two demo prompts define the done bar's input and belong. Section 10's reference to removing two asserts in `verify_deploy.py` defines the check's oracle and is acceptable.

Use test run over every mechanism in 6–8 and 10: the ordering gate and its 8 s skip (in-order history; CONTRACT says requests arrive out of order), per-event Dict entries plus header (600 s scaledown across demo pauses), the per-session lock (threads), the duplicate-`event_id` skip (retries), late results (contract), `pending_correction_marks` (the "correction sent at E<m>" line), issue keys and the lifecycle (D72), `selected.json` and the swap (D76), the thirteen checks (each one cheap test of a decided behaviour), the one-line approximation note. Each has a one-sentence use; none needs a further mechanism. Zero findings.

## Register verification

- D1 landed (6.4; `checkpoint.py` 121–128, 241).
- D2 landed with a defect: `kev.api.prepare` does not exist (F1); the probs/answer claims are correct (`serve.py` 147–148, 189; `api.py` 143–159).
- D3 landed (1, 6.1, 7.10, 12); residual boundary race (F2).
- D4 landed (10; `verify_deploy.py` 57–58 are the two asserts).
- D5 landed (7.5, 9; `serve.py` 27–29, 52–87).
- D6 landed (7.2, 7.9; `serve.py` 132–160).
- D7 landed (6.5, 7.10).
- D8 landed (7.6); walked on five sequences, no defect.
- D9 landed (7.10, 7.1); "never fill every slot" is stronger than the mechanism guarantees but the 8 s skip bounds it; initial `last_seq` unstated (F5).
- D10 landed (7.1); seam hazard with companion 6.1's renderer conversion (F4).
- D11 landed (6.5).
- D12 landed (7.4, 7.8, 7.9); notation-table nit on G1.
- D13 landed (7.5, 7.7, 7.9).
- D14 landed (7.6).
- D15 landed (7.7, 8).
- D16 landed (7.3, 8; 6.3 takes B_state).
- D17 landed (7.3, 7.6); residual: E<m> is approximated by the first event received after the response, so an event in flight can start L7 one event early; a wrong "ignored" only keeps the finding open, and the next L7 corrects it. No fix proposed.
- D18 landed (7.1, 7.8).
- D19 landed (7.9).
- D20 landed (6.1, 10, 13).
- D21 landed (6.2).
- D22 landed (9); one cost still unpriced (F6).
- D23 landed (12).
- D24 landed (6.3; CROSS-TRACK-NOTES 17).
- D25 defense holds: `model.py` 18–20 define `SERVE_MAX_STATE`, `SERVE_MAX_BRANCH` (= state + 8,192) and `SERVE_MAX_PACKED`; `admit` (138) calls `encode` with only `max_state` and `max_branch`; the per-row check is line 112; `max_packed` is consulted only by `fits()` (145–149), the training-side check; `SystemOneRequest.questions` has no upper bound (`api.py` 46); rows are chunked by `rows_per_pass` (340), never rejected.

## Three most likely failure points

1. **The shared-module seam (6.3).** The module does not exist yet and two agents build to it; F4 is one concrete way the two sides double-count an instruction while the byte-for-byte state test still passes on fixtures without an AskUserQuestion.
2. **The 8 s boundary (F2).** The one event per burst that crosses 8 s can be lost or delivered twice; a doubled `inject_agent` is the visible failure, and `burst-backlog` cannot reliably catch a few-percent race.
3. **Turn ends that are not answers (F3), and the fallback path.** A user interrupt during the demo can draw a G2 correction. Separately, if stock serves (B_state 8,191), the overflow switch sits near 4.8–5K tokens of instructions plus documents, so section 1's "the demo never reaches the overflow path" holds only if the demo repo's documents stay under that; I could not measure them, so this is a condition to check, not a finding.

## Verdict

Buildable as written on the demo path once F1, F4 and F5 are pinned (each has one correct answer and adds no mechanism). Two owner decisions remain, neither blocking a Phase 1 start:

- **Q1 (F3):** G2 and G5 on every `turn_completed` (D72) or on `answer` turns only (companion 4.2)? If answer-only, 6.1 reads `turn.reason` and names the default when it is absent.
- **Q2 (F2):** keep the 8.0 s lateness threshold and state the boundary race as an exception to "no lost results", or set it inside the backend's wait by the measured overhead.

## Coverage ledger

| File | Lines read | Every line |
|---|---|---|
| `C:\Users\david\.claude\skills\reading-context\SKILL.md` | 1–98 | yes |
| `C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md` | 1–103 | yes (`date` run) |
| `C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md` | 1–29 | yes |
| `C:\Users\david\.claude\skills\design-ethos\SKILL.md` | 1–72 | yes |
| `C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md` | 1–606 | yes |
| `C:\Users\david\.claude\skills\initializing-projects\SKILL.md` | 1–134 | yes |
| `C:\Users\david\.claude\skills\task-file-builder\SKILL.md` | 1–207 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md` | 1–261 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\backend\app.py` | 1–200, 201–394 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\classifier\app.py` | 1–161 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\RUNTIME-SPEC.md` (target) | 1–200, 201–345 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md` | 78–109 (4.2), 144–279 (6.1–6.7), 545–554 (9.5) | every cited section in full; headers located by one grep |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md` | 1–200, 201–400, 401–600, 601–800, 801–1000, 1001–1182 | yes |
| `C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\CROSS-TRACK-NOTES.md` | 1–21 | yes |
| `…\docs\audits\2026-11-07-51-runtime-spec-external-claims-audit.md` | 1–100 | yes |
| `…\docs\audits\2026-11-07-52-runtime-spec-review-opus-audit.md` | 1–200, 201–263 | yes |
| `…\docs\audits\2026-11-07-53-runtime-spec-review-fable-audit.md` | 1–135 | yes |
| `…\docs\research\2026-11-07-31-stock-kev-modal-measurements-and-intent-probe-research.md` (receipts, Part 2) | 1–98 | yes |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\David\classifier\verify_deploy.py` (receipt, D4) | 1–101 | yes |
| scratchpad `kev-verify\repo\kev\serve.py` at `fc4a17e1` (receipts D2, D5, D6, 7.10) | 1–200, 201–358 | yes |
| scratchpad `kev-verify\repo\kev\api.py` (receipts D2, F1) | 1–165 | yes |
| scratchpad `kev-verify\repo\kev\model.py` (receipt D25) | 85–150, 290–349; lines 16–55, 138–149, 294, 337–340, 408 located by grep | partial, targeted |
| scratchpad `kev-verify\repo\kev\checkpoint.py` (receipt D1) | grep-located lines only (16, 60–61, 85–128, 141–146, 241) | partial, grep only |
| `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\mod\hooks\register.tsx` (receipts F3, F5) | 195–235, 270–295, 505–520, 590–605; `seq`/`reason` sites located by grep | partial, targeted |

Shell commands run, all foreground and exited: `date`; `wc -l` over the in-scope files; `ls` of the Kev clone plus `git rev-parse HEAD` (returned `fc4a17e194bca35a48c57211392ec49ea54a94ac`). No background processes; no files written.