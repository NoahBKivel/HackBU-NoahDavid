# Kev-4B 8K -> 16K/32K: training cost research (2026-11-07)

Legend: [M]=measured/reported by source; [E]=my estimate; [U]=UNVERIFIED. All post-cutoff material (Qwen3.5/3.8, Kev, FlashQLA, 2026 papers) fetched, not recalled. Budget-limited (~20 min): several fetches returned abstracts only.

## 0. Bottom line
- No public measured tokens/s or peak-memory table for Qwen3.5-4B LoRA at 16K-64K exists (searches found none). Numbers below derive from Kev's own measured runs + FLOP arithmetic [E].
- Kev's own data: 4B LoRA at 7,552 max tokens peaked 47.7 GB (batch 2, H200) [M]. 32K batch 1 with checkpointing should fit comfortably on 96/141 GB [E]; 64K probably fits [U].
- Kev-27B reached validated 65K with ONLY 3,200 long states (8k-32k) + 7,617 code-assembled long docs inside a 145,840-record full-FT mix; never trained on 64K [M]. That is the template for "fold into one run".
- Kev-4B at 16K is already within tolerance on point estimate (-1.1pp, CI lower -3.4 breaches the -3pp rule); real drop is at 32K (-5.8pp) [M]. Goal 16K is a small gap; 32K is the real gap.

## 1. Memory / throughput
### Measured (Kev, github.com/jaredpalmer/kev, docs/model-cards/kev-4b.md)
- Stage 1: 4B LoRA r16/a32 (attn+MLP+DeltaNet proj, 33.8M params), bf16 autocast over fp32 weights, grad ckpt, eff batch 8 (4x2): 12,576 recs x2 epochs, 1 H100, ~56 min, peak 24.6 GB [M].
- Stage 3: 5,219 CFPB docs, max 7,552 tok, batch 2x4, 1 H200, 43 min (7,219 incl. 2,000 replay -> ~2.8 rec/s) [M]. Stage 4: 11,320+4,000 replay recs, 1,915 steps, 1.4 h, peak 47.7 GB [M]. Avg tokens/record not stated [U] -> if ~3K avg, implies ~8K tok/s [E, cross-check only].
- Inference: 61k-token state on Kev-4B = 17.2 s, 17.2 GiB above weights on H100 (memory-efficient fp32 kernel enabled for 32k-64k rows to avoid OOM) [M] (docs/releases/kev-1.0.md). Implies eval-time kernel OOMs at long length were a real issue; fixed via mem-efficient path.
- Kev-27B (full FT, FSDP2, 8xH200): 1,140 steps x128 recs, 16.2 h wall = 129 GPU-h; serving peak 78.7 GB @32k, 87.1 GB @64k on H200 [M] (kev-27b.md). lr 2e-6 backbone / 1e-4 head.
- Unsloth guide: Qwen3.5-4B bf16 LoRA ~10 GB VRAM (short ctx; no tok/s or ctx) [M] https://www.unsloth.ai/docs/models/qwen3.5/fine-tune ; recommends gradient_checkpointing="unsloth".
- Third-party training tok/s: NVIDIA Megatron Bridge page lists Qwen "3.8-27B" H100 pretrain ~339 tok/s/GPU, GB200 long-ctx SFT ~2,007 tok/s/GPU, seq len unstated, not LoRA; credibility low [U] https://docs.nvidia.com/nemo/megatron-bridge/nightly/models/qwen/qwen3.8-27b.html

