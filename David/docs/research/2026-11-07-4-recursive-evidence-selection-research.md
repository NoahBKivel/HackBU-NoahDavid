# Recursive evidence selection for Kev monitor — research (2026-11-07)

Legend: [NEW] post-cutoff 2026 source; [BASE] known baseline. All facts are from fetched pages unless marked UNVERIFIED. Searches ran ~20 min; many details are from abstract/HTML text only.

## 1. Extract-and-evaluate (EaE) [NEW]
Source: https://arxiv.org/html/2601.21112 ; https://proceedings.mlr.press/v306/arike26a.html
- Mechanism: Extractor sees full CoT+actions, reasons about suspiciousness, outputs verbatim EXCERPTS (not a score). Evaluator sees ONLY main-task description + excerpts, outputs suspiciousness score. Separate models and separate contexts; single-context extract-then-score was NOT competitive (same arXiv page).
- Gains (1% FPR catch rate, BigCodeBench-Sabotage): GPT-4.1-mini +16.8pp over best of 4 baselines (+19.9 on subtle side tasks); GPT-4.1 evaluator + 4.1-mini extractor +31.5pp (+39 subtle). Best in 7/8 main pairs; beats best other monitor in 11/16 pairs (App. B.1). MLE-Sabotage: Gemini 2.0 Flash AUROC 0.924 at ~$0.004/transcript. Weaker on SHADE-Arena.
- Cost: extractor reads long input, evaluator short; added cost "modest".
- Failure modes (authors): (1) extractor misses the damning quotes (judged side task benign, or never verbalized) so evaluator has nothing to score; (2) evaluator sees real excerpts but rationalizes them benign. Both more frequent in SHADE-Arena.
- Limits: number of excerpts unspecified; only asynchronous, post-hoc, scaffold-level; few environments.
- Also: more info is not monotone better ("less-is-more"): CoT+action worse than less-informed monitors in 7/8 pairs (search summary, UNVERIFIED on exact count).
- Design relevance: this is exactly the screen-then-judge shape, and its own #1 failure mode is screen false negative. No always-on global check in EaE.

## 2. Cascades / high-recall screens
- Conformal Cascade (arXiv 2607.25018) [NEW]: split conformal, deferral by prediction-set size; targets ACCURACY not recall. https://arxiv.org/pdf/2607.25018
- CRC-Screen (DNA synthesis screening) [NEW]: Conformal Risk Control bounds expected false-negative rate of a screener. https://arxiv.org/pdf/2603.14623 (UNVERIFIED mapping of ID to CRC-Screen; search result listing ambiguous).
- SUPG-IT (semantic SQL cascades) [NEW]: proxy handles most rows, oracle on uncertain; joint precision/recall guarantees online; thresholds refined iteratively from oracle samples. Source via search result only (UNVERIFIED which arXiv ID among 2605.00074 / 2604.00660).
- Search found no LLM two-stage paper with finite-sample recall bound; recipe must be built from Learn-Then-Test / CRC [BASE technique]: label a calibration set of (pack, event) pairs for "pack contains needed evidence", choose threshold on screen score so empirical miss rate <= alpha with a finite-sample correction; guarantee holds only under exchangeability (breaks under distribution shift: new project docs, new agent behaviors).
- Unblocked (practitioner, 12,927 pairs) [NEW]: tightening criteria to "necessary" cost ~20 points recall; they tuned the THRESHOLD instead, prompt variants (9) gained little. https://getunblocked.com/blog/jev-in-production-vs-cross-encoder/index.md
- Designs where stage 2 doesn't depend solely on stage 1: SLEIGHT-Bench authors suggest cheap monitors always on + expensive monitor as second stage; ensembles of specialized prompts, since each targeted prompt degrades some other category (https://alignment.anthropic.com/2026/sleight-bench/). SearchJev escalates uncertain System-1 judgments to System 2 (https://arxiv.org/abs/2610.05107), thresholds delta/tau_keep values in appendix, not read.

