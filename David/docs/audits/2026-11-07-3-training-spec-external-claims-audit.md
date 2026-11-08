I found 13 claims that need fixing: 3 that are wrong or would block the build, 1 hidden mismatch with Kev's length limit, and 9 that are right but imprecise or not backed by the source. About 70 other claims checked out. Nothing in any project file was edited, and nothing from the Kev repository was run.

The Kev clone is at `C:\Users\david\AppData\Local\Temp\claude\e4a7ca8b20dbf3e0\48a356b8-0453-4fa7-b972-ac20964e049d\scratchpad\kev-verify\kev`, on commit `fc4a17e194bca35a48c57211392ec49ea54a94ac`. Code paths below are relative to it (K = that folder).

## Findings

**F1. §7.3, replay table. Wrong.**
- **Spec:** "jaredpalmer/kev-suites decision-v7 train | 2,000 | Through the trainer's `--suite evals/v7/decision-v7 --replay` path; yes/no labels rebalanced to 50/50 per source (boolq, agnews); minimal-pair groups kept together."
- **Source:** `K\kev\train.py:93-97`: `pool = load_split(a.suite, "train"); replay = random.Random(f"replay:{a.seed}").sample(pool, min(a.replay, len(pool)))`, followed by `reqs = reqs + replay`.
- **Why it's wrong:** `--replay` draws a plain random sample from the whole pool. It cannot rebalance yes/no labels per source, and it cannot keep minimal-pair groups (`pair_id`, `sibling`) together. §9.2 lists no patch that adds either.
- **Consequence:** a builder who uses `--replay 2000` gets neither property. Either pre-build the 2,000 records and pass them through `--data` (dropping `--replay`), or add a patch to §9.2.

**F2. §1, §9.3 and §12.1, the four adapter parts and the α = 0 identity. Wrong as specified.**
- **Spec:**
  - §1: "It has four parts: a LoRA weight change Δ, an interpolation weight α that scales Δ, … The exact core is stock Kev-4B reading the same states; the four parts are the only deviations from it."
  - §9.3: "α scales the LoRA change at load".
  - §12.1: "at α = 0 … logits equal stock Kev's, bit-exact in fp32".
- **Source:**
  - `K\kev\train.py:553-557`: `--init_from` warm-starts both the LoRA adapter and the pointer head.
  - `K\kev\train.py:576-578`: the head's parameters are in the optimizer, at `head_lr or lr`. The pointer head therefore trains too.
  - `K\kev\checkpoint.py:104`: Kev's built-in α is `lora_scale`, documented as "interpolation between base (0) and fine-tuned weights (1)". `K\kev\checkpoint.py:307-311` multiplies the whole adapter's `scaling` by it.
- **Why it's wrong:**
  - The trained pointer head is a fifth deviation that the spec does not list.
  - Kev's own α knob scales the whole adapter, so `lora_scale = 0` gives the Qwen3.5 base, not stock Kev-4B.
  - "α scales Δ relative to Kev-4B" has no native support. The change is B₁A₁ − B₀A₀, which no single LoRA `scaling` factor can express.
- **Consequence:** the identity-parity gate cannot pass with `KEV_LORA_SCALE`. Two options:
  - Write a weight-level interpolation W_kev + α(W_new − W_kev) that also interpolates the head, and add it to §9.2.
  - Freeze the head. That would also need a patch, because `kev.train` has no head-freeze flag.

**F3. §9.1 and §12.1, the kernel requirement. Unsupported; as written, it stops the run.**
- **Spec:** "the fused DeltaNet kernels must be active (no torch fallback) and FlashAttention on the 8 full-attention layers; the run does not start otherwise."
- **Source:**
  - `K\kev\model.py:252-255`: the backbone loads with `attn = attn or ("sdpa" if … cuda …)`.
  - `K\kev\train.py:370-438`: `parse_args` has no flag for the attention backend.
  - `K\kev\shared_prefix.py:113-114`: the shared-prefix path passes explicit custom masks to the attention layers.
  - `K\kev\checkpoint.py:117-119`: Kev's "fused" kernels are a serving option ("rewrite a merged hybrid backbone … kev.serve turns it on"). During training, the DeltaNet layers run on fla's Triton kernels instead (`K\kev\shared_prefix.py:9, 16-19`).