### Kernels (FLA / FlashQLA)
- FLA (github.com/fla-org/flash-linear-attention): Gated DeltaNet in fla/ops/gated_delta_rule, fwd+bwd timed (chunk_gdn, GB200, CUDA12.9, torch2.9) [M]; varlen via cu_seqlens [M]; context-parallel added Mar 2026, FlashQLA backend Jul 2026 [M]. No memory figures; no known-issues section; 54 open issues unread [U]. `fuse_linear_cross_entropy` may reduce precision (disable if diverging) [M].
- FlashQLA (github.com/QwenLM/FlashQLA): claims 2-3x fwd, 2x bwd vs FLA Triton on Hopper+Blackwell; SM90/100/103/120/121, CUDA 12.8+, torch 2.8+; SM120 (RTX PRO 6000 Blackwell) backward only from v0.1.3; auto intra-card context parallelism for long sequences [M, claims not independently benchmarked]. RTX PRO 6000 = SM120: check version >=0.1.3 [E].
- Chunkwise algorithm, chunk_size default 64 in reference impls [M, tenstorrent docs]. Backward supports long lengths in principle (linear time); memory blowup risk = fp32 chunk states/intermediates saved for bwd; not documented [U]. Unverified hazard: if HF fallback torch path (no FLA/causal-conv1d installed) is used, training is slow and memory-heavy [E].
- Arch: Qwen3.5-4B layout 8x(3 GDN->FFN, 1 gated-attn->FFN) => only 8 full-attention layers; quadratic cost small, KV cache tiny, GDN state constant [M] https://huggingface.co/litert-community/Qwen3.5-4B (hidden size ~2560, vocab ~248K: [U], from recall).

### Logits saving [E]
- Full LM head at 32K tokens x 248K vocab: fp32 = 32 GB, bf16 = 16 GB, plus grad/softmax copy ~2x => 30-65 GB avoided. Pointer head scores only option-closing tokens vs final token => negligible. At 64K, 64-130 GB avoided, i.e. the head is what makes long ctx feasible. Confirm Kev trainer never materializes lm_head logits over all positions [U].

### Memory/throughput estimate for 4B LoRA, ckpt on, batch 1 [E]
- Activations stored: ~32 layers x T x 2560 x 2 B ≈ 5 GB @32K, 10 GB @64K; per-layer recompute transient few GB; FA2/SDPA on 8 attn layers is linear memory. Weights 8.4 GB bf16 (16.8 GB if fp32 master as Kev does). Predict @8K ~20 GB, 16K ~25-30 GB, 32K ~35-50 GB, 64K ~60-90 GB (wide: GDN fp32 intermediates). Both GPUs fit through 32K; 64K on 96 GB risky [U].
- Throughput: LoRA+ckpt ≈ 6N FLOP/token ≈ 25 GFLOP/tok (N≈4.2B); H200 bf16 dense ~989 TFLOPs; at 20-35% MFU => 8-14K tok/s. RTX PRO 6000 (~half H200 bf16 dense compute, 1.8 TB/s mem) => ~0.5-0.6x of H200 [E; spec figures UNVERIFIED]. Use 8K tok/s @16K, 7K tok/s @32K central for H200.

## 2. Kev's long-context recipe
- Kev-27B (v2; docs/model-cards/kev-27b.md [M]): 145,840 records / 337,130 questions, 1 epoch, full FT (--full_ft 1) on 8xH200 FSDP2, 1,140 steps x128, 16.2 h/129 GPU-h; then weight-average 0.85 (new) / 0.15 (earlier adapter Kev-27B) [M README]. Long data: 3,200 "long states" (Kev-corpus states, incl. buried facts, embedded in 8k-32k-token documents, labels carried over unchanged; only manifest public: evals/sft-v2-r22/manifest.json) + 7,617 code-assembled long docs (labels computed by code) [M]. Max train state 32,768 [M]; validated 65,536 under its rule [M]. Long docs ≈ 7.4% of records [E].
- Kev-27B CUAD (longdoc-v1 test) v2 acc/ECE: <8k 0.874/.059; 8-16k 0.880/.052; 16-32k 0.873/.061; 32-64k 0.867/.060; all 0.874 (v1 0.890; v2 -1.6pp [-3.0,-0.3]) [M]. Dev vs 8k: +0.2 (16k), -0.2 (32k), -1.1 (64k) pp [M]. v2 trades ~1.6pp accuracy/worse calibration for extrapolation.
- Kev-4B (kev-4b.md [M]): validated 8,192; trained max 7,552; serve limit 65,536. Four LoRA stages on Qwen3.5-4B-Base (decision-v7 12,576 -> dates/missing evidence 1,425 -> documents-v1 5,219 CFPB -> hard-v1+devtools-v1 11,320), then T=2.41 calibration.
- Kev-4B CUAD by length (longdoc-v1 dev, T=2.41; ~452 q/bucket): 
| len | n | acc | ECE | Δ vs 8k pp [95% CI] |
|---|---|---|---|---|
| 4k | 443 | .847 | .047 | n/a (different contracts) |
| 8k | 453 | .837 | .048 | ref |
| 16k | 452 | .823 | .057 | -1.1 [-3.4,+1.2] |
| 32k | 454 | .788 | .022 | -5.8 [-9.0,-2.8] |
| 64k | 452 | .781 | .035 | -5.2 [-8.2,-2.0] |
- Takeaway: 4B gets -5pp at 32k/64k without any long training; bounded loss, not collapse. Note calibration ECE at 32k is good. Gap to recover is ~5pp at 32K, ~1pp at 16K (CI-limited).

