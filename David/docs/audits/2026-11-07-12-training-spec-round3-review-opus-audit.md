# Round-3 review: `docs/TRAINING-SPEC.md`

**Verdict: not implementation-ready yet.** One question blocks the build: R3-01, how agent text and `turn_completed` events map to rendered units and cut points. Separately, R3-02 is a one-line fix that must land before labelling, because the literal formula inverts every G1 label. The D46 stopping rule (≤ 2 findings, none blocking) is not met.

Date anchor: `date` returned Sat Nov 7 22:38 EST 2026. I edited no file and invoked no skill. Every shell command ran in the foreground and exited.

## Part 0: Register verification (53 entries)

| Entry | Status | Receipt or defect |
|---|---|---|
| R2-F1 none pairs | LANDED WITH NEW DEFECT | §9.1 has `--p_none_pair 0`. The sentence "None-pair passes add work per step without changing S" is now stale (R3-24) |
| R2-F2 KEV_TEMPERATURE | LANDED | §9.5 "read only by Kev's command-line entry points, `kev.serve`, `kev.benchmark` and `kev.evaluate`" |
| R2-F3 tokenizer | DEFENSE HOLDS | No counter-evidence. Kev's code is not on this machine, so I did not re-verify it |
| R2-F4 SDPA | DEFENSE HOLDS | Same as R2-F3 |
| R2-F5 checkpoint format | LANDED | §9.2.4 "full-weight checkpoint (`weights="full"`…)"; §12.1 per-α fallback |
| R2-F6 detail-budget floor | LANDED | §10 "max(0.40 · B_state − tokens(…), 0.15 · B_state)" |
| Builder note (P covers largest record) | LANDED WITH NEW DEFECT | §10 "smoke run on the largest record", but §15 runs the pass-cap measurement in Phase 1, before any record exists (R3-22) |
| R2-07 positive floor (decided) | LANDED WITH NEW DEFECT | §10/§12.2 carry D44. The added "share measured on each source's first labelled batch" makes the gate noise-driven (R3-08) |
| R2-06 long gate (decided) | LANDED WITH NEW DEFECT | §7.9/§10/§11/§12.3/§15 carry D18. The scored question is no longer named (R3-06). Items "at the overflow threshold" exceed B_state (R3-07) |
| R2-10 TRACE scoring (decided) | LANDED WITH NEW DEFECT | §12.4 carries D37. "Last completion claim" has no locator in the TRACE conversion (R3-31) |
| Ties to the positive class (decided) | LANDED WITH NEW DEFECT | §8.3. The literal G1 formula inverts G1, and G2 choice ties go to the Sol vote (R3-02) |
| R2-01 positive class | LANDED WITH NEW DEFECT | §4.1 defines it. §8.2 item 2 still says "yes" (R3-03). "Flagged record" includes M8, which conflicts with §6.6 (R3-04) |
| R2-02 B_state | LANDED | §6.4 "B_state = 32,767 … the state never depends on the questions" |
| R2-03/A4 seam gate | LANDED | §12.3 "scored once, on the selected adapter and stock Kev … reported" |
| R2-04 surface gate | LANDED WITH NEW DEFECT | §12.3/§9.4. What it means for a candidate to "pass" is undefined (R3-09) |
| R2-05/F7 calibration gate | LANDED | §12.3 Calibration row; §9.4 serving-path sentence |
| R2-08 stock baseline | LANDED | §12.4 "T_q and b_q fitted jointly by NLL" |
| R2-09/F2/F4 probe conversions | LANDED | §7.9 IFBench, aspi and UIB conversions |
| R2-11 demo | LANDED | §7.9 "Never trained on: the demo repository and prompt" |
| R2-12 construction basis C | LANDED | §7.3 legend "C = construction … yields to the teacher"; §2.3 |
| R2-13 | LANDED | §1 table has no "down-weighted"; the kernel bound matches §12.1 |
| R2-14/A1 identity parity | LANDED WITH NEW DEFECT | §12.1 is correct, but §1 still says "logits equal stock Kev-4B's … bit-exact in fp32" (R3-05). The new "next candidate" fallback conflicts with §13 (R3-23) |
| R2-15 | LANDED | Through R2-F1 |
| R2-16/A3 renderer parity | LANDED WITH NEW DEFECT | §12.1 Phase 2 "the same fixtures written as source records" cannot be written for most source formats (R3-10) |
| R2-17/F5 cap bookkeeping | LANDED | §7.8 |
| R2-18 invariant wording | LANDED | §1 coherence invariant |
| R2-19/F6 screen ledger | LANDED | §6.6 "LATEST EVENT in full … within 15%"; cap counts the ledger once |
| R2-20 tool renders | LANDED | §6.1, §6.4 |
| R2-23 note set excluded | LANDED | §7.5 "excluded from selection scoring and calibration" |
| R2-24/F13 note-crutch population | LANDED | §12.3 "whose no-note copy's target is 0 or 1" |
| R2-25 served T_q refit / F15d | LANDED WITH NEW DEFECT | §9.5 is correct; §1's invariant still describes the served T_q as cross-fitted (R3-05) |
| R2-26 D2 trigger | LANDED WITH NEW DEFECT | §8.2.6 is correct; §4.2's D2 row still says "when a question fired" (R3-04) |
| R2-27 OPEN FINDINGS ids | LANDED | §7.3 hook and pushback rows. A separate, earlier defect sits in the same row (R3-26) |
| R2-28/F14 RF recall | LANDED | §12.3 Requirement filter row |
| R2-29/C1 | LANDED | §9.1 "~$10–19 … (section 11)" |
| R2-30 teacher wall-clock | LANDED WITH NEW DEFECT | §11. The band contradicts its own inputs (R3-17) |
| R2-31/C2/C3 cost rows | LANDED | §11 rows present. Relabel passes are still unpriced (R3-18) |
| R2-32/F8 requirement units | LANDED | §6.7; §7.3 InFoBench |
| R2-33 G2/G5 at `turn_completed` | LANDED WITH NEW DEFECT | §4.2 "carries G2 and G5 only; its final text was already judged as a message unit" assumes a message unit the event schema never produces (R3-01, R3-04) |
| R2-34/L3 absolute bins | LANDED | §7.2; D43/D45 "Earlier:" clauses |
| A2 retention | LANDED | §10/§12.3. Arithmetic checked: SE = √(0.25/2172) = 0.0107, P(pass at parity) = 0.80 |
| A5 | LANDED | Through the claims pass |
| F10 batch size | LANDED | §8.3 |
| F11 effort span | LANDED | §6.4 |
| F12 goal-splice in slice | LANDED | §9.4 |
| F15 a/b/c/e | LANDED | §1, §8.5, §12.2. The unbounded can't-tell loop (R3-14) was there before round 2 |
| F16 §13 scope | LANDED | §13 "(Retention, Demo check)" |
| F18 f_long padding | LANDED | §7.7. The padding assumption itself is R3-13 |
| T1 | LANDED | §14 Q2 |
| Ledger lag | LANDED | D30, D33, D40–D44 and D47 updated |
| Cut R2-22/F9 builder patch | LANDED | §9.2 has four items, none a long-state builder |
| Cut RF held-out set | LANDED | §12.3 uses dev's RF rows |
| Defense R2-21/F3 | DEFENSE HOLDS | Verified in `Noah/mod/hooks/register.tsx`: queued corrections go only into `answer.context`, while the event is built from `ran` by `toolEvent(…)` |

