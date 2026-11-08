# Round-3 review of `docs/RUNTIME-SPEC.md`

I ran `date` first: Sun Nov 8 00:03 EST 2026. Every mandated file was read in full, in order, in chunks; the coverage ledger is at the end. All shell commands ran in the foreground and exited. I wrote no files.

**Summary.** All 15 register entries landed. The ordering rule now walks clean in every case I tried. I found one real defect, created by the E9 amendment: 7.5's diagnostics trigger contradicts itself. Read literally, it disables the minor-to-significant upgrade that D72 decided. There are two smaller seam defects from E14 and E7. I found no omission against the ledger, no task material and no overdone mechanism. The spec grew from 345 lines in round 2 to 351 while landing 15 fixes, which is tightening rather than accretion.

---

## Part 1. Logic and contract audit

### Walks that found nothing

**Ordering rule (7.10).**
- **Slow head event.** E1 takes about 12 s, and E2 to E4 arrive behind it. The next due seq (1) has arrived, so the 8 s timer never runs. E2 waits for `last_seq` = 1, then runs; each finishes late against `backend_sent_at` and is stored for delivery. This matches the 10 "Ordering" check: a slow predecessor is waited for, never skipped.
- **Exception.** E4 raises, `last_seq` advances to 4, and E5 proceeds. The backend returns its fallback. If the container restarts before the header is rewritten, the next event waits 8 s for the never-resent E4, then skips it. The gate heals itself.
- **Single gap.** `last_seq` = 3, E4 is missing and E5 is waiting. Next due (4) has not arrived and a later event is waiting, so the timer starts. After 8 s, E4 is skipped, `last_seq` = 4, and E5 runs.
- **Double gap.** E4 and E5 are missing and E6 is waiting. After 8 s both are skipped, `last_seq` = 5, and E6 runs.
- **Mixed.** E3 and E6 are waiting while E4 and E5 are missing. On expiry only E4 is skipped (below the lowest waiting seq). E3 runs; when it finishes, a new 8 s timer covers E4 and E5. The rule is deterministic.
- **Late arrival.** The skipped E4 then arrives with `seq` ≤ `last_seq` and a new `event_id`. It does not wait; it is stored, skipped (7.1), and `last_seq` does not decrease.
- **First event.** The Mod resets `seq` to 0 and increments before building each event (`register.tsx` 226, 281, 289). The first event is `seq` 1, which matches "`last_seq` starts at 0".

**One instruction-list path (6.3, 7.1, 7.2), on a session with an AskUserQuestion answer.**
- E1 `session_started` carries I1 plus documents, and RF runs before the skip, per the 5 lifecycle.
- E2 is a Bash call and is classified.
- E3 is AskUserQuestion: stored and skipped, and the builder makes its answer [I2]. That is new instruction text, so RF runs on it.
- E4's state shows [I1] and [I2] once.
- The Mod never emits an AskUserQuestion answer as a `new_items` entry; only `prompt.submit` creates `user_instruction` items (`register.tsx` 126–146). So the builder cannot double-number an answer from the Mod side.
- Late arrivals do not renumber [I_n] when the builder is fed `event_ids` in processing order, which is what 6.5 stores and what companion 6.4's "arrival order" means.

**Turn ends (7.1, 7.8).**

| Case | What runs | `drift` |
|---|---|---|
| Answer, with text | the every-event set + G2 per R_k + G5 | 1 − p(G1) |
| Aborted, with text | the every-event set | 1 − p(G1) |
| Answer, empty text | G2 + G5 only | null, and excluded from `drift_rate` |
| Aborted, empty text | skipped | — |
| Reason missing | treated as `answer` | — |

The Mod sends `event.turn = {reason, …}` (`register.tsx` 204). This matches companion 4.2, D72 and D76.

**B_state (7.3, 7.11).**
- Before the gate, L = 8,192, so B_state = 8,191.
- The overflow switch is then 0.85 × 8,191 minus LATEST EVENT (up to about 2,000 tokens) and the always-present sections. That is about 4.7K to 6.9K tokens of instructions plus documents, so section 1's "roughly 5K" is the conservative end.
- After the gate, the service is redeployed with the gate's L. The screen state stays at 8,192 tokens, under Kev's `SERVE_MAX_STATE` of 65,536 (`model.py` 18).

