# Kev-4B user-intent capability: published evidence (2026-11-07)

Labels: [M]=measured (numbers in files/reports I read), [C]=claimed by author/third party, [U]=UNVERIFIED/not checked.
Local clone read: scratchpad `kev-src3` (jaredpalmer/kev, depth 1). Paths relative to it. No code run.

## 0. Verdict
- Evidence INSUFFICIENT to call Kev-4B strong or weak at (b) goal inference / intent adherence. No published eval for Kev, OpenJev, Jev, Jeff or Liquid d1 measures IFEval-style adherence, UserIntentBench, clarification-need, implicit-goal inference, or trajectory goal adherence. [M: none in README, model cards, PLAN.md, eval manifests, 5 arXiv abstracts, OpenJev pages]
- (a) routing intent: Kev-4B decent but below Jev on held-out CLINC150 (test 0.793; dev 0.880 vs Jev dev 0.973). BANKING77 was IN training, so no transfer number exists.
- Nearest (b)-adjacent proxies, all indirect and small-n: JevBench `intent` 12/12 (n=12, easy classification), `adequacy` 8/12, `ambiguous` 5/7, When2Call 0.660 (dev), unanswerable-item overconfidence 0.00.
- "OpenJev good at user intent" claim: not found in any OpenJev source as a user-intent claim. Closest is AlquimiaAi/openjev intent/routing row = 92.8% (27B, equal to Jev, below untuned base). See section 2.

## 1. Kev's own evals
Kev-4B = LoRA r16 on Qwen3.5-4B-Base, T=2.41, typed noul/choice/score decisions, not a generator (README.md; docs/model-cards/kev-4b.md).

### 1a. Training data touching intent/instruction (model card "Training data")
- decision-v7: 10,000 recs from ten public sets, 1,000 each: banking77 (intent, IN TRAINING), boolq, ag_news, multi_nli, sst5, yelp, trec, dbpedia_14, amazon_reviews_multi_en, imdb [M]. Plus 896 generated policy minimal pairs, 1,680 rule-structure recs.
- Later stages: dates/missing evidence 1,425; CFPB complaints 5,219 recs; hard-v1 6,000 (7 families incl. judging a proposed answer, missing-fact abstention, trade-offs under stated priorities); devtools-v1 5,320 (CodeReviewer, CommitPackFT, FlakeFlagger, Aegis). No Jev outputs used.
- NOT in training: MASSIVE, CLINC150, IFEval-like, clarification, goal inference.
- Private SFT-v1 (PLAN.md ~l.336-395, round 19) added synthetic "intent / dialogue state / out-of-scope routing" data, but only for Kev-27B-class arms (Qwen3.8-27B), not released Kev-4B. Result: CLINC150 0.873 -> 0.953, SGD 0.647 -> 0.727 (PLAN.md l.395) [M]. Shows intent-routing data moves (a) a lot out-of-training.

### 1b. Held-out results with intent relevance
breadth-v1 DEVELOPMENT (runs/breadth-v1-report/report.md; Kev-4B dev index 40.8):
| dataset | Kev-4B | Jev | Kev-27B | AutoJev-27B |
|---|---|---|---|---|
| clinc150 (150-way intent, chance .10) | 0.880 (ECE .212) | 0.973 | 0.873 | 0.980 |
| sgd (dialogue state) | 0.593 | 0.793 | 0.647 | 0.833 |
| apibank | 0.880 | 0.947 | 0.933 | 0.953 |
| bfcl | 0.940 | 0.980 | 0.967 | 0.967 |
| routerbench | 0.340 | 0.287 | 0.300 | 0.227 |
| Retrieval & Classification index | 55.9 | 75.4 | 62.9 | 76.1 |

Released checkpoint (@139fdd94) TEST (runs/fam-4b-breadthtest/report.json, read directly): clinc150 0.793 (n=150, ECE .143), sgd 0.673, apibank 0.893, routerbench 0.347, bfcl_irrelevance 0.941 (n=17), bfcl_live_irrelevance 0.692 (n=39). Overall breadth test acc 0.690 vs Jev 0.757; index 38.0 [35.5,41.3] vs Jev 54.0 [51.2,57.0] [M, model card]. bfcl "irrelevance" = should no tool be called (weak proxy for request/action fit).

