I found two claims that are wrong and four that are right but imprecise. All 13 round-1 external-claims findings landed. Two of them landed with a new error, and the fix for a third rests on a mistake in the round-1 audit itself. Nothing in the project was edited, and nothing from the Kev repository was run.

The Kev clone is on commit `fc4a17e194bca35a48c57211392ec49ea54a94ac` (checked with `git rev-parse HEAD`; the tree is clean). Below, **K** means `C:\Users\david\AppData\Local\Temp\claude\e4a7ca8b20dbf3e0\48a356b8-0453-4fa7-b972-ac20964e049d\scratchpad\kev-verify\kev`.

## Part 0: the round-1 findings

| Finding | Status | Receipt |
|---|---|---|
| C-F1 replay | Landed | `--suite`/`--replay` are gone from the command. The §7.3 records are pre-built and passed through `--data`. `load_records` keeps each record's own `_meta`, including `source` (`K\kev\data.py:382-383`). Without `--suite`, the only source check is `EVAL_ONLY` (`K\kev\train.py:113-116`), and no decision-v7 or hard-v1 training source is on it. |
| C-F2 α = 0 identity | Landed | §1 now counts LoRA plus head as Δ. Interpolation is in weight space (§9.2 item 5) and no longer uses `lora_scale`. The checkpoint format is a gap: see R2-F5. |
| C-F3 FlashAttention | Landed | The rule is now fla Triton kernels plus SDPA. The wording is slightly off: see R2-F4. |
| C-F4 state budget | Landed | Checked against `K\kev\model.py:31-38` and `:101-103`. See the verified list. |
| C-F5 temperature | Landed with new error | `LoadOptions(temperature=1.0)` is correct (`K\kev\checkpoint.py:241`). The added parenthetical is wrong: see R2-F2. |
| C-F6 none-of-the-above | Landed with new error | The three `augment` flags are 0, but none pairs stay on: see R2-F1. |
| C-F7 0.0055 | Landed | The figure is gone. §12.1 uses the relative 1.5 × stock gap. |
| C-F8 long-state builder | Landed | Cap 7,488 (`K\scripts\build_long_states.py:58`), 8K dev-fit check (`:122`), hard-wired decision-v7 input (`:29`, `:111`). The tokenizer clause rests on a round-1 error: see R2-F3. |
| C-F9 triton | Landed | Matches report -31, line 87 ("resolves 3.9.0; fla 0.5.2 then fails at import"). |
| C-F10 Terminal Wrench, Goodfire | Landed | Both are T. Dossier #2: "LLM judgments plus reward". Dossier #5: "gpt-5.6-sol judge, 3 votes". |
| C-F11 eungyeuk | Landed | T. Dossier #9: "no hack label in the files"; "In 258 sampled trajectories, 0 submitted patches touched…". |
| C-F12 Terminal Wrench duplicates | Landed | "up to 15 … 5 per task and model". Dossier #2 gives 3 models and "5 near-duplicate hack runs per task and model". |
| C-F13 3-point rule | Landed | Now "borrows from Kev's context-validation rule". `K\README.md:38` says CUAD, 3 points, 8k, 95% lower bound. |

Register fixes that touch code or dataset claims:
- **O-F7, retention on 1,204 records:** landed. decision-v7 `development.jsonl` has 1,204 lines, and the manifest also says 1,204 records.
- **V-F8, todos from TodoWrite:** landed. See the verified list.
- **V-F9, correction outside `result_text`:** landed. See the verified list.
- **O-F27, event field superset:** landed. CONTRACT.md §3 lists `schema_version`, `session_id` and `event_id`, and says unknown fields are accepted (`extra="allow"`).

## Findings

**R2-F1. §9.1, the none-of-the-above rationale. Wrong.**
- **Spec:** "the none-of-the-above substitution and distractor options are off, since the question set fixes the option sets". The command also keeps `--p_none_pair 0.25 --none_pair_max_state 2048`.
- **Source:**
  - `K\kev\data.py:346-359` (`none_pair`) builds a "Minimal pair for the none-of-the-above shortcut". In the second record of the pair the labelled option is removed and a none option becomes the answer (`"label": nk`).
  - A question is eligible when it is a choice question with three or more options and no `target` (`:352`).
  - `K\kev\train.py:280-287` (`none_pairs`) and `:290-302` (`record_variants`) apply it to any record with probability `p_none_pair`, with no filter by source.
- **Why it's wrong:** G2 has 4 options and L7 has 6. When the two teacher votes agree there is no `target`, so the row is eligible. Records with states of 2,048 tokens or less will get these extra records on about 25% of draws. That likely covers the short single-response records (IF_multi and InFoBench G2 records, for example). Each extra record teaches a label outside the fixed option set, which is exactly what the C-F6 fix meant to stop.
- **Consequence:** a builder who trusts the sentence gets G2 and L7 rows trained with an extra "none" answer. There are three fixes:
  - Drop none pairs: set `--p_none_pair 0` and remove `--none_pair_max_state`, which needs `--p_none_pair > 0` (`K\kev\train.py:454-455`).
  - Add a patch that limits none pairs to replay sources. Kev's own fine-tune wrapper passes 0.25 (report -1, line 71).
  - Keep the flag and state the exception in the spec.

