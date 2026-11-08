# Runtime spec review: `docs/RUNTIME-SPEC.md`

Date: 2026-11-07 (from `date`). I read the spec as a peer reviewer. All issues below are about correctness or completeness. None of them asks to add or cut scope.

## Coverage ledger

| File | Lines read |
|---|---|
| `~/.claude/skills/reading-context/SKILL.md` | 1–98 (all) |
| `~/.claude/skills/out-of-cutoff/SKILL.md` | 1–103 (all) |
| `~/.claude/skills/receipts-before-claims/SKILL.md` | 1–29 (all) |
| `~/.claude/skills/design-ethos/SKILL.md` | 1–72 (all) |
| `~/.claude/skills/design-ethos/references/gold-standard-spec-template.md` | 1–199, 200–399, 400–605 (all) |
| `~/.claude/skills/initializing-projects/SKILL.md` | 1–134 (all) |
| `~/.claude/skills/task-file-builder/SKILL.md` | 1–207 (all) |
| `HackBU-NoahDavid/CONTRACT.md` | 1–262 (all) |
| `HackBU-NoahDavid/Noah/backend/app.py` | 1–199, 200–394 (all) |
| `HackBU-NoahDavid/David/classifier/app.py` | 1–162 (all) |
| `classifier-for-metagaming/docs/RUNTIME-SPEC.md` (the target) | 1–169, 170–326 (all) |
| `docs/TRAINING-SPEC.md` | 56–109 (4.1 and 4.2), 142–278 (6.1–6.7), 544–553 (9.5); every cited section in full |
| `DESIGN-DECISIONS.md` | 1–200, 200–399, 400–599, 600–799, 800–999, 1000–1165 (all) |
| `docs/CROSS-TRACK-NOTES.md` | 1–18 (all) |
| Report 31 (`docs/research/2026-11-07-31-…measurements…md`, cited by section 9) | 1–99 (all) |
| `Noah/mod/hooks/register.tsx` (checked to verify two findings) | 100–229 read; `seq` and AskUserQuestion located by grep in that file and the sample events |

Every line of every mandated file was read. I could not find a local Kev source checkout, so I could not check whether Kev's serving path enforces a packed-row limit when all rows go in one request (7.3). I am not reporting that as a finding.

---

## Findings

### R1. A correct dismissal cannot stop a finding from reopening
- **Part 1 · error · needs a design choice (blocking).**
- **Spec text.**
  - 7.6 rule 2: "A new finding opens only if this event's cited events include one that finding did not cite; otherwise nothing."
  - 7.5: "D1/D3 cites every event with p ≥ 0.5; if none, LATEST EVENT is cited."
- **Evidence (a worked sequence).**
  1. At E30, G1 fires. D1 cites {E28, E29, E30}. The finding F1 is significant, so a correction goes out and lands on E31.
  2. At E32, L7 answers `dismissed correctly`, so F1 closes. G1 is still below 0.5, because the run looks the same.
  3. At E32 or E33, G1 fires again. That event's LATEST EVENT is new: D1 either cites it, or the fallback cites it anyway. It is not in {E28, E29, E30}, so rule 2 opens F2 and sends a new correction.
  4. The cycle is correction → dismissal → correction, every two or three events.
- **Ledger.**
  - D72 states the rule's purpose: "without the repeat rule the agent would get a correction, and the user a notice, on every tool call."
  - The runtime emergent-interactions table names exactly this case: "Drift finding closed as 'dismissed correctly' × G1 still firing → The same drift finding reopens on the next event."
  - The rule matches D72's wording but cannot do what D72 says it is for.
- **Consequence.**
  - Repeated false corrections on persistent questions (G1, L1). This is the failure `demo-no-false-correction` guards against.
  - `no-reopen-after-dismissal` ("citing the same events") passes only on a contrived fixture, so it cannot catch this.
  - The spec also does not say whether closings happen before or after an event's firings are processed.
