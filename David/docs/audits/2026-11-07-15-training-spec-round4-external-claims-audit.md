I found no claim in the round-4 scope that is flatly wrong about Kev's limits or about the dataset identifiers. I found two claims that are wrong as written (Findings 2 and 4) and five that are right but imprecise. The one that matters most is Finding 1: the serve-path parity gate (§12.1) asks for a logit comparison, but Kev's serving path, as the classifier uses it, returns only probabilities rounded to 4 decimals. I edited no project file and ran nothing from Kev. Every command ran in the foreground and has exited. Today is 2026-11-07 (checked with `date`).

The Kev clone is on `fc4a17e194bca35a48c57211392ec49ea54a94ac` (`git rev-parse HEAD`; the tree is clean). Below, **K** means `...\scratchpad\kev-verify\kev` and **M** means `C:\Users\david\Documents\GitHub\HackBU-NoahDavid\Noah\mod\hooks\register.tsx`.

## Part 0: round-3 findings

| Round-3 item | Status | Receipt |
|---|---|---|
| F1 row limit | Landed (one small gap) | §6.4 now states `max_branch` = `max_state` + 640. Code: `K\kev\model.py:14,31-38` (1024 − 384 = 640) and `:112` (`len(br) > max_branch - len(S)`). The gap: only L7 has a trim rule. G2 and D2 rows quote «R_k» verbatim, so a long list item or a long pysbd "sentence" next to a full state can still break the limit. When that happens the trainer drops the whole record and prints only a count (`K\kev\train.py:104-110`). This is rare. |
| F2 stale none-pair sentence | Landed | The sentence is gone from §9.1 (grep finds no "None-pair"). |
| F3 Kev-27B precedent | Landed | §7.7 now reads "built 3,200 of its long records this way". This matches `K\docs\model-cards\kev-27b.md:163`. |
| F4 retention "≥ 0.8 up to 25%" | Landed (claim removed) | §12.3 retention is now "reported". The only "25%" left in the spec is the can't-tell rate. |
| F5 ExitPlanMode field | Not changed (deferred by the register) | The field is still unsupported. M carries every tool input as `args` (`:291`, `:305`), so the plan text should be in there, but no source names the field. |
| F6 schema vs Mod | Landed, with a new error | The ops and the edit/write-only rule are now correct (M `:621-630`), and §12.1 now uses a recorded or corrected session. But the example's patch shape is wrong; see Finding 2. |
| F7 P vs pair groups | Landed | §9.2 item 2: members "share an optimizer step (they may sit in different passes)". |

Round-3 register fixes that touch code or dataset claims:
- **R3-01 (agent text, `turn_completed`):** landed. There is a caveat about the event's premise; see the turn-reason note in Finding 7.
- **R3-11 (logits):** see Finding 1.
- **R3-12 (secrets patterns):** landed. The patterns cover every secret the dossier §5 says was found: the `sk-ant-oat01-` OAuth token, `sk-svcacct-`, and `.jwt_secret`.
- **R3-20 (identifiers):** landed. All checked against the dossier; see the verified list.
- **R3-22 (P smoke record):** see Finding 3.
- **R3-30 (`both_bad` and AgentJudgeBench coverage as hints):** landed. `both_bad` appears in dossier #90 and #93, and "query coverage" in #104.
- **F R3-03 (Open-SWE filters as hints):** landed. The filters match dossier #24, except that the spec omits #24's "no unrequested docs edits" filter, which is a design choice.
- **F R3-10 (read-only tools named):** see Finding 5.

## Findings

**1. §12.1, serve-path parity: "the winner's max |Δz| (logits) between the training forward and the serving path". Unsupported: Kev's serving path exposes no logits.**
- **Source:**
  - The current classifier serves through `kev.serve.Server.answer` (`HackBU-NoahDavid\David\classifier\app.py:94-99`, `:112-115`).
  - That path runs `model.probs_batch`, `probs_and_prefix` and `probs_with_prefix`, and each returns softmax probabilities only (`K\kev\model.py:413-414`, `:444`, `:462`, `:465-492`).
  - `Server._body` then rounds the answer through `to_answers`. A noul answer becomes `round_prob(p[1])`, which is `round(x, 4)` (`K\kev\api.py:143-153`).
  - Logits appear only in `LocalPredictor` (`K\kev\predictors.py:138-145`). That class calls `model.forward`, which is the training-style forward, not the serving path with its prefix cache, CUDA graphs and fused kernels.