**R2-F2. §9.5, the `KEV_TEMPERATURE` scope. Wrong (low impact).**
- **Spec:** "(the `KEV_TEMPERATURE` variable is read only by `python -m kev.serve`)".
- **Source:** `K\kev\benchmark.py:193` and `K\kev\evaluate.py:193` also call `LoadOptions.from_env()`, which reads `KEV_TEMPERATURE` (`K\kev\checkpoint.py:144`). The round-1 receipt ("serve.py:339 is the only code that calls from_env") was wrong.
- **Consequence:** small. If anyone scores stock Kev with `python -m kev.benchmark`, for example the retention check, they get the checkpoint's 2.406 unless they set `KEV_TEMPERATURE=1`. Argmax accuracy and AUROC do not change, but any probability-based comparison does.

**R2-F3. §9.2 item 3, the long-state builder's tokenizer. Right but imprecise.**
- **Spec:** "it counts tokens with Kev-4B's tokenizer".
- **Source:**
  - `K\scripts\build_long_states.py:27` and `:108` use `ADMISSION_TOKENIZER`. That is `("Qwen/Qwen3.5-4B-Base", "1001bb4d…")` (`K\kev\suite.py:43`), the same tokenizer Kev-4B loads from its base (`K\kev\checkpoint.py:7`, `:238`).
  - Round 1's "Qwen3.8-27B admission tokenizer" was wrong at this commit.
  - What actually differs: the script counts tokens over the JSON form of the state (`:109`, `as_text`), built as `{"records", "primary_record", "note"}` (`:49`).
- **Consequence:** none, as long as the builder changes what is counted (the rendered state text) and not the tokenizer.

**R2-F4. §9.1, the attention path. Right but imprecise.**
- **Spec:** "attention runs through SDPA, the trainer's only path with the custom masks it uses".
- **Source:**
  - On CUDA the trainer always gets SDPA. `K\kev\model.py:253` picks it, `K\kev\train.py:543` passes no `attn`, and there is no attention flag.
  - However, eager attention also accepts these masks (`K\kev\model.py:252`, and `K\kev\shared_prefix.py:72-76` builds float masks for eager).
  - States without padding pass no mask at all (`K\kev\shared_prefix.py:108-113`).
- **Consequence:** none. The SDPA kernel check is correct.

**R2-F5. §9.2 item 5 and §12.1, the interpolated checkpoint. Right but imprecise.**
- **Spec:** "writes θ(α) … (the LoRA as its merged product, plus the pointer head) as a loadable checkpoint". The serve-path fallback is "serve the unmerged LoRA path".
- **Source:**
  - At α = 0.85 the merged change is (1−α)B₀A₀ + αB₁A₁, which can have rank up to 32. A rank-16 adapter cannot hold it.
  - `lora_scale` cannot produce it either, because it scales the whole adapter (`K\kev\checkpoint.py:307-311`).
  - Two formats do load: a rank-32 adapter (peft reads r from `adapter_config`; `Meta.lora` is checked only in `warm_start`, `:316-327`), or full weights (`weights="full"`, `:4-7`, `:273-291`).
- **Consequence:** the tool's output format is unstated. If it writes full weights, the α = 0.85 candidates have no unmerged-LoRA path, so the §12.1 fallback does not exist for them.

**R2-F6. §10 against §6.4, the detail budget. Imprecise (the two sections disagree).**
- **Spec:** §10 says "detail budget 0.40 · B_state − tokens(instructions + documents)". §6.4 says "max(0.40 × B_state − tokens(instructions + documents), 0.15 × B_state)".
- **Consequence:** a builder who works from §10 drops the 0.15 floor.

**Note for the builder (not a claim error).** With `--pass_tokens_max`, a single record whose own padded cost exceeds P stops the run with a `ValueError`; it is not dropped (`K\kev\train.py:217-220`). So P has to cover the largest 32K record together with its question branches. The smoke run should measure P on that record.