- **Why it's wrong:** the stock trainer cannot run FlashAttention. It always uses SDPA with explicit masks, and FlashAttention-2 does not accept arbitrary masks. "Fused DeltaNet kernels" is a serving feature, not a training one. I could not verify the count of 8 full-attention layers, because I did not read the model config.
- **Consequence:** the kernel check as worded halts the run. Reword it as "fla Triton kernels active for the DeltaNet layers; SDPA for attention", or add a patch.

**F4. §6.4 state budget against §9.1 `--max_state 32768`. Hidden mismatch with Kev's admission rule.**
- **Spec:** "budget B_state = 32,768 tokens" together with `--max_state 32768`.
- **Source:**
  - `K\kev\model.py:101-103`: a strict encode raises when `len(state_tokens) + 1 > max_state`. The +1 is the `<state>` token.
  - `K\kev\model.py:31-38`: the whole record may be at most `max_packed = 2048 + (max_state − 384)`, which is max_state + 1,664 tokens.
  - `K\kev\train.py:102-110`: records that don't fit are dropped, and the run only prints a count.
- **Why it matters:**
  - A state filled to exactly 32,768 tokens is rejected outright.
  - Every question on one record shares 1,664 tokens. The every-event set uses about 900 tokens of wording alone (my estimate: 3,637 characters ÷ 4), plus per-question overhead.
  - D1/D3 adds one question per detailed event, so long records with many detailed events go over the limit.
- **Consequence:** the longest records (the f_long share) get dropped silently. Either set B_state to max_state minus the question tokens minus 1, or raise `--max_state`. Also count tokens with Kev's tokenizer and Kev's state rendering.

**F5. §9.5, temperature override. Right but imprecise, with a real consequence.**
- **Spec:** "Kev's stored temperature is overridden (`KEV_TEMPERATURE=1`)".
- **Source:**
  - `K\kev\checkpoint.py:132-144`: `from_env` is "For command-line entry points only; library code passes an explicit LoadOptions."
  - `K\kev\serve.py:339` is the only code that calls `from_env`.
  - `K\skills\kev-deploy\scripts\kev_serve.py:97` builds `LoadOptions(...)` itself, so the checkpoint's temperature is applied.
  - Report -31 §0: the deployed project runtime loads through an explicit `LoadOptions` and serves at T = 2.406.
- **Why it matters:** the environment variable only works for `python -m kev.serve`. The project's Modal class ignores it.
- **Consequence:** stock Kev would be served at 2.406 with T_q applied on top. Adapters saved by `kev.train` already carry T = 1, since nothing in the trainer sets a temperature. The fix is to pass `LoadOptions(temperature=1.0)`.

**F6. §9.1, option shuffling. Right but imprecise, and part of the default behaviour is missing.**
- **Spec:** "Option order is shuffled on every record (the trainer's native behaviour)."
- **Source:** `K\kev\data.py:320-343` (`augment`) works on choice questions only ("Choice only: permute option order (always)"). Yes/no and score questions pass through unchanged.
- **Unstated default behaviour:** with the default `--p_none 0.1`, `--p_none_distract 0.12` and `--p_distract 0.15` (`K\kev\train.py:400-402`), hard-label choice questions with three or more options sometimes have the correct option replaced by "none of the above", or gain a distractor option. Questions with a `target` are only permuted (`data.py:330-331`).
- **Consequence:** G2's four options and L7's six options get extra options or a relabelled answer on about 37% of their hard-label rows. The spec should say so, or set those flags to 0.

