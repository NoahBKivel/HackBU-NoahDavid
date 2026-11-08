# Final full-scope review: `docs/RUNTIME-SPEC.md`

`date`: Sun Nov 8 00:20:48 EST 2026. I read every mandated file in full, in order, in chunks (coverage ledger at the end). I checked Kev's source and the Mod's code only in targeted ranges. All shell commands ran in the foreground and exited. I wrote no files.

**Summary.** All seven register entries landed. I found two real issues, each with one correct answer and neither needing a new mechanism:
- **R1:** 7.6's "new user instruction" exit fires only when the instruction rides on a classified event. The Mod often attaches it to a skipped one.
- **R2:** section 5's lifecycle still says "diagnostics if anything fired" and puts finding updates after diagnostics. That disagrees with the G1 fix in 7.5 and with 7.6's "applied first".

I found no omissions against the ledger, no task material and no mechanism that fails the owner's rule. The spec is 353 lines, against 351 in round 3, after landing seven fixes.

---

## Part 1. Logic and contract audit

**Walks that found nothing:**
- **Ordering (7.10):** slow head event, an exception, single and double gaps, a late arrival.
- **Seq reset within a session:** cannot happen. The Mod resets `seq` only when the session id changes (`register.tsx` 88–92, 220–226).
- **Turn ends (7.1 and 7.3):** answer or aborted, with and without text, and a missing reason.
- **Findings walks (7.6):** an action finding, then a new key on a later action; a run finding that is dismissed, refires, then closes; a minor finding upgraded; one message covering an action finding and a run finding.
- **Pane fields (7.8) against D71.**
- **6.2 against Noah's `Result` model:** every field validates under `extra="allow"`, and `check_late_results` validates each late entry.
- **6.4 against Kev:**
  - `LoadOptions.temperature` and `ck.meta.temperature` exist (`checkpoint.py` 105, 125, 241).
  - `Server.submit` and `Server.probs` return `(probs, stats)` (`serve.py` 132–148).
  - Admission limits only the state and each row (`model.py` 132–138), so 7.3's "no limit on the rows of one request" holds.
- **6.1:** `result_text` is what the agent sees (`ran.text`), and `full_output` is nested in `action.result` (`register.tsx` 305–318). Ignoring `full_output` matches training.

### R1. A new instruction that rides on a skipped event never closes minor or dismissed run findings
- **Part / kind:** 1 · error (ledger transcription gap) · one correct answer · medium-low.
- **Spec text, 7.6 (lines 223–225):** "**Status changes, applied first on each classified event.** … A run-question finding that is minor or `dismissed` closes on the first classified event where its question is asked and does not fire, or when the event brings a new user instruction."
- **Spec text, 7.1:** read-only tools are "stored; skipped". AskUserQuestion is "stored; skipped; the instruction-list builder (6.3) makes its answer the next `[I_n]`".
- **Evidence:**
  - The Mod puts each prompt on the next event it builds, whatever that event's type:
    - `prompt.submit` appends the item to `pending` (`register.tsx` 140).
    - `baseEvent` drains `pending` into `new_items` (282–283, 292).
    - `toolEvent` calls `baseEvent` for every main-agent tool call, read-only ones included (164–186, 299–301).
  - So a prompt lands on a Read, Grep or Glob event whenever that is the agent's first call after the prompt.
  - An AskUserQuestion answer always arrives on its own skipped event.
  - D72: "ends when the question stops firing or the user gives a new instruction". D21.E6 records answers "as user instructions".
- **Consequence:**
  - Built literally, a dismissed or minor run finding (G1, L1, L4, L5…) survives the user's new request whenever that request arrived on a skipped event. The question stays silenced into the next task.
  - On the stock path, G1 fires on most events (report 31: "still pursuing" yes-rate 0.02), so a dismissed G1 finding can stay silenced for the rest of the session.
  - No section 10 check exercises this exit.
- **Answer (one correct):** the closure applies on the first classified event after any event that added an `[I_n]` (a prompt or an AskUserQuestion answer) since the previous classified event.

### R2. Section 5's lifecycle contradicts 7.5's trigger and leaves the order of status changes and the trigger open
- **Part / kind:** 1 · amendment-created (the G1 fix left section 5 stale) · error · one correct answer · low.
- **Spec text, section 5 (line 99):** "… calibrate → fire → diagnostics if anything fired → update findings → compose actions …"
- **Spec text, 7.5 (line 211):** "They run when some fired row has no `open` or `dismissed` finding with its issue key (7.6), or has an `open` finding that is minor".
- **Spec text, 7.6:** "Status changes, applied first on each classified event". Rule 2: "a new finding opens with key K and this event's severity."
- **Evidence:**
  - 7.5's trigger reads finding status.
  - This event's own L7 answers come from the first request, and R1's new-instruction rule can both close a finding before the per-row rules run.
  - Section 5 puts all finding updates after diagnostics, and its trigger is "anything fired".