**Totals:** 36 LANDED, 14 LANDED WITH NEW DEFECT, 3 DEFENSE HOLDS, 0 NOT LANDED, 0 DEFENSE FAILS. All four owner decisions are carried as decided, each with a defect noted above.

## Part 1: Logic and contract audit

**R3-01 · omission (exposed by R2-33) · BLOCKING · How Mod events become rendered units and cut points is undefined for agent text**
- **Spec text:**
  - §6.1 types: `tool_completed | turn_completed | session_started`.
  - §6.4: "A text-only unit renders as `[E43] MESSAGE`"; tool blocks also carry "agent said: <visible text since the previous event>".
  - §7.2 cut points include "agent text units … and `turn_completed` events for G2 and G5".
  - §4.2: "A record cut at a `turn_completed` event carries G2 and G5 only; its final text was already judged as a message unit."
  - §7.3 (HelpSteer3 and others): "each response as a final MESSAGE in its own record".
- **Evidence:**
  - CONTRACT §3 has no message event type. Agent text arrives only as `agent_text` on a `tool_completed` or `turn_completed` event.
  - Ledger D21.U: "One message unit = all assistant visible text plus displayed thinking between two consecutive tool calls, or between the last tool call and turn end, classified once when the next tool call or the turn end arrives."
  - Nothing says:
    - whether text on a `tool_completed` event is its own MESSAGE unit and cut, or only the block's `agent said:` line;
    - how a `turn_completed` event renders as LATEST EVENT;
    - whether one `turn_completed` yields two records (a MESSAGE cut with the every-event set, plus a G2/G5 cut), and what E-number each gets;
    - which event type a converter emits for a "final MESSAGE".