- **Consequence:**
  - Read through the classifier's answers, every row with p > 0.9999 or p < 0.0001 has an infinite log-odds. That means "max |Δz|" is infinite or dominated by rounding, for the winner and for stock alike, so the gate cannot pass or fail meaningfully.
  - The builder must read `Server.probs(rec)`, which gives unrounded fp32 probabilities per question (`K\kev\serve.py:147-148`, `:189`), or add a logits output.
  - The gate should then compare log-odds (yes/no questions) or log-probabilities (choice and score questions). Raw logits cannot be recovered from probabilities: they are fixed only up to an additive constant.

**2. §6.1 event example: `"patch": {"structuredPatch": "..."}`. Wrong shape.**
- **Source:** M `:627` sets `patch: result?.structuredPatch ?? null`. The patch field *is* Claude Code's structured-hunks value, or `null`. It is not an object with a `structuredPatch` key.
- **Consequence:**
  - An event-schema validator written from the example would reject real Mod events.
  - Converters that follow the example would emit a shape the renderer never sees at runtime.
  - The validator must also accept `null` (an Edit or Write result with no `structuredPatch`).
  - The prose in the same section ("the patch as Claude Code's structured hunks") is correct; only the example is wrong.

**3. §10, pass token cap P: "smoke run on a synthetic record at `max_packed` (no real record exceeds it, 6.4)". Right but imprecise.**
- **Source:** with `--shared_prefix 1`, a record's pass cost is `len(states)·max(state) + Σbranches·max(branch)` (`K\kev\train.py:158-161`). Any record over `--pass_tokens_max` raises `ValueError` before step 1 (`:217-220`).
- **Why it matters:** at a full state, the cost is 32,768 + Q × (the longest branch). Unless every branch is the same length, that is more than `max_packed`.
  - Example: 16 every-event and twin rows, with the longest around 110 tokens, cost about 34.5K, already over `max_packed`.
  - An L7 row of 640 tokens plus about 10 short rows costs about 39.8K, against `max_packed` = 34,432.
- **Consequence:** a P measured on a balanced synthetic record at `max_packed` can fall below the cost of real records. The run then halts before step 1 (loudly, not silently), and the smoke run has to be redone. The synthetic record should be built at the largest real padded cost (state plus Q × longest branch).

**4. §7.3, tau2-bench results row: basis "V (`communicate_checks`, assertion results …)". Wrong for the assertion results.**
- **Source:**
  - Dossier #43: the results files' `reward_info` carries `action_checks`, `nl_assertions[{met, justification}]` and `communicate_checks`.
  - tau2-bench source (`src/tau2/evaluator/evaluator_nl_assertions.py`, fetched): `met` and `justification` come from an LLM call (`generate(model=DEFAULT_LLM_NL_ASSERTIONS, …)`), from its `metExpectation` and `reasoning` fields.
  - `evaluator_communicate.py` matches substrings unless the scorer is set to `SEMANTIC`, in which case an LLM decides. Which mode the 2025 results files used is unverified.
- **Consequence:** under §2 principle 3 ("every outcome-based or LLM-judged source label yield[s] to the teacher"), `nl_assertions` labels should be a hint (T), not V. As written, LLM-judged labels would override the teacher. The fix: keep `communicate_checks` as V, after confirming the substring mode was used, and make `nl_assertions` a hint.

**5. §7.2, read-only tools: "(Read, Grep, Glob, WebFetch, by tool name)". Right but imprecise.**
- **Source:** M `:7-8`: `READ_TOOLS = Read, Grep, Glob, WebFetch, WebSearch, LS, NotebookRead`, with the comment "like David's side does".
- **Consequence:**
  - Under §6.1, WebSearch (and LS and NotebookRead, where they exist) is "a tool outside this list". By the name rule it becomes a cut point and is counted as a classified event, not a read in EFFORT.
  - That contradicts §7.2's own definition of a cut point ("tool calls that change something").
  - The volume is small, but the set should match the Mod's.

**6. §6.1, tool names: "Bash (any shell, including keystroke batches and PowerShell)". Right for converters, but incomplete at runtime.**
- **Source:**
  - M passes the tool name through unchanged (`:291`, `:304`).
  - CONTRACT.md §5 lists the actions as "Edit, Write, Bash, PowerShell".
  - Noah's sample 3 has `"tool": "PowerShell"`.
  - MOD_PRD §8 acceptance check 4: the demo deletes tests "(Bash or PowerShell)", on Windows 11 (CONTRACT §1).
- **Consequence:**
  - At runtime, the Windows demo's shell events arrive as `PowerShell`. Under §6.1 they would render as `PowerShell: <command>`, a name training never shows, and an EFFORT counter keyed on `Bash` would miss them.
  - The shared renderer, not only the converters, must map `PowerShell` to Bash.
  - This sits on the M4 demo path (deleting tests).
  - It may predate round 3, but it is a claim about Mod events.

