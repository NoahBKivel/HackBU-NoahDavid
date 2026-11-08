I found no claim in the round-3 scope that is flatly wrong. All six round-2 findings landed, and none of the fixes added a wrong fact. Four claims are right but imprecise, and one fix left a stale sentence behind. Outside the scope you named, I found two things that do matter for a builder (Findings 6 and 7 below). I edited no project file and ran nothing from Kev. Every command ran in the foreground and has exited.

The Kev clone is on commit `fc4a17e194bca35a48c57211392ec49ea54a94ac` (checked with `git rev-parse HEAD`; the tree is clean). Below, **K** means `C:\Users\david\AppData\Local\Temp\claude\e4a7ca8b20dbf3e0\48a356b8-0453-4fa7-b972-ac20964e049d\scratchpad\kev-verify\kev`.

## Part 0: round-2 findings

| Finding | Status | Receipt |
|---|---|---|
| R2-F1 none pairs | Landed; one stale sentence left (Finding 2) | §9.1 now passes `--p_none_pair 0` and no `--none_pair_max_state`. That passes the flag check (`K\kev\train.py:454-455`, which only fires when the flag is set). With no `--none_pair_max_state`, `pairs` is None (`:609`), and `record_variants` adds a pair only if `p_none_pair > 0` (`:298`), so no none pairs are made. |
| R2-F2 `KEV_TEMPERATURE` | Landed | `LoadOptions.from_env()` is called only in `K\kev\serve.py:339`, `K\kev\benchmark.py:193` and `K\kev\evaluate.py:193`, and it reads the variable at `K\kev\checkpoint.py:144`. The other mentions (scripts, the Space app, model cards) are docstrings, or `runs/drift-v1` passing the variable to a subprocess. |
| R2-F3 builder tokenizer | Nothing left to check | The long-state builder patch was cut (R2-22); §9.2 no longer mentions `build_long_states`. |
| R2-F4 SDPA wording | Not changed (defended); acceptable | On CUDA the trainer always gets SDPA (`K\kev\model.py:252`). |
| R2-F5 checkpoint format | Landed | §9.2 item 4 says a full-weight checkpoint with `weights="full"`. Kev loads that layout (`K\kev\checkpoint.py:4-7`, `:182-188`, `:282-291`, `K\kev\model.py:257`). The serve-path fallback in §12.1 now depends on α. |
| R2-F6 detail-budget floor | Landed | §10's formula now matches §6.4: max(0.40·B_state − tokens(instructions + documents), 0.15·B_state). |
| Builder note on P | Landed | §10 says "P ≥ the padded cost of the largest single record (a larger record halts the trainer)". The trainer raises `ValueError` before step 1 (`K\kev\train.py:217-220`). |

Register fixes that touch code or dataset claims:
- **R2-02 (B_state):** landed; see Finding 1.
- **R2-05 (`LoadOptions(temperature=1.0)`):** landed (`K\kev\checkpoint.py:240-241`).
- **R2-09 (probe polarity and conversions):** landed.
- **R2-14 (identity parity):** landed.
- **R2-20 (WebFetch, TodoWrite, ExitPlanMode):** landed for WebFetch and TodoWrite. ExitPlanMode has no source either way; see Finding 5.
- **R2-21 defence (correction outside `result_text`):** confirmed again.
- **R2-31 (cost rows):** the arithmetic checks out.
- **R2-32 (pysbd):** landed.
- **A2 (retention set of 2,172):** landed; see Finding 4.
- **F18 (Kev-27B long records):** landed, but the wording is imprecise; see Finding 3.

## Findings

**Finding 1. §6.4, the fill rule: a row that does not fit is not always admissible in a sibling. Right but imprecise.**
- **Spec:** "A record's question rows share Kev's packed allowance (`max_packed` = `max_state` + 1,664, checked by Kev's own fit test); rows that do not fit move to a sibling record with the same state, in the same pair group."
- **Source:**
  - `fits` checks two limits, not one (`K\kev\model.py:145-149`).
  - One is the packed limit, which the spec names.
  - The other is a limit on each row (state plus one question): `if len(br) > max_branch - len(S)` (`K\kev\model.py:112`), with `max_branch = 1024 + (max_state − 384)` (`:31-38`).
  - At `--max_state 32768`, `max_branch` is 33,408. With a full state (32,767 tokens plus the `<state>` token), every single question branch must therefore be at most 640 tokens. The whole question set gets 1,664.
- **Why it matters:** an L7 row carries the whole correction text, which includes "Evidence: <event content>" for up to three items (§6.5, no length cap), plus six option descriptions. It can easily pass 640 tokens. Near the top of the 16–32K long-record range, such a row cannot fit in any record, sibling or not.
- **Consequence:** the trainer silently drops the whole record and prints only a count (`K\kev\train.py:105-110`). Long L7 records are lost without notice. A builder needs to either keep B_state below the limit by the length of the longest branch, or cap the length of L7's «text».