- **Consequence:**
  - Converters and the runtime agent (D75) can resolve this differently. That breaks "Train equals runtime" on the most common classified unit.
  - Read literally, a chat final message emitted as `turn_completed` carries "G2 and G5 only", so HelpSteer3, arena and WildFeedback records lose the M1 question they exist for.
  - The Phase 1 golden bytes are produced by the renderer itself, so they will not catch any of this.
- **Resolution:** a small design choice, needed before the Phase 1 renderer freezes. Recommended answer, consistent with D21.U and D40:
  - Text before a tool call is that block's `agent said:` line and is judged with the tool call.
  - The final text on `turn_completed` renders as `[E<seq>] MESSAGE`, gets the every-event set, and the same event forms a second record with G2/G5.
  - Converters emit final messages as `turn_completed` events.

**R3-02 · amendment-created · high severity · The tie rule inverts G1 when read literally, and G2 choice ties ignore D30**
- **Spec text:** §8.3: "`label` = target ≥ 0.5 where the positive class is yes, and target ≤ 0.5 for G1"; "`label` is the option with the higher mean (ties go to the Sol vote)".
- **Evidence:**
  - Parallel reading gives `label = (target ≤ 0.5)` for G1. Two "no (drift)" votes (target 0) would then become label = true (on track), so every G1 row is inverted. G1 is the `drift` signal (D17).
  - D30: "a 0.5 tie … resolves to the question's positive class … `broken`/`not done` for G2". Under §8.3 a done-versus-not-done tie on G2 goes to the Sol vote instead.
- **Resolution:** one correct answer.
  - G1: `label = target > 0.5`, so a tie gives no.
  - G2: a tie between a positive option and a non-positive option goes to the positive option. Other ties go to Sol.

**R3-03 · amendment-created (R2-01 incomplete) · The teacher instruction still uses "yes" as the problem answer**
- **Spec text:** §8.2.2 "Answer **yes** only when the visible state shows the problem."
- **Evidence:** G1's yes means on track (§4.2). §4.2 was moved to positive-class language ("Answer with a question's positive class (4.1) only when the state shows it"); the teacher protocol was not.
- **Consequence:** this text is given to every vote. A teacher reading it literally defaults G1 toward no (drift).
- **Resolution:** one correct answer. Use "Answer with the question's positive class only when the visible state shows it."

**R3-04 · amendment-created (R2-01, R2-26, R2-33) · Question-set membership conflicts**
- **Spec text:**
  - §4.1 "flagged record: … at least one positive row on the every-event set, G2, G5 or M8".
  - §8.2.6 puts D5 and D1/D3 on flagged records.
  - §6.6 "Each screen record asks SCR and M8 for every section".
  - §6.5's short-name list has no M8.
  - §4.2's D2 row says "when a question fired", while §8.2.6 says "where M2 is positive or G2 is `broken` or `not done`".
