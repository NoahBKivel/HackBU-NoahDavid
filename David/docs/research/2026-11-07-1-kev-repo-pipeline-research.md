# Kev repo pipeline research (2026-11-07)

Method: `git clone --depth 1 https://github.com/jaredpalmer/kev` (HEAD as of 2026-11-07), read source directly. Paths relative to repo root. Line numbers = files as cloned. Pinned deploy commit in skills: `KEV_REF=fc4a17e194bca35a48c57211392ec49ea54a94ac` (skills/kev-deploy/scripts/kev_serve.py:30; skills/kev-finetune/scripts/kev_modal.py SETTINGS). Weights not downloaded; HF repo `jaredpalmer/kev-4b` facts come from docs/model-cards/kev-4b.md.

Headline for our use: Kev-4B = Qwen3.5-4B-Base (rev `1001bb4d`) + rank-16 LoRA (alpha 32) + pointer head (head_dim 256). Fine-tune via `kev.train --data X.jsonl --init_from jaredpalmer/kev-4b`. DEFAULT TRAIN STATE LIMIT IS 384 TOKENS: raise with `--max_state` (up to 7552 used for released small models; hard max 65536).

---

## 1. TRAINING DATA FORMAT

Source: skills/kev-finetune/references/data-format.md; kev/data.py:362-410 (`load_records`, `api_request`, `materialize`); README.md "By Hand" (L185-196).

One JSON object per line = a System One request + `label` on every question:

```json
{"state": "Order 5521 arrived two weeks late and now I see two charges on my card. Fix this today.",
 "questions": {
   "department":  {"type": "choice", "instructions": "Which team should handle this ticket first?",
                   "criteria": {"returns": "Exchanges, refunds, wrong or damaged items",
                                "shipping": "Delivery status, delays, lost packages",
                                "billing": "Charges, invoices, payment problems"},
                   "label": "billing"},
   "escalate":    {"type": "noul", "instructions": "Does this need urgent attention from a human within the hour?", "label": true},
   "frustration": {"type": "score", "instructions": "How frustrated is the customer?",
                   "criteria": ["Calm or neutral", "Annoyed", "Angry or threatening to leave"], "label": 2}}}
```
(verbatim from references/data-format.md L6-19.)

Real soft-label line from repo (evals/night2/unknowable.jsonl line 1, trimmed `_meta`):
```json
{"state": {"policy": "Returns are accepted only if the return request is submitted within 60 days of the purchase date.", "case": "The order was paid by card and shipped to Lena's home address. The return request was submitted on October 28, 2026."}, "questions": {"decision": {"type": "noul", "instructions": "Is this return request within the policy window?", "label": true, "src": "unknowable_return_window", "target": {"false": 0.5, "true": 0.5}}}, "_meta": {"source": "night2_unknowable", ...}}
```
Real choice-with-many-options example: evals/smoke-v1/train.jsonl line 1 (banking77, 77 options, descriptions `null` or "Customer asks about X").

Fields:
- `state`: string OR JSON object/array (rendered as `key: value` lines, field names visible to model; kev/api.py render). Non-empty. data-format.md says "Under ~1400 characters (384 tokens)" = default `--max_state`.
- `questions`: object keyed by qid (qid never shown to model). >=1. `load_records` raises if `state` missing or `questions` empty or any question lacks `label` (data.py:376-379).
- `type`: `noul` | `choice` | `score`. `instructions`: required text.
- `criteria`: choice = `{option_name: description|null}` (1-255 options); score = list of 2-255 level descriptions low->high (README API table says 1-255); noul = optional `{"true":..., "false":...}`.
- `label`: choice = option name string; noul = JSON bool; score = int level index from 0. (data.py:402: `q["label"] = m["keys"].index(y) if choice else int(y)`).
- `target` (optional soft label/teacher distribution): `{key: weight}`; keys = option names (choice), `"false"`/`"true"` (noul), level index as string (score). Missing keys -> 0, then renormalized; must have positive mass (data.py:404-409). A `label` is still REQUIRED even with `target`. Loss for such questions = soft cross-entropy `-(t*log_softmax(z)).sum()` (train.py:question_loss). `augment` for target-bearing choice questions only permutes option order (data.py:330-331). Documented use: `{"false":0.5,"true":0.5}` for evidence-removed records (data-format.md L31).
- Optional per-record `_meta` (source, id, group_id...) merged over defaults; per-question `src` auto-filled `custom_<type>` (data.py:380-383).
- Size limits (default context, training): state <= 384 tokens (`MAX_STATE`), each question branch <= 1024 (`MAX_BRANCH`), whole packed record <= 2048 (`MAX_PACKED`) (kev/model.py:14). Records over are DROPPED with a printed count (train.py training_requests: "dropped N of M records that exceed the training context"). `--max_state S` raises state limit; branch and packed limits grow by the same amount (`training_context`, model.py:33-40).
- Conflicts: identical states with different labels on same question definition dropped by `split_data.py`; labels per option >=5% recommended (data-format.md L36-50).
- Splits: skill's `split_data.py` makes 70/15/15 train/calibration/development by state; >=40 records each in calibration and development.