- **Consequence:**
  - Take an implementer who follows section 5's order and uses 7.5's trigger.
  - Case: a run finding whose correction went out is closed this event by L7 "genuinely fixed" while its question fires again. This is likely for G1 on stock.
  - The trigger sees an open non-minor finding, so D5 is not asked.
  - Rule 2 then opens a new finding with "this event's severity", which does not exist.
  - The same happens when a dismissed finding closes on a new instruction while its question fires.
- **Answer (one correct):**
  - The order is: apply 7.6's status changes, then evaluate 7.5's trigger, then run diagnostics, then apply rules 1–2.
  - Section 5's line becomes "… fire → status changes → diagnostics when 7.5's trigger holds → open or upgrade findings → …".

### Considered and not raised
- **L7 trimming constant.** Companion 6.4 states the row limit in `max_state`, not B_state, so 7.3's B_state substitution leaves it at 32,768 + 640. That is consistent with section 9's "carries its whole correction message".
- **"Correction sent at E<m>" for an event that arrived before the carrying response.** The line cannot be written without m, and L7 starts "after the correction reached the agent (7.6)", which reads as after m. There is one natural reading.
- **The merged-state fit check.** 7.9 step 4 says "If the screen renderer reports they do not fit". The training task.md freezes `render_state(...) -> (text, detailed_seqs, fits)` and `render_screen(...) -> (text, fits)` (Step 2, lines 225–226). The merged state is a normal state, so `render_state`'s `fits` answers it. There is one obvious answer.
- **Where correction messages are stored.** 6.5's header has no field for them, although 7.7 says "stored once". Opus raised this in round 3; storing the text with each finding is harmless.
- **Late arrivals that carry an instruction.** Ordering by `seq` renumbers later `[I_n]`. This follows from seq order and matches training.
- **CONTRACT section 4 still says "takes up to 4 calls at a time".** 7.10 sets 32. Concurrency is not an interface field; it is a doc update on David's side.

## Part 2. Cost and latency (section 9 against report 31)

| Claim | Report 31 | Verdict |
|---|---|---|
| 1.2 s at 8K, 2.9 s at 32K, 12 rows, cache miss | C2: 1,221 and 2,907 ms | Holds |
| Modal and Dict add 0.15–0.3 s | C3: about 100 ms of Dict I/O on a skipped event; round trip minus `classify_ms` is 56 ms at p50 | Holds. "Reads the header" overstates a little, because the store is in memory and only writes happen per event |
| About 70 ms per diagnostic row above 4,096 tokens | C2 note | Holds. "10–25 D1 rows" is an upper bound at L = 8,192 |
| L7 row 0.3–0.5 s (G6 basis) | q=1 miss: 107/2,048, 470/8,192, 942/16,384 and 2,056/32,768 give 0.052–0.063 ms per token; 6–7K tokens give 0.36–0.44 s | Holds; the basis is now cited correctly |
| RF about 0.1 s per unit | 107 ms is a 2,048-token miss; RF windows are about 100–200 tokens, graphed and batched | Upper bound; no build consequence |
| Overflow beyond 8 s | 1,789 ms per 8K screen at q=20 | Holds for 4 or more screens; near the switch it may finish faster. Informational |
| $2.27/h | C5 | Holds |

No findings.

## Part 3. Completeness against the ledger

I checked D70–D77 clause by clause, plus the entries they modify or rest on (D10, D11, D13, D17, D19.G7/L7/D1–D5/P, D20, D21.*, D22–D26, D29, D29.W, D35, D40, D47) and every item in CROSS-TRACK-NOTES:
- **D70:** every cut appears in section 1's out list or is absent from the mechanics.
- **D71:** carried in 7.8 and 6.2.
- **D72:** carried in 7.1, 7.3, 7.6 and 7.7; R1 is the one transcription gap.
- **D73:** carried in 7.9.
- **D74:** carried in sections 10 and 12.
- **D75:** carried in 6.3 and section 13.
- **D76:** every bullet is carried.
- **D77:** carried in sections 1, 6.1, 7.10, 11 and 12.

**No omissions.**

**Ledger note (not a spec finding):** D10 still lists `correction_message` among the "Result fields Noah relies on". CONTRACT section 4 has no such field, because the correction rides in `inject_agent`.

## Part 4. Spec/task boundary and proportionality