**Finding 2. §9.1, the loss bullet: a stale sentence. Right but moot.**
- **Spec:** "None-pair passes add work per step without changing S." A few lines later: "the none-of-the-above minimal pairs … are all off."
- **Source:** with `--p_none_pair 0`, no none-pair passes exist (`K\kev\train.py:298`, `:609`).
- **Consequence:** none for the run. A reader may wonder whether none pairs are still on. The sentence can be deleted.

**Finding 3. §7.7, "Kev-27B built its long records the same way". Right but imprecise.**
- **Source:** `K\docs\model-cards\kev-27b.md:163` describes "Long states | 3,200 | Kev-corpus states embedded in 8k–32k-token documents; labels inherited exactly". The next row is "Long documents | 7,617 | Documents assembled by code, labels computed by code".
- **Why it's imprecise:** the 7.4% figure in §3 is (3,200 + 7,617) / 145,840 = 7.42%. Only the 3,200 long states were built by embedding a state in other documents; the long documents were built a different way. The card also does not say the padding documents were "unrelated real" ones.
- **Consequence:** small. The precedent supports the method, but it covers 2.2% of Kev-27B's records, not its whole 7.4%.

**Finding 4. §10, the retention row: "passes with probability ≥ 0.8 up to 25% disagreement". Right but imprecise (a rounding-level nit).**
- **Source:** decision-v7 has `development.jsonl` with 1,204 records and `calibration.jsonl` with 968 (`wc -l`; the manifest gives the same counts). 1,204 + 968 = 2,172.
- **Arithmetic:** at parity with 25% disagreement, the standard error is √(0.25/2172) = 0.01073. The pass probability is Φ(0.03/0.01073 − 1.96) = Φ(0.836) = 0.798.
  - Per question (2,616 questions: 1,468 + 1,148) it is 0.87.
  - Grouping by minimal pairs would lower it.
- **Consequence:** negligible. The claim holds up to about 24.9% disagreement, or holds as stated if accuracy is counted per question.

**Finding 5. §6.1 and §6.4, ExitPlanMode's plan text. Unsupported (low impact).**
- **Spec:** "ExitPlanMode's plan text renders on a `plan:` line."
- **Source:**
  - The Mod has no ExitPlanMode handling. It sends every tool call's input fields as `action.args` (`HackBU-NoahDavid\Noah\mod\hooks\register.tsx:291`, `:305`).
  - `Noah\MOD_PRD.md:74` (FR-12): "The plan-mode plan from ExitPlanMode is **not** collected."
  - No source I read shows the name of ExitPlanMode's input field, and Noah's sample events contain no ExitPlanMode event.
- **Consequence:** the renderer builder has to find the plan's field in a recorded Mod session. Phase 1's golden fixtures will not exercise it.

**Finding 6 (outside the named scope). §6.1, §6.4 example, and the §12.1 renderer-parity fixtures: the sample events do not match what the Mod actually emits. Right per CONTRACT.md, wrong per the Mod code.**
- **Spec:**
  - §6.1 gives `"op": "edit|write|delete"` and `"patch": "..."`.
  - §6.4's example block is `[E42] Bash: rm tests/test_slow.py … files: tests/test_slow.py (delete, -88) / patch: <diff>`.
  - §12.1, Phase 1, uses "raw Mod-event JSON fixtures (Noah's sample events …)".
- **Source:**
  - The Mod builds `file_changes` only for Edit and Write (`register.tsx:622`).
  - It emits only the ops `write` and `edit` (`:626`).
  - The patch is Claude Code's `structuredPatch` object (`:627`), not a diff string.
  - Shell commands get no `file_changes` at all.
  - `Noah\backend\samples\3_tool_bash_deletes_tests.json` is hand-written: it has `delete` ops on a PowerShell command and `stdout`/`stderr` at the action level.
  - `2_tool_edit_normal.json` has a diff-string patch.
  - The CONTRACT.md §3 example also shows `"op": "delete"` on a Bash `rm`.
- **Consequence:**
  - Golden bytes frozen from Noah's samples would contain a `files: … (delete …)` line on shell events. The real Mod never produces that line.
  - Converters that emit delete ops for shell deletions would teach a cue that does not exist at runtime, which breaks the "train equals runtime" guarantee. This matters for M4, since deleting tests is its canonical case.
  - Fix: freeze Phase 1 fixtures from recorded Mod sessions, or a sample corrected to the code's output. Converters should then emit what `register.tsx` emits.

**Finding 7 (outside the named scope). §6.4 and §10, the P cap against pair-group batching. A builder note, not a claim error.**
- **Spec:** Patch 2 makes each pair group "one unit, so its members always share a batch". Finding 1's siblings share a pair group.
- **Source:** with `--pass_tokens_max`, Kev measures one record at a time (`K\kev\train.py:217-220`), and with a shared prefix a pass costs each state once (`:158-163`).
- **Why it matters:** if "share a batch" means "share a pass", two 32K siblings (or a 32K note pair) need P of at least about 2 × 32,768 plus their branches.
- **Consequence:** size P on the largest pair group, or let one optimizer step hold a pair group across several micro-batches.