- **Answer.** The owner must define what "the same issue" means.

### R2. The "No lost results" guarantee is false, and a lost correction silences its question
- **Part 1 · error / unsupported claim · the spec wording has one correct fix; adopting `backend_sent_at` is the owner's already-deferred choice.**
- **Spec text.** Section 1: "A result that finishes after the backend's 8 s wait is delivered once, on the session's next response."
- **The spec contradicts itself.**
  - Section 12: "the first result after a cold start is lost until classify measures lateness from the backend's send time."
  - 7.10 times lateness from "the method started", with `max_inputs=4`.
- **Evidence.**
  - Report 31 §1: a cold session's first result is lost.
  - When more than 4 inputs are outstanding (for example, gate-waiting reads during a burst), the extra ones queue outside the method. Their queue time is not counted, so they can return "on time" after the backend's 8 s wait has already ended.
  - D29 also accepts that the session's final late result has no response to ride on.
- **Consequence.**
  - The runtime records the correction as sent, so the finding stays open.
  - L7 then asks about a correction the agent never saw.
  - Rule 1 ("Otherwise nothing is sent") suppresses that question's corrections for the rest of the session.
  - If the demo deletion lands in the ~23–27 s after a cold prompt (C1 boot time), the catch can be lost and then silenced.
- **Answer.** Narrow the guarantee to what is actually delivered (one correct answer). Whether to adopt `backend_sent_at` stays with the owner.

### R3. The ordering wait does not separate a missing event from a slow one
- **Part 1 · error · one correct answer for the timer; what a late event's `new_items` do needs a design choice.**
- **Spec text.**
  - 7.10: "an event with `seq` s is released when `last_seq` = s − 1, or after waiting 8 s for the missing one (it is then skipped)."
  - 7.1: a duplicate "returns a skipped result; nothing stored".
- **Evidence.**
  - `last_seq` means *processed*.
  - Under burst-backlog, which the ledger expects ("An agent faster than one event per 1.2 s builds a queue"), an event waits more than 8 s behind predecessors that have arrived but not finished.
  - Read literally, the gate would then release s while s−1 still runs, so both write the same session record. When s−1 finally runs it is a "duplicate": it gets skipped and its `new_items` are dropped.
  - The Mod puts each new user prompt on exactly one event (`register.tsx` 117–132, 271–283), so dropping `new_items` drops an instruction for good.
  - D76's intent is "so one dropped event cannot stall a session". That means an event that never arrived.
- **Consequence.**
  - Unscored events, lost user instructions, and concurrent mutation of the session record.
  - `burst-backlog` can still pass, because skipped results are still delivered.
- **Answer.**
  - The 8 s timer should run only while s−1 has not arrived (one correct answer).
  - Whether a late arrival's `new_items` are still recorded is the owner's choice.

### R4. AskUserQuestion answers never reach USER INSTRUCTIONS
- **Part 1 and Part 3 · omission · needs a small choice: the text form must match the training converters.**
- **Ledger (D21.E6, verbatim):** "**TodoWrite and ExitPlanMode results are classified. AskUserQuestion answers are recorded as user instructions**: they update the requirements and re-run D20's filter, unclassified. *Partner-confirmed*."
- **Spec text.** 7.1 marks AskUserQuestion only "stored; skipped". Answers become `[I_n]` only "each `user_instruction`" in `new_items`.
- **Evidence.**
  - The Mod creates `user_instruction` only in `prompt.submit` (`register.tsx` 117–132).
  - There is no AskUserQuestion handling anywhere under `Noah/`, so the answer arrives only in that tool's `result_text`.
  - Training renders the answer as an instruction: companion 6.4 "[I2] <later prompt or AskUserQuestion answer, verbatim>", and 6.1 "AskUserQuestion answers become `user_instruction` items."
- **Consequence.**
  - Training and runtime diverge.
  - M7 ("choices it checked or asked about are no") is judged without the user's answer.
  - RF never sees the answer, so it never becomes an R_k.