**Diagnostics on the overflow path (7.5, 7.9).** Every diagnostic runs on the merged state, and the 7.5 and 7.9 texts agree.

**Fire set and Pane fields (7.4, 7.8).** `risk` ≥ 0.5 holds exactly when a question other than G1 fired. G1 shows only as drift. This matches D71.

### Findings

**F1. 7.5's diagnostics trigger contradicts itself, and read literally it disables D72's upgrade path.**
- **Part / kind:** 1 · amendment-created (E9) · error.
- **Spec text:**
  - 7.5: "They run only when some fired row, under 7.6, would open a new finding or upgrade a minor one; a firing that maps to an open or dismissed finding needs no diagnostics."
  - 7.6, rule 1: "if it is open, minor, and this event's severity is significant or serious, it is upgraded".
  - 7.7: "D5 is asked once per event".
- **Evidence:**
  - Whether a firing "would upgrade a minor one" depends on "this event's severity", which is D5's answer. D5 is itself a diagnostic in 7.5's second request, so the trigger depends on the output it gates.
  - A minor finding is an *open* finding, so the second clause tells the builder to skip diagnostics for exactly that case.
  - Action-question minor findings close as soon as their notice is sent (7.6), so the upgrade path exists only for run questions.
  - D72 decided: "if its question fires again while it is open at significant or serious, the correction goes out."
- **Consequence:** under a literal build, a minor run finding (L1, G1, L5 and so on) is upgraded only when some other question opens a new finding on the same event. D5 is otherwise never asked, so a drift that worsens from minor to significant never sends its correction. Stock Kev's G1 bias (report 31: 0.02 yes-rate on "still pursuing") makes persistent minor G1 findings likely on the stock path.
- **Answer (one correct):** diagnostics run when a fired row maps to no finding, or to an open *minor* finding (D5 decides the upgrade). A firing that maps to an open non-minor finding or a dismissed finding needs none. This adds no mechanism; it restores the D72 behaviour.

**F2. Phase 1 claims a check whose pass condition needs a phase-2 component.**
- **Part / kind:** 1 · amendment-created (E14 with E5) · error, low.
- **Spec text:**
  - 13, phase 1 "Clears": "…; skipped events; …", with "Depends on: none".
  - 10, "Skipped events": "…; an AskUserQuestion answer appears exactly once, as the next `[I_n]`."
  - 13, phase 2 builds "the shared module wired in: instruction list, …".
  - 6.5: "Instructions are not stored separately; the instruction-list builder (6.3) derives them from the stored events."
- **Evidence:**
  - The `[I_n]` clause can only be checked through the instruction-list builder, a shared-module export (6.3) that enters in phase 2.
  - Phase 1 is meant to need nothing from the training build.
- **Consequence:** phase 1 cannot close the "skipped events" check as written. An agent working the phase ladder either stalls or writes its own interim builder, which is the second instruction path E5 removed.
- **Answer (one correct):** move the `[I_n]` clause, or the whole AskUserQuestion part of the check, to phase 2's "Clears", for example under "shared renderer".

**F3. Section 8 still states the E7 value for stock Kev only.**
- **Part / kind:** 1 · amendment-created (E7) · error, nit.
- **Spec text:**
  - 8: "State budget | B_state = L − 1, L the gate's validated length (8,192 for stock Kev)".
  - 7.3: "for any served model without a gate result yet, stock Kev included, L = 8,192".
- **Evidence:** the E7 amendment widened the rule in 7.3, but the sizing table kept the old narrower wording.
- **Consequence:** a reader who takes the value from the sizing table can serve a trained model awaiting its gate at 32,768. 7.3 governs, so this is only a seam inconsistency.
- **Answer (one correct):** in section 8, write "(8,192 for any served model without a gate result)".

### Considered and not raised
- **L7 on an empty-text answer turn end.** 7.1's "only G2 and G5" could be read as excluding L7, which 7.3 asks "from the first classified event". Either reading is harmless: L7 runs on the next event.
- **Where correction messages are stored.** 6.5's header lists no store for correction messages, although 7.7 says "stored once and linked". Embedding the text in each finding record persists it, so a container rebuild loses nothing.
- **The ledger's minor-finding closing rule.** 7.6 also closes a minor run finding on a new instruction, which D72 states only for dismissed findings. This applies D72's own "a new instruction starts a new issue", and the cost is at most one extra notice.
- **Choice of severity names in D5.** 7.5 fills D5's «short names» with every fired question, including ones mapped to suppressed findings. This matches how training labels D5 on a flagged record, so it is train-equals-runtime and not a defect.