## 3. Decision model / reranker as retriever
- Unblocked, Jev fan-out vs cosine-top100 + cross-encoder [NEW] (https://getunblocked.com/blog/jev-in-production-vs-cross-encoder/index.md): recall of relevant notes 63.8% -> 77.6%; precision 34.8 -> 46.4; silent-when-none-relevant 48.4 -> 59.4; nDCG@5 +0.0479 (CI +0.018..+0.077); p50 0.20 -> 0.35 s; $1.87 -> $1.76 per 1k questions. Per-PAIR Jev (one note per call) was WORSE (-0.0333 nDCG@5): isolated judging grades too charitably; relevance partly relative. Shipped: question as shared state, 20 notes per request. Single workload, LLM-judge labels (93.0% repeat agreement).
  - Implication: a yes/no probe per isolated pack is the weak mode; batch several packs/candidates in one state with comparative framing. But our states cap ~8K validated.
- SearchJev (2610.05107) [NEW]: relevance NDCG@10 in-dist SearchJev-4B 99.0 vs Qwen3.5-4B AR 96.7, Jev 98.5; OOD FRAMES 99.0 vs 93.8; latency batch1 median 37.1 ms vs 195.2 ms AR. 0.8B AR variant retained ~3x more docs, exhausted context in 67/100. End-to-end BrowseComp-Plus 54 vs 45 System-2-only. No recall@k vs BM25 reported. https://arxiv.org/html/2610.05107
- Jeva (2610.18773): option-encoder design, thousands of candidates, option reuse; architecture differs from Kev; no numbers read. https://arxiv.org/abs/2610.18773
- LLM rerankers vs BM25: rankings weakly correlated with BM25 (Kendall tau 0.19-0.41), i.e. not just lexical (https://www.arxiv.org/pdf/2602.18613, UNVERIFIED not fetched). InfoSearch instruction retrieval: GPT-4o listwise WISE 33.5; splitting instruction into typed clauses 32.9 -> 47.6 (search summary only, UNVERIFIED; date in result looked odd). CheckThat! 2026: cross-encoder -1.55 vs hybrid on test (overfit) https://arxiv.org/pdf/2607.24803 (UNVERIFIED). No direct recall@k of yes/no probe vs BM25 on requirement retrieval found. GAP.
- [BASE] Standard practice: BM25/dense first stage maximizes recall, cross-encoder reranks top-k; hybrid (RRF) beats either on paraphrase/lexical mismatch.

## 4. Long-horizon monitors
- SLEIGHT-Bench (arXiv 2605.16626; 40 attacks, 11 categories; Opus 4.6 monitor, 1% FPR) [NEW] https://alignment.anthropic.com/2026/sleight-bench/ : catch rates plausible naming 90%, authorization confusion 55, system state 46, needle-in-haystack 38, multi-session 30, file/object reuse 15, counting 13, model priors 13, N-hops 0, omission (missing steps) 0, jailbreaks 0. Overall 32% catch; 20/40 never flagged. Omission = harm from action NOT taken; monitors rarely flag absence. System state = cumulative changes unnoticed. Multi-session = split across separately monitored sessions. Fixes: targeted prompts (each trades off others), ensembles, code-executing monitor (~10x invocations, 14x output tokens); more compute/thinking helps.
  - Implication: per-event monitors with evidence packs need explicit checklist/obligation questions ("required step X done yet?") fed by persisted state; screening by relevance of the current event cannot find omissions.
- TRACES (EMNLP 2026, arXiv 2605.27690) [NEW] https://arxiv.org/html/2605.27690 : observer LLM hidden states -> mechanism bank (K=8) -> GRU over steps; online/recurrent, only prefix info. Per-step cost = one observer forward + small encoder + GRU update (inferred; efficiency appendix D.4 not read). ATBench recall 93.9 / F1 84.5 (Qwen3-4B). Failure: early false alarms, late/missed alarms, observer dependence, offline eval. Bounds cost by constant-size recurrent state, not by re-reading history.
- StepGuard (arXiv 2608.24777, EMNLP 2026) [NEW]: step-level guard trained via StepGen paired safe/unsafe trajectories; -77.3% attack success AgentDojo/AgentDyn, -2.8pt utility (https://www.opentrain.ai/papers/stepguard-learning-step-level-guardrails-with-scalable-supervision-and-safety-ut--arxiv-2608.24777/). Per-step cost not read. RGE: NOT FOUND/UNVERIFIED.

## 5. System One / Jev / Kev
- Kev-4B: LoRA + pointer head on Qwen3.5-4B-Base, Jev-compatible API, Apache-2.0, ~$95 H100 training [NEW] https://runtimewire.com/article/jared-palmer-kev-qwen35-decision-models ; https://github.com/jaredpalmer/kev
- Chain evidence: SearchJev = System-1 relevance/sufficiency/action decisions with System-2 escalation (above). Jev as "typed decisions for agents" (https://openclawdatabase.com/jev/index.md, not read). "Just Ask Jev" and "SOMA": NOT FOUND in searches (UNVERIFIED/absent). No source on Kev/Jev as safety monitor found.
- Jev API: 262,144 ctx per docs.aimlapi vs 64K budget/32K state per OrcaRouter (conflict; UNVERIFIED which); sample 3 questions, 406 in tokens, 96 ms (https://docs.aimlapi.com/api-references/decision-models/typesafe/jev.md). Price $0.042/M input, output free, questions evaluated in parallel on one shared state read (https://www.orcarouter.ai/blog/jev-vs-kev). Jev route median 151 ms, p95 247 ms (same).
- Kev accuracy (README): Kev-4B new sources 0.817 dev / 0.838 test, Brier 0.269/0.242; trained 0.873/0.865; at 5% error budget Kev-4B/9B/27B automate 0.52-0.69 vs Jev 0.70. Validated context for 0.8B/4B/9B = 8,192 tokens; at 16K can't show within 3 pts; at 32K measurably worse (CUAD). Probs bf16 vs fp32 differ up to ~0.03; top answer flips ~1/300.

## 6. Throughput (Kev README https://github.com/jaredpalmer/kev) [NEW]
- H100 Kev-4B: 6 questions short text 18.1 ms new / 12.9 cached; 5 questions on 2,200-token state 89.4 ms new / 22.5 ms cached. L40S same: 145.2 / 43.0 ms.
- M5 MLX Kev-4B ~270 tok: 721 ms new / 136 ms cached (5 q). 65K doc: Kev-4B 84.5 s first / 716 ms cached.
- Deployed Modal H100 Kev-4B: p50 102.1 ms web endpoint, 36.9 ms direct (1 client).
- Server throughput, 64 concurrent clients x 6 questions: Kev-4B 51.4 req/s L40S, 100.8 req/s H100; Kev-0.8B 62.8 L4. Forward budget 16,384 tokens; answers independent of question splitting.
- Cache is keyed on exact state text, so any pack-order or content change = full re-read; cached cost ~ questions only. Third-party figure 779 ms (Qwen3.5 Kev-4B, M5, ~230 tok, 5 q) vs 174 ms Qwen3: regression (search summary).
- Sizing rule (derived, ESTIMATE): per event on H100, cold ~ 90 ms per 2.2K-token pack-state (5 q), warm ~ 22 ms. Packs P of ~2K tokens, one screening question each: cold cost ~ P x ~50-90 ms sequential, but batchable ~100 req/s aggregate => P=20 packs ~0.2 s throughput-bound. Doc packs are static across events, so screen-state (pack text + broad question) is cache-hit if the event is placed AFTER the pack in the state... but then the event text sits in the suffix and each pack is still a distinct state; only the pack prefix is reused, event+question suffix re-read (short). Placing the event first destroys reuse.

## Synthesis
Best-evidence shape (inference, not directly tested anywhere): hybrid cascade with NON-exclusive routing:
1. Always-on global layer, never gated by the screen: a small fixed state holding user's original instruction + pinned constraints/obligation checklist + rolling compact run-state (TRACES-style constant-size summary), asked the detailed typed questions every event. Covers omission, multi-session, cumulative state, where per-event relevance screening is blind (SLEIGHT 0%/30%/46%).
2. Recall-first pack selection by UNION of cheap and Kev signals: BM25/embedding top-k (lexical/paraphrase cover) OR Kev screen prob >= tau, plus all packs hit last N events (stickiness) plus a random exploration sample of unselected packs (gives unbiased recall estimates and catches drift). EaE's failure #1 argues against screen-only.
3. Screen with comparative multi-candidate states (Unblocked: per-pair isolated probing lost -0.033 nDCG; fan-out 20 candidates won) packing several short packs under 8K, ask "which of these conflict/constrain this event"; tau chosen by threshold-at-recall on labelled calibration, not prompt tightening.
4. Stage 2: merge selected evidence into one <=8K state (prefix-cache friendly: stable instruction + pinned prefix first, selected packs sorted by pack id, event last), ask all detailed questions in one forward.
5. Uncertain screen scores (band around tau) escalate to include the pack rather than drop it (SearchJev-style defer).
Do not rely on 4B beyond 8K; Kev-4B new-source acc ~0.82-0.84 means screen miss floor is nonzero.

Instrument for screen recall in our build:
- Gold set: events x packs labelled "needed" by an expensive oracle (all packs, all questions, frontier LLM or exhaustive Kev-merge) on a sample of trajectories incl. injected violations (SLEIGHT-style omission/multi-session/paraphrase cases).
- Metrics: pack-level recall at chosen tau (and Wilson/CRC upper bound on miss rate), VERDICT-level recall (does the final stage-2 decision flip vs full-evidence run, the metric that matters), by category (lexical vs paraphrase vs omission).
- Online shadow: on a random p% of events (e.g. 2-5%) run the full pack x question grid in the background and log screen-miss = (full flags violation) AND (cascade didn't); alert if miss rate CI exceeds alpha; recalibrate tau on drift. Counterfactual log of unselected packs' screen scores for reliability diagrams.
- Cost check: log cold vs cached ms per pass, cache hit rate by state shape.

## Gaps
No source found for: recall@k of yes/no probe vs BM25 on requirement/instruction retrieval; RGE; "Just Ask Jev"; SOMA; Kev as monitor; per-step costs of TRACES/StepGuard; finite-sample recall guarantees for LLM cascades.