- **Evidence:** D19.P: "The ~200 training records are screen states labelled on both questions."
- **Consequence:**
  - M8-positive screen records pick up D5 and D1/D3 rows, which contradicts §6.6 and D19.P.
  - The D1/D3 wording «short names of the questions that fired» has no name to fill for M8.
  - "Carries G2 and G5 only" contradicts the diagnostics on flagged `turn_completed` records.
- **Resolution:** one correct answer.
  - Drop M8 from "flagged record" for diagnostic labelling, so screen records carry SCR and M8 only.
  - Turn_completed records carry "G2 and G5, plus their diagnostics when flagged".
  - §4.2's D2 row becomes "when M2 or G2 fired".

**R3-05 · amendment-created (R2-14/F17, R2-25) · §1's guarantees lag behind §12.1 and §9.5**
- **Spec text:** §1: "At α = 0, T_q = 1, b_q = 0 the adapter's logits equal stock Kev-4B's. *Discharge:* … bit-exact in fp32". Invariant: "T_q minimizes negative log-likelihood on dev … cross-fitted over five dev folds".
- **Evidence:**
  - §12.1 compares against "stock Kev-4B merged to full weights the same way … within stock's own run-to-run spread".
  - §9.5: "the served T_q is refitted on all of dev".
  - D42 matches §12.1.
- **Consequence:** an executor reading §1 expects bit-exactness against unmerged stock. That fails whenever the Triton kernels are nondeterministic, and §12.1 says nothing is scored until identity parity passes.
- **Resolution:** one correct answer. Align §1 with §12.1 and §9.5.

**R3-06 · amendment-created (R2-06) · The long-context gate does not say which question it scores**
- **Spec text:** §12.3 "accuracy within 3 points of the model's own 8K accuracy"; §7.9 "constraint-insertion records (7.4) …".
- **Evidence:** the round-2 Opus report cites the earlier text as "§7.9 padded M2 items". The rewrite dropped the question.
- **Consequence:** accuracy pooled over every row would be dominated by rows the inserted constraint never decides.
- **Resolution:** one correct answer. Score M2, the construction's target, whose answer the inserted constraint decides.

**R3-07 · amendment-created (R2-06 made it routine) · States at the overflow threshold exceed B_state**
- **Spec text:** §6.4: overflow applies "If instructions and documents exceed B_state − 0.15 × B_state − tokens(LATEST EVENT)", and "OPEN FINDINGS and EFFORT always". §7.9 builds gate items with "documents at the overflow threshold of 6.4".
- **Evidence:**
  - At the threshold, the detail budget is max(0.40B − docs, 0.15B) = 0.15B.
  - Documents + LATEST + 0.15B of detail already equals B_state.
  - The section headings, OPEN FINDINGS, EFFORT and the count line have no reserved room, and the count-line rule only shrinks one-liners.
- **Consequence:** Kev "rejects a state whose token count plus one exceeds `max_state`". The single-state-limit arm of the gate, and any long record near the threshold, fails to score or halts the trainer.
- **Resolution:** one correct answer. Subtract the always-present parts in the threshold, or let the detail blocks yield first.

**R3-08 · amendment-created (R2-07) · The positive-floor gate is driven by noise**
- **Spec text:** §10: "P_q = Σ over sources of s · n^plan × the source's positive share for q | share measured on each source's first labelled batch".
- **Evidence:** §8.3 batches hold 10–20 records. At a 3% true share, a 15-record batch shows 0 positives 63% of the time, and otherwise shows ≥ 6.7%.
- **Consequence:** an inflated P_q triggers "rebuild … trimming that objective's largest source" for no reason in a timed build. A deflated P_q makes the floor slack.
- **Resolution:** one correct answer. The gate runs in Phase 3 after every record is labelled, so measure the share on each source's full labelled set. The gate then catches exactly what D44 targets: lost positives from shortfalls and redistribution.

**R3-09 · amendment-created (R2-04) · design choice · A candidate's pass on the surface-feature gate is undefined**
- **Spec text:** §9.4 "candidates that pass the surface-feature gate (12.3) rank before those that fail". §12.3 defines the gate per question with a "logistic model".
- **Evidence:**
  - "Pass" read naturally means passing on every question. That is a conjunction of about 16 noisy paired-bootstrap tests, including rare questions near the dev floor.
  - The logistic baseline is undefined for the choice and score questions (G2, L7, D5).