- **Where it belongs.** Section 7.1, as a rule that converts the answer into the next `[I_n]`, in the converters' exact form.

### R5. Trimming fields at storage changes what the renderer outputs
- **Part 1 · error · needs a design choice.**
- **Spec text.** 7.1: "`result_text`, patches and plan text keep their head and tail up to 16,000 characters each."
- **Evidence.** The renderer derives several outputs from the full field (companion 6.4):
  - the "[cut N tokens]" count;
  - `files: … (edit, +3/-12)`;
  - the one-liner "(+12/-3)".
  - A trimmed patch gives wrong +/− counts.
  - A trimmed field gives the wrong N.
  - Trimming a structured patch by characters can make it unparseable.
- **Consequence.**
  - The "Train equals runtime" guarantee breaks on any event with a field over 16,000 characters, for example a Write of a new file or verbose pytest output.
  - The byte-for-byte renderer test only passes if it is fed the already-trimmed events.
- **Answer.** The owner chooses what is stored so that derived fields stay exact. Note that the cap itself (D76) is not in question.

### R6. The list of questions that can fire is incomplete, so `flagged` and `risk` can disagree
- **Part 1 · error · one correct answer.**
- **Spec text.**
  - Section 4 says "fired" means "a problem score ≥ 0.5" and gives every yes/no question a problem score.
  - 7.4 excludes only "L7 and RF never fire".
  - 7.8 builds `risk` excluding "G1, L7, RF and the diagnostic questions", and says `flagged` is "equivalently, a question other than G1 fired".
- **Evidence.**
  - **Overflow case.** SCR is yes/no and not excluded. A relevant section with SCR = 0.8 therefore counts as fired. Under 7.6 it opens a finding. Under 7.8 it gives `risk` 0.8 and `flagged` true, a red Pane point with no problem behind it. This contradicts 7.9.3 and D73, where only an M8 yes is a finding.
  - **Normal case.** On a G1-only event, the diagnostics still run. A D1 row at 0.7 "fires" by the definition, so `flagged` is true by 7.8's second clause but false by its first clause, because diagnostics are excluded from `risk`.
- **Answer (one correct).** The questions that can fire are the every-event set (G1 inverted), G2, G5 and M8. SCR, RF, L7, D1, D2 and D5 never fire.

### R7. M8 findings have no short name, position, correction or severity path
- **Part 1 · omission · needs a design choice (blocks Phase 3 only; the demo never reaches overflow).**
- **Spec text.**
  - 7.9.3: "An M8 fire is a finding of question M8 (7.6)."
  - 7.7 composes actions from "<short names>" and the shared builder's "item order".
- **Evidence.**
  - Companion 6.5's order list (M2 … L1/G1), short-name list and corrections list contain no M8.
  - The D6 and D26 tables contain no M8 either.
  - M8 fires on screen states, so it is unclear which state D5 is asked on.
  - The shared module is imported read-only.
- **Consequence.** The action composer cannot render an M8 finding.

### R8. Findings are identified per question, but G2 and M8 fire per row
- **Part 1 · omission · needs a design choice.**
- **Spec text.**
  - 7.6.1: "Open finding for q exists… Otherwise nothing is sent."
  - 7.4: "G2 on p(`broken`) for any R_k."
  - 7.7: "a G2 row whose status is `not done`".
- **Evidence.**
  - If findings are keyed by question, a second requirement found broken at a later turn end is never corrected while the first G2 finding is open.
  - The same applies to M8 per section.
  - G2's "status" is not defined: it could be the highest-probability option, or p(`not done`) ≥ 0.5.