JevBench public (runs/jevbench-public/kev-4b-r10/summary-*.json, read directly; r10 is the 4B stage per PLAN.md l.187, hash match to release [U]):
- original tier 72 items acc 0.931; n=12 each: intent 1.000, policy 1.000, routing 1.000, ordinal 1.000, extraction 0.917, adequacy 0.667 [M].
- hard tier 111 acc 0.541 (card: all 231 = 0.758; hard ECE 0.112): adversarial .833 (n6), ambiguous .714 (n7), judge_hard .529 (17), long_policy .316 (19), multi_hop .611 (18), probability .500 (10), routing_hard 1.0 (5), temporal_numeric .200 (15), tradeoff .500 (6), trap 1.0 (8) [M].
- Reading: JevBench "intent" is easy classification; "adequacy" (response adequate?) is the nearest request-satisfaction proxy; "ambiguous" nearest clarification proxy. n too small for conclusions. Jev per-family numbers not retrieved. Jev hard tier: Kev-9B hard 0.568 vs Jev 0.741 (PLAN.md l.3140).

Other (model card "Other results", Kev-4B vs Jev): When2Call (devtools-v1 dev, call/ask/refuse) 0.660 vs n/a; prompt injection 0.753 vs 0.893; SemIf (144) 0.889 vs 0.965; MMLU 0.725 vs 0.90; MMLU-Pro 0.565 vs 0.840; deadline dates 0.65 vs 0.95. transfer-v4 locked test 0.838 / Brier .224 (dev 0.817 vs Jev 0.857). hard-v1 test 0.803; devtools-v1 test 0.756; documents-v1 test 0.903; decision-v7 test 0.865. Unanswerable items answered at p>=0.9: Kev-4B 0.00 vs Jev 0.09 (good abstention under missing evidence, a clarification prerequisite) [M]. Kev-0.8B When2Call fell to 0.133 test after skills stage (docs/releases/kev-1.0.md l.49): skill stages can damage ask/call behaviour. Model card limitation: gains are in-distribution; trails Jev by 16 index points on held-out datasets.
- Third party (orcarouter.ai/blog/jev-vs-kev; Jev reseller, [C]): Kev-9B 0.952 vs Jev 0.897 on scienthoon 900-ticket routing. Kev README says scienthoon was REMOVED as a gate (templated text, one question needs an unstated rule). Unreliable.
- AIMultiple (aimultiple.com/system-one, search snippet only [U]): Kev-9B System One Index 69 vs Jev 1.13 66; browser DecisionBench Kev-9B 20/50 vs Jev 17/50. 9B, not intent.

## 2. OpenJev: three different projects share the name
1. Zefan-Cai/Open-Jev (github.com/Zefan-Cai/Open-Jev; README via WebFetch) [C, self-run]: MIT; 2B/9B/27B v1.1, Qwen bases, LoRA + scalar head. JevBench public 231: 2B 150/231 (64.94%), hard 46/111 (41.44%); 9B 179/231 (77.49%), hard 66/111 (59.46%); 27B-v1.1 197/231 (85.28%), hard 80/111 (72.07%); "Jev ahead by three overall, one Hard". Internal (27B): Old Test 98.31%, Expanded Test 96.65%. Support-routing pilot (2B) 166/256 = 64.8% vs BM25 211/256 = 82.4% (2B loses to BM25); 14 errors in 88 accepted rows. README: "natural intent routing" data prepared, "no completed model result". Weak: wiki, T-Rex, painting OOD, some customer-workflow judgments. No user-intent or instruction-adherence benchmark.
   Cross-compare: Kev-4B JevBench all 0.758 / hard 0.541 sits between Open-Jev 2B (.649/.414) and 9B (.775/.595).
2. AlquimiaAi/openjev (huggingface.co/AlquimiaAi/openjev) [C, self-reported]: 27B BF16, base unnamed. 10,000-q text set: Jev 85.4%, OpenJev 84.0%, untuned base 80.4%. Intent/routing/topic (1,218 q): OpenJev 92.8 / Jev 92.8 / untuned base 93.2 (tuning gave nothing on intent). Others (OpenJev/Jev/base): sentiment 82.1/81.5/78.3; spam-hate 80.4/81.2/80.1; legal 78.9/78.8/77.8; ethics-policy 78.1/75.8/65.5; commonsense 85.8/88.3/80.3; science-claims 82.5/89.0/81.0; reading 89.2/89.3/83.3. MASSIVE 80.4 -> 85.8. Option-order flips 2.3% vs 18.5% untuned. Page itself: no separate user-intent claim. Likely origin of the "good at intent" idea; it is (a), 27B.
3. razorback16 OpenJev (DiffusionGemma 26B-A4B) and "SemIf, formerly OpenJev" (frozen Qwen3.5-4B logits; 0.845 modal agreement vs Jev 0.883 on 102 rows; 27B 0.958 balanced acc on 144) via pinggy.io/amp/blog/best_open_source_jev_alternatives_self_hosted_decision_models/ [C, secondary]. No intent numbers. Same page: Laya 421M BANKING77 0.425 vs Jev 0.870.