- **Consequence:** either no candidate passes, so the ranking does nothing, or one passes by chance and jumps ahead of better intent scores.
- **Resolution:** owner choice. Options: report only; rank by the number of questions passed; or restrict the gate to yes/no questions with at least the dev floor of positives.

**R3-10 · amendment-created (R2-16) · Phase 2 renderer parity cannot be met by most converters**
- **Spec text:** §12.1 "each converter's output for the same fixtures written as source records … renders to the same golden bytes"; "no converter's records are built until its own check passes".
- **Evidence:** Mod fixtures carry Bash, Edit, `todos` and `file_changes`. HelpSteer3 and the arena sets are chat, and CATCH and Aria are single file writes. Those formats cannot express the fixtures.
- **Consequence:** read strictly, those converters never pass, which blocks their records.
- **Resolution:** one correct answer. Per converter, use the subset of fixtures whose fields its source format can express.

**R3-11 · error · Serve-path parity in probability space penalizes the tuned model's own design**
- **Spec text:** §12.1 "the winner's max |Δp| … ≤ 1.5 × stock Kev's own gap".
- **Evidence:**
  - |Δp| ≈ σ′(z)|Δz|, which is largest at p = 0.5.
  - Soft targets of 0.25, 0.5 and 0.75 train mid-range outputs.
  - Stock answers with "a fixed yes/no lean" (D32.P; still-pursuing yes-rate 2%).
  - So the same serving logit error gives a larger |Δp| for the tuned model.
- **Consequence:** systematic failures push the pick toward α = 1.0 candidates or stock for reasons unrelated to serving correctness.
- **Resolution:** one correct answer. Measure |Δz| (logits) and keep D44's 1.5× relative rule.

**R3-12 · error · The secrets scan uses bare prefixes that match ordinary code**
- **Spec text:** §12.2 "zero matches for … `ghp_`, … `AKIA`, `hf_` …"
- **Evidence:** `hf_` occurs in `hf_hub_download` and `hf_token`, which are common in SWE-chat, Open-SWE and TonyDzi code.
- **Consequence:** the scan never reaches zero, or "scrub" corrupts code and patches inside states.
- **Resolution:** one correct answer. Use token-shaped patterns, for example `hf_[A-Za-z0-9]{34}`, `AKIA[0-9A-Z]{16}`, `ghp_[A-Za-z0-9]{36}`.

**R3-13 · error · Padding with "unrelated real documents" can change labels**
- **Spec text:** §7.7 "labels are unchanged, since the added documents bear on nothing". §7.9 pads gate items with "unrelated real documents".
- **Evidence:** M2 asks whether the action breaks "a requirement stated in … PROJECT DOCUMENTS". Real agent and project documents (the CLAUDE.md files and AgentIF prompts the spec uses elsewhere) contain such rules.
- **Consequence:** wrong M2, L5 and G4 labels on about 10% of training records and on the long-gate items.
- **Resolution:** one correct answer. Pad only with non-normative text (QuALITY-style articles), or have the teacher label each padded record.

**R3-14 · error · The can't-tell relabel loop has no end**
- **Spec text:** §8.5 "> 25% | … tightened, labels redone"; §12.2 "tighten instructions, relabel".
- **Evidence:** agreement is bounded ("relabelled once; a second failure is reported"); can't-tell is not. For reasoning-rich sources, can't-tell is the visible-evidence rule working, so tightening may never get it under 25%.
- **Resolution:** one correct answer. Relabel once, then report.

**R3-15 · error · Dev top-up weighting is per question, but top-up records carry every question**
- **Spec text:** §7.9 "top-up records are weighted back to their question's pre-top-up rate wherever dev prevalence is used (calibration, ECE)".
- **Evidence:** 300–600 top-ups out of about 1,600–1,900 dev records. Each top-up record carries the full question set (D30 label scope), so it shifts π^dev for every other question too.
- **Consequence:** biased π^dev feeds b_q and shifts served probabilities for every question.
- **Resolution:** one correct answer. Compute prevalence-dependent quantities on base dev only, or weight per question so each question keeps its base-dev rate.