## 3. Datasets (existing labels)
| Set | Access / license | Size | Avg len | Label | Mechanical conversion | Notice |
|---|---|---|---|---|---|---|
| CUAD | HF theatticusproject/cuad-qa; CC BY 4.0 [M] | 510 contracts, 41 categories, >13K labels; 22,450 train/4,182 test QA rows [M] | not on card; contracts long (Kev buckets 4k-64k) [U] | extractive spans | per (contract, category): span present => "Does contract contain X?" yes/no; empty => no. Kev already uses CUAD in eval (longdoc-v1) => TRAIN/EVAL CONTAMINATION RISK: train only on contracts disjoint from Kev's eval split [E] | no anti-training text; "not representative" disclaimer; underlying EDGAR contracts not licensed by creators [M] |
| ContractNLI | stanfordnlp.github.io/contract-nli; CC BY 4.0 + Hitachi terms [M] | 607 NDAs, 17 fixed hypotheses [M] | not on page (~2-3K words typical) [U] | Entailment/Contradiction/NotMentioned + evidence spans | 3-way multiple choice per (doc, hypothesis) = ~10K items; evidence spans allow position augmentation | none beyond Hitachi ToU |
| QuALITY | github.com/nyu-mll/quality, v1.0.1 zip; per-article license field, no repo license stated [M] | counts not on page (~6.7K Q / 381 articles, UNVERIFIED recall) | ~5,000 tokens [M] | 4-way MC, `difficult` flag | native MC => pointer head directly; need concatenate-articles/distractors to reach 16-32K; test labels withheld; some articles CC-licensed per-article | check per-article licenses [U] |
| MAUD | github.com/TheAtticusProject/maud; paper arXiv 2301.00876; CC BY 4.0 [M] | >39K examples, >47K annotations [M]; agreements/questions count not found [U] | merger agreements very long (often >50K tok) [U]; extract relevant sections | MC deal-point questions | MC native; whole doc exceeds 32K => section-trimmed contexts | no repo license stated; paper license CC BY 4.0 |