**F7. §12.1, the 0.0055 figure. Right but imprecise.**
- **Spec:** "(sourced: bf16 serving noise measured at 0.0055)".
- **Source:** report -31 §C4 measured something narrower: a segment-cache prototype against a full prefill. That was 60 comparisons, max |Δp| 0.0055, both sides in bf16, and the report says "Not bit-exact (DeltaNet chunking restarts at the boundary; bf16)".
- **Why it matters:** this is a comparison between two serving paths. It is not a comparison of the training forward pass against the server. The serve-path gate compares more things at once: fp32 weights with bf16 autocast and an unmerged LoRA against merged bf16 weights with fused kernels and CUDA graphs. Kev's own comparable figure is max |dp| 0.009 for merged against unmerged on 27B (`K\kev\checkpoint.py:100-101`).
- **Consequence:** the 0.01 threshold has little headroom and is not supported by the cited measurement.

**F8. §9.2 item 3, the `build_long_states.py` cap. Right but imprecise.**
- **Spec:** "`build_long_states.py`'s 7,552-token cap is raised to the 32K budget and the script takes our records as input."
- **Source:** `K\scripts\build_long_states.py`:
  - Line 26 imports `MAX_TRAIN_STATE_8K` (7,552), but line 58 rejects at `min(1.25*length, 7552 - 64)`. The real cap is 7,488.
  - Lines 122-123 also require every dev record to fit the 8K serving context.
  - Lines 27 and 109 count tokens with the Qwen3.8-27B admission tokenizer, over the JSON serialisation of the state.
  - Lines 29 and 111 hard-wire the input to decision-v7.
  - Line 49 builds states as `{"records": [...], "primary_record", "note"}`.
- **Consequence:** two more limits need changing. The script's output format is also a training-only state format, which conflicts with design principle 2 ("No training-only formatting exists") and with §6.4. Sections 7.3 and 7.7 never say what the script's output is used for.

**F9. §9.1, the triton pin. Right but imprecise.**
- **Spec:** "triton 3.7.1 (later triton breaks fla 0.5.2 at import)".
- **Source:**
  - `K\uv.lock:1904-1905` locks triton 3.4.0.
  - `K\skills\kev-deploy\scripts\kev_serve.py:61` asks for `triton>=3.7.1`.
  - Report -31 §4 item 1 saw only 3.9.0 fail.
- **Why it matters:** "later" goes beyond the evidence; versions between 3.7.1 and 3.9.0 were never tried. Torch 2.8.0, transformers 5.17.0, peft 0.21.0 and fla 0.5.2 all match the lockfile or `FLA_VERSION`. However, all of these pins were measured in the serving image, not in training.

**F10. §7.3, label basis for terminal-wrench and Goodfire. Unsupported.**
- **Spec:**
  - terminal-wrench: "V (`key_hack_steps`)".
  - Goodfire: "V for enacted flags".
  - §2.3: "A label from a human reading the visible trace or a rule over visible tool calls outranks…"
- **Source:**
  - Dossier entry #2: "Labels, `explanation`, `observed_categories` and `key_hack_steps` are LLM judgments plus reward".
  - Dossier entry #5: labels come from a 3-vote LLM judge, and an audit of 30 flags found "6 clear, 10 borderline, 14 disagree".
- **Why it matters:** these labels come from LLM judges, not from humans or rules. By the spec's own definition they should not be final over the teacher.

**F11. §7.3, eungyeuk label basis. Unsupported.**
- **Spec:** "V (negatives)".
- **Source:** dossier entry #9 says the files carry "no hack label" and the holdout grading output is not shipped. Only 258 of about 4,300 runs were sampled.
- **Why it matters:** the negative labels rest on a sample check, not on a label.

**F12. §7.3, terminal-wrench grouping. Imprecise.**
- **Spec:** "five near-duplicates per task".
- **Source:** dossier entry #2 says "5 near-duplicate hack runs per task and model". With 3 models, that is up to 15 per task. Grouping by task still covers this.

**F13. §12.3, the retention tolerance. Imprecise attribution.**
- **Spec:** "(the 3-point tolerance of Kev's own validation rule)".
- **Source:**
  - `K\README.md:38`: Kev's 3-point rule is for validating context length, measured on CUAD.
  - `K\skills\kev-finetune\scripts\kev_modal.py:306-313`: Kev's retention check on 300 decision-v7 dev records only reports results and sets no tolerance.