I ran the use test over every mechanism in sections 6–8, 10 and 13:
- the ordering gate and its 8 s skip;
- `last_seq` in the header;
- per-event Dict entries;
- the per-session lock;
- the duplicate-`event_id` skip (standard idempotency on a keyed store);
- `pending_correction_marks` (needed for the shared "correction sent at" line);
- `backend_sent_at`;
- issue keys by question kind;
- the diagnostics trigger;
- the overflow screen and its clean raise;
- `selected.json` and the swap;
- the null-calibration fallback;
- the 16 checks in section 10.

Each has a one-sentence use in this build, none guarantees more than was asked, and none needs a further mechanism. Sections 12 and 13 hold dependencies and phasing, not task material. **Zero findings.**

## Register verification

| Entry | Verdict |
|---|---|
| G1 | Landed (7.5). The trigger is now a predicate on finding status, matching D72 and D76. It left section 5's summary stale, which is R2. |
| G2 | Landed (7.3, line 201). Agrees with 7.1, companion 4.2 and D72. No new defect. |
| G3 | Landed (6.3, line 147). No new defect; renumbering on a late instruction follows from seq order and matches training. |
| G4 | Landed. "Instruction numbering" clears in phase 2; "Minor upgrade" clears in phase 1 and can be tested on fixtures. No new defect. |
| G5 | Landed (section 8). Matches 7.3. |
| G6 | Landed (section 9). The arithmetic checks against report 31's q=1 column. |
| G7 | Landed (header, 3, 6.3, 6.4, 7.11). The paths exist. Training task.md Step 9 writes `selected/`, `calibration.json` and `long_context.json` (8,192 until the gate reports) to `intent-monitor-training`, and leaves `intent-monitor-model` alone. No new defect. |

## The three most likely failure points

1. **The shared-module seam.** Phase 2 depends on the training agent passing its Step 2 gate. The frozen interface matches 6.3 except for where the merged-state fit check comes from (see "considered").
2. **G1 on the stock path.** G1 fires on nearly every event under stock Kev. With R1 unfixed, a dismissed G1 finding stays silenced across user turns. With a minor G1 finding open, diagnostics run on every event, adding 0.7–1.8 s and pushing bursts into late delivery.
3. **Serving at 8K before the gate reports.** The Mod sends README.md with every session start (`register.tsx` 236–244), so RF judges every README sentence before the first scored event. The overflow switch also sits near 5K tokens of instructions plus documents.

## Verdict

**Implementation-ready. No blocking question is open, and nothing needs an owner decision.** R1 and R2 are one-sentence edits with one correct answer each. R1 should land before the task.md: a literal build silently departs from D72, and no check would catch it. R2 is a seam fix to section 5's summary line.

---

## Coverage ledger

| File | Lines read | Every line |
|---|---|---|
| `reading-context/SKILL.md` | 1–98 | yes |
| `out-of-cutoff/SKILL.md` | 1–103 (`date` run) | yes |
| `receipts-before-claims/SKILL.md` | 1–29 | yes |
| `design-ethos/SKILL.md` | 1–72 | yes |
| `design-ethos/references/gold-standard-spec-template.md` | 1–200, 200–409, 410–606 | yes |
| `initializing-projects/SKILL.md` | 1–134 | yes |
| `task-file-builder/SKILL.md` | 1–207 | yes |
| `HackBU-NoahDavid/CONTRACT.md` | 1–262 | yes |
| `Noah/backend/app.py` | 1–200, 200–395 | yes |
| `David/classifier/app.py` | 1–162 | yes |
| `docs/RUNTIME-SPEC.md` (target) | 1–120, 120–239, 240–353 | yes |
| `David/docs/TRAINING-SPEC.md` | 56–110 (4.1–4.2 with its closing paragraph), 142–281 (6.1–6.7), 547–558 (9.5); headings located by one grep | every mandated section in full |
| `DESIGN-DECISIONS.md` | 1–150, 150–279, 280–409, 410–529, 530–639, 640–739, 740–839, 840–929, 930–1019, 1020–1185 | yes |
| `docs/CROSS-TRACK-NOTES.md` | 1–36 | yes |
| Audit `-57-…opus` | 1–207 | yes |
| Audit `-58-…fable` | 1–155 | yes |
| Report 31 | 1–99 | yes |
| Kev clone at `fc4a17e1` | `checkpoint.py` 85–110 plus grep; `serve.py` 128–150 plus grep; `model.py` 128–143 plus grep | targeted, by design |
| `Noah/mod/hooks/register.tsx` | 20–343 (four ranges) plus grep | targeted, for R1 and the seq claims |
| `David/training/task.md` | 222–233 plus one grep | targeted, for G7 and the seam |

Shell commands, all foreground and exited: `date` and `wc`; `git log` and greps in the Kev clone; `ls` and grep in the Mod; `sed` in the Kev clone.