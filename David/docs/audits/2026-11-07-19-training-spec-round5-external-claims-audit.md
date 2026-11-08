I found no claim that is flatly wrong. Every round-4 fix touching code or data landed. Three claims are right but imprecise enough to change what a builder does (Findings 1–3), and one is low-impact (Finding 4).

- **Date:** 2026-11-07, checked with `date`.
- **Kev checkout:** `git rev-parse HEAD` gives `fc4a17e194bca35a48c57211392ec49ea54a94ac` and the tree is clean.
- **Discipline:** I edited no project file and ran nothing from Kev. Every command ran in the foreground and has exited.
- **Abbreviations:** **K** is `...\scratchpad\kev-verify\kev`. **M** is `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\mod\hooks\register.tsx`.

## Part 0: round-4 items

| Item | Status | Receipt |
|---|---|---|
| Claims 1: serve-path parity | LANDED | §12.1 now reads "Kev's unrounded probabilities (`Server.probs`), compared as log-odds". `K\kev\serve.py:147-148`: `probs` returns `submit(rec).result()`. `:189` gives `[q.tolist() for q in p]`: fp32 softmax output, not rounded. Rounding happens only in `_body` → `to_answers` (`:211-216`). There is a temperature caveat; see Finding 1. |
| Claims 2: patch shape | LANDED | §6.1: `"patch": <Claude Code's structured hunks, or null>`. M `:627`: `patch: result?.structuredPatch ?? null`. |
| Claims 3: pass cap P | LANDED | §10: "a full state plus its question count × its longest row". `K\kev\train.py:156-159`: with shared prefix, the cost is states × the longest state + branches × the longest branch. `:216-219`: an over-cap record raises `ValueError`. |
| Claims 4: tau2 basis | LANDED, now supported | Details in the dedicated check below. |
| Claims 5: read-only set | LANDED | §6.1 lists Read, Grep, Glob, WebFetch, WebSearch, LS, NotebookRead. M `:8` has the same seven. |
| Claims 6: PowerShell | LANDED | §6.1: "The shared renderer, not only the converters, renders PowerShell as Bash". M passes the tool name through unchanged (`:291`, `:304`). |
| Claims 7: AskUserQuestion | LANDED | §6.1: the renderer turns the result into a `user_instruction`, and AskUserQuestion is never a cut point. M makes `user_instruction` items only in `prompt.submit` (`:117-131`), so the renderer is the right place. The spec does not say which result field holds the answer (`action.result_text` or `action.result`), which I count as minor. |
| Turn-reason note | LANDED, with gaps | §4.2: G2 and G5 apply "when the turn's end reason is `answer`". See Finding 3. |
| R4-04: CodeTraceBench is T, its annotation a hint | LANDED | Dossier #25: "human-verified step labels … Labels mark competence errors, not intent". Never loading `agent_state.pkl` and mapping `step_id` both match #25. |
| R4-05: TonyDzi Stop-hook rows are T, the hook a hint | LANDED | Dossier #21: hook blocks "locate a false claim in the preceding Claude turn"; "Whether every hook refers to a claim in the same session is unverified". The second PII pass and keeping Russian text match #21. |
| R4-12: quoted «R_k» trimmed to the row limit | LANDED | `max_branch` = `max_state` + 640, checked as `len(br) > max_branch - len(S)`. The round-4 receipt (`K\kev\model.py:31-38`, `:112`) still holds. |
| F F9: IN3 ask renders as `turn_completed` | LANDED | It is consistent with dossier #54 (importance 1–3, 80/20 vague skew). The question it raises about G2 is in Finding 3. |

## Findings

**1. §12.1 serve-path parity. Spec text: "serving-path outputs are Kev's unrounded probabilities (`Server.probs`), compared as log-odds". Right but imprecise: the temperature is not pinned on either side.**
- **Source:**
  - `K\kev\model.py:211-218`, `:220-223`: the pointer head divides logits by `self.temperature` in eval mode, in both `forward` (the training forward) and `many` (the graphed serving readout).
  - `K\kev\checkpoint.py:241`: `m.head.temperature = meta.temperature if opts.temperature is None else opts.temperature`.
  - `K\docs\model-cards\kev-4b.md:79`: "One temperature, T = 2.41, stored in `head.pt` and applied at load time".
  - The trainer never sets a temperature (no `temperature` in `K\kev\train.py`), so saved adapters carry 1.0.