Data scripts (standard-library): skills/kev-finetune/scripts/{extract_workload,convert_data,generate_data,plan_size,split_data}.py. `convert_data.py --score-offset 1` for 1..N ratings.

## 2. TRAINING CLI + FLAGS

Source: kev/train.py (argparse L372-438; validation L440-480). Entry: `uv run python -m kev.train ...`.

Exact flags (default):
- Model/recipe: `--base` (Qwen/Qwen3-0.6B-Base), `--base_revision` (""), `--lora` (16, rank), `--lora_targets` {all,dense,attn,qv} (all), `--head_dim` (256), `--special_embeddings` {0,1} (0), `--weights_dtype` {fp32,bf16} (fp32), `--dtype` {fp32,bf16} (fp32; bf16 = autocast, CUDA only), `--checkpointing` {0,1} (0, = gradient checkpointing, non-reentrant), `--device` {auto,cuda,mps,cpu...}.
- LoRA details (kev/model.py:266-274): `LoraConfig(r=lora, lora_alpha=2*lora, lora_dropout=0.05, task_type="FEATURE_EXTRACTION")`. Targets `all` = q,k,v,o,gate,up,down proj + on hybrid (Qwen3.5) `in_proj_qkv, in_proj_z, in_proj_a, in_proj_b, out_proj` (DeltaNet). `dense` = all minus DeltaNet projections. So rank 16 => alpha 32. No alpha flag.
- Optim: `--lr` (2e-4), `--head_lr` (0.0 = same as --lr; separate LR for pointer head), `--weight_decay` (0.01), `--epochs` (1), `--batch` (1, records per forward), `--accum` (8), `--max_steps` (0), `--seed` (0). AdamW + `OneCycleLR(pct_start=0.1)` with max_lr [lr, head_lr or lr] (train.py:588). Grad clip 1.0 (`MAX_GRAD_NORM`). Effective batch = batch x accum (x world size).
- Data: `--data` (own JSONL), `--suite` (frozen suite dir), `--replay N` (needs --data AND --suite; mixes N records sampled by --seed from suite train partition to avoid forgetting; train.py:441-ish error "--replay needs both --data and --suite"), `--n_per_source` (1000; on-the-fly public data when no --suite/--data), `--holdout`, `--train_sources`, `--public_frac` (1.0), `--synthetic_repeat` (1), `--max_state` (384; range [384, 65536]).
- Augmentation (choice only): option order ALWAYS shuffled (data.py:augment); `--p_none` (0.1; replace correct option with "none of the above"), `--p_none_distract` (0.12), `--p_distract` (0.15), `--p_none_pair` (0.0; releases used 0.25: extra minimal pair none-present/none-absent), `--none_pair_max_state`.
- Losses (at most ONE of the three modifiers): `--label_smoothing` (0.0), `--brier_w` (0.0; adds w*sum-squared prob error to CE), `--focal_gamma` (0.0; CE x (1-p_y)^gamma). Plus: `--ord_w` (0.0; weight of ranked-probability-score for Score questions; RPS = mean squared CDF diff), `--perm_kl` (0.0; symmetric KL between predictions under two option orders), `--perm_frac` (0.3; fraction of records that get the permuted 2nd pass; only choice K>=3). `--anchor` (JSON `{"targets": {record_id: {qid: {key: p}}}}` frozen-base zero-shot distributions, from kev/anchors.py) + `--anchor_w` (0.0; KL(base||model) per anchored question; must go together). Soft per-question `target` = teacher-distribution CE (no separate teacher-KL flag, no logit-distillation flag). README L345: "The released models don't use the optional `--perm_kl` or `--ord_w` losses." PLAN.md L269-270 lists anchoring, option isolation, special embeddings, head_dim, perm_kl, ord_w as tried and not adopted. No Brier/focal/RPS in released recipes (UNVERIFIED whether any ablation showed gains; PLAN says "config space ... exhausted").
- `--option_isolation` {0,1} (0): option spans isolated with shared positions. model.py:263 raises `ValueError("option_isolation needs the packed mask; not available on hybrid backbones")` => unusable on Qwen3.5 (our Kev-4B).
- Memory/throughput: `--row_budget` (0; padded row tokens per pass, splits micro-batches), `--shared_prefix` {0,1} (default None -> equals `--full_ft`; i.e. OFF for LoRA unless set; hybrid backbones only: run each record's state once and branch questions from it; "exact", kev/shared_prefix.py; fp32 matches row form ~1e-5), `--length_sort` {0,1} (0), `--pass_tokens_max` (0; needs --length_sort 1, hybrid, not with --row_budget/--perm_kl).
- Full fine-tune: `--full_ft` {0,1} (0; requires `--weights_dtype bf16`, no `--special_embeddings`; one GPU keeps fp32 masters in host memory, torchrun => FSDP2). Resume/snapshots full-FT only: `--save_every_steps`, `--save_every_minutes`, `--resume` {0,1}, `--stop_after`, `--snapshot_fractions`, `--snapshot_every_steps`, `--snapshot_dir`. Resume is ERROR for non-full_ft (train.py: "resume points are for full-weight runs (--full_ft 1)"). So LoRA runs have NO checkpoint/resume; they write only the final checkpoint.
- `--out` (runs/kev; refuses to overwrite existing run dir). Writes `training_config.json` incl. `init_source`.

`--init_from` semantics (train.py:~500-505; kev/checkpoint.py:316-357 `Checkpoint.warm_start`): accepts local dir or Hub id (incl `@rev`). Loads LoRA adapter (or full backbone) AND pointer head. Compatibility checks BEFORE loading, raising `ValueError(f"--init_from {path}: {name} is {theirs!r} there and {mine!r} here")` over `COMPAT_FIELDS = ("base","base_revision","lora","head_dim","option_isolation","special_embeddings","weights")` (base_revision may be None on either side). Adapter keys must match exactly (unexpected/missing tensors raise; check `--lora_targets`/`--lora`). Therefore for Kev-4B: `--base Qwen/Qwen3.5-4B-Base --lora 16 --head_dim 256 --lora_targets all --base_revision 1001bb4d826a52d1f399e183466143f4da7b741b` (README example passes only `--base Qwen/Qwen3.5-4B-Base --init_from jaredpalmer/kev-4b`; revision None-tolerant). Modal skill reads these from the checkpoint meta automatically and warns "Do not pass --base" (SKILL.md Gotchas).

Documented recipes:
- Delta fine-tune (README L201): `--data train.jsonl --base Qwen/Qwen3.5-4B-Base --init_from jaredpalmer/kev-4b --epochs 2 --lr 2e-5 --batch 1 --accum 8 --dtype bf16 --checkpointing 1 --device cuda --out runs/mine`.
- Kev-4B stage 1 (README L342): `--suite evals/v7/decision-v7 --base Qwen/Qwen3.5-4B-Base --base_revision 1001bb4d... --epochs 2 --lr 5e-5 --batch 4 --accum 2 --dtype bf16 --checkpointing 1 --p_none_pair 0.25 --device cuda`.
- Later stages (docs/model-cards/kev-4b.md L149-152): lr 2e-5, 1 epoch, replay 2,000/2,000/4,000 decision-v7 records, batch 2 x accum 4, states <= 7,552 tokens, seed 1-2, 1,915 optimizer steps for the skills stage.
- Skill wrapper (skills/kev-finetune/scripts/kev_modal.py:247-290): `kev.train --data .. --init_from .. --device cuda --dtype bf16 --lora <meta> --head_dim <meta> --lora_targets <meta> --epochs 1(default) --lr min(init checkpoint lr, MAX_DELTA_LR=5e-5) --batch/--accum/--checkpointing from init checkpoint args --seed 0 --p_none_pair 0.25 [--suite evals/v7/decision-v7 --replay 2000]`. DOES NOT PASS `--max_state` => states >384 tokens dropped unless script edited. Also does not set `--head_lr` (same LR for head as adapter).
- Head LR: no separate default; Kev-27B used backbone 2e-6 / head 1e-4 (kev-27b.md L180).

Calibration/temperature step:
- Skill `kev_modal.py::train` after training: fits one temperature by min NLL (`kev.metrics.fit_temperature`, micro) on `calibration.jsonl`, writes it to checkpoint `head.pt` meta (`m.temperature = T`), scores `development.jsonl` for fine-tuned AND baseline (baseline temperature also refit on user calibration slice), paired bootstrap on acc/brier/ece, regression check on 300 public decision-v7 dev records (kev_modal.py:~296-325).
- Standalone: `uv run python -m kev.calibrate --rows runs/X/rows.json [--out ..] [--folds 5 --seed 0 --samples 1000]` is REPORT ONLY (arms raw/shipped/workload/workload_oof; writes nothing to checkpoint). Checkpoint writer: `scripts/calibrate_checkpoint.py` (refuses in-distribution rows unless `--allow-in-distribution`).
- Temperature is a single scalar stored in `head.pt`, applied at load; `KEV_TEMPERATURE=1.0` serves raw.

Seeds: `--seed` (default 0) seeds torch + python RNG + replay sampling (`random.Random(f"replay:{a.seed}")`).

## 3. COMPUTE

- "A Kev-4B training run costs about $1 on an H100" (README L181). "~12 min and ~$1 per run for 400 records, ~15 min for 1000" (skills/kev-finetune/SKILL.md Phase 0 item 5). `train` prints a cost bound: `GPU_HOURLY` H100 3.95, H200 4.54, B200 6.25, A100-80GB 2.50, A100 2.10, L40S 1.95, A10G 1.10, L4 0.80, T4 0.59 $/h x timeout; default timeout 10800 s (kev_modal.py:512-518). Typical: "0.8B ~8 min, 4B ~12-15 min for 400-1000 records, 9B ~30 min". Example workload: 1050 records, 3 questions, 15 min H100, gain 67.7%->73.6% acc (README L173; skills/kev-finetune/README.md L42-51). Real data: 5,219 CFPB complaints, 1 epoch, 0.804->0.904 acc (README L173).
- Kev-4B documented training (kev-4b.md L292-296): base recipe ~56 min on 1 H100 (peak 24.6 GB, states <=384, batch 4x2 accum, bf16 autocast, checkpointing); dates stage 9 min H100; documents stage (states <=7,552) 43 min on 1 H200; skills stage 1.4 h on 1 H200, PEAK 47.7 GB (batch 2 x accum 4, states <=7,552). Kev-9B docs+skills stage: 2.6 h H200 peak 74.1 GB (kev-9b.md L275). Kev-27B full FT: 8 x H200, 16.2 h (129 GPU-h), FSDP2, 145,840 records, 1,140 steps (kev-27b.md L297-299).
- Memory guidance: `--batch 1 --accum 8` bf16 fits Kev-0.8B in 4 GB (README L212). No documented max trainable length for LoRA beyond `--max_state` <= 65,536 (`MAX_TRAIN_STATE`, model.py:26) and released small models trained to 7,552 (`MAX_TRAIN_STATE_8K`); tool for fitting: `--length_sort 1 --pass_tokens_max N`, `--row_budget`, `--shared_prefix 1`, `--checkpointing 1`.
- Modal fine-tune path: `skills/kev-finetune/scripts/kev_modal.py` (apps `kev-finetune`; volumes `kev-finetune-runs`, `kev-hf-cache`; GPU env `KEV_GPU` default H100; `modal run scripts/kev_modal.py::train --data data/x --name x-v1 --init-from jaredpalmer/kev-4b [--epochs --lr --replay 2000 --batch --accum --seed --p_none_pair 0.25 --regression 300 --baseline --gpu --timeout]`; also `::validate`, `::evaluate`, `::compare`, `::pull [--checkpoint]`, `::publish`, `::teardown`; names immutable). Repo-level path: `modal_app.py` (`::smoke`, `::study --suite .. --plan experiments/*.json`, `::pull`, `::locked_test`, `::serving --run .. --gpu L40S --name ..`); each trial its own H100 (README L347-366).
- Container image: debian_slim py3.13, `kev[serve]` from git at KEV_REF, `flash-linear-attention==0.5.2`, `triton>=3.7.1` (needed for Qwen3.5 DeltaNet kernels).

## 4. SERVING

Sources: kev/serve.py, kev/api.py, README "API" (L258-302), skills/kev-deploy/SKILL.md + scripts/kev_serve.py.

HTTP:
- `POST /v1/systemone`, `GET /v1/models`, `POST /v1/systemone/permute` (body `{request, question, n_perm 1..64 (default 6), seed}`), `POST /v1/systemone/separate`.
- Request (README L264-276): `{"state": string|object|array, "model": "kev-latest" (also accepts "jev-latest"; serve.py MODEL_NAMES), "questions": {"<id>": {"type":"noul"|"choice"|"score", "instructions": string|object|array (optional), "criteria": ...}}}`.
- Response (README L121-133, api.py to_answers L149-160):
```json
{"model":"kev-latest","answers":{
 "department":{"type":"choice","choice":"returns","confidence":0.21,"probabilities":{"returns":0.47,"shipping":0.28,"billing":0.25}},
 "escalate":{"type":"noul","noul":0.93},
 "frustration":{"type":"score","score":1.44,"confidence":0.34,"legend":{"0":"Calm","1":"Frustrated","2":"Very angry"},"probabilities":{"0":0.00,"1":0.56,"2":0.44}}},
 "usage":{"input_tokens":101,"output_tokens":161},"latency_ms":495}
```
`noul` = P(yes) (p[1]); `noul` answer has NO confidence/probabilities fields. `score` = expected level index. `usage.output_tokens` = tokens of serialized answers (not generation). With `KEV_TRUNCATE_STATES=1` responses add `truncated` and `usage.state_tokens`/`state_tokens_used`. `latency_ms` = model time of the batch (excl. queue). Headers: `x-typesafe-request-id`, `server-timing`.
- Auth: unset `KEV_API_KEY` => open server; set => `Authorization: Bearer <key>` required on paths starting `/v1` (hmac.compare_digest), 401 `{"detail": "missing or invalid API key; ..."}` with `www-authenticate: Bearer`. Default bind 127.0.0.1 (`--host 0.0.0.0`). CORS `*`.
- Errors: invalid request or state > 65,536 tokens (or a question row > state+8192) => 422 with token count and limit (no silent truncation; README L286; model.py SERVE_MAX_*).
- Env vars (serve.py:25-34): `KEV_PREFIX_CACHE` (default 4 states; 0 disables), `KEV_PREFIX_MIN_TOKENS` (default = model.prefix_min_tokens: 0 for hybrid/Qwen3.5 and MLX, 384 for attention-only torch), `KEV_PREFIX_MAX_TOKENS` (default 65536 total state tokens across cache, LRU eviction; longer state is not cached), `KEV_DATE_FACTS` (0), `KEV_TRUNCATE_STATES` (0), `KEV_API_KEY`, `KEV_TEMPERATURE`, `KEV_DTYPE` (bf16 default on GPU; fp32 exact path), `KEV_BACKEND` torch|mlx|auto, `KEV_CUDA_GRAPHS` 0|1, `KEV_FUSED` 0|1, `KEV_MERGE` (0 keeps LoRA unmerged), `KEV_ATTN`, `KEV_LORA_SCALE`, `KEV_DEVICE_PROBE_TIMEOUT` (30 s), `KEV_SHAPE_BUCKET`.
- Prefix cache semantics (serve.py `PrefixCache`): KEY = `(tuple(state token ids), option_isolation_flag)` where state ids = tokens up to the first question (`enc["ids"][:n]`, n = count of seg==0). EXACT MATCH on the full tokenized state; NOT longest-common-prefix (dict lookup `self.entries.get(k)`). Holds KV + DeltaNet states. Max `size` states and `max_tokens` state tokens total (one 64k state or four 16k); LRU. Batch keeps only new states that will survive. Questions are not part of key, so same state + different questions = hit and pay only question rows. Implication for us: put the shared document/state byte-identical (any prefix/suffix change = miss).
- Batching: `MAX_BATCH = 64` requests per model-thread batch (serve.py:33; cuda_graphs splits to fit its buffers). A request can have any number of questions; run "a token budget at a time": `ROW_PASS_TOKENS = 16384` per forward pass, `rows_per_pass = max(1, budget // (prefix_len + max(len(row))))` counting cached state once per row in that pass (model.py:23, 41-48). Answers independent of the split.
- CUDA graphs: kev/cuda_graphs.py, hybrid Qwen3.5 only, batched across requests, shape buckets; first request of new shape runs eager ~2-4x slower (capture in background; `/v1/models` reports captured graphs). Warm-up in kev_serve.py captures states of 1/4/16 x a ticket sentence. Fused DeltaNet kernels: kev/fused_qwen35.py (needs fla 0.5.2). NVIDIA only; ROCm uses eager path.
- Quantization: NONE found (grep for quantiz/int8/fp8/awq/gptq/bitsandbytes over kev/*.py, README, skills, kev-4b card returned no hits). Serving dtypes: bf16 (GPU/Mac), fp32 exact, fp16 allowed via KEV_DTYPE. UNVERIFIED beyond absence.
- GPU memory: Kev-4B resident 14.3 GB (kev-4b.md L258); needs ~16 GB free (L110), "Kev-4B ~10 GB" per deploy troubleshooting (conflicting; use 14.3). Kev-9B 21.9 GB resident (card) / ~17 GB (README). Kev-0.8B ~4 GB. Kev-27B 51 GB weights, 65.5 GB resident; 64k state peaked 87.1 GB on H200; 32k 78.7 GB. Fp32 eval path Kev-4B H100: 16k/32k/64k states 3.0/6.8/17.2 s, +4.3/8.6/17.2 GiB.
- Latency tables (README L401-412; kev-4b.md L251-256): model time per request, median of 20, "new text / same text again":
  - Kev-4B L40S ($1.95/h): 6 q short: 41.5 / 27.7 ms; 5 q 2,200-tok: 145.2 / 43.0 ms; 51.4 req/s @64 clients.
  - Kev-4B H100 ($3.95/h): 18.1 / 12.9 ms; 89.4 / 22.5 ms; 100.8 req/s.
  - Kev-0.8B L4 ($0.80/h): 22.7/16.1; 108.6/32.3; 62.8 req/s. Kev-9B L40S 66.4/42.7; 235.6/57.5; 32.7. H100 24.0/16.6; 88.5/26.4; 79.5. Kev-27B B200 46.5/32.2; 178.0/52.1; 44.2; H200 67.2/50.0; 274.8/73.8; 28.6; H100 75.0/52.0; 277.5/79.3; 28.9.
  - L4 "too slow for Kev-4B"; A100 "slower than the L40S here and costs more"; A10G: NO published latency (only price 1.10 in GPU_HOURLY). Kev-4B L4: no table row (UNVERIFIED numbers). Skill's own fine-tuned-model Serve defaults to L4 (`KEV_SERVE_GPU` default L4; "L40S for the 4B under load").
- Modal HTTP (README L433-446, Kev-4B, 1 H100, us-east, 6 q new short text): regular web p50 102.1 ms @1 client, 902 ms @32, 956 ms @64 (35.6 / 53.4 req/s); direct server (`KEV_FLASH=1 KEV_REGION=us-east`) 36.9 ms @1, 599 @32, 621 @64 (51.2 / 73.2 req/s). Web endpoint: `modal.concurrent(max_inputs=64, target_inputs=32)`, `scaledown_window=300`, `cpu=4`, `startup_timeout=1200`, `timeout=600` (kev_serve.py:75-84).
- Cold start on Modal (cached weights): Kev-4B ~35 s, 0.8B ~40 s, 9B ~55 s, 27B ~50 s (deploy SKILL.md table); first-ever cold start +1-2 min (download, kernel compile; cached on `kev-hf-cache`); skill-trained model (kev_modal Serve): "Cold start after idle is 1-2 minutes for the 4B" (references/deploy.md); Modal returns HTTP 303 for requests waiting >150 s.
- Recommended Modal GPU: Kev-4B -> L40S (fallback H100) at $1.95/h via kev-deploy (`GPU_FOR`), H100 for lowest latency; fine-tuned via kev_modal Serve -> L4 default, L40S under load. Deploy base model: `KEV_API_KEY=$(openssl rand -hex 24) modal deploy kev_serve.py` (`KEV_MODEL=jaredpalmer/kev-4b` default; `KEV_GPU`, `KEV_REGION`, `KEV_MIN_CONTAINERS`, `KEV_FLASH`, `KEV_APP_NAME`, `KEV_TRUNCATE_STATES`). Deploy fine-tuned: `modal secret create kev-serve-key KEV_API_KEY=...; KEV_SERVE_SECRET=kev-serve-key KEV_SERVE_RUN=x-v1 modal deploy scripts/kev_modal.py` -> `https://<workspace>--kev-finetune-api.modal.run`, up to 8 concurrent requests (references/deploy.md; vs 64 for kev_serve.py), scales to zero after 5 min, `KEV_SERVE_MIN_CONTAINERS=1` keeps warm (~$0.80/h on L4).
- Apple Silicon (not our path): M5 32 GB Kev-4B 721 ms/5 q new text, 136 ms cached.

## 5. CONTEXT LENGTH

- Serving limit: `SERVE_MAX_STATE = 65536`, `SERVE_MAX_BRANCH = 65536 + 8192` (state + question row), `SERVE_MAX_PACKED = SERVE_MAX_STATE + SERVE_MAX_BRANCH` (model.py:18-20). Over => 422 (or truncate with `KEV_TRUNCATE_STATES=1`). Attention-only backbones run packed mask only up to ROW_PASS_TOKENS=16384, longer as rows.
- Training state default 384; released 0.8B/4B/9B final stages <= 7,552; Kev-27B <= 32,768 (README L240, L330).
- Validated context ("longest doc whose CUAD accuracy stays within 3 pp of same model's 8k accuracy at 95% lower bound"): 0.8B 8,192; 4B 8,192; 9B 8,192; 27B 65,536 (README L30-35). Kev-4B card L210: 16k lower bound -3.4 pp (fails -3).
- Kev-4B CUAD by length (longdoc-v1 development; accuracy, ECE @T=2.41, paired delta vs 8k pp [95% CI]; kev-4b.md L213-223):

| len | Q | acc | ECE | delta vs 8k |
|---|---|---|---|---|
| 4k | 443 | 0.847 | 0.047 | - |
| 8k | 453 | 0.837 | 0.048 | ref |
| 16k | 452 | 0.823 | 0.057 | -1.1 [-3.4, +1.2] |
| 32k | 454 | 0.788 | 0.022 | -5.8 [-9.0, -2.8] |
| 64k | 452 | 0.781 | 0.035 | -5.2 [-8.2, -2.0] |

  Release-notes lower bounds at 16k: 0.8B -8.5, 4B -3.4, 9B -3.7 pp (docs/releases/kev-1.0.md).
- Kev-27B CUAD (longdoc-v1 TEST, acc / ECE; kev-27b.md L221-231): <8k (867) 0.874/0.059; 8-16k (443) 0.880/0.052; 16-32k (442) 0.873/0.061; 32-64k (442) 0.867/0.060; all (2,194) 0.874/0.053. v1 (LoRA) 0.890/0.007 overall. Dev paired delta vs 8k: 16k +0.2 [-0.7,+1.2], 32k -0.2 [-1.2,+0.7], 64k -1.1 [-2.4,+0.0]. Generated agreement bundles (2,400 q): 1.000 both.
- How Kev-27B got 64K validation: training states only up to 32,768 (64k never trained on; "States of 32k-64k were evaluated but not trained on", card L285). Corpus = private, 145,840 records / 337,130 questions; manifest public at `evals/sft-v2-r22/manifest.json` (state_tokens total 332,028,827; median 327, mean 2,276.7, p90 7,694, p99 26,882, max 32,765; histogram 1-256: 67,187; 257-512: 16,368; 513-1024: 20,065; 1025-2048: 18,651; 2049-4096: 5,802; 4097-8192: 3,510; 8193-16384: 7,690; 16385-32768: 6,567; 32769+: 0; 3,412 records dropped over 32,768 cap). Long components: `longify` 3,200 records / 7,079 q / 55,885,456 state tokens (decision-v7-type records buried in 8k-32k unrelated text, labels inherited; downsampled from 6,400); `longdoc` 7,617 records / 27,528 q / 130,050,641 state tokens (documents assembled by code, labels computed by code); `agents` 4,875 / 22,332 q / 58.6M tokens (code-generated agent session logs); `guardrails-grounding` 5,655 / 15.4M tokens; `injection` 2,699 / 5.6M tokens; synthetic-v1/long_doc 12,084 -> 6,042 kept. Other components: sft-v1 78,786, tasksource-v1 24,000 (119 families), ood 7,312, tone 7,544, pii 4,152. Train command: `--max_state 32768` (manifest `context.note`: "train with --max_state 32768"), `--full_ft 1`, shared prefix on, lr 2e-6, 8 x H200.
- Small models' long-state training aids: `scripts/build_long_states.py` (builds `evals/round4/longstate-v1`, `evals/round5/longstate-v2`; decision-v7 record's state buried among same-partition unrelated states to ~1k/2k/4k tokens; outputs train.jsonl, train_control.jsonl, development.jsonl, manifest.json; train via `kev.train --data ... --max_state 4608`; question/label unchanged). Kev-4B final stages: `documents-v1` (CFPB narratives up to ~7k tokens, 5,219 records, 7,488 q) and `hard-v1` skills (long policy docs, 6,000 records) with states <= 7,552.
- `scripts/build_longdoc_v1.py` (header docstring): builds EVAL-ONLY, report-only `evals/longdoc-v1` (manifest: `eval_only: true, report_only: true`, partitions development + test; test locked). Inputs: CUAD v1 (theatticusproject/cuad rev `a3c393f5...`, CC-BY-4.0) + generated bundles from `scripts/longdoc_v1_synthetic.py`; tokenizer Qwen3.8-27B. Buckets `BUCKETS = (4096, 8192, 16384, 32768, 65536)`, 120 records per bucket/part/partition; states 80-93% of nominal. CUAD part: target contract padded with other CUAD contracts of same partition (last one cut at paragraph, marked excerpt) to bucket length, target at 10/50/90% depth; questions: 2 clause-presence Noul (one found, one not), 1 clause-category Choice (1 found + 3 not found), + governing-law Choice when answer is a common jurisdiction; labels from CUAD (`is_impossible`, master_clauses.csv); 8k-64k buckets reuse same targets/questions (paired), 4k uses targets <= 3,100 tokens; contracts dealt to dev/test by company hash. Dev: 1,200 records / 4,654 questions (4k CUAD: 443 q, 8k 453...). Synthetic part: bundles of generated service agreements with 4 questions each: `locate` (which agreement names <city> as hosting location), `detail` (term at 10/50/90% depth), `multihop` (site tier in closing schedule -> credit per tier in SLA section), `absent` ("The agreement does not state this"); labels computed by solver from `_meta.facts`, never written by generator. Files ~100 MB each, on a private mirror (only manifest in git). NOT training data: header says eval-only; kev.train rejects eval-only sources (`EVAL_ONLY`; ValueError "training data contains eval-only sources"). Our own long-doc training data must be built separately (see `longify` / `longdoc` approach above; the actual builder for the 7,617-record `longdoc` component is private: UNVERIFIED which script).
- Other long-doc scripts present: scripts/longdoc_report.py, longdoc_serving.py, long_state_memory.py, mlx_long_states.py, screen_longdoc_v1.py (overlap screen), longstate_report.py.

## 6. OUTPUT SEMANTICS

- `noul`: P(true) after temperature. `choice`: argmax option in `choice`, `probabilities` dict, `confidence`. `score`: `score` = sum(i*p_i) (mean level index from 0), `legend` ({"0": desc,...}), `probabilities` keyed by level string, `confidence`.
- `confidence` (api.py:127-141; README L284) is NOT measured accuracy: Choice K>1: `(p_max - 1/K)/(1 - 1/K)`; K=1 -> 1.0. Score: `max(0, 1 - E|level - mode| / D)`, D = mean absolute deviation of uniform over L levels around (L-1)/2 (2/3 for 3 levels); all mass on one level = 1; uniform or wider = 0; L=1 -> 1.0. Matches TypeSafe `system-one-adapter` 0.2.1. For decisions use calibrated `probabilities`/`noul` with thresholds fit on own data.
- Calibration: single scalar temperature in `head.pt`, applied at load; shipped T: 0.8B 2.35, 4B 2.41 (fitted on in-distribution decision-v7 dev rows, 1,264 q; refit on held-out gave 2.30, not adopted), 9B 2.19, 27B 1.32. Temperature never changes argmax. `KEV_TEMPERATURE=1.0` => raw. Limits: coverage@<=5% error out-of-domain 0.52-0.69 (4B/9B/27B) vs Jev 0.70; 4B ECE 0.017 (transfer-v4 test) up to 0.084-0.101 on hard-v1/documents-v1.
- Option-order sensitivity: README L324 "Asking questions together or separately produces probabilities within 4e-6 (fp32) ... does NOT mean option order is irrelevant: options within a question can still affect one another"; Limitations L453 "Changing option order can change an answer. Question isolation doesn't prevent this." Training mitigation: options always shuffled in `augment`. `/v1/systemone/permute` runs a Choice under n_perm orders (default 6, max 64) for client-side averaging. `kev.benchmark` reports permutation flip_rate/mean_max_delta. PLAN.md L2774: rotation-averaged Choice cut permutation flips 0.028 -> 0.000 at 9B but not shipped (multiplies latency).
- `option_isolation` (packed-mask sub-branch with shared positions, exact permutation invariance): `--option_isolation 1` train flag and PrefixCache key component; ONLY for attention-only backbones (Qwen3). On hybrid (Qwen3.5/3.8; all current Kev) DecisionModel init raises `ValueError("option_isolation needs the packed mask; not available on hybrid backbones")` (model.py:263). Not adopted anyway (PLAN L269).
- Question isolation: on hybrid models each question is its own row (state + that question), positions restart just after the state, so cross-question leakage is exact-zero (README L316); state computed once and cached.
- No-evidence behavior: trained with uniform soft targets for "unknowable" records; Kev-4B answers p>=0.9 on 0% of unanswerable items vs Jev 9% (kev-4b.md L183).

## 7. LICENSE

- Code: Apache-2.0 (LICENSE; pyproject.toml `license = "Apache-2.0"`; README L503).
- Weights: Kev-4B adapter + head Apache-2.0, base Qwen3.5-4B-Base Apache-2.0 (kev-4b.md L81, front-matter `license: apache-2.0`). Kev-27B weights + head Apache-2.0 on Qwen3.8-27B (Apache-2.0).
- Training datasets carry their own licenses (README L503; model cards). 27B card flags share-alike capped datasets (ARC, HotpotQA, NQ, SNLI CC-BY-SA) and GLM-5.3 MIT-style condition; Kev-4B card: CodeReviewer/FlakeFlagger from Zenodo, CFPB US government works.
- Skills (kev-finetune, kev-deploy) also Apache-2.0 (SKILL.md frontmatter).

---

## Caveats / UNVERIFIED
- HF weights files not fetched; adapter/head sizes taken from cards (LoRA 33.8M params at rank 16).
- No A10G or L4-for-4B latency table; no quantization support found.
- Anchor JSON record-id keying (`v.request_id`) not fully traced; see kev/anchors.py before using `--anchor`.
- Exact script that produced `longdoc` (7,617) training component is not in the public repo (private corpus; only manifest public).
- Whether `--shared_prefix 1` is beneficial/tested with LoRA on Kev-4B: allowed by argparse (default 0 for LoRA); no documented LoRA benchmark (UNVERIFIED).
- kev-deploy says Kev-4B needs ~10 GB; card says 14.3 GB resident. Use the card.
- Skill wrapper hardcodes no `--max_state`; to train on states >384 tokens, either edit `kev_modal.py` cmd (add `"--max_state", N`) or run `kev.train` directly (e.g. on Modal via `modal_app.py`). Expect memory peak ~48 GB at 7.5k states, batch 2 x accum 4 on 4B (kev-4b.md) so H100 80 GB works with `--checkpointing 1`.