- **Why it matters:** applying the 3-point figure to retention is the spec's own choice, not Kev's rule.

## Claims verified correct

**Command and trainer flags**
- Every flag in the §9.1 command exists (`K\kev\train.py:370-438`).
- `--init_from repo@sha` is accepted (`K\kev\checkpoint.py:30, 44`).
- The decision-v7 manifest does not pin Qwen3.5-4B-Base, so passing `--base_revision` is required and correct (manifest `base_revisions`; `train.py:512-520`).
- `--max_state 32768` is within the allowed range [384, 65536] (`model.py:26, 35`; `train.py:452`).
- `--shared_prefix` defaults off for LoRA, so it must be passed explicitly (`train.py:440`).
- `--pass_tokens_max` needs `--length_sort 1` and a hybrid backbone, and conflicts with `--row_budget` and `--perm_kl` (`train.py:464-466, 558-562`).
- `--none_pair_max_state` needs `--p_none_pair > 0`, and the pairs count in the length-sort cost (`train.py:404-405, 454-455, 194-197`).
- `--replay` needs both `--data` and `--suite` (`train.py:456-457`).
- Soft cross-entropy is used whenever `target` is present (`train.py:47-49`).
- Every question must carry a `label` (`data.py:379`).
- The target formats match: `"false"`/`"true"` keys for yes/no, an integer index for score (`data.py:400-409`).
- The eval-only list in §6.3 exactly matches `data.py` `EVAL_ONLY` plus the manifest's `eval_only_sources` (`data.py:290`; manifest; `train.py:113-116`). The name check does not catch eval-only datasets inside tasksource rows, but that is a design point.
- OneCycle uses `pct_start=0.1` (`train.py:588`). "Decay to 0" really ends near max_lr/250,000 (torch defaults), and the warm-up starts at max_lr/25.
- With `--pass_tokens_max`, steps = ⌈R/16⌉, so S ≈ 763 at R = 12,200 (`train.py:583`).
- `--resume` and snapshots are refused for LoRA runs, so §9.2 patch 1 is genuinely needed (`train.py:472-477`).

**Pins and serving**
- torch 2.8.0, transformers 5.17.0 and peft 0.21.0 match `K\uv.lock`; fla 0.5.2 matches `FLA_VERSION` (`K\kev\fused_qwen35.py:53`).
- Kev-4B revision `6cfce5c2…`, base revision `1001bb4d…`, and a checkpoint temperature of 2.406 match report -31 §0.
- `KEV_TEMPERATURE=1` means raw logits (`checkpoint.py:105`), with the scope caveat in F5.
- Screen budget 8,192 is Kev-4B's validated length (README:38).
- The long-context rule ("within 3 points of 8K at the 95% lower bound") matches README:38.
- The 300-record decision-v7 regression set matches `kev_modal.py:307`.
- H100 at $3.95/h matches report -1 §3.