## Verified claims
- B_state = 32,767: Kev rejects a state when its token count + 1 > `max_state` (`K\kev\model.py:102`). `max_state` = 32,768 is within [384, 65,536] (`:26`, `:31-38`).
- `max_packed` = `max_state` + 1,664 = 34,432 (`K\kev\model.py:14`, `:37-38`), checked by `fits` (`:145-149`).
- The state is counted on the materialized string state, which `api.render` returns unchanged (`K\kev\api.py:50-53`, `:117`; `K\kev\data.py:398-400`).
- Kev loads `weights="full"` from `config.json` + `model*.safetensors`, in the dtype head.pt names. `lora_scale` must be 1 for a full-weight checkpoint (`K\kev\checkpoint.py:182-188`, `:237`, `:268-291`).
- `LoadOptions(temperature=1.0)` gives raw logits (`K\kev\checkpoint.py:105`, `:241`).
- `KEV_TEMPERATURE` is read only by kev.serve, kev.benchmark and kev.evaluate (grep receipts above).
- `--p_none_pair 0` without `--none_pair_max_state` is valid and makes no none pairs (`K\kev\train.py:403-405`, `:454-455`, `:298`, `:609`).
- The noul target keys `"false"`/`"true"` and score label indices match Kev's API (`K\kev\api.py:95-101`; `K\kev\data.py:389-395`).
- The decision-v7 development and calibration partitions have 1,204 and 968 records, 2,172 together (files and manifest).
- WebFetch's key argument is `url` (`register.tsx:614`). Every tool's input becomes `args` (`:291`, `:305`).
- `todos` come from TodoWrite's `content` and `status` (`register.tsx:160-162`; `types/index.d.ts:28`). The list is updated before the event is built (`:160-176`).
- The correction is attached outside `result_text`: it goes only into `answer.context` (`register.tsx:165-173`), and `result_text` is `ran.text` (`:307`).
- The Mod sends every tool call, reads included. `READ_TOOLS` is used only by the mock classifier (`register.tsx:154-185`, `:542`).
- TRACE: 517 conversations (249 benign, 268 hacked), so 467 are not in the probe. The probe's 50 TRACE ids are unique.
- TRACE's tool results sit inside assistant messages without ids, and it has scripted follow-up user turns that can challenge or expose the hack, as in trajectory_0018 (dossier #108).
- G5 at completion claims is supported (dossier #108: "G5 (final success claims)").
- Probe polarity:
  - implicit_goal: true = benign, which maps to M1 no.
  - request_satisfaction: true = passes the strict verifier, which maps to M2 no.
  - clarification_need: true = base_prompt (should ask), which maps to M7 yes.
  - still_pursuing: true = preserved or new predicate, which maps to G1 yes.
  - Each capability has 25 true and 25 false (manifest; report -31 lines 67-71).
- Probe item structure for IFBench (request and response), aspi (prompt and ground-truth tool calls) and UserIntentBench (original request, update, "Next I'm building this part: <predicate>") matches report -31 line 75 and dossier #39 and #42.
- pysbd exists, and `Segmenter(language='en', clean=False, doc_type=None, char_span=False)` takes `clean=False` (installed pysbd 0.3.4, checked with `inspect.signature`).
- Kev-27B's long records are about 7.4% of its training set: 10,817 / 145,840 (`kev-27b.md:157-163`).
- The long-gate size n = 0.06 / (0.03/3.24)² ≈ 700, and the Hanley–McNeil standard error is about 0.034–0.035 at 60 positives with AUROC 0.8.
- S = ⌈R/16⌉ under `--pass_tokens_max` (`K\kev\train.py:579`).

## Coverage ledger
- **Read in full:**
  - The three skill files: reading-context, out-of-cutoff and receipts-before-claims.
  - TRAINING-SPEC.md, lines 1-673.
  - The round-2 claims audit, lines 1-120.
  - The round-2 dispositions, lines 1-70.
  - CONTRACT.md, lines 1-262.
  - Report -31, lines 1-98.
  - Report -9, lines 1-76.
  - `types/index.d.ts`, lines 1-48.
- **Kev code read by range:**
  - `model.py`: 1-175 and 240-278.
  - `train.py`: 95-120, 200-225, 275-335, 365-490 and 523-680.
  - `checkpoint.py`: 1-362, in full.
  - `data.py`: 285-410.
  - `api.py`: 1-142.
  - `kev-27b.md`: 150-175.
- **Mod code read by range:** `register.tsx` lines 100-420, 530-560 and 596-640. The rest of that file was not read.
- **Dossier:** entries #39 (777-793), #42 (830-848), #69 (1171-1180), #107-#108 (1601-1624) and the heading index.
- **Data:**
  - The probe manifest: all 200 lines, parsed and tallied.
  - decision-v7: manifest `files`, `protocol` and `context`, and the development and calibration partitions (counted and tallied by source).
  - Noah's sample events 2 and 3.
- **Reports -1 and -33:** searched for the cited lines only.
- **Mod docs:** MOD_PRD.md and the notes files, searched for ExitPlanMode and FR-12/13/24 only.

Every line of every file marked "read in full" was read.