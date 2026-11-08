# Decision-model fine-tuning frontier (research, 2026-11-07)
Budget ~20 min. Sources fetched via WebFetch unless marked UNVERIFIED (search-snippet only). Arxiv IDs 26xx post-date training cutoff; all fetched and real.

## 0. Bottom line
- Best direct evidence for our setup is "Releasing the Inner Jev" (Geuter, Cheng, Alvarez-Melis, 2610.17205): plain CE LoRA + head, soft targets, ~400 steps, temperature scaling. Every fancier loss tested was within seed noise.
- No paper found that trains a small decision model/monitor on counterfactual minimal pairs for authorization-dependent labels. Family (b) is evidence-light for the pairing itself; closest support: StepGen same-context/different-action (StepGuard) and CPA (NeurIPS 2026).
- "RH-Detect Oct 2026" NOT FOUND (searched exact name; nearest: Cheap Reward Hacking Detection 2606.08893). Treat as nonexistent/mis-named unless user supplies link.
- TRACE ICML 2026 (Patronus, 2601.20103) is a BENCHMARK, zero training. Separate "TRACE" 2510.01367 is truncated-CoT-AUC (training-free). Neither is a training-recipe source.

## 1. POST-CUTOFF / NEW

### 1.1 Releasing the Inner Jev (arXiv 2610.17205, 12 Oct 2026) https://arxiv.org/html/2610.17205v1
Recipe (Gemma4-31B; Qwen3.5-4B variants noted):
- LoRA r32 a64 drop0 on q/k/v/o+gate/up/down; head init from LM-head answer-letter rows; no RL/aux loss.
- AdamW wd0; LR 2e-5 LoRA, 1e-4 head; warmup 250, const to 300, decay to 0 at 400 steps (WSD); batch 65,536 tokens (~190 q); 400 steps = 76k q = 18% of 417,825-row pool; final step used, no early stop; 3 seeds. Qwen3.5-4B: 23 min on 4xH200.
- Loss: CE vs soft targets where available else hard. Options reshuffled each epoch.
- Data: 300k public hard-label (79 tasks) + 117,783 soft rows (annotator distributions Civil Comments/MHS/STS-B/ChaosNLI + 30.6k synthetic + 19.5k custom, teacher = avg of 2 thinking samples each from Qwen3.5-122B-A10B and Qwen3.6-27B).
- Ablations (31B, ref 84.4 OpenDecisions): head-only frozen backbone 78.9; LoRA w/ head frozen at init 84.9 (head training unnecessary); no recipe on base 70.3; rank 16/64/128 = 84.7/84.5/84.9 (rank irrelevant); public data only (no teacher labels) 82.5 (teacher labels +1.9); hard instead of soft labels 84.1 (soft +0.3, small).
- Training length: 800 steps 84.7, 1200 83.9, 1500 83.6, 2300 82.9, 3900 82.6. Decline mainly calibration -> mild overfit. Short runs are right.
- Qwen3.5-4B (63.6 zero-shot, 66.6 mean best) single changes at 400 steps: LoRA LR 1e-4 63.4 (vs 63.0 base recipe, ~no gain); distill from trained 31B 65.1; half of questions in eval format 63.8; all three combined 66.6 (seeds 68.0/66.4/65.5, spread ~2.5 pts); averaging targets with zero-shot preds 64.0 (rejected). 4B gain over zero-shot is small (+3). Seed noise ~1-2.5 pts: single-run comparisons are unreliable.
- Loss table (Qwen3.5-4B, frozen backbone+head, Table 16, macro acc 7 held-out sets; CE 78.5 x3 seeds, ECE .092): Brier 79.6 (1 seed, ECE .093); focal g2 76.3 (ECE .193, bad); CE+soft-binned-ECE ~0 change (λ up to 3 hurts ECE); CE+MMCE +0.1/+0.3; CE->mixed target a=.8 +0.6 (ECE .088); expected-utility r=3 +0.9 (3 seeds, raw ECE .076 but .094 after T). Finding: after temperature scaling no loss beats CE ECE by >0.01. Expected utility without CE: 81.2 vs 84.8 with CE on 31B. Order-invariant encoding: no clear benefit on 4B.
- Calibration: one T per question type fit by NLL on 3,884 held-out q; clamped >=1 (trained Qwen T<1 hurt). Zero-shot Gemma31B T=6.0 choice/7.2 yes-no, capability 72.9->79.6. After fine-tune T near 1, gains small. Jeff-1.0-Large final T: choice 1.52, yes/no 1.31, score 1.31 (https://huggingface.co/jgeuter/Jeff-1.0-Large).
- Selection on OpenDecisions (2,352 q) dev set; JevBench never touched.

### 1.2 LLM2Jev (2610.02076) https://arxiv.org/html/2610.02076v1
- Training-free 4B = 81.4 JevBench, ECE .057 (already calibrated). LoRA 4B 84.0 (only setting beating baseline); full FT 80.5 and Banking77 drop 69.0->75.9/74.2 mixed.
- LR: LoRA 1e-4, full 2e-6 (4B) / 5e-6 (0.6B); AdamW wd .01, clip 1, bs32, 10% warmup, linear decay to 10%, 1 epoch; LoRA r16 a32. Steps 100-2,984.
- Loss: tree-factorized listwise NLL + λ(KL anchors: mass, illegal tokens, full-dist). No head-to-head vs plain CE. λ=1 best at 4B; no anchors -> 69/231 queries ramble past answer; λ>=0.01 fixes. LoRA beat full FT at 4B at every λ.
- Narrow-intent-only training HURTS broad tasks (81.4->76.2 after 1 epoch of 95k intent examples), induces "yes" bias. Adding reasoning data (9k) removes yes-bias, best calibration. Scaling short-context data to 21-30k lowers long-input accuracy; adding long data restores. Fine-tuning at 4B does NOT clearly improve calibration (ECE .057->.067-.079). Relevance: replay/anchor/mixed-in general data is supported evidence for family (b)'s replay/KL anchoring; yes-bias on narrow data is a risk for a binary monitor.

### 1.3 Liquid open d1 (d1-3B) https://www.liquid.ai/blog/d1-open
- Claims "long inputs, shuffling answer options, fixing shortcuts in data made bigger difference than more advanced techniques." Several seed/mixture fine-tunes then weight-merged; base = weight-average of two LFM2.5 checkpoints; final step: average with previous checkpoint "for regularization". No numbers/ablations disclosed. d1-ultra: "specifically trained for reliable probabilities", method undisclosed (https://www.liquid.ai/blog/d1-ultra).

### 1.4 Kev (target model) https://hongjun7.github.io/logs/2026/10/10/jev-kev-decision-models.html
- Qwen3.5 0.8B/4B/9B LoRA + pointer head (bilinear z_i = v_i^T u / sqrt(d), temperature softmax); 27B full-tune. CE loss. Maintainer-reported transfer-v4 (656 q): Kev-4B new-source acc .817 dev/.838 test, Brier .243/.224 (page notes conflicting .269/.242). Hyperparameters in repo README "by-hand" (github.com/jaredpalmer/kev @fc4a17e) NOT READ. UNVERIFIED re: SecJev (no page found).

### 1.5 Baseten mammoth-1/elephant-1 (Oct 21 2026) https://aicoder.com/news/news-20261022-baseten-base-labs-mammoth-1-elephant-1-open-decision-models
- Full FT of Qwen3.5-27B/9B on 6.21M decision examples (public+synthetic; includes safety/abstention, judging); block-bidirectional attention over options. No loss/ablation/calibration detail in secondary source; Baseten blog not retrievable. Scale far beyond hackathon.

### 1.6 Laya / RLCD / Just Ask Jev
- Laya: ModernBERT-large, "RLCD with Brier score training", fine-tunable (secondary: https://arxiv.org/pdf/2609.28940 metadata only; PDF unreadable -> UNVERIFIED).
- Just Ask Jev (2609.29429, https://www.alphaxiv.org/abs/2609.29429): Jev zero-shot generic NOUL question, median AUROC .886 on 31 alignment-failure benchmarks (incl. reward hacking); targeted wording +.006 only; per-benchmark median ECE .168 vs null .074 (pooled calibrated, per-source NOT); threshold fit on 10 items +.087 F1 on unvalidated labels but -.025 on validated. => per-source calibration drift is the norm; fix with per-source/held-out threshold or T, don't trust pooled ECE.
- Clef, Nimble, OpenDecider: nothing found (UNVERIFIED/no hits). Jeff (firelex, Qwen3.5 0.8B/2B): 2h/3.5h training, final-epoch ckpt chosen over lowest-dev-loss in v1.1, calibration err .049->.021 (https://www.developersdigest.tech/blog/jeff-jev-compatible-decision-models-2026); domain fine-tune 11k ex, 30 min: 31.7->95.8% held-out (in-domain).

### 1.7 Monitors for reward hacking / goal drift
- Li et al. 2604.23488 (https://arxiv.org/html/2604.23488): 800 trajectories/source; ModernBERT-large, MLP/LogReg probes, zero-shot GPT-4.1/o4-mini/GPT-5.4. Held-out hack-type transfer (train self-written-test hack, test exit-based): training-time data -> ModernBERT 100, MLP 74.7, LogReg 61.9; prompt-elicited data -> 31.2/22.2/12.2; zero-shot LLMs 4.8-15.6. Lesson: label SOURCE (on-policy natural hacks vs prompt-elicited synthetic) dominates generalization; synthetic-trained monitors fail on real hacks (e.g. LogReg 8.8%). Fine-tuned small models >> zero-shot LLM monitors OOD here. No hyperparameters.
- Cheap Reward Hacking Detection (2606.08893, https://arxiv.org/html/2606.08893v1): 13.8M-param encoder from scratch, 7,114 trajs, split by task_id; AUC .9467 TPR@5%FPR .83; stripping reasoning text -> AUC .763. NO unseen-source test; authors: "generalization to unseen architectures untested". LR 3e-4, bs32, 8k steps.
- TRACE benchmark (2601.20103, https://arxiv.org/html/2601.20103): 517 trajs, 54 hack categories; best zero-shot GPT-5.2 45% isolated -> 63% contrastive (clusters N=5 gives ~35% gain, N=10 diminishing); semantic hacks (context exploitation, info leakage) match rate 0-.4 vs syntactic .6-.95; detectors wrongly trust user acceptance and agent self-disclosure. No training experiments. Takeaway: our "authorization" class is the semantic hard case; labelers/teachers will fail there too.
- StepGuard (2608.24777, https://arxiv.org/html/2608.24777): Qwen3-4B-Instruct, 3K StepGen cold-start SFT (CE) then Balance-GRPO. SFT 79.7 acc (safe 69.3/unsafe 91.1, gap 21.8) -> GRPO 81.5 -> Balance-GRPO 82.2 (gap 8.0). StepGen same-context-different-action prefix-aligned supervision: avg 80.4/82.0 -> 83.8/83.4; benign tool-reuse negatives: TS-Bench-Harm F1 69.2->75.2. Held-out risk sources (SFT only): trained on 2 sources, 6 unseen -> 74.9/78.1 vs full-coverage 76.8/80.7 vs backbone 49.6/35.6 (small OOD gap from only 2 sources). Learning rate/epochs not retrieved. Lesson: SFT on 4B shows safe/unsafe asymmetry (over-flags); RL not feasible in 22h but class-gap balancing is.
- Asymmetric goal drift (2603.03456), inherited goal drift (2603.03258), ARCTIC diff-intent drift (2607.29516): measurement/detection studies, no trained monitor (search snippets, UNVERIFIED depth).

### 1.8 Counterfactual / minimal-pair / context-use
- CPA (NeurIPS 2026, https://neurips.cc/virtual/2026/171167): generate+audit opposite-label counterfactual per pointwise item; train joint pointwise+pairwise, deploy pointwise. Qwen3-8B LoRA per criterion (6 criteria): +2.5 macro-F1 over pointwise-only; beats model merging at all weights; +11.8 over Gemini 3.6 Flash zero-shot. No OOD reported. Closest direct support for (b); gain modest.
- Curriculum judge (2606.09165, https://arxiv.org/html/2606.09165): gemma-3-12b SFT; fixed rubric 2 epochs then dynamic rubric share +0.1/epoch to 80%; cross-rubric range .76 vs fixed-only 1.44 vs naive mixing 3.60 (naive mixing WORSE). Lesson: augmentation ordering/curriculum matters; naive mixing of context variants can hurt.
- READ (AIES 2026, snippet only, UNVERIFIED): judges answer from safety prior rather than the supplied policy; perturb policy to test. Use as eval: flip authorization, require label flip.
- PairCFR (2406.06633, known-baseline-ish): contrastive regularizer on CAD pairs improves OOD over plain CAD. ACL-SRW 2026 minimal fallacy pairs: marginal gains (snippet only, UNVERIFIED).
- Calibration/rebalancing: RCV1 multi-label paper 2609.26468 (snippet only, UNVERIFIED): oversampling/loss reweighting improve performance but worsen calibration; focal improves both. Contradicts Inner-Jev focal result (worse acc, ECE .193 raw) but different setting. No LLM-classifier prior-shift study found.

## 2. KNOWN-BASELINE (pre-existing background, not re-verified)
- Guo et al. 2017 temperature scaling: fit single T on held-out NLL; standard post-hoc fix (https://proceedings.mlr.press/v70/guo17a.html, cited by Kev page).
- Kaushik et al. 2020 CAD: counterfactually-augmented data reduces spurious reliance, OOD gain modest and needs pairs near-identical.
- Logit adjustment / prior correction after rebalancing: standard (suggest p' ∝ p·π_true/π_train); no 2026 measurement found.
- Label smoothing/soft targets reduce overconfidence generally.

## 3. Per-family verdict

### (a) Direct supervised decision CE
For: Inner Jev: CE+LoRA, 400 steps, 23 min on 4B; loss variants tied after T-scaling (<=.01 ECE); hard->soft only -0.3; Brier ~+1.1 (1 seed). StepGuard SFT baseline 79.7 -> strong enough. Cheap RH detection: plain supervised small encoder AUC .95 in-distribution.
Against: Li et al.: synthetic/prompt-elicited labels transfer 4-31% to real hacks; 4B gain over zero-shot only +3 in Inner Jev; narrow data induces yes-bias and loses broad ability (LLM2Jev); SFT shows safe/unsafe gap 21.8 (StepGuard); more steps overfits calibration.
Hyperparams: LoRA r16-32 a2r, LR 1e-4 (LLM2Jev, with no gain at 4B in Inner Jev: 2e-5 LoRA/1e-4 head vs 1e-4 both ~same), 250-400 steps, ~190 q/step (~76k q), bs 32 (LLM2Jev), WSD/linear decay, wd 0-.01, final ckpt, 3 seeds, shuffle options each epoch, T per question type fit on held-out, clamp T>=1.

### (b) Contrastive/counterfactual teacher distillation + replay/KL anchor
For: teacher soft labels +1.9 over public-only (Inner Jev); distilling from trained 31B +2.1 on 4B; CPA +2.5 F1 and beats zero-shot frontier; StepGen same-context-different-action +3.4 acc/+6 F1; KL/anchor + mixed-in general data prevents format collapse and yes-bias (LLM2Jev, λ=1 at 4B); label source realism matters most (Li et al.), so verified/on-policy labels are the right axis; weight-averaging with prior ckpt used by Liquid.
Against: no direct trial of authorization-flip pairs; naive mixing of variants hurt cross-rubric stability (2606.09165) -> use curriculum/ordering; teachers fail on semantic hacks (TRACE bench 0-.4 match) so teacher labels on authorization cases are noisy; CPA gains modest, no OOD; at 4B soft-vs-hard only 0.3 so distillation benefit is mostly from more/cleaner data, not soft targets; adds pipeline risk in 22h.
Hyperparams: anchor λ=1 (4B), 0.1 (0.6B); distill-from-teacher mix as in Inner Jev (117k soft of 418k, ~28%); curriculum: pairs share +0.1/epoch (2606.09165).

### (c) Process/prefix-supervised temporal (TRACES-style)
For: StepGuard prefix-aligned supervision +3.4 acc; TRACE (2510.01367) shows early-prefix signal detects hacking, beating CoT monitors 30-65% (training-free); Cheap RH: reasoning text is the signal (strip -> AUC .95->.76).
Against: weak per-prefix labels noisy; no paper shows small-model prefix training generalizing to unseen sources; costs multiples of data length (context 8k validated for Kev-4B); StepGuard's OOD gain came from risk-source diversity, not prefix per se.
Hyperparams: none specific beyond StepGuard 3K cold-start demos (LR missing).

## 4. Calibration summary
- Post-hoc per-type temperature (fit on held-out, clamp >=1) is the evidenced fix; training-time losses (Brier, ECE-pen, MMCE, focal, EU) give <=.01 ECE after T (Inner Jev Table 16). Fine-tuned T near 1.3-1.5 (Jeff-Large).
- Per-source calibration drifts (Just Ask Jev median per-benchmark ECE .168 vs .074 null): hold out whole sources for T and threshold; 10-item threshold fits unreliable.
- Rebalancing: if oversampling, expect miscalibration; fix with prior correction or T on natural-prevalence held-out. Evidence UNVERIFIED (snippet).

## 5. Anything dominating?
- No post-cutoff method shown to dominate CE+LoRA at 4B for small data. Candidates worth cheap add-ons: weight averaging with prior/pre-FT ckpt or multi-seed merge (Liquid, undisclosed numbers); balanced-class advantage (StepGuard, needs RL, skip); training-time-source (natural) labels over synthetic (Li et al.); evaluate with source-held-out splits.
- Gaps: no fetched ablation of permutation consistency or replay for Kev/Mammoth; Kev README hyperparameters unread; StepGuard LR/epochs unread; Baseten blog and Laya paper unreadable.