## Verified claims
- Every flag in the §9.1 command exists and validates (`K\kev\train.py:370-485`).
- `--init_from repo@sha` matches `HUB_ID` (`K\kev\checkpoint.py:30`).
- Without `--suite`, `--base_revision` is used directly (`K\kev\train.py:512-520`).
- `--head_lr` 0 is the default and means the head trains at `--lr` (`K\kev\train.py:376`, `:578`, `:588`).
- `--anchor_w` 0 is the default and must go together with `--anchor` (`K\kev\train.py:409`, `:450`).
- `--p_none 0`, `--p_none_distract 0` and `--p_distract 0` pass `augment`'s check, so choice options are still shuffled every time (`K\kev\data.py:323-342`).
- Soft-target choice questions are only permuted (`K\kev\data.py:330-331`).
- Dropping `--suite`/`--replay` is valid. `--replay` needs both flags (`K\kev\train.py:456`). With `--data` alone, the only source check is `EVAL_ONLY` (`K\kev\train.py:113`).
- Replay records keep their own `_meta.source` (`K\kev\data.py:383`). decision-v7's training sources (manifest `trainable_sources`) and hard-v1's `hard_*` sources are not eval-only, so the trainer accepts them.
- hard-v1 has a train partition (manifest: 6,000 records, gitignored).
- decision-v7 marks minimal pairs with `_meta.pair_id`, the same key the spec uses.
- The §6.3 eval-only list equals `EVAL_ONLY` plus decision-v7's `eval_only_sources` (`K\kev\data.py:290`; manifest).
- `label` is required on every question (`K\kev\data.py:379`). Soft cross-entropy is used when `target` is present (`K\kev\train.py:47-49`).
- Admission limits: a state is rejected when state + 1 > `max_state` (`K\kev\model.py:102`), and `max_packed` = 2048 + (`max_state` − 384) = `max_state` + 1,664 (`K\kev\model.py:14`, `:37-38`).
- B_state = 32,768 − Q − 1 always fits those limits. It is more conservative than needed, since it does not use the 1,664-token allowance.
- Records that don't fit are dropped with only a printed count (`K\kev\train.py:105-110`).
- `--max_state 32768` is inside [384, 65,536] (`K\kev\model.py:26`; `K\kev\train.py:452`).
- S = ⌈R/16⌉ ≈ 763, and none pairs do not change S (`K\kev\train.py:583`).
- OneCycle uses `pct_start` 0.1 (`K\kev\train.py:588`). The /25 start and the near-zero end are torch defaults (not re-read).
- `--resume` is refused for LoRA runs, so patch 1 is needed (`K\kev\train.py:472-473`).
- Both the LoRA and the head are warm-started and trained (`K\kev\train.py:553-557`, `:576-578`).
- `LoadOptions(temperature=1.0)` gives raw logits (`K\kev\checkpoint.py:105`, `:241`).
- The kernel check matches the trainer: SDPA on CUDA, fla Triton kernels for the DeltaNet layers (`K\kev\model.py:253`; `K\kev\shared_prefix.py:16-19`).
- Long-state builder limits: 7,488 cap, 8K dev-fit check, decision-v7 input (`K\scripts\build_long_states.py:58`, `:122`, `:29`, `:111`).
- Environment pins (torch 2.8.0, transformers 5.17.0, peft 0.21.0, fla 0.5.2, triton 3.7.1) and the 3.9.0 import failure match report -31, lines 12 and 87.
- The 3-point long-context rule matches `K\README.md:38`.
- Retention uses 1,204 dev records (`development.jsonl`).
- The event fields match CONTRACT.md §3. Extra fields are allowed (§3, line 78). PowerShell is listed as an action (§5).
- `todos` come from TodoWrite's `content` and `status` (`HackBU-NoahDavid\Noah\mod\hooks\register.tsx:154-156`; `types/index.d.ts:28`).
- The correction is attached outside `result_text`. The event is built from `ran` and the correction goes only into `answer.context` (`register.tsx:158-168`; `NOAH.md:66-72`; MOD_PRD.md FR-24). CONTRACT.md itself says only "attaches `text` to the agent's next tool result" (§4 Actions).
- r = 7/644 matches CONTRACT.md §5, line 204.
- H100 at $3.95/h matches report -1, lines 83 and 115.
- Per-source basis lines match the dossier: Terminal Wrench T (#2), Goodfire T (#5), eungyeuk T (#9). eungyeuk's L6 hard negatives match #9, where the agent reads and runs the test runner it was given.

## Coverage ledger
- **Read in full:** reading-context, out-of-cutoff and receipts-before-claims `SKILL.md`; TRAINING-SPEC.md lines 1-660; round-1 report lines 1-210; dispositions lines 1-74; CONTRACT.md lines 1-262; `K\kev\train.py` 1-680; `K\kev\model.py` 1-508; `K\kev\checkpoint.py` 1-362; `K\kev\shared_prefix.py` 1-141; `K\scripts\build_long_states.py` 1-137.
- **Kev code read in part:** `K\kev\data.py` 40-79 and 285-410; `K\kev\suite.py` 36-48; `K\kev\benchmark.py` 185-200; `K\kev\evaluate.py` 186-200; `K\kev\serve.py` 330-345; `K\README.md` 36-40.
- **Kev data:** the decision-v7 and hard-v1 manifests (fields printed) and decision-v7 `development.jsonl` (counted and keys tallied).
- **Dossier:** entries #2 (lines 175-201), #5 (243-263) and #9 (327-343) read in full, plus the heading index.
- **Reports -1, -9 and -31:** searched for targeted lines only. Report -33 was searched only for TodoWrite and had no hits.
- **Mod docs:** NOAH.md, Noah/MOD_PRD.md and `register.tsx` were read where the correction and todos claims depended on them.

Every line of every file marked "in full" was read. All commands ran in the foreground, and no process is left running.