**R3-23 · amendment-created (R2-14) · §13 conflicts with the serve-path fallback**
- **Spec text:** §13 "A failed correctness gate stops its stage". §12.1 Serve-path parity, a correctness gate, falls back to "the next candidate in pick order".
- **Resolution:** one correct answer. Add serve-path parity to §13's list of gates that move down the pick order.

**R3-27 · error · Correction-window p values are drawn from a narrower range than the runtime fires at**
- **Spec text:** §7.4 "its p values drawn uniformly from [0.6, 0.99]".
- **Evidence:** D25 fires at "calibrated p ≥ 0.5". Runtime L7 «text» will show p in [0.5, 0.6), which training never shows.
- **Resolution:** one correct answer. Draw from [0.5, 0.99].

**R3-28 · error · Two dev sets have sizes that cannot be computed or conflict with their floors**
- **Intent slice:**
  - **Spec text:** §9.4 "~200 dev records", while §7.9 requires "the same floor per intent question".
  - **Evidence:** by Hanley–McNeil at AUROC 0.8, 60 positives with 140 negatives gives SE = 0.037 > 0.035. Four questions at about 60 positives each do not fit in about 200 records without heavy overlap.
- **Note-pair diagnostic set:**
  - **Spec text:** §7.5 sizes it "so the paired-difference standard error is ≤ 0.02".
  - **Evidence:** no discordance input is named, so n = d/0.02² cannot be computed.
- **Resolution:** one correct answer. Size both by formula. Use a pilot discordance for the note set, as the long gate does, and treat the slice's ~200 as an estimate.

**R3-29 · error · The "saying yes everywhere" instrument cannot fire where it matters most**
- **Spec text:** §13 "per-question positive rate on benign dev (above 2× stock's → flag)".
- **Evidence:** stock's still-pursuing yes-rate is 2% (D3), so stock's G1 positive (drift) rate is about 98%, and twice that is unreachable.
- **Resolution:** small design choice. Anchor to the teacher's positive rate on benign dev, and state whether p is raw or calibrated.

**R3-30 · error · design choice for David (touches decided items) · Two final visible-based label rules contradict their questions' own wording**
- **Spec text:**
  - §7.3 AgentJudgeBench "G1 = no below 0.5 coverage", but G1's wording says "Yes if it is still working toward the user's goal, even slowly or with mistakes".
  - Arena `both_bad` is "both M1-yes", but the CodeTraceBench row says "competence errors are negatives for every question".
- **Consequence:** visible-based labels are final over the teacher (§8.4), so these rules write label noise into G1 and M1, the intent questions.
- **Resolution:** owner choice (D45, D30). Make both teacher-labelled with the source label as a hint, or keep them as decided.

**R3-31 · amendment-created (R2-10) · TRACE's "last completion claim" has no locator**
- **Spec text:** §12.4 "G5 is asked at the agent's last completion claim before the cut". The §7.9 TRACE conversion produces no `turn_completed` events.
- **Resolution:** one correct answer. Treat each assistant-turn end as a `turn_completed` event and ask G5 at the last one before the cut.

## Part 2: Cost audit

**R3-17 · amendment-created (R2-30) · The teacher wall-clock band contradicts its own inputs**
- **Spec text:** §11 "0.4–2 h (2–5 min per call, 50–100 parallel)" with "~1,000–2,000 calls".
- **Evidence:** 2,000 × 5 / (60 × 50) = 3.3 h. 11,000 items × 2 votes / 10 per call = 2,200 calls, which gives 3.7 h.
- **Resolution:** one correct answer. The band is about 0.3–3.7 h.

**R3-18 · omission · Relabel passes are not priced**
- **What is missing:** §11 has no row for:
  - the agreement-failure relabel ("its rows relabelled once"), which re-sends whole records;
  - the can't-tell relabel;
  - the up to 3 mismatch attempts per construction record (§7.4).
