# Data mixing / ordering for Kev-4B LoRA continuation (research, 2026-11-07)

Tags: [M]=measured in cited source; [E]=my estimate/extrapolation; [NEW]=2026 post-cutoff work; [BASE]=known baseline. Mostly abstract/snippet-level evidence unless "fetched". No head-to-head study matches our setup (LoRA, 4B, ~15 heads, agent trajectories); most evidence is indirect.

## 0. Corrections to premises
- 2610.02076 is titled "LLM-as-Jev" (Li, Wagle; Qwen3.5-4B, Qwen3-0.6B). Fetched full text: narrow intent-only training gives "aggressive confirmation bias toward yes"; JevBench acc 81.4% -> 74.9% [M, NEW]. Table 7 "Yes" count, 4B: 36 (orig) -> 49 (Intent-1ep, 95,461 ex) -> 55 (Intent-100, 3,000 ex). Balanced reasoning data restores it: Reason-9k (3k intent + 6k other = 33% intent) back to 81.4%, Yes=44. Reason-21k (14% intent) and Reason-30k (10%) also tested. No explicit "replay ratio"; KL anchor lambda=1 default (0.1/0.01/0 ablated), top-64 tokens. https://arxiv.org/html/2610.02076v3 (first 100k of 157k chars read). Key: bias appeared even at 3,000 narrow examples, so it is composition, not volume; a ~67% non-target share fixed it.
- 2606.09165 ("Reliable to Expressive", ICML'26 AIWILDS workshop) is a 12B safety judge; curriculum = clean fixed-rubric supervision first, then noisier dynamic-rubric data. Naive mixing raised cross-rubric variance 1.44 -> 3.60; curriculum 0.76 [M, NEW, abstract only; abstract uses "range" and "variance" interchangeably]. https://arxiv.org/abs/2606.09165 . Transfer to us is weak: its ordering axis is clean-vs-noisy rubric, not source heterogeneity.
- Kev-4B facts come from secondary pages (Choice/Noul/Score, pointer head, prefill-only; one card says 8K context) and are inconsistent across sources; verify at github.com/jaredpalmer/kev. https://haimaker.ai/models/jaredpalmer/kev-4b . Check whether the 4B was ever trained on 16-32K before assuming long-context behaviour.

## 1. Mixture ratios
- Data Mixing Laws (Ye et al., ICLR'25): predicts loss for unseen mixtures from small runs; extends to continual training / forgetting [BASE]. https://arxiv.org/pdf/2403.16952.pdf
- CAMEL (2603.08022) [NEW]: mixtures tuned on small models transfer poorly to larger; claims -50% mixture-opt cost, up to +3% downstream (author claims). https://arxiv.org/html/2603.08022v1 . MergeMix (2026) [NEW]: merge weights as proxy, claims >100x cheaper search (author claim).
- SFT-specific: online DoReMi-style methods are hard to use in small SFT (small data, no proxy, long exploration) (Zhu et al. 2406.11256) [M]. https://arxiv.org/html/2406.11256v1 . DynamixSFT: bandit mixing, up to +2.2% over 10 benchmarks on Tulu-v2. https://arxiv.org/html/2508.12116v1 . Data Mixing Optimization for SFT (2508.11953): budget-aware domain weights, proxy-to-large transfer unreliable. https://arxiv.org/html/2508.11953v1 . DomainPilot (2607.22769) [NEW]: Qwen3-1.7B SFT, +2% MMLU-Redux, +3.8% LiveCodeBench v5. https://www.alphaxiv.org/abs/2607.22769.md
- Temperature sampling p_i proportional to n_i^alpha (alpha=1/T; T=2 used in DataVisT5) [BASE]; proportional underfits low-resource tasks, high T overfits them; start high T then cool (2024 low-resource MT). https://arxiv.org/pdf/2109.09138 , https://arxiv.org/pdf/2408.07401
- Found no controlled study showing mix ratio beats data quality at small budgets; tuned-mixture gains are ~2-4% (author-reported). [E] At our budget, per-question coverage floor and class balance matter more than fine ratio search.

## 2. Replay
- Kotha & Liang 2603.04964 [NEW]: replaying generic pretraining data during fine-tuning raised target data efficiency up to 1.87x (FT) and 2.06x (mid-training), 150M models, 4M target tokens in 4B total; helps more when target is less seen in pretraining; 8B: +4.5% agentic web navigation, +2% Basque QA. A secondary summary gives best replay ratios ~0.5-0.6 for FT (unverified; PDF unparsed). https://arxiv.org/abs/2603.04964 , https://www.emergentmind.com/topics/replaying-pre-training-data
- Healthcare Qwen2.5: 1:1 FineWeb mix kept OOD within 1.4 points (67.4) while keeping most in-domain gain; helped mainly at smaller scale [M, snippet]. https://arxiv.org/pdf/2605.01077
- Practitioner heuristics (not benchmarked): 5-20% (zeroentropy), 20-30% (genai-systems-lab), 1-5% for LoRA (dev.to). https://www.zeroentropy.dev/concepts/catastrophic-forgetting/ . LoRA forgets less than full FT (Biderman 2024) [BASE].
- Reading across: the two measured 2026 points sit at >=33% non-target share (LLM-as-Jev) and ~50% (Kotha-Liang, secondary). Kev's 2-4K replay is probably <10% of our mix [E]. Replay must be label-balanced (contain many "no"s), not just generic.

## 3. Curriculum / ordering
- ACL'26 Findings 2026.findings-acl.1021 [NEW]: random-only shuffling lacks a progressive effect; easy->hard early, then reshuffle the same data later. https://aclanthology.org/2026.findings-acl.1021.pdf
- ACL'26 long.1591 [NEW]: offline SFT ordering; no curriculum dominates; forward vs reverse depends on model reasoning capacity. https://aclanthology.org/2026.acl-long.1591.pdf
- A deductive-reasoning preprint finds ordering negligible; Kim & Lee (Mistral/Gemma 7B) find a slight gain vs random shuffle [BASE]. Dai et al. 2605.30334 [NEW]: cyclic/continuity ordering schemes, no numbers retrieved. https://arxiv.org/html/2605.30334v1
- Multi-task serving (2411.03644): high-resource tasks first, then full mix, to avoid over/underfitting. https://arxiv.org/html/2411.03644v2
- Verdict [E]: ordering effects are small and inconsistent; no matched-budget staged-vs-single-mixed evidence for source-heterogeneous SFT. Pairs-early vs mixed: no direct evidence found.

## 4. Class imbalance, many binary heads
- Benchmark of SMOTE vs class weights vs threshold calibration (30 datasets x 15 models): threshold calibration most consistently effective (2409.19751) [M, classical ML]. https://arxiv.org/html/2409.19751v1
- SMOTE-style oversampling can degrade calibration (2511.17629); reweighting can raise ECE and stacking it on logit adjustment can hurt (Frontiers 2023). https://arxiv.org/pdf/2511.17629v2 , https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2023.1296897/pdf
- Likelihood ratios survive prior shift, so only the threshold/prior moves (2602.08128 [NEW]); prior-shift framing of imbalance (2601.10630 [NEW]). https://www.arxiv.org/pdf/2602.08128 . Downsample + hold-out calibration is established (Amazon 2311.11723; Dal Pozzolo 2015).
- Gap: no LLM-classifier-specific evidence found. [E] Any balanced/oversampled training shifts the prior, so raw head probabilities are not natural-prevalence probabilities; fix post hoc with per-head prior-shift logit plus Platt/temperature on a grouped natural-prevalence dev set.

## 5. Long context
- ProLong (Gao et al. 2410.02660; fetched): final mix 30% code repos, 30% books, 3% textbooks, 37% ShortMix (~63% long); best long-task average at 60/40; short-context performance falls monotonically with long share; SFT on short UltraChat (~1B tok) alone; adding synthetic long SFT data lowered avg 55.7 (0%) -> 54.1 (1%) -> 53.5 (3%) -> 43.3 (50%) [M, BASE]. https://arxiv.org/html/2410.02660v4 . This is continued PRETRAINING at ~10B scale / 40B tokens: weak analogue for a LoRA SFT run, so ProLong's 40-60% should not be copied.
- Kev-27B ~7% long: user-supplied, not verified. [E] Our long examples are label-bearing trajectories; 8-12% of examples, interleaved uniformly, is the safe range. Concentrating them in a late block risks short-context drift (no direct source).

## 6. Rare questions / multi-epoch
- Kopiczko 2602.11149 [NEW]: at a fixed update budget, many epochs on a small subset beat 1 epoch on a larger set (long-CoT SFT; 20-50x epochs, ~8x less compute); val loss rises yet downstream keeps improving; no extra forgetting. https://arxiv.org/html/2602.11149v1
- 2607.04969 [NEW]: overfitting onset depends on data size; contrasts the ~4-epoch heuristic with Phi-4's gains up to 12 epochs on synthetic data. https://www.alphaxiv.org/abs/2607.04969 . Muennighoff 2305.13230: up to ~4 epochs about as good as fresh data; larger models overfit repeats [BASE]. https://arxiv.org/pdf/2305.13230.pdf
- Gap: no rare-task-specific study. Repeating 50-label questions helps but risks memorizing specific trajectory text.

## 7. Grouped splits
- 2604.23488 (Li et al.) [NEW]: monitors trained on prompt-elicited hacking data often fail on naturally arising RL hacking; monitors trained on natural (Trace-and-Amplify) trajectories generalize better to unseen hacking types. No numbers in abstract. https://arxiv.org/abs/2604.23488
- Leave-one-out round-robin over 4 reward-hacking datasets (2601.23086) https://arxiv.org/html/2601.23086v1 ; BaitBench (EMNLP'26 Findings): planted shortcut removed from held-out split https://aclanthology.org/2026.findings-emnlp.2477.pdf [NEW].
- [E] Best unseen-source predictor: leave-one-source-out; minimum: grouped by trajectory/task. Minimal pairs share a pair id and must stay on one side of every split, or near-duplicate leakage inflates metrics.

## Recommended recipe (numbers are [E] unless tied to evidence)
1. Single shuffled run, not staged. Evidence: ordering effects small/inconsistent (ACL'26 x2, deductive preprint); the one pro-curriculum result (2606.09165) is clean-vs-noisy rubrics. Risk: a large noisy teacher-labelled pool hurts early; see step 8.
2. Sampling: temperature sampling alpha=0.5 (T=2) over per-question label counts; cap any single question at ~15% of examples; floor each rare question at ~300 sampled examples per run (i.e. up to ~4-6x repeats of a 50-label question). Evidence: temperature sampling [BASE]; repeats ok to ~4 (2305.13230), sometimes far more (2602.11149, 2607.04969). Risk: memorizing rare trajectories; track grouped-val per question and stop upsampling when it plateaus.
3. Replay: >=30% of examples from general decision data, label-balanced (many "no"s), up from 2-4K flat. Evidence: LLM-as-Jev (33% intent share restored 81.4%; 3k narrow examples already gave yes-bias), Kotha-Liang (~0.5, secondary). Optional KL anchor on replay (lambda=1, top-64 as in LLM-as-Jev). Risk: slows learning of rare questions.
4. Benign Claude Code pool ~15-25% of mix, matched to hack sources by tool/format. Evidence: yes-bias finding and shortcut risk (2604.23488). Risk: model learns "Claude Code style = negative".
5. Minimal pairs ~10-15% of mix, interleaved (not a separate early stage), both members in the same batch. No direct evidence for pairs-early. Risk: few distinct contexts teach only the flip cue; cap repeats per pair id.
6. Long examples 8-12% of examples, spread uniformly, length-bucketed batches. Evidence: ProLong short-perf decline and short-SFT sufficiency; Kev-27B ~7%. Risk: too few long examples to shift behaviour at 4B; evaluate a long held-out slice separately.
7. Imbalance: mild oversampling of positives to at most ~1:3 pos:neg per head, no heavy loss weighting; per-head prior-shift logit + temperature/Platt fit on grouped natural-prevalence dev; thresholds set there. Evidence: 2409.19751, 2602.08128, 2511.17629, Amazon 2311.11723. Risk: heads with <~30 dev positives give unstable thresholds; report CIs, pool or use shrinkage.
8. Ordering: only a warm-up, first ~5% of steps from gold/clean-labelled sources, then everything shuffled with teacher-labelled items entering. Evidence: 2606.09165 (weak). Risk: low; drop if awkward.
9. Splits: group by pair id > trajectory > task > source; headline = hold out the most distinct source (plus all its pairs); rotate more if budget allows. Dev prefers natural (non-prompted) trajectories. Evidence: 2604.23488, 2601.23086, BaitBench. Risk: single held-out source is a high-variance estimate.
10. Skip DoReMi/online mixing and mixing-law fitting for this run. Evidence: 2406.11256, 2508.12116 (small gains, no proxy). Risk: forgoing ~2% gains.

Unverified: steps 2 (floor/cap numbers), 4, 5, 6 have no matched source. Cheapest validating ablation: replay 15% vs 35%, scored by per-head yes-rate on benign held-out and by grouped-val on rare questions.