---

## Part 2. Cost and latency (section 9 against report 31)

| Claim in section 9 | Report 31 | Verdict |
|---|---|---|
| 1.2 s at 8K and 2.9 s at 32K, 12 rows, cache miss | C2: 1,221 ms and 2,907 ms | Holds (model time only) |
| Modal and Dict add 0.15–0.3 s | C3: about 100 ms of Dict I/O on a skipped event; round trip minus `classify_ms` = 56 ms at p50 | Holds; the design adds a header read and two writes |
| About 70 ms per diagnostic row above 4,096 tokens | C2 note (L43) | Holds |
| 10–25 D1 rows, 0.7–1.8 s | 70 ms × rows | Arithmetic holds. At L = 8,192 the detail budget (1.2K–3.3K tokens) gives fewer rows, and states under 4,096 tokens use cheaper graphed rows, so this is an upper bound |
| L7 row adds 0.3–0.5 s | Labelled an estimate from long-row prefill (an 8K miss costs about 400 ms of state prefill) | Labelled honestly |
| RF about 0.1 s per unit | C2: 107 ms for one row on a 2K miss | An upper bound, since RF windows are short and batched |
| Overflow beyond 8 s | C2: 1,789 ms per 8K screen state at q = 20 | Holds for four or more screen states. At L = 8,192 the documents are around 5–7K tokens, which fit one or two screens, so it may finish under 8 s. That is an informational overstatement, not raised |
| $2.27/h | C5 | Holds |

No findings.

---

## Part 3. Completeness against the ledger

I checked D70–D77 clause by clause, plus the entries they modify (D13, D17, D23, D25, D29, D71), D10, D11, D19.G7, D19.L7, D20, D21.E1/E2/E8, D21.E5/E6/E7/E9, D21.U, D22, D24, D26, D40, D47, and both parts of CROSS-TRACK-NOTES.
- Every D76 bullet is carried in 6.4–7.11.
- D72 is carried in 7.6 and 7.7. It has been updated for E6, and F1 restores its upgrade clause.
- D73 is carried in 7.9. "Drop the lowest-scoring until it fits" faithfully implements "highest-scoring first".
- D74 is carried in sections 10 and 12, and D77 in 1, 6.1, 7.10 and 11.
- D13's 08:00 rule matches section 11.

**No omission findings.** One stale clause sits in the ledger itself, not the spec: D10's "the Modal Dict is dropped" is superseded by D76's Dict store.

---

## Part 4. Spec/task boundary and proportionality

I ran the use test over the mechanisms the amendments added or changed:
- the `last_seq` rule and its multi-gap skip;
- per-event Dict keys;
- the single instruction-list call;
- reading `turn.reason`;
- L = 8,192 before the gate, with a redeploy when the gate reports;
- diagnostics gating;
- the shared line formatter;
- the two stated late-result exceptions;
- the reordered phases.

Each has a concrete use for this build, none guarantees more than a reasonable engineer would ask for, and none needs a further mechanism. The fix for F1 removes a contradiction and adds nothing. Sections 12 and 13 hold dependencies and the done bar, not task material.

**Zero findings.**

---

## Register verification

| Entry | Verdict |
|---|---|
| E1 | Landed (6.4). Verified: `to_record` returns `(rec, meta)` (`api.py` 102–117); `probs` returns `(ps, stats)` (`serve.py` 147–148, 189); noul options are `[no, yes]` (`api.py` 110). No new defect. |
| E2 | Landed (6.4). Score keys `"0"`, `"1"`, `"2"` match `question_keys` (`api.py` 94–99), and the missing-id fallback is stated. No defect. |
| E3 | Landed (7.10). Walked on a slow head, an exception, single and double gaps, and a late arrival. Clean. |
| E4 | Landed (6.5, 7.1). No defect. |
| E5 | Landed (6.3, 6.5, 7.1). The Mod emits no duplicate answer items. Its interaction with phasing creates F2. |
| E6 | Landed (6.1, 7.1, 10); D72 is updated and the Mod sends `turn.reason`. No defect. |
| E7 | Landed (7.3), but section 8 was not updated (F3). |
| E8 | Landed (1). The arithmetic gives 4.7K–6.9K, so "roughly 5K" is the conservative end. |
| E9 | Landed (7.5, 7.6) with a defect: the trigger is circular and contradicts itself for minor upgrades (F1). |
| E10 | Landed (6.3, 7.6). No defect. |
| E11 | Landed (1, 11). No defect. |
| E12 | Landed (9, 7.2, 7.9). The figures check against report 31. |
| E13 | Landed (11), matching D13. |
| E14 | Landed (13), with F2. |
| E15 | Landed (4). No defect. |