- **Consequence:** one failing subjective question (M7, L2 or G4 are likely) adds up to a full second pass of about 1,000–2,000 calls after the first. That is a direct risk to the 07:00 rule.
- **Resolution:** one correct answer. Add the row.

**R3-19 · unsupported claim / omission · The $200 cap binds, the price was not checked, and nothing says what yields first**
- **Spec text:** §11 "the $200 cap binds … (no current Haiku/Sonnet 5.5 price was checked) … stage closes at the cap".
- **Evidence:**
  - The price is one lookup away; design-ethos #6 calls an inspection-estimate with the instrument one command away a defect.
  - Agent runs have a redistribution path (D28: "past the cut-off their shares go to the same objective's other sources").
  - Generation has no substitute: constructions, L7 continuations, rewrites, notes and sampled responses.
- **Consequence:** if runs drain the cap, constructed L2, L4 and L7 data is lost with no fallback.
- **Resolution:** one correct answer derived from D28. Reserve generation's estimated spend first, give the remainder to agent runs, and check the prices.

Checked and found consistent:
- §9.1 run time: about 82M state tokens at about 7.5K tokens/s training throughput is about 3 h, inside 2–3.5 h.
- §11 candidate scoring: 21 × about 1,750 × 6.7K is about 246M tokens, about 2.3 h at 30K tokens/s.
- Agent-run wall-clock: 0.75–2.5 h.
- Training cost: $3.95/h × 2–3.5 h.

## Part 3: Completeness against the ledger

**R3-16 · omission · There is no calibration for stock when stock is the selected model**
- **Spec text:** §9.5 "Calibration (selected adapter only)" uses the closed-form b_q, yet §12.4 says "stock has no training rate for the closed-form offset". Stock can be selected (§1, §13).
- **Ledger D76:** "a stock-Kev fallback uses the calibration fitted for the lift baseline".
- **Belongs in:** §9.5, together with saving that fit as a deliverable.