## 3. Head-to-head benchmarks
- JevBench public: only place Kev-4B and Open-Jev (Zefan-Cai) share a harness (above). Family-level Open-Jev not published.
- System1-Arena 2610.21244 (arxiv.org/html/2610.21244, first 100k of 223k chars read): 30 models; 10 System-1 = Jev 1.13, Decision-2.0 Vega-27B/Lux-9B/Nox-4B/Kai-0.6B/Sol-2B, Laya, CLM-v0.1-8B, Microsoft-Decision-1, OpenAI Decisions API. Kev, OpenJev, Jeff, Liquid d1 NOT included. Columns Dialog (Jev 73.2, Nox-4B 70.7), Route (Jev 64.5, Nox-4B 59.0), Judge (Jev 68.4, Nox-4B 58.3). No intent/IFEval/clarification breakdown in read portion; remaining 123k chars UNREAD [U].
- S1CogBench 2611.00911 (abstract only): five unnamed open models + Jev, 24 cognitive tasks; not (b); Kev unnamed [U].
- Just Ask Jev 2609.29429 (abstract only): Jev only; 10 failures incl. reward hacking, sycophancy, prompt injection, deception; 44 benchmarks; median AUROC 0.886 with one generic question; 63x cheaper than LLM judge. No Kev/OpenJev; instruction following not a listed category; per-failure numbers [U].
- Releasing the Inner Jev 2610.17205 (abstract only): Gemma 4 31B/12B, Qwen3.6-27B, Qwen3.5-4B (same base as Kev-4B); OpenDecisions 2,352 q; Gemma-31B untuned 79.6 vs Jev 80.1; tuned 84.4 OpenDecisions / 81.5 JevBench v1.7. Kev absent; per-family tables [U].
- JevOut 2609.30243: natural background context redirects 61.4-73.2% of correct decisions of four systems (Jev named); robustness caveat for implicit-context inference; Kev not named.
- LLM2Jev: not searched [U].
- Jeff-1 (GestaltLabs; Qwen3-4B-Instruct-2507 LoRA, gradually.ai/en/ai-models/jeff-1, snippet) and Liquid d1-3B (3.12B; open-weight status disputed; mer.vin, vercel.com/ai-gateway/models/d1, snippets) [U]: no intent or instruction benchmark found.
- No source compares Kev-4B, OpenJev, Jeff, d1 on any (b) task.

## 4. IFEval / UserIntentBench / clarification / trajectory adherence
None for any Jev-family model (grep of README, cards, PLAN.md for ifeval, clarif, user intent: no hits beyond banking77/CLINC/When2Call/MASSIVE-as-excluded-source). Tangents only: When2Call, bfcl irrelevance, JevBench adequacy/ambiguous/judge/trap, hard-v1 judge and abstention families, unknowable-item test.

## 5. Unmeasured (b)-capabilities for a small probe
1. Implicit/unstated goal inference (choose true goal vs literal-reading distractors).
2. Request satisfaction: does response/action satisfy request, incl. partial; IFEval-verifiable constraints as yes/no.
3. Clarification need: ambiguous vs fully-specified minimal pairs; ask vs act. Baselines: When2Call 0.660, bfcl_live_irrelevance 0.692, JevBench ambiguous 5/7.
4. Implied constraints/requirements extraction; user-intent shift across turns.
5. Trajectory goal adherence/drift; reward-hacking detection (Jev-only evidence).
6. Robustness: option-order sensitivity and context-injection (JevOut) for Kev.
Probe suggestion: ~100-200 paired items per capability, Kev-4B vs Jev API vs untuned Qwen3.5-4B logit-reading; accuracy and ECE, paired bootstrap (kev.compare). Prior: Kev-4B trails Jev on every held-out Retrieval & Classification set (55.9 vs 75.4), and intent SFT lifted Kev-27B CLINC150 by 8 pp, so a gap on (a) is expected; (b) is unknown.

## 6. Sources
jaredpalmer/kev: README.md, docs/model-cards/kev-4b.md, docs/releases/kev-1.0.md, PLAN.md, runs/breadth-v1-report/report.md, runs/fam-4b-breadthtest/report.json, runs/jevbench-public/kev-4b-r10/summary-{original,hard}.json, evals/breadth-v1/manifest.json. github.com/Zefan-Cai/Open-Jev; huggingface.co/AlquimiaAi/openjev; arxiv.org/abs/2609.29429, 2610.21244, 2611.00911, 2610.17205, 2609.30243; pinggy.io blog; orcarouter.ai/blog/jev-vs-kev; aimultiple.com/system-one; gradually.ai jeff-1; mer.vin d1.