## The three most likely failure points

1. **The shared-module seam between two parallel Codex builders (6.3).** The runtime depends on five exports the training agent must add on the strength of CROSS-TRACK-NOTES. Companion 6.1 still says the renderer itself converts AskUserQuestion results. The byte-for-byte check runs the same module on both sides, so only the "`[I_n]` exactly once" clause can catch a mismatch.
2. **The 8K serving path before the gate reports.** The Mod sends `README.md` as a project document at every session start, alongside `CLAUDE.md` and `AGENTS.md` (`register.tsx` 236–244). That pushes the demo repo toward the overflow switch at about 4.7–6.9K tokens. RF also runs on every README sentence at session start, which delays the first scored events into late results.
3. **Persistent minor run findings under stock Kev's G1 bias.** With F1 unfixed, a drift that worsens never escalates to a correction. With F1 fixed, diagnostics run on every event while the minor finding stays open, adding 0.7–1.8 s per event, which pushes bursts into late delivery.

## Verdict

**Implementation-ready once F1 is fixed.**
- **F1 is the one blocking item.** It has one correct answer, but a literal build silently disables a decided behaviour (D72's upgrade), and an attentive builder would have to stop and ask about the contradiction.
- **F2 and F3 are non-blocking.** Each is a one-line edit with one correct answer.

No owner design choice is outstanding.

---

## Coverage ledger

| File | Lines read | Every line |
|---|---|---|
| `~/.claude/skills/reading-context/SKILL.md` | 1–98 | yes |
| `~/.claude/skills/out-of-cutoff/SKILL.md` | 1–103 (`date` run) | yes |
| `~/.claude/skills/receipts-before-claims/SKILL.md` | 1–29 | yes |
| `~/.claude/skills/design-ethos/SKILL.md` | 1–72 | yes |
| `…/design-ethos/references/gold-standard-spec-template.md` | 1–606 | yes |
| `~/.claude/skills/initializing-projects/SKILL.md` | 1–134 | yes |
| `~/.claude/skills/task-file-builder/SKILL.md` | 1–207 | yes |
| `HackBU-NoahDavid/CONTRACT.md` | 1–262 | yes |
| `HackBU-NoahDavid/Noah/backend/app.py` | 1–395 | yes |
| `HackBU-NoahDavid/David/classifier/app.py` | 1–162 | yes |
| `docs/RUNTIME-SPEC.md` (target) | 1–120, 120–239, 240–351 | yes |
| `docs/TRAINING-SPEC.md` | 78–107 (4.2 with its closing paragraph), 144–278 (6.1–6.7), 547–554 (9.5); headings located by one grep | every mandated section in full |
| `DESIGN-DECISIONS.md` | 1–200, 200–399, 400–599, 600–799, 800–999, 1000–1185 | yes |
| `docs/CROSS-TRACK-NOTES.md` | 1–30 | yes |
| Audit `-54-…external-claims` | 1–98 | yes |
| Audit `-55-…opus` | 1–304 | yes |
| Audit `-56-…fable` | 1–139 | yes |
| Report 31 (the source section 9 cites) | 1–98 | yes |
| Kev clone at `fc4a17e1` (claim checks only) | `serve.py` 1–215 and 223–225; `api.py` 1–150; `model.py` 18–28, 87–99, 130–143, plus grep hits; `cuda_graphs.py` and `checkpoint.py` grep hits | targeted, by design |
| `Noah/mod/hooks/register.tsx` (claim checks only) | 115–378 | targeted, by design |

Shell commands, all foreground and exited: `date`; `wc -l` on the in-scope documents; `git log -1` and `ls` in the Kev clone (HEAD is `fc4a17e194bca35a48c57211392ec49ea54a94ac`); greps in the Kev clone and in the Mod.