2026 / newer (post-cutoff), none confirmed as yes/no or MC training sets:
- LongBlocks (2026, multilingual synthetic long-ctx QA, hyper.ai/en/datasets/51465): format unknown [U].
- sxiong/DHSA_Long-Data-Collections (HF): length-bucketed repack of Together long-data; open-ended QA/summarization [M-search], not decisions.
- LongBench Pro (arXiv 2601.02872): 1,500 samples 8k-256k, EVAL ONLY. LongBench v2: 503 MC, eval only [M-search]. Don't train on them (contamination of any later eval).
- Realistic route (Kev's own): code-assembled documents with computed labels + embedding short Kev-corpus states in filler (see Kev-27B recipe). No new annotation.

## 4. Methods (no RoPE changes)
Post-cutoff / 2026:
- ProxyCoT (ACL 2026 long, 2026.acl-long.1917; arXiv 2605.20201; code github.com/oaimli/ProxyCoT): stage 1 get CoT traces on SHORT proxy context (RLVR or teacher); stage 2 SFT student on those traces paired with FULL long input. Claims beating baselines at lower compute, shorter traces, OOD gen; SciTrek Qwen3-4B numbers (67.2 vs 30.8/38.8 EM) come from a third-party summary and are unverified [U]. Needs: CoT-producing teacher/RL + reasoning format. Kev is a pointer-head, no-CoT classifier => only the "short-to-long supervision transfer" idea applies: labels from the short state (Kev corpus) paired with long embedding = what Kev-27B did. Hybrid applicability: architecture-agnostic [E]. Models/lengths tested not seen [U].
- RoPE-Perturbed Self-Distillation (ICML 2026; arXiv 2604.14339, Microsoft): second view with shifted RoPE indices, consistency/self-distill vs fixed standard view; up to +12.04% RULER-64K (Llama-3-8B), +2.71% RULER-256K (Qwen-3-4B); short ctx maintained [M-abstract]. Applicability to Qwen3.5 hybrid: only 8/32 layers use RoPE attention; GDN layers are position-implicit, so gain likely smaller and would require modifying position_ids in the full-attn layers [E]. 2x forward cost per example (teacher view) [E]. No code link found [U]. Low priority for 22h.
- Attention Amnesia in Hybrid LLMs (arXiv 2606.11052, Jun 2026): CoT SFT degrades long-range recall in distilled hybrids because few softmax-attn layers drift; mitigation exists (details unread) [U]. Relevant risk: LoRA on attention layers of Qwen3.5 may drift retrieval layers; mitigation = replay of long-context data / lower LR on attention LoRA [E]. READ before launching.
- HALO/HypeNet (arXiv 2601.22156), HydraHead (2606.20097): hybrid conversion papers, 3-stage with long-ctx finetune; not directly usable.
- "First Drop of Ink" (2605.10828): hard distractors nonlinearly pull attention from gold doc => supports mixing easy and hard distractors [M-abstract].
Known baseline (no 2026 sourcing in this pass, [E] from standard practice + Kev evidence):
- Multi-length mixing (keep short replay, e.g. Kev replays 2,000-4,000 recs/stage): cheap; Kev-27B did this. Applies directly.
- Evidence-position augmentation (random placement of relevant span/state within filler): cheap, uses existing labels (CUAD/ContractNLI spans, Kev-corpus embedded states); Kev "buried facts" already do this. Applies.
- Distractor insertion (other contracts/docs as filler, hard negatives): cheap; label-preserving only if distractors cannot change answer (use different-category/different-doc). Applies.
- Weight-average with prior adapter (0.85/0.15) was Kev's guard against regression [M].

## 5. Cost table: GPU-hours for ONE epoch LoRA, H200, Qwen3.5-4B [E]
Assumptions: batch 1/ckpt on; pointer head (no full logits); FLA/FlashQLA kernels active (not torch fallback); throughput 8K tok/s @16K, 7K tok/s @32K central (low band 0.6x, high band 1.5x); exactly L tokens/example; excludes eval, load (~5-10 min), restarts. RTX PRO 6000 ≈ 1.7-2x the hours [E][U].
| N examples | 16K tokens: tokens | central h | range h | 32K tokens: tokens | central h | range h |
|---|---|---|---|---|---|---|
| 500 | 8.2M | 0.28 | 0.19-0.47 | 16.4M | 0.65 | 0.43-1.08 |
| 1,000 | 16.4M | 0.57 | 0.38-0.95 | 32.8M | 1.30 | 0.87-2.17 |
| 2,000 | 32.8M | 1.14 | 0.76-1.9 | 65.5M | 2.60 | 1.7-4.3 |
| 5,000 | 82M | 2.84 | 1.9-4.7 | 164M | 6.5 | 4.3-10.8 |
- Reference points: Kev-27B used 10,817 long recs of 8-32K inside full FT, 129 GPU-h [M]; 4B stage 4 (15.3K recs <=7.5K tok) took 1.4 h [M]. A combined run = short replay (~5-10K recs, ~1.5 h) + 1-2K long (16K+32K mix) ≈ 2-4 h central => 22h hackathon holds ~2-3 iterations plus eval. Eval of 5 buckets x ~450 q at 64k costs ~17s/state inference => 64k bucket alone ~2 h at batch 1 unless cached [E from 17.2 s/61k state, M].

## 6. Key risks/to-verify before committing
1. Confirm FLA + causal-conv1d installed (else HF torch fallback). 2. Dry-run 32K batch 1, record peak memory and tok/s on both GPUs (30 min). 3. Read 2606.11052 (attention drift) and Kev PLAN.md/skills/kev-finetune for the actual long-state pipeline (not fetched). 4. Keep CUAD eval contracts out of training. 5. Weight-average/replay to protect 8K accuracy (Kev-27B v2 lost 1.6pp on all-length CUAD).
