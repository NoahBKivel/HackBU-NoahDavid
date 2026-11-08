# System One models vs Kev-4B on user-intent discrimination: capability survey

Date: 2026-11-07. Status: **FINAL v2**. All five research threads are folded in: Kev family (self), Jev-family agent, non-Jev agent, Semantic-Router/THX agent, and post-cutoff discovery agent (§6).

**Labels**
- **[M-ind]**: measured by an independent third party (a leaderboard lab run, or an outside paper running both models).
- **[M-own]**: measured by the model's author, on a primary page.
- **[C]**: claimed with no number or method behind it.
- **[U]**: UNVERIFIED (secondhand, aggregator text, or a figure shown only in an image).

**Sources**
- Every fact carries its source URL.
- "DI" means the Jev Decision Index 0.4.1 board by multimodalart. Its data files were generated 2026-11-06. Every entrant runs on 1x RTX PRO 6000 under the native inference helpers, with no prompt tuning. Sources: https://huggingface.co/spaces/multimodalart/jev-decision-index, `data/index.json`, `data/v03.json`, `data/methodology.json`.
- DI per-benchmark scores are [M-ind]. The "full" index is 0.6 × private same-skill tests + 0.4 × private new-domain tests. Nobody can train on these private tests, so they are the only leak-proof numbers in this document (methodology changelog v0.4).
- DI "Kev 4B r10" is the released `jaredpalmer/kev-4b`. The Kev card says: "published 2026-09-24 as round 10's confirmed candidate; included unchanged in Kev 1.0" (https://github.com/jaredpalmer/kev, `docs/model-cards/kev-4b.md` l.303).

**Sense (b) proxies used below.** No benchmark in the field measures (b) directly: unstated goals, request satisfaction, instruction adherence. These are the closest proxies.
- **When2Call MCQ** (n=3,652): answer, call a tool, ask for details, or decline. This is the clarification-need proxy (https://huggingface.co/datasets/nvidia/When2Call).
- **typed-decisions**: agent-trace outcome, next action and needs-review (https://huggingface.co/datasets/LocalLLaMA/typed-decisions).
- **System1-Arena Dialog/Judge** columns. They contain clarification_need, state_tracking, user_satisfaction, instruction_following (IFBench/IFEval) and agent_trajectory (AgentRewardBench, tau-bench). Only domain aggregates are published.
- **safeagents-judge-bench**: allow or block a coding-agent tool call (reward hacking, overreach).
- **RAGTruth**: is the response faithful to its source.

---

## 0. Bottom line

1. **Sense (a), routing.** Kev-4B is clearly beaten on held-out data at the same 4B size.
   - On DI [M-ind], CLINC150+OOS macro-F1 is:
     - Kev-4B: 0.750.
     - pplx-decider-flash-v1.2: 0.933.
     - vllm-sr/d3-mini: 0.963.
     - Jeffan-4B-2010: 0.953.
     - OneJev1.6-4B: 0.958.
     - KnowLine-4B-Gen5.5: 0.926.
   - Kev's own breadth-v1 test agrees [M-own]. CLINC150 accuracy is Kev-4B 0.793 vs Jev 0.953 (n=150).
   - Kev-4B's BANKING77 0.829 is **in-distribution**: banking77 is in its training cardData. Even so, every 4B competitor listed above beats it (0.90–0.93).
2. **Sense (b).** One direct (b)-type head-to-head exists. On every proxy, Kev-4B is behind.
   - **LLMBar** is the direct one: pairwise instruction-following judgment, n=419. Source: arXiv 2611.00505, Table 1, single run, all benchmarks held out for Kev [M-ind], https://arxiv.org/html/2611.00505v1.
     - Kev-4B: 71.8 Choice / 81.1 Checklist.
     - pplx-decider-flash-v1.2: 75.2 / 85.0.
     - Clef-flash (9B): 70.4 / 78.5.
     - Jev 1.14: 87.4 / 85.2.
   - The same paper reports more Kev-4B vs pplx-flash gaps:
     - JudgeBench: 66.6 vs 70.0.
     - RewardBench 2: 57.3 vs 64.3.
     - ECE: 0.058 vs 0.041.
     - Appended-note attack success: Kev-4B 32.2% vs pplx-flash 16.7%.
   - Proxies:
   - **When2Call** [M-ind DI]:
     - Kev-4B: 0.667.
     - 4B peers: 0.845–0.928.
     - elephant-1 (9B, MIT): 0.915.
     - Jev 1.14: 0.817.
   - **typed-decisions** [M-ind, Jeva paper]: Kev-4B 66.0 vs Jev 74.1 vs Jeva-4B 78.3 vs InternDecision-4B 78.7.
   - **DI private new-domain tests** (leak-proof, general decision ability, not intent-specific):
     - Kev-4B: 25.4.
     - pplx-decider-flash-v1.2: 40.0.
     - StartLux-4B: 38.1 (non-commercial).
     - KnowLine-4B: 37.3.
     - d3-mini: 36.5.
     - elephant-1: 44.4.
     - Jev: 48.3.
3. **The one area where Kev-4B is credibly strong on (b)-adjacent behaviour is abstention and calibration.**
   - Missing-evidence P≥0.9 share is 0.00% for Kev-4B vs 27.27% for Nox-1.0 (vllm-sr Decision-1.0 card [M-own vendor]).
   - Transfer ECE is 2.61% for Kev-4B vs 11.8% for Nox-1.0 (same card).
   - The Kev card reports unanswerable items with p≥0.9 at 0.00 (Jev 0.09).
   - Kev also has the best fine-tuning pipeline: `kev.train --init_from`.
4. **Is a swap justified by evidence?**
   - For (a): **yes**.
   - For (b): **the case is moderate.**
     - The single held-out direct judgment eval (LLMBar) gives pplx-flash a +3.4 / +3.9 pt edge over Kev-4B. That is a single run, and the 95% CI at n=419 is about ±4 pt.
     - The When2Call gap of about 22–26 pt is large. However, competitors' training data is mostly undisclosed, while Kev held When2Call out. A head-to-head bake-off on *our own* (b) set (Kev-4B vs pplx-decider-flash-v1.2 vs d3-mini, optionally elephant-1) is cheap: under 2 h and under $5. It should decide the swap. Do not decide from this survey alone. See §5.

---

## 1. Kev family (known baseline)

All facts are from the HF cards and https://github.com/jaredpalmer/kev, labelled [M-own] unless noted.

**Shared properties of the family**
- **Licence.** Apache-2.0 for adapter, head and base.
- **Interface.** One forward pass, no generation, TypeSafe `POST /v1/systemone`.
  - `choice`: 1–255 named options, dynamic per question.
  - `score`: 1–255 ordered levels.
  - `noul`: yes/no.
- **Shared state.** The state is computed once and cached. Each question is a separate row continuing from it, and the server packs questions within a 16,384-token budget. Packed and separate runs agree to within 4e-6 in fp32. Endpoints: `/v1/systemone`, `/permute`, `/separate`.
- **Fine-tuning.** `kev.train --init_from jaredpalmer/kev-<size>` on JSONL (API request plus `label`).
  - Example: 5,219 CFPB complaints went from 0.804 to 0.904 accuracy in one epoch.
  - A Kev-4B run costs "about $1 on an H100" (README).
  - Modal deploy: `modal deploy kev_serve.py`. Cold start is about 35 s; `KEV_FLASH=1` keeps one container warm.
- **Leakage.** **Kev-4B training cardData includes `legacy-datasets/banking77`**, plus boolq, ag_news, MNLI, sst5, yelp, trec, dbpedia, amazon, imdb, commitpackft, Aegis 2.0 and CFPB (https://huggingface.co/api/models/jaredpalmer/kev-4b). So any Kev BANKING77 score is in-distribution.
  - CLINC150, SGD, When2Call and the breadth-v1 sources are eval-only: the manifest lists `trainable_sources: []` (https://github.com/jaredpalmer/kev, `evals/breadth-v1/manifest.json`).

| | Kev-0.8B | Kev-4B (ours) | Kev-9B v2 | Kev-27B v2 |
|---|---|---|---|---|
| HF id | jaredpalmer/kev-0.8b | jaredpalmer/kev-4b (rev 139fdd94) | jaredpalmer/kev-9b | jaredpalmer/kev-27b |
| Base | Qwen3.5-0.8B-Base, frozen, LoRA r16 (11.3M) | Qwen3.5-4B-Base, frozen, LoRA r16 (33.8M) + pointer head, T=2.41 | Qwen3.5-9B-Base, LoRA r16 (45.4M), T=2.19 | Qwen3.8-27B, full FT (8×H200, 16.2 h) + 0.85/0.15 weight average, T=1.32 |
| Context, accepted / validated | 64k / 8k (16k fails tolerance) | 64k / 8k (CUAD 16k Δ −1.1 pp, lower bound −3.4; 32k −5.8; 64k −5.2) | 64k / 8k | 64k / **64k** (trained to 32k) |
| GPU memory | 3.8 GB (L4) | 14.3 GB resident | 21.9 GB | about 65.5 GB resident; 87.1 GB peak at 64k |
| Latency, new / repeated state | L4: 22.7 / 16.1 ms (6 q) | H100: 18.1 / 12.9 ms (6 q); 89.4 / 22.5 ms (2.2k state). L40S: 41.5 / 27.7 ms | H100: 24.0 / 16.6 ms | 64k state: 9.4 s new / 733 ms cached |
| CLINC150 acc, breadth-v1 **test** (n=150, eval-only) | 0.740 | **0.793** | 0.820 (released) | 0.913 |
| SGD acc, breadth-v1 test (n=150) | 0.487 | **0.673** | 0.667 | 0.720 |
| breadth-v1 test index | 23.3 | 38.0 | 40.0–41.0 | 52.3 |

**Comparators on breadth-v1 test**
- Jev: CLINC150 0.953, SGD 0.733, index 54.0.
- AutoJev-27B (`denis-pplx/autojev-27b`): CLINC150 0.933, SGD 0.833, index 50.0.
- Source: `runs/fam-breadth-test-report/report.json` and `runs/r24-breadth-report/report.md` in the Kev repo.
- **Our earlier "Jev ~0.97 dev" figure** is Jev's breadth-v1 *development* CLINC150 score of 0.973. On the same dev split Kev-4B scores 0.880 (`runs/breadth-v1-report/report.md`, split=development). So the like-for-like gaps are: test 0.793 vs 0.953, dev 0.880 vs 0.973.

**Kev-4B (b)-adjacent numbers [M-own]**

| Eval | Kev-4B | Comparison |
|---|---|---|
| When2Call (devtools-v1 dev, eval-only) | 0.660 | – |
| Prompt injection | 0.753 | Jev 0.893 |
| hard-v1 test, includes "judging a proposed answer" (no per-family score) | 0.803 | Jev dev 0.777 |
| **agents-ood-v1** (synthetic agent sessions, held-out world, n=2,084, median state 12.7k tokens) | 0.847 | Kev-27B k-w85 0.988; Kev-0.8B r15 0.655 |

- agents-ood-v1 is eval-only, but it comes from the same generator family as Kev's training data (sft-v2), so it is not independent. Sources: `runs/r28-4b-r10-agentsood/report.json`, `evals/agents-ood-v1/manifest.json`.

**Kev-4B on DI [M-ind]**

| Benchmark | Kev-4B |
|---|---|
| BANKING77 macro-F1 | 0.829 (in-distribution) |
| CLINC150+OOS macro-F1 | 0.750 |
| When2Call | 0.667 |
| API-Bank | 0.534 |
| RAGTruth F1 | 0.675 |
| SGD (buggy, see below) | 0.478 |

| DI aggregate | Kev-4B |
|---|---|
| Full index | 34.93 (rank 170 of 274) |
| Same-skill | 36.17 |
| New-domain | 25.40 |
| ECE | 0.032 |
| Median latency | 59.2 ms |

- The DI SGD row is **excluded from the index because of a build bug**: "the builder gave every SGD row the whole dialogue, including the turns after the one being classified" (methodology.json). Ignore every DI SGD number, including Jev 1.14's 0.090.

**Other Kev-family checkpoints**
- Kev-0.5b, 0.6b and 8b are prototypes (Qwen2.5 / Qwen3 bases; https://huggingface.co/api/models?author=jaredpalmer).
- Derivatives:
  - turintech/Kev-{0.8B,27B}-Artemis-GGUF: quantization only. IQ4_XS keeps 97.8% of answers the same; llama-server `/v1/systemone`; prefix caching not mentioned (https://huggingface.co/turintech/Kev-27B-Artemis-GGUF).
  - yale-cultural-heritage/kev-4b-europeana-persons.
  - SecJev (§2).

---

## 2. Models on the assigned list

Labels:
- "DI" = [M-ind] per-benchmark row (B77 mF1 / CLINC+OOS mF1 / When2Call / RAGTruth).
- "new" = DI private new-domain score.

### 2.1 Jeff
- **Two unrelated families share the name.**
- **jgeuter Jeff-1.0 / 1.1**
  - IDs: `jgeuter/Jeff-1.1-Qwen-4B` (Qwen3.5-4B), `-Qwen-27B` (Qwen3.6-27B), `-Medium` (gemma-4-12B-it), `-Large` (gemma-4-31B-it) (https://huggingface.co/api/models?author=jgeuter).
  - Licence: **weights CC-BY-NC-4.0**; code Apache-2.0 (https://github.com/j-geuter/Jeff).
  - Architecture: merged LoRA plus a 16-slot head.
  - Context: 8,192 accepted and validated. Longer input is condensed or refused.
  - Interface: `/v1/systemone` with noul/choice/score. Up to 256 options, run as rounds of 16. Yes/no answers are committed to 0.199/0.801 by default; `--commit off` returns calibrated probabilities.
  - Intent and (b): **none reported**.
  - [M-own] OpenDecisions Capability: 1.1-Large 89.0, 1.1-Qwen-4B 79.3, Jev 1.13 80.1. Training length was selected on OpenDecisions. JevBench public: 4B 72.7 (Kev-4B card: 0.758).
  - Fine-tuning: recipe published (LoRA r32, 800 steps), **no training code**.
  - Prefix caching: not reported. Cost: 4B about 9 GB, 49 ms per decision on an H200 (arXiv 2610.17205; https://huggingface.co/jgeuter/Jeff-1.1-Qwen-4B).
- **jeff-legacy / firelex Jeff**
  - IDs: `jeff-legacy/Jeff-Qwen3.5-{0.8B,2B}`, `Jeff-Gemma4-E2B`, superseded by `mstrasser/jeff-base` v1.3. Apache-2.0. CLINC150 and MASSIVE are in training.
  - The support-intents adapter on held-out Bitext/HWU64/SNIPS (n=5,577) [M-own]: base 85.1%, adapter 96.8%. Adapters hot-swap at runtime (https://huggingface.co/jeff-legacy/Jeff-Qwen3.5-0.8B-support-intents).
- **DI "jeff"** (logan-markewich, gliformer-large 0.58B) is a third, weak entry: DI 0.610 / 0.443 / 0.233 / 0.171; new 3.29.

### 2.2 Open-Jev (Zefan Cai)
- IDs: `ZefanCai/Open-Jev-2B` (Qwen3.5-2B), `-9B` (Qwen3.5-9B), `-27B-v1.1` (Qwen3.8-27B). Each is a LoRA plus a scalar head.
- Licence: adapters Apache-2.0, code MIT (https://github.com/Zefan-Cai/Open-Jev).
- Context: 4,096 tokens per candidate, accepted and validated.
- Interface: `/v1/systemone` ("partial compatibility"). Options are dynamic with no hard maximum.
- Intent and (b): **none reported**. The training data is browser, workflow and game control.
- [M-own] JevBench public, overall / hard:

| Model | Overall | Hard |
|---|---|---|
| Open-Jev-2B | 64.9 | 41.4 |
| Open-Jev-9B | 77.5 | 59.5 |
| Open-Jev-27B | 85.3 | 72.1 |
| Jev 1.13 | 86.6 | 73.0 |

- Fine-tuning: **public `python -m jev.train`**, LoRA r8.
- Prefix caching: `--prefix-cache` is experimental and failed probability tolerance on 9 of 11 workloads.
- Cost: 2B peaks at 6.9 GiB. Customer-service latency is 85 ms local vs 295 ms for Jev.
- Not on DI by this name. `AlexWortega/openjev` and `pngwn/system-one-qwen3.5-4b-scorer-v2b` ("open-jev (pngwn)") are listed. pngwn DI: 0.505 / 0.576 / 0.466 / 0.004; new 25.19.

### 2.3 AlquimiaAi/openjev (= openjev/openjev)
- Size and licence: 27B, about 54 GB bf16. Base is unnamed (tagged qwen3_5). **Weights CC-BY-NC-4.0** (https://huggingface.co/AlquimiaAi/openjev).
- Context: 16,384 accepted; tested to about 15.1k.
- Interface: `/v1/systemone`. Up to 52 options per pass, more in groups.
- [M-own] Intent/routing/topic (n=1,218, 34 unnamed sources):

| OpenJev | Jev | Untuned base |
|---|---|---|
| 92.8 | 92.8 | 93.2 |

  So training added nothing for intent. MASSIVE DE/FR/HI/JA: 85.8 vs base 80.4.
- (b)-adjacent [M-own], untuned base → OpenJev:
  - Desktop next action: 76.5 → 88.0.
  - Web next action, unseen sites: 68.5 → 87.4.
  - Web next action, unseen domains: 65.7 → 84.5.
  - MiniWoB: 39, equal to Jev.
- Fine-tuning: no training code.
- Prefix caching: **vLLM `--enable-prefix-caching`**. A cached page with a new question takes 118 ms at 1.1k tokens.
- Hardware: one 80 GB GPU in FP8. Not a 4B option.

### 2.4 SecJev
- Weights are GitHub release tarballs (https://github.com/UESTC1010/SecJev). HF mirrors: `macmacmacmac/SecJev-4B`, `-Action-Monitor-C1`.
- **Continued from Kev-4B, 0.8B and 9B.** Same LoRA r16 plus head shape as Kev.
- Licence: **custom "SecJev Use and Distribution Agreement v1.0"**.
- Interface: no HTTP server; `infer.py` CLI. Intent: none.
- Retention vs Kev-4B [M-own]:

| Suite | SecJev-4B | Kev-4B |
|---|---|---|
| decision-v7 | 86.58 | 87.08 |
| transfer-v4 | 83.84 | 83.69 |

- (b)-adjacent [M-own], AgentDojo action monitor. "Does the user's request authorize this tool call?" is an intent-adherence task (https://huggingface.co/macmacmacmac/SecJev-4B-Action-Monitor-C1):
  - Hijack rate: 34.1% undefended → 1.6% (stop) / 0.8% (redact).
  - Normal tasks completed: 97.3% → about 90%.
  - Against an adaptive attacker: 58% hijacked vs 64% undefended.
  - SecJev-0.8B trust-boundary score: 80.28 vs Kev-0.8B 51.88.
- **Relevance:** existence proof that `kev.train --init_from` adds an adherence skill without losing base skills. This is a recipe, not a swap candidate.

### 2.5 Liquid d1-3B / d1-omni / d1-ultra
- **Licence for all open d1 models: `lfm1.0`**, which bars commercial use above $10M annual revenue (https://huggingface.co/LiquidAI/d1-3B/blob/main/LICENSE). The blog says "without restrictions", which conflicts (https://www.liquid.ai/blog/open-d1).
- **d1-3B** (3.1B, LFM2.5-VL-3B)
  - Context: 32k claimed.
  - Interface: `system_one` with noul/choice/score (score 2–10). Multi-question in one pass. `/v1/systemone` compatibility and max options: not stated.
  - [M-own] MASSIVE intent 87.3. Split and leakage not stated.
  - DI: 0.880 / 0.912 / 0.866 / 0.776; new 11.47; 16.1 ms.
- **d1-2B** (1.92B, LFM3-VL-2B)
  - Context: 128k accepted; "less reliable past about 64K" [C].
  - DI: 0.880 / 0.902 / **0.898** / 0.784; new 13.26.
  - [M-own] H100 5.7 ms per question.
- **d1-Omni-2B**
  - DI: 0.878 / 0.887 / 0.895 / 0.768.
  - [M-own] SLURP intents 87.4; Speech-MASSIVE 85.2.
- **d1-omni-600M**
  - DI: 0.837 / 0.853 / 0.408 / 0.023.
- **d1-ultra: hosted-only.** Base unnamed. Priced at $0.042 per 1M input tokens. Context 32k (https://www.liquid.ai/blog/d1-ultra).
  - AIM System One Index rank 1 (index 60; AIM-Decision Classification 52.1) (https://aimultiple.com/system-one, updated 2026-11-03).
  - "Beats Jev 1.14 across all tasks" [U]: the figures are images only.
- **For the whole family:**
  - **Very low DI new-domain scores (11–13)**: strong on public tasks, weak on unseen ones.
  - No training code; fine-tuning by contact form.
  - (b) proxy: safeagents-judge balanced accuracy 0.823 for d1-3B [M-ind].

### 2.6 Cloudflare Clef / Clef-flash
- IDs and licence: `Cloudflare/clef` (27B, Qwen3.8-27B) and `Cloudflare/clef-flash` (9B, Qwen3.5-9B). Apache-2.0; also hosted on Workers AI (https://huggingface.co/Cloudflare/clef, https://blog.cloudflare.com/clef-decision-models).
- Context: 64k claimed (blog); card default `max_length` is 16,384.
- Interface: "fully compatible with Jev", `/v1/systemone` via SGLang dev-clef.
- **Architecture conflict.** The card describes a joint-schema head; the blog describes a frozen backbone plus rank-256 adapters.
- DI:

| Model | B77 | CLINC+OOS | When2Call | RAGTruth | new |
|---|---|---|---|---|---|
| Clef | 0.941 | 0.974 | 0.725 | 0.795 | 45.06 |
| Clef-flash | 0.908 | 0.669 | 0.653 | 0.356 | 35.00 |
| Clef-omni | 0.942 | 0.975 | 0.567 | 0.345 | – |

- [M-own] card comparisons are against Kev **9B**:
  - CLINC: Clef 97.43 / Kev-9B 79.03.
  - When2Call: Clef 72.37 / Kev-9B 49.6.
- (b) [M-own] TypeSafe workflow "agent trace observability": Clef 68.5, Clef-flash 69.8, Jev 71.6.
- (b) safeagents-judge balanced accuracy [M-ind]: Clef 0.718, Clef-flash 0.721, Clef-omni 0.845.
- Fine-tuning: no public code; offered as a service.
- Derivative: **TypeScript/FastBrain-9B** (Apache-2.0, fine-tuned from Clef-flash), self-reported [M-own]:
  - CLINC+OOS 98.44 and When2Call 81.13 on the Cloudflare DI v0.2.1 harness.
  - safeagents-judge 0.974. The labels come from a model panel and the test set has 39 "allow" items, so this is noisy.
  - Recommends `--no-cache-prompt` (https://huggingface.co/TypeScript/FastBrain-9B).
  - **The "98.4%" in the user's THX-01 claim may be conflated with FastBrain's 98.44 CLINC** [U].

### 2.7 Laya
- ID and licence: `convaiinnovations/laya`, Apache-2.0. 421M (ModernBERT-large); 512 context (multilingual variant 1,024–8,192).
- Interface: `/v1/systemone`. Recommends fewer than 20 options (https://huggingface.co/convaiinnovations/laya).
- [M-own] BANKING77 0.425–0.492 (n=400).
- DI: 0.143 / 0.032 / 0.119; new 6.63.
- System1-Arena [M-ind]: overall 44.5, Dialog 47.7, Judge 41.7.
- Fine-tuning: Kaggle 2×T4 notebook.
- **Not a candidate.**

### 2.8 GLiNER2.5-Decide
- ID and licence: `fastino/GLiNER2.5-Decide`, Apache-2.0. About 340–490M, DeBERTa-v3-large encoder.
- Interface: **not `/v1/systemone`**; uses `classify_text` label schemas.
- [M-own] fast-decisions test 60.2%. The tasks are custom banking_intent, support_intent and agent_handoff label sets, not BANKING77 (https://huggingface.co/datasets/fastino/fast-decisions).
- DI: 0.656 / 0.604 / 0.334 / 0.253; new 4.86.
- safeagents-judge: 0.577. Parallel blog: last on every task (https://parallel.ai/blog/are-all-system-one-models-created-equal.md).
- Fine-tuning: `ExtractorTrainer`.
- **Not a candidate.**

### 2.9 OpenDecider (400M / 4B)
- IDs and licence: `manjunathshiva/opendecider-nano` (Ettin-400m, 2,048 context) and `opendecider-small[-td]` (LoRA on Qwen3-4B-Instruct-2507, 8.9 GiB, 38 ms per question on L40S). Apache-2.0. Serves `/v1/systemone` (https://github.com/manjunathshiva/opendecider/blob/main/COMPARISON.md).
- [M-own] BANKING77 (Laya battery, n=400): nano 0.645, small 0.748, Jev 1.13 0.845.
- typed-decisions: small-td 0.792 vs Jev 0.754. This compares a model fine-tuned on that train split against a zero-shot Jev.
- Not on DI.
- The page contained an embedded prompt-injection string (ignored).
- **Not a candidate.**

### 2.10 AgentJev-0.6B
- ID and licence: `aimeigaoshou/agent-jev`, Apache-2.0. Qwen3-0.6B plus a permutation-equivariant head; 2,048 context.
- Interface: `POST /api/evaluate`, **not `/v1/systemone`**.
- Shared-state encoding plus a candidate trie [M-own]: P50 278 → 43.9 ms.
- typed-decisions 79.25. This is agreement with a teacher model.
- Intent and (b): none (https://github.com/malevrigns/agent-jev).
- **Not a candidate.**

### 2.11 Nimble (Bespoke Labs)
- **Bespoke-Nimble-9B v1/v2**: Apache-2.0, LoRA on Qwen3.5-9B. **Public CUDA LoRA trainer** (https://github.com/bespokelabsai/nimble). 8,192 context, 255 choices.
  - The CUDA scorer rescores the full prompt per field (no prefix reuse).
  - DI v2: 0.694 / 0.308 / 0.727.
- **Nimble-9B v3**: **CC-BY-NC-4.0**. DI 0.837 / 0.883 / 0.868 / 0.762; new 38.2.
- **Nimble-v4-max v4.1** (27B): **CC-BY-NC-4.0**. `shared_prefix` caching. DI 0.931 / 0.963 / 0.914 / 0.861; new 58.09; DI rank 8 (https://huggingface.co/bespokelabs/Nimble-v4-max).
  - The v4.0 → v4.1 jump on BANKING77 (79.9 → 93.2) is unexplained; training data is undisclosed.
- Parallel blog [M-ind]: Nimble-9B and Kev-4B both score "above 91" out of the box on query routing. After prompt tuning, mean AP is Nimble 89.7 vs Kev-4B 86.4.

### 2.12 Baseten / Base Labs mammoth-1 and elephant-1
- IDs and licence: `baselabs/elephant-1` (9B, full fine-tune of Qwen3.5-9B) and `baselabs/mammoth-1` (27B, Qwen3.5-27B). **Both MIT** (https://huggingface.co/baselabs/elephant-1, https://labs.baseten.co/articles/mammoth-1-and-elephant-1-frontier-decision-models).
- Context: **16,384 hard limit**; longer requests are refused.
- Interface: choice 1–255, yes/no P(true), score 2–10. Uses the `qev` package's SystemOneRequest; HTTP `/v1/systemone` is not stated.
- **Shared-prefix KV caching**: the state is prefilled once, each question pays only for its suffix, and a block-bidirectional mask keeps the cache valid [M-own design claim].
- Training: Mix 8, 6.21M examples, including 1.0M judging and 1.0M safety/abstention. Decontamination claimed against Jev DI and AA DI only. Whether BANKING77/CLINC/When2Call train splits were used is not stated.
- DI:

| Model | B77 | CLINC+OOS | When2Call | RAGTruth | API-Bank | Full index | New-domain | Latency |
|---|---|---|---|---|---|---|---|---|
| elephant-1 | 0.929 | 0.973 | **0.915** | 0.853 | 0.890 | 60.26 | **44.41** | 113.7 ms |
| mammoth-1 | 0.939 | 0.976 | 0.917 | 0.858 | – | 68.44 | 56.27 | 220.1 ms (rank 13) |

- Fine-tuning: recipe published (elephant-1: LR 3.5e-6, 1 epoch on 128×H100). **No training code**, but these are standard Qwen3.5 weights, so continued training is DIY.
- Memory: about 19 GB / 55 GB bf16 [U, estimate].

### 2.13 SearchJev
- IDs and licence: `SearchJev/SearchJev-4B` and `-0.8B`. LoRA r16 on Qwen3.5. Apache-2.0 (https://huggingface.co/SearchJev/SearchJev-4B; arXiv 2610.05107).
- Context: **2,048** (state truncated).
- Interface: Python `JEVPredictor`, **no HTTP server**.
- **Trained on the BANKING77, CLINC150 and MASSIVE training splits**, so its intent scores are in-distribution.
- [M-own] Table 9, all labels as options, at most 1,000 items, split unstated:

| Model | B77 | CLINC150 | MASSIVE-en |
|---|---|---|---|
| SearchJev-4B | 89.0 | 94.6 | 87.2 |
| Jev 1.13 | 79.7 | 92.6 | 86.2 |

- Out-of-distribution routing: 55.8 vs Jev 62.3, so it loses out of distribution.
- (b): When2Call MCQ test (n=1,500) 72.1 vs Jev 73.1 vs base 42.5. When2Call training status not stated.
- Fine-tuning: **full public pipeline** `start_training.py` with `--resume auto`.
- Latency: 37.1 ms per decision on an H200.

### 2.14 Jeva
- ID and licence: `LIQIIIII/Jeva-4B` (Qwen3.5-4B, LoRA r64, 13.4M decision core), Apache-2.0 (https://huggingface.co/LIQIIIII/Jeva-4B; arXiv 2610.18773).
- Interface: Python `system_one`, no `/v1/systemone`. Up to 2,048 candidates; `allow_null` adds an explicit "none of these" output. Option encodings are cached across requests.
- **The only paper running Kev-4B head-to-head** [M-ind for Kev, M-own for Jeva]:

| Benchmark | Jeva-4B | Jev 1.13 | Kev-4B | InternDecision-4B |
|---|---|---|---|---|
| BANKING77, K=16 | 91.62 | 82.50 | 82.47 | – |
| MASSIVE, K=16 | 90.22 | 81.61 | 73.54 | – |
| typed-decisions | 78.30 | 74.10 | **66.00** | 78.70 |
| Mind2Web cross-task | 79.99 | 66.26 | 40.32 | – |

  - Null detection AUROC: Jeva 98.66 vs Kev 93.61. Permutation flips: Jeva 0% vs Kev 17.5%.
- **Caveats:**
  - Jeva trained on about 80k unnamed "intent recognition" examples, and leakage is not addressed.
  - Kev was trained on BANKING77, which flatters Kev on that row.
- Fine-tuning: `jeva-finetune` CLI (head or LoRA).
- `OPENGRAPE/Jeva-9b` is unrelated and leaked (it used the test split as validation).

### 2.15 vLLM Semantic Router Decision 1.0 / 2.0 (Lux-9B, Sol-2B, Nox-4B, Vega-27B, Kai-0.6B)
Sources: https://huggingface.co/vllm-sr/Decision-2.0-{Lux-9B,Nox-4B,Vega-27B,Kai-0.6B,Sol-2B}. All Apache-2.0.

- **Interface.** `system_one` in the Jev schema, 2–**255** options (`max_options`). A shared 256-d bilinear candidate head ("shared candidate heads": **verified**). `/v1/systemone` via the vLLM-SR runtime.
- **Shared-state prefill** (`decision2/shared_ctx.py`, tree or cache mode) is **opt-in**.
- **Runtime** tested on one ROCm GPU only; CUDA is not shown as tested.

| Model | Params | Base | Max input (claimed; validated not reported) | Training |
|---|---|---|---|---|
| Nox-4B | 4.21B | Qwen3.5-4B-Base (same as Kev) | 16,384 | LoRA r128 merged |
| Lux-9B | 7.94B | from Decision-1.0-Lux | **16,384 (claim verified)** | full-weight soup |
| Vega-27B | – | Qwen3.8-27B | 32,768 | LoRA r512 adapter |
| Sol-2B | 1.88B | – | 16,384 | – |
| Kai-0.6B | – | Qwen3-0.6B-Base | 8,192 | – |

- **The "Lux-9B ~76.94 overall on complex classification/routing" claim is stale and misdescribed.** 76.94 was the Decision **1.0** Lux score in card revisions of 2026-09-22; it is now 77.40. It is a 54-task mixed benchmark scored by the vendor, with panel weights "chosen after observing benchmark results" (https://huggingface.co/vllm-sr/Decision-1.0-Lux-9B).
- **Vendor head-to-head [M-own vendor], 54 tasks:**
  - Overall: Jev 81.05, Lux-1.0 77.40, Nox-1.0 73.09, Kev-9B 71.89, Kev-4B 70.09.
  - Intent routing is saturated: Kev-4B, Nox and Lux all score 100. Intent routing EN: Kev-4B 87.5, Nox 91.67, Jev 91.67.
  - Answerability: Kev-4B 81.67, Nox 88.33, Lux 93.33, Jev 90.83.
  - **Missing evidence:** Kev-4B is much better calibrated (P≥0.9 share 0.00% vs Nox 27.27%).
- **Leakage:** the 1.0 attribution files show **training on the BANKING77 and CLINC150 train splits**. 2.0 data is undisclosed; the 2.0 cards claim a row-level audit against Index test items.
- **DI:**

| Model | B77 | CLINC+OOS | When2Call | RAGTruth | New-domain |
|---|---|---|---|---|---|
| Nox-4B 2.0 | 0.785 | **0.877** | 0.615 | 0.680 | 27.91 |
| Lux-9B 2.0 | 0.840 | 0.899 | 0.569 | 0.641 | 34.02 |
| Vega-27B 2.0 | 0.881 | 0.936 | 0.646 | 0.814 | 48.12 |
| Sol-2B 2.0 | 0.783 | 0.786 | 0.517 | 0.102 | – |
| Kai-0.6B 2.0 | 0.716 | 0.652 | 0.386 | 0.010 | – |

  **On When2Call, every Decision 2.0 model is below Kev-4B (0.667).**
- **System1-Arena** (arXiv 2610.21244; https://raw.githubusercontent.com/TianyuCodings/S1-Arena/main/leaderboard/results.json) [M-ind]:

| Model | Acc | Dialog | Judge | Route |
|---|---|---|---|---|
| Vega | 73.0 | 73.5 | 68.4 | 66.5 |
| Jev 1.13 | 72.6 | 73.2 | 68.4 | 64.5 |
| Lux | 67.0 | 70.7 | 60.6 | 58.4 |
| Nox | 65.1 | 70.7 | 58.3 | 59.0 |
| Kai | 50.3 | 53.6 | 47.9 | 46.0 |
| Laya | 44.5 | 47.7 | 41.7 | 42.4 |

  - LLM reference: Claude Opus 5.5 at 81.1 Acc, 76.5 Dialog, 77.8 Judge.
  - Agentic loop success: Vega 26.5 vs Jev 17.4.
  - **Kev is not in System1-Arena.** No per-task numbers are published, so clarification_need and instruction_following cannot be isolated. There is no contamination analysis.
- Fine-tuning: partial. Vendored `dev2model/lora.py` and data contracts; no trainer loop or data.
- **The newer d3 family is in §3.**

### 2.16 THX-01 (HAL-X AI)
- ID: **`doofz/THX-01`** (https://huggingface.co/doofz/THX-01). Successor: `HAL-X-AI/THX-02` (4.5B).

| Claim | Verdict |
|---|---|
| 322M params (mmBERT-base 307M + 15M head) | verified |
| Non-autoregressive | verified |
| Apache-2.0 | verified |
| About 10 ms | vendor-measured: p50 10.06 ms, 3 questions, RTX 4090, earlier checkpoint |
| **98.4%** | **misleading**: average on HAL-X's own 15-category support-ticket set (n=2,843) |

- **Leakage on that ticket set:** support tickets were in training stage S5, and the "independent" test set was written by the same LLM that taught the training data.
- On that same set [M-own vendor]: Jev 97.4, Kev-4B 92.8.
- Independent and other evidence:
  - typed-decisions: **0.377**, last of 18 and below the 0.487 prior.
  - THX-02 card: THX-01 scores 11.30 on DI 0.3 public.
  - BANKING77 (own suite): 65.9%.
- Input: 1,024 tokens per question, truncated. No prefix sharing.
- **Not a candidate.**

---

## 3. New models found during this survey (not on the assigned list)

These are the actual swap candidates. All open-weight and all 4–9B. DI numbers are [M-ind].

| Model (HF id) | Licence | Base | B77 | CLINC+OOS | When2Call | RAGTruth | API-Bank | DI full | DI same-skill | **DI new-domain** | Median latency | Interface | Training code |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **jaredpalmer/kev-4b (ours)** | Apache | Qwen3.5-4B-Base | 0.829* | 0.750 | 0.667 | 0.675 | 0.534 | 34.93 | 36.17 | **25.40** | 59.2 ms | /v1/systemone, 255 options, state cache | **yes, init_from** |
| **perplexity-ai/pplx-decider-flash-v1.2** | Apache | Qwen3.5-4B | 0.901 | 0.933 | 0.896 | 0.825 | 0.864 | 54.29 | 56.16 | **40.02** | 74.8 ms | choice 1–255, noul, score 2–255; joint multi-question in one sequence; **not /v1/systemone** | no |
| **vllm-sr/d3-mini** | Apache | Qwen3.5-4B | 0.927 | 0.963 | 0.845 | 0.716 | 0.839 | 49.97 | 51.90 | 36.52 | 50.4 ms | /v1/systemone (vLLM-SR Engine; vLLM PR, nightly) | no |
| **PelaAI/KnowLine-4B-Gen5.5** | Apache, code MIT | Qwen3.5-4B | 0.903 | 0.926 | 0.905 | 0.809 | 0.890 | 55.99 | 61.20 | 37.28 | 35.2 ms | /v1/systemone, ≤64 questions per state | no |
| tattrongvu/Jeffan-4B-2010 | Apache | Qwen3.5-4B | 0.914 | 0.953 | 0.907 | 0.819 | 0.860 | 52.21 | 58.03 | 33.52 | 50.4 ms | choice ≤255 (engine); vLLM plugin **disables prefix caching**; vLLM path needs a B200 | no |
| OmniJev/OneJev1.6-4B | Apache | Qwen3.5-4B | 0.900 | 0.958 | 0.884 | 0.834 | 0.890 | 48.88 | 55.78 | 29.56 | 27.2 ms | noul/choice/score; /v1/systemone via Flide | no |
| startlux-models/StartLux-Decision-v1.1-4B-Instant | **CC-BY-NC** | Qwen3.5 | 0.907 | 0.935 | 0.928 | 0.840 | 0.870 | 54.80 | 58.60 | 38.07 | 38.3 ms | /v1/systemone, ≤26 options per read | no |
| **baselabs/elephant-1** (9B) | **MIT** | Qwen3.5-9B | 0.929 | 0.973 | 0.915 | 0.853 | 0.890 | 60.26 | 62.44 | **44.41** | 113.7 ms | choice 1–255; shared-prefix KV cache; 16k hard cap | no (recipe only) |
| Jev 1.14 (hosted, reference) | – | – | 0.799 | 0.903 | 0.817 | 0.751 | 0.866 | 60.24 | 59.28 | 48.26 | – | – | – |

\* Kev-4B's BANKING77 score is in-distribution.

Sources:
- DI: `data/index.json` and `data/v03.json`.
- pplx: https://huggingface.co/perplexity-ai/pplx-decider-flash-v1.2
- d3-mini: https://huggingface.co/vllm-sr/d3-mini
- KnowLine: https://huggingface.co/PelaAI/KnowLine-4B-Gen5.5
- Jeffan: https://huggingface.co/tattrongvu/Jeffan-4B-2010
- OneJev: https://huggingface.co/OmniJev/OneJev1.6-4B
- StartLux: https://huggingface.co/startlux-models/StartLux-Decision-v1.1-4B-Instant
- Licences and gating: HF API, `gated=False` for all.

**Notes per candidate**

- **pplx-decider-flash-v1.2** (https://huggingface.co/perplexity-ai/pplx-decider-flash-v1.2)
  - Distilled from Perplexity's 27B deciders: "the student learns the teachers' full probability distributions". Soup of several runs. tasksource data. The 27B sibling used official training splits "decontaminated against test sets".
  - Context: `max_length` 262,144; **trained to about 32k**; spot-checked at 243k.
  - Custom architecture: full-attention layers are **non-causal over the whole request**, plus a [255, 2560] readout. Stock causal inference does not reproduce the checkpoint. A fast path uses CUDA graphs.
  - Weights: about 9 GiB bf16. Development calibration: ECE 0.021 at T=1.554.
  - Multi-question: the card recommends **one question per request by default**. Joint mode costs −15.4 on BFCL and −20.1 on ACOS, but gains +6.6 on SATA-Bench. So shared-state multi-question is not free here.
  - No prefix caching and no training code.
- **d3-mini** (https://huggingface.co/vllm-sr/d3-mini)
  - Self-reported DI 0.3.2: new-domain 45.6. The 0.4.1 board, with harder new-domain tests, gives 36.52.
  - safeagents-judge 0.692 [M-ind].
  - typed-decisions 0.743 [M-ind, SaylorTwift board: https://huggingface.co/buckets/SaylorTwift/typed-decisions-evals/resolve/leaderboard.md].
  - Serving: MI325X, 18.1 ms per question; peak memory 14.8–22.5 GiB. Verified on AMD; the CUDA wheel is not run on NVIDIA [C].
  - Training data not disclosed.
- **KnowLine-4B**
  - **Leakage flag:** the DI entrant note says it trained on DI benchmark train splits. The discovery agent relayed this; I did not re-read it. Its intent numbers are therefore in-distribution.
  - Merged LoRA r32 soup. "No output of Jev or any other decision model was used as a training label."
  - Read-twice front end for requests of at most 3,000 tokens. Serving via SGLang FP8. **No training code.**

**Other leads**
- **AutoJev-27B** (`denis-pplx/autojev-27b`; MIT code / Apache weights; full SFT, 73k examples on one H200; `configs/train.sh`).
  - Kev breadth-v1 test: CLINC 0.933, SGD 0.833 [M-ind by Kev author].
  - 27B, so it is a reference point, not a swap.
- **pplx-decider-v1.2** (27B): DI new-domain 57.76, When2Call 0.903.
- **Parallel blog** [M-ind] (https://parallel.ai/blog/are-all-system-one-models-created-equal.md). Average rank over 4 production tasks: Jev 1.75, pplx-decider-v1 2.00, d1 3.00, Rune-26B 4.25, Nimble-9B and Kev-4B 6.00, GLiNER 8.00.
- **AIM System One Index** (https://aimultiple.com/system-one, 2026-11-03). Top 10: d1-ultra, AutoJev-27B, decider-12b, GLiDE, Drex Max, Solar Decide, Jev 1.14. Its classification set includes "browser task done check" (a (b)-adjacent task). Kev-4B is not in the top 10; the full CSV was not read.
- Other HF leads, not verified (from the Jev-family agent):
  - JevAgentHarness/AgentDecision-4B (CC-BY-NC; arXiv 2610.21412 AgentDecisionBench).
  - alanhuangya/OpenJev-4B (LoRA on kev-4b, Mind2Web plus typed-decisions).
  - wayfind/metask-jev-4b-policy-mix.

---

## 4. Leakage summary (why every (a) number except two is soft)

- **Kev-4B:** BANKING77 is in training. CLINC, SGD and When2Call are held out (verified in manifests). This makes Kev's CLINC and When2Call numbers *harder* tests than its competitors face.
- **Decision 1.0 Lux/Nox and SearchJev:** trained on the BANKING77 and CLINC150 train splits (disclosed).
- **pplx-decider:** official training splits, decontaminated against test sets (disclosed in general terms; datasets not named).
- **Everyone else** (d3, KnowLine, Jeffan, OneJev, elephant-1, StartLux, d1): training sets undisclosed.
- **tasksource**, credited by Perplexity, includes BANKING77, CLINC and SGD train splits [U: not checked here].
- **When2Call has a public train split.** Decision-1.0-Route-0.6B lists it. Whether the candidates trained on it is unknown.
- **Leak-proof numbers:**
  - DI private same-skill and new-domain tests.
  - Kev's breadth-v1, used only on models that never saw its sources.
- **On the leak-proof private tests**, Kev-4B (36.2 same-skill / 25.4 new-domain) trails pplx-flash (56.2 / 40.0) and elephant-1 (62.4 / 44.4) by 15–26 points. That gap is general decision ability, not intent-specific, but it is the cleanest evidence in this survey that the 4B peers are stronger models overall.

---

## 5. Decision support

### (1) Is any model credibly better than Kev-4B?
- **(a) Routing and classification, held-out: yes.**
  - On DI CLINC150+OOS, the clean held-out comparison for Kev, five Apache 4B models beat Kev-4B by 0.18–0.21 macro-F1.
  - Kev's own author measures Kev-4B 0.16 behind Jev on CLINC150 test.
  - Leakage risk on the competitors' side cannot be excluded. But the DI private same-skill tests, which are leak-proof, show the same ordering.
- **(b) Goal inference and intent adherence: one direct held-out eval favours pplx-flash, by a small margin.** LLMBar instruction-following judgment: 75.2/85.0 vs Kev-4B 71.8/81.1 (§6). No eval exists for goal inference or unstated goals for any model. The proxy evidence is consistent and large.
  - When2Call: Kev-4B 0.667 vs 0.85–0.93 for pplx-flash, d3-mini, KnowLine, Jeffan and elephant-1.
  - typed-decisions agent-trace: Kev-4B 66.0 vs 74–79.
  - Kev-4B's genuine (b)-adjacent strengths:
    - Abstention and missing-evidence calibration (0.00% overconfident).
    - Low ECE (0.032 on DI).
    - The best adherence fine-tuning evidence (SecJev, CFPB +10 pt).

### (2) Swap candidates

**A. perplexity-ai/pplx-decider-flash-v1.2: the strongest 4B on leak-proof DI new-domain tests.**
- **Why better:**
  - When2Call +0.23, CLINC+OOS +0.18, RAGTruth +0.15, API-Bank +0.33.
  - New-domain +14.6. Same-skill +20.0.
  - Distilled from the 27B pplx deciders, so it inherits their judging skill.
  - Trained to 32k context vs Kev's 8k validated.
- **Cost:** about 9 GiB bf16, so any 16–24 GB GPU (L4/A10G/L40S) works. 74.8 ms median on DI.
- **Training on 1×H200 or a 96 GB RTX PRO 6000:** a full fine-tune of a 4.5B model with AdamW (about 16 bytes per parameter, roughly 72 GB plus activations) fits on an H200. It is tight on 96 GB and needs 8-bit Adam or LoRA. But **there is no training code.** We would have to write a trainer around the custom non-causal attention and the readout head. That is about 4–8 h of the 22 h hackathon, with risk [estimate].
- **What we lose:**
  - `kev.train --init_from` and the calibrate pipeline.
  - The TypeSafe `/v1/systemone` HTTP shape: the request schema is similar (criteria, A/B codes), so an adapter shim is needed.
  - Cheap shared-state multi-question: the card recommends one question per request.
  - Kev's measured abstention behaviour (unmeasured for pplx).

**B. vllm-sr/d3-mini**
- **Why better:**
  - Top 4B on CLINC+OOS (0.963) and BANKING77 (0.927).
  - When2Call 0.845. typed-decisions 0.743 [M-ind].
  - `/v1/systemone` through vLLM-SR.
- **Cost:** about 15–22 GiB serving.
- **What we lose:**
  - Verified only on AMD; CUDA is unproven [C].
  - No training code; training data undisclosed.
  - Lower new-domain score than pplx-flash (36.5 vs 40.0).

**C. PelaAI/KnowLine-4B-Gen5.5**
- **Why better:**
  - Highest DI full and same-skill scores among Apache 4B models (56.0 / 61.2).
  - When2Call 0.905. `/v1/systemone` drop-in, up to 64 questions per state.
- **What we lose:**
  - No training code.
  - Each question runs its own forward pass (no shared prefix).
  - Its read-twice layout is limited to requests of at most 3k tokens.

**D. baselabs/elephant-1 (9B, MIT): the best measured (b) proxies under 27B.**
- **Why better:**
  - When2Call 0.915; new-domain 44.4; RAGTruth 0.853.
  - **Shared-prefix KV caching** by design, the same as Kev.
  - Its training includes 1.0M judging examples.
- **Cost:** about 19 GB bf16. 113.7 ms median (2× Kev). Inference on L40S/A100-40 [estimate].
- **Training:** a full fine-tune of a 9B model does not fit on 96 GB with standard AdamW. It needs LoRA via PEFT on standard Qwen3.5 weights, which is plausible but has no code.
- **What we lose:** the training pipeline, 64k acceptance (16k hard cap), and about 2× latency.

**E. Stay on Kev-4B and fine-tune for (b)** (the SecJev pattern).
- **Why:**
  - The only documented continue-training path: about $1 per run on an H100, about 20–50 min on one H200 (Kev cards).
  - Best calibration and abstention.
  - Validated prefix caching and multi-question; TypeSafe API.
- **Cost:** known; our pipeline already exists.
- **Risk:** we start 15–25 points behind the 4B peers on every held-out proxy. In-domain fine-tuning closes in-domain gaps (CFPB 0.804 → 0.904) but not general skill. The Kev card's own words: gains are "largest in-distribution".

**Inference budget, all options.** About $30 of Modal credit is roughly 7–15 GPU-hours at L40S–H100 rates [U: Modal prices not re-checked]. Every 4B and 9B candidate fits. A 27B model (mammoth-1, Nimble-v4-max) needs an 80 GB-class GPU, which roughly halves the hours.

### (3) Plain verdict
- **Sense (a):** the evidence justifies saying Kev-4B is not the best open 4B intent classifier. pplx-decider-flash-v1.2, d3-mini and KnowLine-4B are clearly better on held-out data.
- **Sense (b):** the evidence does **not** demonstrate superiority, because no direct eval exists for any model. It does show Kev-4B behind on every available proxy, with Kev better only on abstention and calibration.
- **A swap is not justified by published evidence alone. A bake-off is.**
  - Run Kev-4B, pplx-decider-flash-v1.2 and d3-mini (plus elephant-1 if time allows) on our own (b) set: adherence, clarification need, request satisfaction. Score with the same prompts and report accuracy, ECE and AUROC.
  - Include When2Call MCQ as a public anchor.
  - Expected cost: under 2 GPU-hours on one L40S/H100, about $4–8 [estimate].
- **Decision rule:**
  - If a candidate beats Kev-4B by at least 5 pt on our (b) set *and* survives a trainer port within about 4 h, swap.
  - Otherwise keep Kev-4B and spend the hackathon fine-tuning it with `--init_from` on (b) data, since its pipeline is the only proven one.

---

## 6. Post-cutoff discovery (agent report; items I re-verified are marked ✔)

**Direct (b) evidence**
- **✔ arXiv 2611.00505**, "To Jev or Not to Jev: When Can System-1 Decision Models Replace LLM Judges?" (S. Subramanian, 2026-10-31).
  - 14 System-1 judges are compared; Kev-4B is held out from every benchmark; single run.
  - Rows from Table 1 (JudgeBench Choice/Checklist/+ref · LLMBar Choice/Checklist · RewardBench 2 Choice/Checklist · ECE · appended-note ASR):

| Model | JudgeBench | LLMBar | RewardBench 2 | ECE | ASR |
|---|---|---|---|---|---|
| Kev-4B | 66.6 / 68.3 / 88.0 | 71.8 / 81.1 | 57.3 / 71.0 | .058 | 32.2% |
| pplx-flash-1.2 | 70.0 / 72.3 / 91.4 | 75.2 / 85.0 | 64.3 / 77.3 | .041 | 16.7% |
| Clef-flash | 68.0 / 67.7 / 82.0 | 70.4 / 78.5 | 60.3 / 67.0 | .093 | 40.4% |
| DReX v1.5 (9B) | 69.1 / 70.3 / 90.3 | 76.4 / 82.3 | 63.3 / 74.3 | .112 | 17.7% |
| Jev 1.14 | 82.3 / 79.1 / 91.4 | 87.4 / 85.2 | 81.7 / 83.0 | .019 | 23.3% |
| DReX-Max (27B) | 83.7 / 80.6 / 91.0 | 88.3 / 87.8 | 87.0 / 84.7 | .024 | 0.0% |
| d1-ultra (hosted) | 84.6 / 84.3 / 93.4 | 87.6 / 87.6 | 86.7 / 81.0 | .030 | 0.4% |

  - **Checklist (pointwise) framing adds +9.3 pp LLMBar for Kev-4B.** This is a usable lever whichever model we keep: ask adherence as per-criterion noul questions, not one pairwise choice.
- **arXiv 2610.21412, JevAgentHarness / AgentDecisionBench.**
  - AgentDecision-4B (Qwen3-4B LoRA, trained on Jev labels) scores 67.4% at "must-ask" (clarification) states vs Jev 58.3%, and 91.5 task success vs Jev 82.0.
  - **Weights not released.** Kev not tested.
- **arXiv 2610.18610, Jev-ToM** (goals, desires, intentions). This is the closest goal-inference benchmark. Jev leads at 73.2%. **Kev not included.**
- **Agent-failure modes relevant to (b):**
  - 2610.25947 "Claim Laundering": decision models trust logged success claims and stop or advance in 53–100% of claimed-but-failed steps.
  - 2610.24649: Jev is poorly calibrated on Terminal-Bench completion.
  - Neither paper tests Kev.

**More 4B DI entries** [M-ind board; leakage notes from DI entrant metadata, relayed by the agent]

| Model | B77 / CLINC / When2Call | Full | Licence | Leakage |
|---|---|---|---|---|
| apertixai/cerno-4b-v1.2 | .899 / .940 / .901 | 53.88 | Apache | **trained on BANKING77, CLINC and When2Call train/dev splits** |
| WangSenQWQ/Senova-4B-v4 | – | – | – | **test-derived data per its author; exclude** |
| victorbennett/Verdin-4B-v1.1 | – | – | – | trains on index-source splits |
| h2oai/h2o-lightning-e4b | – | – | non-commercial | – |
| chiranko/PKU-KCL-Meteor-2B | – | 34.75 | – | public 60.95, a big public→Full drop that signals overfit |
| alibiserikbay/JevK5 | MASSIVE-60 .738, CLINC151 .700 (own) | – | – | trains on When2Call `train_pref` |

- Kev-4B's public→Full drop is small (37.95→34.93), consistent with no benchmark training.
- **The ordering survives the leakage filter.** Drop every model flagged as trained on intent splits (KnowLine, Cerno, Senova, Verdin, JevK5). pplx-decider-flash-v1.2 and d3-mini remain clearly ahead of Kev-4B on When2Call, CLINC and Full.

**Other leads (not re-verified)**
- **OneJev1.6-4B via Flide** (arXiv 2610.42148): exact state forking, claimed ≤9.5× faster than vLLM/SGLang. This is the closest analogue to Kev's shared-state caching among the swap candidates.
- **autotrust/JEV-9B:** choice capped at 2–16 options, which is bad for intent routing. vLLM prefix caching measured.
- **nace-ai/drex-max-v1** (27B, Open RAIL-M, commercial terms [U]): LLMBar 88.3/87.8, close to the best open judge. 27B.
- **Kev-4B fine-tunes:**
  - ai-ecoverse/kev-4b-vision-intent: Mind2Web ACT top-1 89.8 vs 82.0.
  - Flolep2607/kev-4b-actions and kev-4b-guard: held-out next-action plus done check 82.8 vs Kev 67.7.
  - These are more evidence that `--init_from` fine-tuning moves (b)-adjacent agent skills by 8–15 pt.
- **Artificial Analysis When2Call** excludes the 229 ask-for-info items, so prefer the DI When2Call (3,652 items including clarification) as the clarification anchor (https://artificialanalysis.ai/evaluations/when2call).

**Searches that returned nothing relevant** (HF API and arXiv): clarif, ambigu, adherence, instruction-follow, agent-judge, satisf, trajectory-judge, goal-infer, intent-align, "intent adherence", "goal drift". **No open decision model is published for intent adherence or goal drift specifically.**

## 7. Revised verdict after §6
- LLMBar is the one held-out, direct instruction-following-judgment benchmark. pplx-decider-flash-v1.2 beats Kev-4B on it by 3–4 pt, within noise for a single run at n=419. It also beats Kev-4B on JudgeBench (+3.4), RewardBench 2 (+7.0), calibration and injection robustness.
- Together with When2Call (+23) and the DI private tests (+15 to +20), pplx-decider-flash-v1.2 is **the one swap candidate with consistent held-out evidence on (a) and (b)** at Kev-4B's size and cost (about 9 GiB, about 75 ms).
- What it lacks:
  - A training pipeline.
  - The `/v1/systemone` HTTP shape.
  - A recommended shared-state multi-question mode.
- **Recommendation is unchanged: bake-off first** (§5 (3)).
  - Kev-4B (with checklist framing) vs pplx-decider-flash-v1.2 (with checklist framing) vs d3-mini, on our own (b) set plus DI-style When2Call.
  - Swap only if pplx-flash wins by at least 5 pt on our set *and* we accept giving up `kev.train --init_from`. Otherwise keep Kev-4B and fine-tune it on (b) data. The SecJev, Flolep and ai-ecoverse fine-tunes show +8–15 pt on adherence-adjacent tasks this way.