**7. §6.1, "AskUserQuestion answers become `user_instruction` items". Right but imprecise (low impact).**
- **Source:** M has no AskUserQuestion handling. The call arrives as a `tool_completed` event with the answer in the tool's result (M `:155-176`, `:290-311`). `user_instruction` items come only from `prompt.submit` (`:117-131`). David's notes say his side treats these answers as instructions.
- **Consequence:** the conversion has to happen in the shared renderer. Converters that emit `new_items` directly produce streams shaped differently from runtime streams, so the renderer-parity fixtures need a real AskUserQuestion event.

**Note on the turn's end reason (low impact):** M fires `turn_completed` at the end of every turn and attaches `turn: {reason, duration_ms, is_aborted}` (`:189-196`). CONTRACT §5 lists the reasons: answer, aborted, refusal, error. G2's wording assumes "The agent says the task is done". So G2 and G5 are asked even on aborted turns, error turns, and turns that end with a question to the user. The fact the spec claims (the final text arrives on `turn_completed`) is correct; only this premise is.

## Verified claims
- `turn_completed` carries the final text: `event.agent_text = e.answer` (M `:193-194`; sample 4).
- Agent text arrives on the next event: step text accumulates in `turn.step` (M `:139-153`) and is taken by `baseEvent` (`:264-288`), consistent with sample 2. Hook ordering is not visible in the Mod code.
- The event types are `tool_completed`, `turn_completed` and `session_started` (M `:193`, `:237`, `:292`; CONTRACT §3).
- `schema_version`, `session_id` and `event_id` are present (M `:277-279`). The backend accepts extra fields (CONTRACT §3).
- `file_changes` exist only for Edit and Write, with ops `edit` and `write` (M `:621-630`).
- The correction is attached outside `result_text` (M `:165-176`, `:307`).
- B_state = 32,767: strict rejection when token count + 1 > `max_state` (`K\kev\model.py:102`).
- `max_packed` = `max_state` + 1,664 (`:14`, `:37-38`), checked by `fits` (`:145-151`).
- `max_branch` = `max_state` + 640, so 640 tokens are left beside a full state (`:31-38`, `:112`).
- The batched training forward with shared prefix exists (`K\kev\model.py:389-392`).
- The AISI OLMo identifier, the kl0.02 sibling and the 484 failed-exploit "clean" rows match dossier #3.
- The tau2-bench repo identifiers and "join each results file to its own embedded tasks" match #43.
- SWE-Misbehavior (`duc-anh-2002` and `dxlong2000`), the AST and file-change checkers, and the appended boundary match #45.
- The Coding Agent Misalignment Atlas (instruction and intention episodes, LLM labels, SWE-chat dedupe, turn mapping) matches #32.
- SWE-bench Verified annotations (#46): per-annotator `underspecified`, the issue-text join, and the instance-id exclusion match.
- MALT (`metr-evals/malt-public`): vague_cot-family labels, the final-sample history, and M2, M4, L4, L5 match #13.
- The probe manifest exists at `docs/research/heldout-intent-probe-manifest.jsonl`: 200 rows, 50 each for implicit_goal (TRACE), request_satisfaction (IFBench), clarification_need (aspi) and still_pursuing (UserIntentBench).
- The secrets patterns cover the dossier §5 findings: `sk-ant-oat01-` through `sk-ant-…`, `sk-svcacct-`, and `.jwt_secret`.
- Arena `both_bad` (#90, #93) and AgentJudgeBench query coverage (#104) are present in the dossier.
- The note rate r = 7/644 matches CONTRACT §5.

## Coverage ledger
- **Read in full:**
  - The three skill files.
  - TRAINING-SPEC.md, lines 1-664.
  - The round-3 claims audit, lines 1-144.
  - The round-3 dispositions, lines 1-43.
  - CONTRACT.md, lines 1-261.
- **Mod code:**
  - M lines 1-669. Lines 670-1246 (UI rendering) were not read.
  - Samples 2, 3 and 4.
  - MOD_PRD.md lines 55-90 and 175-190.
  - The two notes files, searched only.
  - `types/index.d.ts` lines 1-50.
  - `David\classifier\app.py` lines 80-161.
- **Kev code:**
  - `model.py` lines 1-499.
  - `predictors.py` lines 60-219.
  - `serve.py` lines 1-260, plus a grep of the rest.
  - `train.py` lines 95-120, 150-225 and 305-330.
  - `api.py` lines 143-165.
  - `kev-27b.md` lines 157-164.
- **Dossier:** entries #3, #13, #24, #32, #43-#46, #90-#93 and #104 in full, plus the heading index and a grep for secrets and PII.
- **Data:** the probe manifest, all 200 rows parsed and tallied.
- **Web:** two tau2-bench evaluator source files.
- **Reports -1, -9, -31 and -33:** searched for the cited terms only, not read in full.

Every line of every file marked "read in full" was read.