### R9. The correction message has no size bound
- **Part 3 · omission · needs a design choice.**
- **Ledger (D26, verbatim):** "**Message size:** a sized quantity, bounded by formula."
- **Spec text.** 7.7: "first three with full evidence (the cited events' detailed blocks …)".
- **Evidence.**
  - D1 cites every detailed event with p ≥ 0.5 (7.5).
  - Detailed blocks can each reach 2,000 tokens.
  - The detail budget is up to 0.40 × 32,767 ≈ 13,100 tokens (companion 6.4).
  - So a single `inject_agent` message can reach tens of thousands of tokens.
- **Where it belongs.** Section 7.7.

### R10. The state budget under the validated length is ambiguous, and stock Kev has no length
- **Part 1 and Part 3 · error / omission · one correct answer by D18 and D45, plus a gap in the shared-module interface.**
- **Spec text.**
  - Section 8: "B_state per companion 6.4, with the validated length from the training track's gate."
  - 7.11: the validated length is "read by the overflow switch".
- **Ledger.**
  - D18, "Revisit if" (verbatim): "Long-context training fails its accuracy gate; the trained budget then drops to the validated length and the overflow path carries more traffic."
  - D45: "8,192 tokens (stock Kev's validated length)".
- **Evidence.**
  - The companion fixes B_state at 32,767.
  - If the length L is used only by the switch, states still fill to 32K even when L = 16K.
  - Section 6.3 gives the renderer no budget parameter, and no detailed-event list (which D1 needs).
  - `stock-fallback-config` gives no L.
- **Answer.** B_state = min(32,767, L) for both filling and switching, with L = 8,192 for stock. This needs the shared renderer to accept a budget.

### R11. L7 timing and per-finding L7 rows
- **Part 1 · error · one correct answer for timing; a small choice for the second point.**
- **Spec text.** 7.3: "`L7#F<n>` for each open finding with a correction sent". 7.6 defines "correction sent at E<m>" as the carrier event.
- **Evidence.**
  - The Mod attaches the correction to the current tool result, then builds that event (`register.tsx` 165–176). So at E<m> the agent has not yet acted.
  - L7's wording asks "From the agent's actions since then". Asked at E<m>, it tends toward "ignored", and that status then appears in OPEN FINDINGS.
  - Separately, one message covering several findings gives identical L7 rows, so the findings can only close together.
- **Answer.** Start L7 at E<m+1> (one correct answer). How L7 handles a multi-finding message is a small owner choice.

### R12. Drift is undefined on events where G1 is not asked
- **Part 1 · omission · one natural answer.**
- **Spec text.** 7.1: a `turn_completed` with empty text gets "only G2 and G5". 7.8: "`drift` = 1 − p(G1) on classified events".
- **Gap.** The spec does not say whether drift is null on these events, or whether they count in `drift_rate`'s window w. The natural answer is null and not counted.

### R13. The overflow path breaks when instructions alone are too large
- **Part 1 · omission · one correct answer (extend the existing raise).**
- **Spec text.** 7.9: it raises only if "USER INSTRUCTIONS alone exceed the state budget."
- **Gap.**
  - The screen cap is "(screen budget − instructions − ledger)/10" (companion 6.6). It goes negative once instructions exceed about 7K tokens.
  - When instructions alone are above the switch threshold but below B_state, the merged state can never fit, so step 4 never terminates.
- **Answer.** Raise in both of those cases too, consistent with the owner's existing raise rule.

### R14. The `warmup()` method is not carried
- **Part 3 · omission · one correct answer.**
- **Ledger (D35, verbatim):** "**Modal `Classifier` class:** weights load once per container in `@modal.enter()`; `classify(event)` and a no-op `warmup()` share a container…"
- **Gap.** Sections 1, 6.1 and 7.11 never require `warmup()`. CONTRACT section 4 and Noah's `/health` call it.
- **Where it belongs.** Section 6.1.

### R15. The 6.2 output example contradicts 7.8
- **Part 1 · error · one correct answer.**
- **Spec text.** The example has `"flagged": false, "risk": 0.12` next to `"fired": {"M4": 0.91}`, and it combines `skipped` with non-null values.
- **Consequence.** Low, but a contract test written from this example would be wrong.