**Dataset counts and arithmetic**
- decision-v7 has 12,576 records and 15,576 questions (manifest; dossier #79).
- boolq is 64% true and agnews 25% true (dossier #79).
- Kev-27B's long share is about 7.4% (dossier §5).
- Σn^plan = 10,630, with goal-flip pairs counted inside their objective, so s = 0.809.
- 2,000 + 500 + 500 = 3,000 replay; 200 + 200 = 400 long; r = 7/644 = 0.011, giving about 537 note-bearing records.
- The held-out probe manifest has 200 items (report -31 §3).

**Per-source facts in §7.3, all against the dossier**
- CheatBench (#1): MIT; Pilot `stdout` stream-json; `$NN` placeholders; HAL-USACO; `attempt` rows are positives; the first offence is recomputed rather than taken from `loc_line_start`; the OAuth token and canaries are scrubbed.
- impossible-swe (#15): gated; `label_class` and `is_hack`; "DO NOT MODIFY THE TESTS".
- HVTB (#6): `harbor auth login`; the L2/L3 prohibition sentences; `admin/`; `solve.sh`.
- willjgriff (#10): `prompt.txt` and `transcript.json`, and all the field names.
- terminal-wrench (#2): stripped and sanitized variants; pairing with baselines; keystrokes become Bash events.
- CATCH (#11): 16 duplicates; the family value with a leading space; the NonHacking companion.
- Goodfire (#5): channels; `node_index`; considered-only rollouts as negatives; the appended section; `sampled=false` nodes.
- aria (#4): the `run_tests` rules.
- AISI OLMo (#3): 484 relabelled clean rows; the prohibition rewrite.
- TB-science (#22): `extra.raw_arguments`; canary; final claim; mid-work drops.
- openguardrails (#23): `dsh` scaffold and `final_response`.
- Open-SWE (#24): claudecode split; `metadata.reference_patch`; `reasoning_content`; filters.
- TonyDzi (#21): hook template table; PII pass.
- tau2 (#43): join to embedded tasks; `communicate_checks`; write without an explicit yes.
- IF_multi (#66): per-instruction checkers; position and paraphrase; RF negatives after filtering.
- AgentIF (#70): blank-line split; `state: success`; broken checkers; Chinese-heavy records.
- Atlas (#32): dedupe against SWE-chat.
- InFoBench (#72).
- SWE-Misbehavior (#45): the boundary is appended.
- Ambig-SWE (#47).
- SWE-bench annotations (#46): instance-id exclusion.
- IN3 (#54): 80/20 skew.
- JL-ActionBoundary (#56): families.
- lhaw (#40): SWE-Bench Pro part.
- SWE-chat (#20): pushback rule; success ≥ 70; paths.
- HelpSteer3 (#86): preference from −3 to 3.
- The arena sets (#90, #92, #93): `both_bad` and tags.
- WildFeedback (#99).
- UserBench (#103).
- AgentJudgeBench (#104).
- rpotham (#14): user-side relabel; `api_key_exfil`; `[TOOL_CALL]`; release obligations.
- CodeTraceBench (#25): `agent_state.pkl`; `step_id`.
- monitoringbench-honest (#27): 2 side-task-C runs and 5 scoreless runs; `side_task_*` and scores excluded.
- tasksource (#85): `license_use`; CLINC and SGD dropped; `kind` mapping.
- QuALITY (#81): padding, pointer, option shuffle.
- hard-v1 long_policy (#80): fresh instances.
- Secrets-scan strings and the §7.9 held-out and not-used lists match dossier §5 and entries #12, #13, #19, #39, #42, #53, #68, #69, #74, #82, #83, #95-#97, #101, #102 and #107-#114.

**Not checkable from the given sources:** the "Releasing the Inner Jev" T < 1 result, the ≤ 1:3 data-mixing ratio, the 7/644 desktop measurement, the "≥ 33% non-target" study, and the "8 full-attention layers" count.

## Coverage ledger
- **Skill files** (reading-context, out-of-cutoff, receipts-before-claims): every line read.
- **TRAINING-SPEC.md**, 1–657: every line read. These reads were in my context before the crash and were not repeated, since the context survived; that is safe only because nothing was edited during the task.
- **Reports -1** (1–171), **-9** (1–76) and **-31** (1–98): every line read.
- **DATASET-DOSSIER.md**, 1–1874: every line read.
- **Kev source, read in full:** `kev/train.py` 1–680 and `scripts/build_long_states.py` 1–137.
- **Kev source, read in part:**
  - `kev/data.py` 270–410. Lines 1–269 are the source builders and were not needed.
  - `kev/model.py` 1–151 and 228–277.
  - `kev/checkpoint.py` 100–149.
  - `kev/suite.py` 178–241.
  - `kev/shared_prefix.py` 1–40.
- **Kev source, searched only:** `kev/serve.py`, `skills/kev-deploy/scripts/kev_serve.py`, `skills/kev-finetune/scripts/kev_modal.py`, `kev/fused_qwen35.py`, `uv.lock`, `pyproject.toml`, `README.md`, and the decision-v7 manifest (its key fields were printed).

Every line of the spec, dossier and reports is covered. The Kev code was read wherever a claim depended on it, not end to end.

After the crash I ran each command in the foreground, one at a time, and started no background processes.