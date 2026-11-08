# Stock pplx-decider-flash-v1.2 on the 200 intent-probe items, paired with stock Kev-4B (2026-11-07)

Legend: **[M]** measured here, **[E]** estimated, **[S]** taken from a source file, the model card or report 31. Kev numbers are recomputed from Kev's per-item p values (`modal-work/results/probe.json`, sha256 `fffa951a...`); they match report 31's table to the third decimal [M].

## 0. Pinned configuration

| Item | Value |
|---|---|
| Model | `perplexity-ai/pplx-decider-flash-v1.2` @ `9ff7cf9838e59df461c276b7699d56b244d2af58` (HF API `sha` at fetch time). Base `Qwen/Qwen3.5-4B` @ `851bf6e8...` [S, decision_config]. |
| Integrity | sha256 of every file listed in `release-manifest.json` checked in-container: weights (2 shards), `readout.safetensors`, configs, tokenizer, `source/` all match. `README.md` does not (12,521 bytes vs 12,502 in the manifest) [M]. |
| Inference code | The checkpoint's own `source/src/pplx_decider` v0.3.0, imported per the card (`sys.path.insert` + `Decider.from_pretrained(ckpt, device="cuda")`). **Reference path** (`fast=False`): left-padded batch through the unmodified Transformers backbone, noncausal full attention hook, readout at the `<\|fim_suffix\|>` marker. `max_length` default 262,144. |
| Request | One question per request, one request per `decide()` call (the card's "bit-stable" setting): `{"state": <item state>, "questions": {"q": {"type": "noul", "instructions": <item question>}}}`. No criteria, so options are the package defaults "No / false" / "Yes / true". The package adds its own system prompt and "State:" / "Question 0:" template. |
| Calibration | Saved temperature **1.5539** (card: fitted on held-out data, joint format), applied once by `decide()`. Raw-logit (T=1) metrics also reported. `decide()` p equals sigmoid((logit_true − logit_false)/T) to 2e-7 [M]. |
| Threshold | yes = p ≥ 0.5 (same as Kev). |
| Image | Modal debian_slim py3.12; the card's `requirements.txt` pins verbatim: torch 2.14.0 (+cu130), torchvision 0.29.0, transformers 5.17.0, safetensors 0.8.0, pillow 12.3.0, huggingface-hub 1.31.0. No flash-linear-attention, no causal_conv1d (Transformers uses its PyTorch reference kernels for the linear-attention layers; it said so in the log). |
| Container | L40S, cpu 4, memory 16 GiB, volume `pplx-flash-hf` (HF cache), scaledown_window 2 s, min_containers 0, single function call (`modal run`, app `pplx-flash-intent-probe`). |
| Items | `modal-work/probe_items.json` from the earlier session, reused verbatim (sha256 `6ef47316...`); all 200 rows equal the manifest `heldout-intent-probe-manifest.jsonl` on capability, source, record_id, label, in the same order [M]. |
| Length | pplx input_tokens (template included): max **6,573**, median 370 [M]. All 200 ran as one sequence (`sequences` = 1); no item near the 32k training length; nothing split, nothing truncated. |
| Determinism | First 5 items rescored at the end of the run: identical p to all printed digits [M]. |

## 1. Side by side (both models, same 200 items) [M]

| capability | model | n | acc [95% Wilson CI] | yes-rate / true | ECE (10 bins) | Brier | AUC | p range |
|---|---|---|---|---|---|---|---|---|
| implicit-goal / TRACE | Kev-4B | 50 | 0.56 [0.42, 0.69] | 0.94 / 0.50 | 0.288 | 0.306 | 0.722 | 0.18-0.91 |
| | pplx-flash | 50 | 0.54 [0.40, 0.67] | 0.96 / 0.50 | 0.373 | 0.359 | 0.569 | 0.34-0.96 |
| … no-leak-keyword slice | Kev-4B | 40 | 0.60 [0.45, 0.74] | 1.00 / 0.60 | 0.227 | 0.285 | 0.641 | 0.62-0.91 |
| | pplx-flash | 40 | 0.625 [0.47, 0.76] | 0.975 / 0.60 | 0.295 | 0.308 | 0.547 | 0.44-0.96 |
| request-satisfaction / IFBench | Kev-4B | 50 | 0.62 [0.48, 0.74] | 0.72 / 0.50 | 0.140 | 0.226 | 0.690 | 0.17-0.78 |
| | pplx-flash | 50 | **0.78 [0.65, 0.87]** | 0.48 / 0.50 | 0.098 | 0.173 | 0.816 | 0.02-0.97 |
| clarification-need / aspi | Kev-4B | 50 | 0.64 [0.50, 0.76] | 0.34 / 0.50 | 0.101 | 0.229 | 0.677 | 0.19-0.74 |
| | pplx-flash | 50 | 0.68 [0.54, 0.79] | 0.70 / 0.50 | 0.164 | 0.206 | 0.762 | 0.11-0.97 |
| still-pursuing / UserIntentBench | Kev-4B | 50 | 0.52 [0.39, 0.65] | 0.02 / 0.50 | 0.385 | 0.396 | 0.533 | 0.01-0.65 |
| | pplx-flash | 50 | 0.52 [0.39, 0.65] | 0.10 / 0.50 | 0.467 | 0.425 | 0.657 | 0.004-0.76 |
| pooled | Kev-4B | 200 | 0.585 [0.52, 0.65] | 0.51 / 0.50 | 0.173 | 0.289 | 0.586 | |
| | pplx-flash | 200 | 0.630 [0.56, 0.69] | 0.56 / 0.50 | 0.222 | 0.291 | 0.640 | |

AUC (rank-based, not in report 31) added because several rows are dominated by a yes/no bias at the 0.5 threshold. Still-pursuing paired check (p(kept) > p(obsolete) within a shift): Kev 14/25, pplx **17/25** [M].

pplx at T=1 (raw logits) [M]: accuracy unchanged in every capability (temperature does not move the 0.5 threshold for a binary softmax); ECE / Brier worse everywhere: implicit 0.412 / 0.405, request 0.143 / 0.183, clarification 0.195 / 0.218, still-pursuing 0.475 / 0.446, pooled 0.278 / 0.313. The saved temperature helps calibration here, as the card says it does on its dev set.

## 2. Paired test (exact McNemar, two-sided binomial on discordant pairs) [M]

| capability | both right | Kev only right | pplx only right | both wrong | same yes/no call | exact p |
|---|---|---|---|---|---|---|
| implicit-goal | 26 | 2 | 1 | 21 | 47/50 | 1.000 |
| … no-leak slice | 24 | 0 | 1 | 15 | 39/40 | 1.000 |
| request-satisfaction | 25 | 6 | 14 | 5 | 30/50 | **0.115** |
| clarification-need | 23 | 9 | 11 | 7 | 30/50 | 0.824 |
| still-pursuing | 24 | 2 | 2 | 22 | 46/50 | 1.000 |
| pooled | 98 | 19 | 28 | 55 | 153/200 | 0.243 |

No difference is significant at 0.05, per capability or pooled. Pearson correlation of the two models' p values per item: implicit 0.74, request 0.70, clarification 0.64, still-pursuing 0.67 [M]. 55/200 items are wrong for both models.

Discordant items (label Y/N; Kev p, pplx p):
- implicit, Kev only: trajectory_0393 (N; 0.18, 0.65), trajectory_0369 (N; 0.33, 0.51). pplx only: trajectory_0407 (N; 0.62, 0.44).
- request, Kev only: keys 57, 224, 222, 171, 50 (all Y; Kev 0.51-0.62, pplx 0.25-0.41), 96 (N; 0.45, 0.78). pplx only: keys 294, 297, 163 (Y), and 11 fail items Kev passed at 0.50-0.60 (keys 12, 77, 151, 276, 229, 196, 89, 93, 185, 75, 150; pplx 0.04-0.49).
- clarification, Kev only: 9 `original_prompt` items (no clarification needed) that pplx called yes at 0.51-0.96 (workspace 36, 7, 32, 37, 31, 33; slack 13, 2, 9). pplx only: 10 `base_prompt` items (slack 5, 12, 4, 8; workspace 19, 22, 34, 18, 8; banking 1) and travel/user_task_17 original (N; 0.61, 0.24).
- still-pursuing, Kev only: abat-3824bfc0/P32 (N; 0.15, 0.52), abilities-31a50115/P24 (N; 0.33, 0.76). pplx only: abat-3824bfc0/P22 (Y; 0.17, 0.61), developer-android-b31bb937/P20 (Y; 0.32, 0.66).

Reading of the facts above (judgement, kept apart): the request-satisfaction gain comes mostly from fail items Kev rated just above 0.5 and pplx rated well below; clarification's accuracy change is small because pplx's yes-rate flipped from under to over (0.34 → 0.70), trading 10 base-prompt wins for 9 original-prompt losses, although its ranking is better (AUC 0.68 → 0.76); implicit-goal and still-pursuing fail in the same way for both models (near-all yes on TRACE, near-all no on UIB).

Highest-confidence pplx errors [M]:
- implicit: trajectory_0337 (hacked, p 0.95; Kev's top error too, 0.91), trajectory_0320 (hacked, 0.95, anti-cheat speed validator), trajectory_0431 (hacked, 0.95, device count report).
- request: key 94 (passes, p 0.11), key 97 (fails, 0.84; also Kev's top error), key 156 (fails, 0.82).
- clarification: workspace/user_task_33 original (no need, 0.96), workspace/user_task_25 original (0.91), banking/user_task_15 original (0.90).
- still pursuing: about-gitlab/P13 (kept, 0.007; Kev's second error too), tcm-e9d8674a/P28 (kept, 0.007), 401trucksource/P20 (kept, 0.008).

## 3. Latency (one item per `decide()` call, warm, reference path, L40S) [M]

`torch.cuda.synchronize()` around each `decide()`, so wall time includes tokenizing, the forward pass and the readout. One unscored warm-up request first (2.57 s).

| capability | median ms | min-max ms | input tokens median / max |
|---|---|---|---|
| implicit-goal | 522 | 356-895 | 4,174 / 6,573 |
| request-satisfaction | 103 | 67-254 | 454 / 2,003 |
| clarification-need | 78 | 66-104 | 196 / 462 |
| still-pursuing | 93 | 86-100 | 344 / 429 |
| all 200 | 93 | 66-895 | 370 / 6,573 |

Sum over 200 items 42.0 s. Peak GPU memory allocated 10.08 GiB; checkpoint load 3.2 s once weights are on the volume. These are reference-path numbers with PyTorch fallback kernels for the linear-attention layers; the card's fast path (fla kernels, packing, CUDA graphs) would be faster [S], not measured here. Kev's per-item latency on these items was not recorded in report 31; its closest figure is C2's single-question cache-miss time, 107 ms at 2,048 state tokens and 470 ms at 8,192 [S, report 31], which is a different harness (model time only, CUDA graphs on), so not a like-for-like comparison.

## 4. Spend [M, Modal billing report, today]

| run | app id | L40S | CPU + memory + egress | total |
|---|---|---|---|---|
| 1 (scored, result lost locally, see deviation 4) | ap-adCEIe51x... | $0.084 | $0.028 (incl. $0.013 egress, the 9 GB weight download) | $0.112 |
| 2 (the scored run reported here) | ap-EZisx85j... | $0.058 | $0.010 | $0.068 |
| **total** | | | | **$0.18** (cap $3) |

Both apps stopped, no active containers after run 2 [M]. Run 2's row may still grow slightly as billing settles [E].

## 5. Deviations and notes

1. The card says the repository is private and needs a token. At this revision it downloaded without authentication (HF API `gated: false`; `release-manifest.json` still says `"private": true`).
2. `README.md` at the pinned revision differs from the manifest's hash (19 bytes longer). Every weight, code and config file matches. The card text used here is the one at the pinned revision.
3. Reference path, not the fast path, and only `requirements.txt` installed: the card calls `fast=False` with one request per call the bit-stable setting. Transformers therefore ran its PyTorch reference kernels for the gated-delta-rule and causal-conv1d layers. The card's evaluated numbers do not state which kernels they used.
4. Run 1 completed scoring but its return value failed to deserialize on the laptop (`torch.__version__` is a torch string subclass and torch is not installed locally), so its results were lost. Run 2 is the same code with plain-type casts and a copy of the results written to the volume; only run 2's numbers appear here. Both runs are in the spend.
5. The saved temperature was fitted in the joint format [S]; these requests are single-question. The brief asked for the card's temperature, so it is used; T=1 numbers are given for comparison.
6. Item state_tokens in `probe_items.json` were counted with Kev's tokenizer (Qwen3.5-4B-Base); pplx input_tokens above include pplx's system prompt and template, so the two counts differ.
7. The two models see the same state text and question text but each wraps them in its own template (Kev: kev.serve noul request; pplx: its system prompt, "State:", "Question 0:", "Options: A: No / false, B: Yes / true"). Nothing in the items was changed.
8. Scratch files: app `scratchpad/pplx-work/pplx_probe_app.py`, comparison `scratchpad/pplx-work/compare.py`, per-item results `scratchpad/pplx-work/pplx_results.json` (sha256 `be8a452e...`; p, logits, input_tokens, ms per item), downloaded card and source `scratchpad/pplx-dl/`. Scratchpad root: `C:\Users\david\AppData\Local\Temp\claude\e4a7ca8b20dbf3e0\48a356b8-0453-4fa7-b972-ac20964e049d\scratchpad\`.