**R3-20 · omission (self-containment) · Several sources cannot be located from the spec alone**
- **Spec text:** §6's header promises "every … source … is stated here", but these lack the identifiers the dossier gives:
  - AISI OLMo rollouts: `ai-safety-institute/reward-hacking-olmo3.1-32b-kl0.0-seed2-rollouts` (dossier #3).
  - SWE-Misbehavior: two candidate repos, `duc-anh-2002/…` and `dxlong2000/…` (#45).
  - MALT: `metr-evals/malt-public` (#13).
  - tau2-bench: `HuggingFaceH4/tau2-bench-data` and `sierra-research/tau2-bench` (#43).
  - "Misalignment Atlas" is `ND-SaNDwichLAB/coding-agent-misalignment` (#32). The spec uses both names.
  - "SWE-bench Verified annotations" (#46).
  - The path of `heldout-intent-probe-manifest.jsonl`, which is `docs/research/`.
- **Belongs in:** §7.3 and §7.9.

**R3-21 · omission · The demo check's form is not pinned**
- **Ledger D74:** "Noah's scripted session passes: the deletion flagged with actions". Emergent-interactions table: "`demo-flag-check`: before 07:00, the winner scored on the demo scenario must flag it".
- **Spec text:** §12.3 does not name the record (the slow-tests scripted session, cut at the deletion), what "flags" means (any every-event problem question at calibrated p ≥ 0.5, D71), or what happens if the scenario does not exist at pick time.
- **Belongs in:** §12.3, Demo check row.

**R3-26 · omission · An undefined K**
- **Spec text:** §7.3 SWE-chat post-pushback: "the K events after it form the record". K is defined nowhere.
- **Resolution:** a small choice, for example cut at the last classified event of the agent's responding turn.

**R3-22 · amendment-created (builder note) · Phase order: the pass-cap measurement needs a record that does not exist yet**
- **Spec text:** §15 Phase 1 clears "pass-cap measurement"; §10 measures it with a "smoke run on the largest record".
- **Evidence:** records are built in Phase 2 and Phase 3.
- **Resolution:** one correct answer. Use a synthetic record at `max_packed` (B_state + 1,664). Sibling records guarantee no real record exceeds that.

**R3-24 · amendment-created (R2-F1) · A stale sentence about none pairs**
- **Spec text:** §9.1 "None-pair passes add work per step without changing S", while `--p_none_pair 0` is set.
- **Resolution:** delete the sentence.

## Part 4: Spec/task boundary

**Task material:** none found. The spec carries no session recovery, status documents, cut-off scheduling or completion checklist.

**R3-25 · unneeded mechanism · Two open items are already decided**
- **Spec text:** §14 lists "Q4 … *Stand-in:* screen budget 8,192 tokens … and 10 sections per state" and "O-FIRING-THRESHOLD … *stand-in* p ≥ 0.5".
- **Evidence:** D73 fixed "screen states of 10 sections in 8,192 tokens". D25 fixed "Every question fires at calibrated p ≥ 0.5".
- **Resolution:** state both as decided and delete the open items. §12.3's "until the runtime sets one" also goes.

## Counts

- **Register entries verified:** 53.
- **Findings:** 31.
  - Amendment-created: 14 (R3-02 to R3-10, R3-17, R3-22, R3-23, R3-24, R3-31).
  - Error: 9 (R3-11 to R3-15, R3-27 to R3-30).
  - Omission: 6 (R3-01, R3-16, R3-18, R3-20, R3-21, R3-26).
  - Unsupported claim: 1 (R3-19).
  - Unneeded mechanism: 1 (R3-25).
  - Task material: 0. Overreach: 0 (§1's bit-exact overclaim is counted under R3-05).
- **Need a design choice:** R3-01, R3-09, R3-29, R3-30. Every other finding has one correct answer.
- **Blocking:** 1 (R3-01).

## Three most likely failure points

1. **Silent label corruption.** The literal G1 formula and the teacher's "yes" instruction invert G1, the drift signal (R3-02, R3-03). Padding with normative documents mislabels about 10% of records (R3-13). Final visible-based rules contradict G1 and M1 wording (R3-30).
2. **The renderer seam.** Agent-text and `turn_completed` mapping (R3-01) and states that overflow at the threshold (R3-07) both break the train-equals-runtime guarantee or halt scoring at the single-state limit.
3. **The overnight schedule.** The understated teacher band, unpriced relabel passes, a binding $200 cap with no allocation, and a noise-triggered floor rebuild (R3-17, R3-18, R3-19, R3-08) together push toward the 07:00 fallback.

## Implementation-readiness

Not ready. The one blocking question is **R3-01**: how a Mod event becomes rendered units and cut points for agent text and `turn_completed`. It must be decided before the Phase 1 renderer freezes, because the runtime adopts that renderer unchanged.

R3-02 needs no decision but must land before Phase 3 labelling. R3-09, R3-29 and R3-30 are small owner choices that do not block the build.

## Coverage ledger

| File | Lines read |
|---|---|
| reading-context SKILL.md | 1–98 |
| out-of-cutoff SKILL.md | 1–103 |
| receipts-before-claims SKILL.md | 1–29 |
| design-ethos SKILL.md | 1–71 |
| gold-standard-spec-template.md | 1–200, 200–399, 400–605 |
| initializing-projects SKILL.md | 1–133 |
| task-file-builder SKILL.md | 1–206 |
| CONTRACT.md | 1–261 |
| TRAINING-SPEC.md | 1–200, 200–359, 360–519, 520–673 |
| DESIGN-DECISIONS.md | 1–200, 200–399, 400–599, 600–799, 800–999, 1000–1143 |
| TRAINING-SPEC-TRACE.md | 1–37 |
| Round-2 dispositions (-7-) | 1–70 |

Every line of the files above is covered.

Targeted reads, located by grep and then read: round-2 Fable report (-10-) lines 146–150; round-2 Opus report (-9-) lines 120–135 and 240–250, plus grep hits; Noah's `register.tsx` lines 140–180; `DATASET-DOSSIER.md` lines 1613–1623 and its headings; grep hits in the round-1 reports and the research notes. Kev's source is not on this machine, so Kev claims rest on the earlier external-claims passes.