- **Consequence:**
  - §9.5 pins `LoadOptions(temperature=1.0)` only for the classifier.
  - If stock's training-forward side is loaded with default options and scored in eval mode, its log-odds are divided by 2.41. Stock's own gap then becomes about 0.59 × |log-odds| instead of a numerical gap.
  - That inflates the "1.5 × stock Kev's own gap" bar, so the gate passes vacuously.
  - **Fix:** both sides of the gate, for every candidate, load with temperature 1.0.
- **A smaller related point:**
  - Compute log-odds as log p₁ − log p₀ from both softmax entries.
  - Do not compute logit(p_yes) from one entry. In fp32, p_yes rounds to exactly 1.0 once the log-odds pass about 16.6, and logit(p_yes) is then infinite.
  - The minority entry stays representable down to about e⁻⁸⁷ (`model.py:444`, `:505` return the full softmax vector).

**2. §10 positive floor. Spec text: "T sources from the dossier's measured rate for that source (0 where none, so the source adds nothing to P_q)". Right but imprecise: no T source has a measured positive rate for a monitor question.**

The dossier has rates for several T sources, but each one measures something else:
- **#25 CodeTraceBench:** "52.8% of trajectories have an incorrect step". This is a competence-error rate, and the spec itself uses it only as a hint.
- **#20 SWE-chat:** pushback in 48.6% of sampled prompts (correction 38.7%, failure_report 8.8%). These are rates per prompt, not per cut window, and a spot check found only 6 of 12 labels right.
- **#5 Goodfire:** enacted flags 57.4% (SWE) and 6.2% (ImpossibleBench). These are judge flags, and an audit disagreed with 14 of 30.
- **#14 rpotham:** `is_misaligned` 253 of 1,050, and 131 unanimous. This is the judge's construct, before the spec's relabelling from the user's side.
- **#2 terminal-wrench:** class counts. The positive share actually follows from the spec's pairing rule.
- **#22 terminal-bench-science and #23 openguardrails:** 73% of reward-0 runs (#22) and 53% of dsh reward-0 runs (#23) open with an unqualified claim. This is a conditional rate, not a G5 or M5 share.
- **#24 Open-SWE:** "claims done but resolved 0" at 22.2% and 34.6%, which the dossier calls a "competence overclaim".
- **#46 SWE-bench Verified annotations:** the underspecified distribution, which describes the request, not the action.
- **#9 eungyeuk:** about 0%, which matches the spec.
- **No figure at all:** TonyDzi Stop-hook rows (#21 gives only "at least 8% of sessions are hook-flagged"), #32 Atlas, #47 Ambig-SWE, #72 InFoBench, #86 HelpSteer3, #90/#92/#93 arena sets, #99 WildFeedback and #104 AgentJudgeBench.

**Consequence:**
- Whether a source "has a rate" is a reader's call, so two builders will compute different P_q values, and therefore different floors.
- Under the strict reading (none of these is a positive rate, so 0), P_q comes only from C and V sources. For M1 and G1 that is almost entirely the goal-flip and goal-splice constructions plus UserBench.
- **Fix:** list per source which dossier figure counts, or state that T sources contribute 0.

**3. §4.2. Spec text: "plus G2 and G5 when the turn's end reason is `answer`". The value is right; it is imprecise in three ways.**
- **Source:**
  - M `:195`: `event.turn = { reason: e.reason, duration_ms, is_aborted }`.
  - CONTRACT §5 (line 208): "why the turn ended (answer, aborted, refusal, error)".
  - `Noah\backend\samples\4_turn_completed.json:9`: `"turn": { "reason": "answer", … }`.
- **(a) Converters are never told to set the field.** §6.1's field list omits `turn`, and §6.1 tells converters to leave unfillable fields empty "never invent it". So nothing tells a converter to set `turn.reason` = `answer` on the final MESSAGE events it emits, and the G2/G5 gate is undefined for converted records.
- **(b) The reason set cannot tell a question from a "done" claim.** A turn that ends by asking the user something also ends as `answer`. So the IN3 "ask" records (§7.3: "an ask renders as a `turn_completed` MESSAGE asking the question, cut there") would carry G2 and G5, whose wording assumes "The agent says the task is done". The round-4 note named this case, and the fix covers only aborted, refusal and error.
- **(c) Two places still state the old rule.** The §4.2 table says "at each `turn_completed` event" for G2 and G5, and §8.2 item 6 says "G2 per requirement and G5 only on records cut at a `turn_completed` event". A builder following either one asks G2 and G5 on aborted and error turns.

**4. §7.3 tau2-bench results row. Spec text: "V for `communicate_checks` scored by substring match". Right, and now supported; the only gap is that the spec does not say how to tell the mode.**
- **Source:**
  - tau2-bench at the 2025-06-10 "release" commit (`37199f3`, fetched): `evaluator_communicate.py` matches only by substring, `if info_str.lower() in message.content.lower().replace(",", ""):`.
  - The semantic (LLM-judge) mode exists only on current main. The file's only later commits are dated 2026-03-18 and 2026-10-20.
  - Dossier #43 places the shipped results in 2025.
  - On current main, semantic checks carry a `[llm_judge]` prefix in `justification`, and `RewardInfo.info.communicate_scoring` is set only in semantic mode.
- **Consequence:** low. Treating the shipped 2025 files as substring-scored is correct. A builder who later adds newer results files can check that prefix or that field.

## Verified claims (one line each)
- `Server.probs(rec)` returns (per-question unrounded fp32 probability lists, stats) (`K\kev\serve.py:147-148`, `:189`).
- Serving-path rounding happens only in `_body` → `to_answers` (`serve.py:211-216`).
- `patch` is `structuredPatch` or `null`, Edit and Write only, ops `edit` and `write` (M `:621-630`).
- The read-only set is Read, Grep, Glob, WebFetch, WebSearch, LS, NotebookRead (M `:8`).
- The Mod passes tool names through unchanged, so `PowerShell` arrives as is (M `:291`, `:304`; CONTRACT §5 "Edit, Write, Bash, PowerShell").
- The Mod makes `user_instruction` items only from `prompt.submit`, and AskUserQuestion answers arrive in a tool event (M `:117-131`, `:155-176`; CONTRACT §5 "answers to AskUserQuestion").
- `turn_completed` carries `agent_text = e.answer` and `turn.reason`, and `answer` is a real value (M `:193-195`; CONTRACT §5; sample 4).
- The pass cost formula and the hard halt on an over-cap record (`K\kev\train.py:156-159`, `:216-219`).
- Saved adapters carry T = 1 and stock carries T = 2.41 (`model.py:211-223`, `checkpoint.py:241`, `kev-4b.md:79`).
- tau2 `nl_assertions` are LLM-judged (round-4 fetch, not re-fetched), so T is correct; `communicate_checks` are substring-matched in the June 2025 code.
- Joining each tau2 results file to its own embedded tasks, and the "write without a preceding explicit yes" rule (#43).
- CodeTraceBench: human-verified competence labels as a hint, `agent_state.pkl` never loaded, `step_id` mapped (#25).
- TonyDzi: Stop-hook blocks as a hint, recoveries for L7, second PII pass, Russian text, filters for benign rows (#21).
- IN3: importance 1–3 and the 80/20 vague skew (#54).
- SWE-chat: success ≥ 70 with no pushback for benign; the strict pushback relabel (#20).
- terminal-bench-science, openguardrails and Open-SWE conversions and filters (#22, #23, #24).

## Coverage ledger
- **Read in full:**
  - The three skill files.
  - `TRAINING-SPEC.md` lines 1–664.
  - The round-4 claims audit, lines 1–134.
  - The round-4 dispositions, lines 1–33.
- **Mod:**
  - M lines 1–340 and 560–669; UI lines not read.
  - CONTRACT.md lines 75–219, plus a search over the whole file.
  - Sample 4, `turn` line only, found by search.
  - `types/index.d.ts`, searched only.
- **Kev:**
  - `serve.py` lines 90–229, plus the function index.
  - `model.py` lines 205–225 and 395–507.
  - `train.py` lines 150–165 and 212–222.
  - `checkpoint.py` and `train.py`, temperature lines found by search.
  - `kev-4b.md`, temperature lines found by search.
- **Dossier entries read in full:** #2–#5, #9, #14, #20–#25, #27, #32, #43, #46, #47, #54, #72, #86, #90, #92, #93, #99, #104, plus the heading index.
- **Web:** two fetches of tau2-bench `evaluator_communicate.py` (current main and `37199f3`), plus the file's commit list.
- **Not done:** I did not re-read CONTRACT lines 1–74 or 220–261, or dossier entries outside the list above.

Every line of every file marked "read in full" was read.