### R16. Section 9 is cost-incomplete for flagged events and uncounted work
- **Part 2 · unsupported claim / omission.**
- **Spec text.** "plus about 70 ms per diagnostic row on long states (D1 per detailed event, D5, D2 per R_k)".
- **Evidence.**
  - The row count is never stated. At 32K, 13K of detail budget over typical 300–600-token blocks gives about 20–45 D1 rows, roughly 1.4–3.2 s. The block size is my own estimate, not a measurement.
  - Add about 0.07 s × R_k for D2 on top of 2.9 s. A flagged long-state event can therefore approach or pass 8 s. Those are the results that carry corrections.
  - RF is not priced. Report 31 measured q=1 at a 2K state as 107 ms; units × ≤ 0.1 s if run serially, which matters for README-sized documents at session start.
  - Writing the whole growing session record through to the Dict on every event is not priced. Report 31's ~100 ms of Dict I/O was measured on the stub's tiny record.

### R17. Section 12 carries coordination items, not spec
- **Part 4 · task material · low.**
- **Spec text.** "who sets `min_containers=1` on demo day", the NOAH.md cutoff/status note, and Noah's pilot plan under "Demo:".
- **Assessment.** These are operations or status items the builder cannot act on. They belong in the task file or the ledger.

---

## Part 2: section 9 against report 31

| Claim | Report 31 | Verdict |
|---|---|---|
| 1.2 s at 8K and 2.9 s at 32K, 12 rows, cache miss | C2: 1,221 ms and 2,907 ms | Defend. This is model time only; C3 adds about 0.05–0.15 s for Modal and Dict. |
| About 70 ms per diagnostic row on long states | C2 note: "~70 ms whether or not the state is cached" above 4,096 tokens | Defend the rate. Challenge the total (R16). |
| Overflow events go past 8 s | C2: 8K at q=20 is 1,789 ms per screen. About 4 screens plus a 2.9 s merged state is about 10 s. | Defend. |
| $2.27/h | C5 [E]: list price | Defend. |

## Part 4: proportionality

No mechanism fails the owner's rule. I checked and kept:
- the write-through persistence (a 600 s scaledown with demo pauses needs it);
- the ordering gate (D29);
- the duplicate-`seq` rule;
- the serving-path calibration check;
- the one-line named-approximation note.

R5 is the only place where one mechanism (the storage cap) would need another to keep the train-equals-runtime guarantee. It is listed as a design choice, not as a cut.

---

## The three most likely failure points

1. **R1: corrections keep cycling after a correct dismissal.** Persistent G1 or L1 drift brings a new correction every two or three events, which hits the demo's no-false-correction bar head-on.
2. **R2 and R3: results lost or wrongly skipped under bursts and cold starts.** A lost correction then silences that question for the rest of the session.
3. **R4, R5 and R10: training and runtime diverge.** AskUserQuestion answers never reach USER INSTRUCTIONS, trimmed fields change the renderer's derived counts, and the state budget is ambiguous once the validated length is known.

## Verdict: not implementation-ready yet

The structure, the contract shape, the formulas and the cited latency numbers check out. These questions need the owner's answer before a builder can finish without making design choices:
1. What "the same issue" means after a correct dismissal (R1).
2. Whether findings are identified per question or per row for G2 and M8, and what G2's "status" means (R8).
3. M8's short name, order position, correction text and where its severity comes from (R7; blocks Phase 3 only).
4. The bound on correction message size (R9, already decided in principle by D26).
5. What is stored for long fields so the renderer's derived fields stay exact (R5).
6. The text form in which an AskUserQuestion answer becomes `[I_n]` (R4).
7. Whether a late-arriving event's `new_items` are recorded (R3), and whether to adopt `backend_sent_at` (R2).

The builder could settle R6, R10–R15 and the spec-wording half of R2 on their own, since each has one correct answer. The spec should still state them.