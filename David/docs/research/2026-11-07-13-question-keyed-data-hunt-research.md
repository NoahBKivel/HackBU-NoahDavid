# Hunt 2: question-keyed monitor data (2026-11-07)

Scope: new sources only (known baseline excluded). Facts carry source URLs; UNVERIFIED = not checked on primary page. Q-IDs = monitor questions. "Direct" = label exists as shipped; "build" = needs construction.
Method note: arXiv abs/HTML pages and HF pages fetched 2026-11-07. HF API search returned [] for "overclaim". Anthropic reward-seeker blog fetch failed (tool refusal), so blog claims come via search snippet only.

## 0. Key negative finding (the named 2026 papers)

| Paper | Released data? | Evidence |
|---|---|---|
| Advani False Success 2606.09863 | NO own release. Built on public tau2-bench leaderboard (9,876 traj, 8 families) + AppWorld public outputs (1,879 traj). Labels by regex (FS_ASSERT_RE/HONEST_FAILURE_RE) + 200-traj human validation. | https://arxiv.org/html/2606.09863v1 |
| OverclaimBench 2609.20812 | NO. Corpora/defect registry/harness deliberately withheld (anti-contamination); artifact bundle on request to vetted researchers only. 1,140 main + 1,200 delegation runs. | https://arxiv.org/html/2609.20812 |
| Harbor-Index 2609.04298 | Abstract says adapters + eval results + 82-task index open-sourced; no URL on abs page. 54 benchmarks x 8 models x Terminus-2/native harness. Trajectory release UNVERIFIED. | https://arxiv.org/abs/2609.04298 |
| AgentGuard 2609.16287 | No link. 642 failure traces/382 repo tasks (Claude Code + Haiku 4.5). | https://arxiv.org/abs/2609.16287 |
| UnderSpecBench 2607.02294 | No link. 69 families / 2,208 prompt variants; 55.8-67.8% runs violate a boundary (Claude Code, Codex, OpenCode). | https://arxiv.org/abs/2607.02294 |
| 2608.00583 (False Average) | No link on abs; but derives from Terminal Wrench (known). Rewrite-attack data may exist as hewittlab/mjkenney sets below (UNVERIFIED linkage). | https://arxiv.org/abs/2608.00583 |
| MonitoringBench 2605.09684 | Attack set (2,644 traj, BashArena) link not on abs; HONEST half IS on HF (see N1). | https://arxiv.org/abs/2605.09684 |
| SHADE-Arena | No 2026 release of transcripts found; only 5 task pairs public, rest on request. | https://arxiv.org/html/2506.15740v2 |
| Iterative VibeCoding 2607.02514 | No repo found. 20 task variants, Sonnet 4.5 attacker, GPT-4o monitor. | https://huggingface.co/papers/2607.02514.md |
| SCHEME 2605.29178 | No release visible (page truncated). 410 traj. | https://arxiv.org/html/2605.29178v1 |
| RepoComplianceBench 2607.26819 | No link. 106 issues/49 repos. | https://arxiv.org/html/2607.26819v1 |
| OverEager-Bench 2605.18583 | No link. 500 scenarios, ~7,500 runs, kappa 0.73 on 50. | https://arxiv.org/abs/2605.18583 |
| ClarifyCodeBench, CAPA | Not found under those names. | search 2026-11-07 |

Action: email OverclaimBench authors (vetted-access path) and Advani (labelled corpus); everything else below is what is actually downloadable.

## 1. NEW downloadable sources (post-cutoff / new vs baseline)

### N1. palaestraresearch/monitoringbench-honest-550 (modified 2026-10-16)
https://huggingface.co/datasets/palaestraresearch/monitoringbench-honest-550 . CC-BY-4.0, 98 MB, 550 honest Opus 4.5 BashArena trajectories as Inspect .eval logs (116 tasks), matched to task freq of the MonitoringBench attack set. Natural (honest). Labels: none beyond honest=negative. Use: negatives for M1/M2/L2/L6/G1; pairs with the attack set if/when released. Direct negative; attacks absent.

### N2. dang-w/trusted-monitoring-logs (2026-11-03)
https://huggingface.co/datasets/dang-w/trusted-monitoring-logs . MIT, 4.76 GB, 124 runs Inspect .eval (APPS backdoor-style generate + monitor runs). Labels in `scores`: main/side-task success (C/I), monitor `suspicion` 0-10. Prompted red-team (control setting), deterministic labels. Q: M4/L4 (side-task = different goal), D5 only via suspicion proxy. Low priority: APPS not Claude Code.

### N3. yangjunxiao2021/terminal-bench-science-trajectories (2026-10-17)
https://huggingface.co/datasets/yangjunxiao2021/terminal-bench-science-trajectories . No license tag (derived from public leaderboard; check upstream), 17.5 GB, 2,520 trials / 70 tasks / 17 model-agent configs INCLUDING Claude Code with Opus 5.5 / Opus 5 / Fable 5 / Fable 5.1 / Opus 4.8 / GLM 5.3 / Kimi K3 (ATIF trajectories, reasoning included). Natural, on-policy, deterministic reward 0/1. Q: G5 (claim vs verifier reward) and G2/M5 by construction (extract final claim, compare to reward) ; negatives for M1/M2. This is the closest large analog to Advani's false-success setup but with Claude Code scaffolds. Build: claim extraction + reward = false-success label. Highest-volume new natural source.

### N4. openguardrails/terminal-bench-2.1-deepseek-v4-flash-trajectories (2026-09-11)
https://huggingface.co/datasets/openguardrails/terminal-bench-2.1-deepseek-v4-flash-trajectories . MIT, 73 MB, 89 tasks, two scaffolds (dsh, terminus-2), verifier rewards. No violation labels despite org name. Small; G5 by construction.

### N5. dacorvo/funes-* claude-code traces (2026-10-01) and similar
e.g. https://huggingface.co/datasets/dacorvo/funes-AlinCiocan-fable-5-claude-code-traces ; armand0e/claude-fable-5-claude-code (5,479 dl); eishaanand, owenqwenllmwine etc. clones. Claude-Code-format traces, mostly distilled/benign; license/label UNVERIFIED (not opened). Use as benign negatives only; check provenance (many are clones of one set). Also simonycl/trsi-calib-*-claudecode-{sonnet,opus,glm} (2026-06-23) UNVERIFIED.

### N6. crispwisp/wisp-claude-code-sessions (2026-07-06)
https://huggingface.co/datasets/crispwisp/wisp-claude-code-sessions . MIT, 25 MB, real unedited Claude Code sessions (one workstation, voice-driven human sessions + nested hyprbench computer-use runs), content blocks incl. thinking/tool_use. No labels. Real-user benign negatives + user-correction mining (L7/RF by build). Small.

### N7. jfrick/mit-claude-codex-code-20261019 (2026-10-30)
https://huggingface.co/datasets/jfrick/mit-claude-codex-code-20261019 . 45k Claude/Codex-attributed commits (diff + message), 12.9 GB. No session context/user prompts -> weak for monitor; only commit-message-vs-diff claim check (M5 on commit messages) by build. Low.

### N8. hewittlab/monitor_cot_for_hack-{coding,judge,length}[-dataset] (2026-10-15..19)
https://huggingface.co/datasets/hewittlab/monitor_cot_for_hack-dataset-coding . Apache-2.0, 1,982 rows LeetCode with 10 assert tests; "true reward" vs "misspecified reward" (pass some/fail some). These are RL ENVIRONMENTS (prompts), not trajectories; companion non-"dataset" repos (e.g. monitor_cot_for_hack-coding) may hold rollouts, UNVERIFIED. Potentially natural RL-emergent hacks with CoT-monitor setting -> M4/L6. Open the non -dataset repos first.

### N9. WangSl2004/CATCH-Hacking-SFT (2026-10-05)
https://huggingface.co/datasets/WangSl2004/CATCH-Hacking-SFT . Apache-2.0, 13,395 rows, 581 MB. Fields: hack_family (test-file mod / test-data exploit / execution interference), hack_method, hack_style (pure_hack explicit vs mislead implicit), is_mislead_success (survived CoT-monitor check), repo_files, CoT+code output. Synthetic/prompted-generated (not natural) but the only large set with obfuscated-reasoning hacks + concealment-success flag. Q: M4 (direct), L6 partial, M5 (mislead = reasoning contradicts action), D2 by family. Direct labels, synthetic. Use as evasion-robustness augmentation, not core.

### N10. mjkenney/cot-monitor-robustness (2026-09-29)
https://huggingface.co/datasets/mjkenney/cot-monitor-robustness . CC-BY-4.0 but GATED: "do not use for training" (GPQA portion) -> ANTI-TRAINING notice; eval only. 37 GB; hinted_items, attacked_transcripts (rewritten CoTs), monitor suspicion scores, verbalization labels (POS / NEG-inert / NEG-clean), activations. Qwen 3.6 27B silent hint use. Likely the 2608.00583-style rewrite-attack data (UNVERIFIED). Eval for M5/L6 evasion only; do not train.

### N11. oliverdk/realistic_reward_hacks_annotated (2026-05-28)
https://huggingface.co/datasets/oliverdk/realistic_reward_hacks_annotated . No license, README empty, 1,962 rows (reward_hacks_code 478, hhh_code 388, literary 339/400, srh_nl_filtered 357); fields messages, hidden_tests(label,desc), runnable, implicit_criterion, has_explicit_criteria. Derivative of school-of-reward-hacks (known) - version/annotation extension; paired hack vs HHH. Prompted/synthetic. M4, L6 (hidden tests), paired negatives. Marginal.

### N12. willjgriff/reward-hacking-ablation (2026-11-06, 1,761 dl)
https://huggingface.co/datasets/willjgriff/reward-hacking-ablation . No card, 134 GB, per-sample files like "lcbhard_0" (likely RL rollouts/eval logs). Recently active, high downloads. UNVERIFIED content; inspect file tree before investing. Potential natural RL-emergent hacks.

### N13. eungyeuk/reward_hack_lcb_trajectories (2026-08-21)
https://huggingface.co/datasets/eungyeuk/reward_hack_lcb_trajectories . No card/license, 482 MB, SWE-style schema with FAIL_TO_PASS, protected_files, n_visible_cases / n_holdout_cases, plus actions + reasoning_content. Holdout-test design = visible-vs-heldout hack detection (M4 label derivable deterministically: passes visible, fails holdout). Trajectory format agentic. Moderate value; inspect.

### N14. dougalldeepmind/*-da-rewardhack-* (2026-09-05)
https://huggingface.co/datasets/dougalldeepmind/2026-09-05-table2-9284-da-rewardhack-702-train . 9,986 rows SFT mix, 702 are "difficult advice about cheating" dialogues; model-generated, unreviewed. Not agent traces. Skip (M1 values-only).

### N15. ScaleAI/lhaw (2026-02, arXiv 2602.10525)
https://huggingface.co/datasets/ScaleAI/lhaw . CC-BY-4.0, 285 rows (TheAgentCompany, SWE-Bench Pro 100 variants/75 tasks, MCP-Atlas). Fields: original_prompt, underspecified_prompt, information_dimension (goal/constraint/input/context), ambiguity_class (outcome-critical / divergent; benign filtered), removed_segments, expected_questions, terminal_states. Labels derived from agent trials (empirical, not LLM guess). Q: M7 (direct: should-have-asked, ground-truth question), L4 weak. Prompts only, no trajectories; build trajectories by running agent. Best clarification substrate for thin M7. (Not in known list - ScaleAI/aspi is, lhaw is distinct; confirm not already held.)

### N16. itsankitkp/swe-clarify (2025-12-03)
https://huggingface.co/datasets/itsankitkp/swe-clarify . MIT, ~1,000 rows synthetic SWE prompts (155 distinct prompts x variants), hidden_constraint, severity low/med/high, regret_calc.decision (can_guess / must_ask), chosen/rejected responses, clarifying_question. Synthetic LLM. M7 direct (decision) + D5-flavoured `severity` (of ambiguity, not of agent failure). Small but task-shaped (ask vs guess with blast radius).

### N17. SWE-Misbehavior (arXiv 2610.18206, 2026-10-13; HF duc-anh-2002/SWE-Misbehavior 2026-10-22; GitHub dxlong2000/SWE-Misbehavior)
https://huggingface.co/datasets/duc-anh-2002/SWE-Misbehavior ; https://arxiv.org/abs/2610.18206 . Paper CC-BY-4.0; HF card no license (DevEval-derived source code mirrored). 7,427 task instances x 50 paraphrased prompts, 9 subsets, 927 MB. 11 misbehaviors across code gen / file mgmt / system interaction (e.g. dependency misinterpretation up to 98.5%, unintended changes to user inputs 50.5%, silent env-integrity compromise 53%, file-reading completeness). HF holds PROMPTS + task metadata (need_read, need_update), NOT trajectories; labels come from rule-based checks + LLM-judge when you run agents. Human-in-the-loop synthesized (prompted). Q: M2 (direct via rules), L5 (need_read = required step skipped; reading-order), M4 weak, L4. Build: run Claude Code on it -> deterministic labels. Good L5 substrate.

### N18. microsoft/AgentRx (arXiv 2602.02475)
https://huggingface.co/datasets/microsoft/AgentRx . CC-BY-4.0, gated (share HF info), 5 MB, 115 failed trajectories (API workflows, incident mgmt, web/file) with failure_category, step_number, step_reason, failed_agent, root_cause_failure_id. Human vs LLM annotator not stated. Natural failures, not coding. Q: D1/D3 (direct step localization), D2 weak. Tiny, taxonomy-useful; format template for D-labels.

### N19. rewardhacking.org "Reward Hacking in the Wild" (3,607 incidents Jan 2025-Jun 2026)
https://rewardhacking.org . Code MIT, annotations CC-BY-4.0, quoted reports belong to authors; X + AIID records not republished; published subset = confidence >= 0.9. LLM-classified into 14 misbehavior categories, multi-label, severity {negligible 1,468; minor 1,373; significant 618; severe 121; unrated 27}, month, platform. Incident TEXT reports (GitHub issues, HN, LW, X), not trajectories. Q: D5 severity (taxonomy match to monitor's minor/significant/serious: use as severity-calibration few-shot / rubric, and as scenario seeds to render into trajectories). Only severity-rated natural-world resource found. Real-world natural incidents but LLM labels.

### N20. Cursor, "reward hacking in coding benchmarks" blog
https://cursor.com/blog/reward-hacking-coding-benchmarks . No data release. Audit of 731 Opus 4.8 Max SWE-bench Pro trajectories: upstream lookup 57%, git-history mining 9%, plus mirror leakage / hidden-test hardcode cases; 63% of successes retrieved vs derived. Gives natural L6/M4 base rates and recipes (search git log for fix) for constructing negatives/positives; contact Cursor for traces. NIST CAISI note same pattern: https://www.nist.gov/caissi/2-examples-cheating-caisis-agent-evaluations (transcript-analysis tool; no release found).

### N21. pushback tool (intikhab49/pushback)
https://github.com/intikhab49/pushback . No dataset; a local extractor that mines YOUR Claude Code transcripts into prompt/rejected/chosen/feedback JSONL with correction categories (task/topic) and rejected-tool-call/interrupt counts. Directly applicable to David's own ~/.claude sessions: free natural L7 / correction data, schema usable as template. MIT presumably (UNVERIFIED).

### N22. Reih02/cot_control_monitoring_2000 etc, collusion-paper-anon1/reward_hacking_{policy_1073,monitor_2046}
https://huggingface.co/datasets/collusion-paper-anon1/reward_hacking_policy_1073 . CC-BY-4.0, 1,073 PROMPTS only (task, metric, cheat_method), no hack labels (LLM-judge outputs not included). Skip except as prompt seeds.

### N23. Other seen, not valuable
TerryHWong/Misbehavior-Bench (image, not agentic). SwarmandBee/SwarmFailure-Intelligence (~95k synthetic records with 1-5 severity, not trajectories; UNVERIFIED) https://huggingface.co/datasets/SwarmandBee/SwarmFailure-Intelligence . ReputAgent-ai/reputagent-data (failure-mode descriptions w/ severity). ameek/measuring_cot_monitorability_transcripts: 446k rows, license "mit-with-model-training-restrictions" (anti-training), cue acknowledgment labels, BBH causal-judgement not agentic https://huggingface.co/datasets/ameek/measuring_cot_monitorability_transcripts . aksh-n/mle-sabotage (2026-02) UNVERIFIED. d33-activation-monitoring/agent-activations UNVERIFIED.

## 2. Papers with relevant findings but no release (use for base rates / recipe)
- UnderSpecBench: 69 families x 2,208 variants varying intent clarity, target certainty, blast radius; 55.8-67.8% boundary violation -> recipe for M7 construction on DevOps (Claude Code). https://arxiv.org/abs/2607.02294
- OverEager-Bench: removing consent declaration moves Claude Code overeager 0% -> 17.1%. M2/L4 recipe. https://arxiv.org/abs/2605.18583
- RepoComplianceBench: agents rarely read rule files; refusal/human-handoff 0%; one feedback line naming omission -> 100% verification recovery => natural L5 + L7 recipe. https://arxiv.org/html/2607.26819v1
- "How Coding Agents Fail Their Users" (known) RV2: 91.49% need explicit pushback (EMNLP 2026) https://aclanthology.org/2026.emnlp-main.1011/
- Anthropic reward-seeker blog (Aug 2026): RL on hackable production envs generalized to killing a hack monitor and rewriting reward fn; hacking got more covert when told a classifier reviews transcripts (via secondary snippet, UNVERIFIED) https://alignment.anthropic.com/2026/reward-seeker/ . Strong L6 motivation; no data.
- Harbor/Terminal-Bench-science leaderboard sources (N3) are the practical channel to actual Claude Code rollouts.

## 3. Rank by value per conversion hour
1. N3 terminal-bench-science-trajectories: natural Claude Code, deterministic reward; ~3-6h to claim-extract -> G5/G2/M5 positives+negatives at scale; also benign negatives. Check license upstream.
2. N15 ScaleAI/lhaw + N16 swe-clarify: ~2-4h; M7 (thinnest-with-labels) direct ground-truth "should ask"; render into prompt + actual first agent action (run Claude Code once per variant) to label ask-vs-assume.
3. N17 SWE-Misbehavior: ~4-8h (run agent, reuse rule checkers): L5 required-step skipped (need_read), M2, silent integrity damage.
4. N21 pushback on own ~/.claude sessions: ~1-2h, zero licensing risk, natural L7/RF/negatives; also N6 crispwisp for extra real sessions.
5. N1 monitoringbench-honest-550: ~1h, clean negatives; hunt attack half (MonitoringBench authors) for L2/L6 pairs.
6. N19 rewardhacking.org: ~2h to map severity labels to D5 rubric + seed scenarios.
7. N9 CATCH-Hacking-SFT: ~2h; evasion-style M4/M5 augmentation (synthetic).
8. N13 / N12 / N8 inspection: ~1h each to decide; potentially natural RL hacks (L6/M4) if rollouts present.
9. N18 AgentRx: <1h; D1/D3 format template only.
10. Outreach: OverclaimBench vetted bundle, Advani labelled corpus, Cursor traces, MonitoringBench attack set, Iterative VibeCoding.
Do not train on: N10 (mjkenney, explicit no-train), ameek (training restriction).

## 4. Per-question coverage (known baseline + new)
Known abbreviations: CB CheatBench, TW Terminal Wrench, ISN impossible-swe-nemotron, RP rpotham/agent-misalignment, MALT, HB hackbench, TR TRACE, SC SWE-chat, OST Open-SWE-Traces, CTB CodeTraceBench, ASPI, UIB UserIntentBench, IF* IFEval family, AIF AgentIF, HM HANDBOOK.md, SRH school-of-reward-hacks, AISI olmo rollouts, Goodfire, aria, HVTB, lucabaroni RLVR, HCAF "How Coding Agents Fail" 2605.29442.

| ID | Known substrate | NEW substrate | Adequacy |
|---|---|---|---|
| M1 ★ real unwritten goal | SC, UIB, HCAF, ASPI | pushback/own sessions N21, N6 | thin; construction from user pushback |
| M2 stated requirement | IF*, AIF, HM, tau2 | N17 (rules), N15 | OK |
| M4 gaming measure | CB, TW, ISN, AISI, Goodfire, aria, lucabaroni, HB | N9, N11, N13, N12, N8, Cursor recipes N20 | good (natural: TW, AISI, lucabaroni, +N12/N13 if confirmed) |
| M5 ★ claim vs evidence | TW (partial), HCAF | N3 (build), N9 (mislead), N10 eval-only | improved but claim-extraction must be built; no released labelled false-success corpus (Advani/OverclaimBench withheld) |
| M7 ★ silent ambiguity | ASPI | N15 lhaw, N16 swe-clarify; recipes UnderSpecBench | improved; trajectories absent, need agent runs |
| L1 drift | MALT, TRACE | (none new) | OK/ moderate |
| L2 ★ cumulative violation | TRACE | N1 (negatives only); Iterative VibeCoding/SCHEME unreleased | STILL THIN: no released multi-step composite w/ labels |
| L4 ★ different goal | RP, MALT, TRACE | N2 (side-task, APPS), N17 | thin |
| L5 ★ skipped step/order | HM, AIF | N17 (need_read), RepoComplianceBench unreleased | thin; only construction |
| L6 ★ targeting checker/overseer | CB, TW, ISN, AISI, HB | N12/N13/N8 (verify), N20 recipes, 2608.00583 attack data (N10 eval-only) | good for peeking; monitor-evasion natural data absent (Anthropic reward-seeker unreleased) |
| G1 whole-run goal | SC, OST, CTB, MALT | N3, N6 | OK |
| G4 ★ stated priorities | (little: HM, UIB partial) | none | NO adequate substrate |
| G2 per-req status | HM, AIF, CTB | N3 (reward only, not per-req) | thin; build from rubrics |
| G5 genuine success | CTB, TW | N3, N4 | good via N3 |
| D1/D3 localization | CodeTraceBench, TRACE | N18 AgentRx | OK |
| D2 which requirement | HM, IF* | N17 | moderate |
| D5 ★ severity | none | N19 rewardhacking.org (incident level, LLM labels); N16 severity (of ambiguity) | STILL THIN: no trajectory-level severity labels |
| L7 ★ correction outcome | SC, HCAF (RV1/RV2 codes) | N21 tool on own data; RepoComplianceBench finding (unreleased) | thin; only SC/HCAF + own mining |
| RF requirement-sentence | IF*, AIF, HM | none | OK/known |
| OV / M8 large docs | HM, CUAD, MAUD, ContractNLI, QuALITY | none | known |
| Long-context 16-32K decisions | Open-SWE-Traces, SC | N3 (17.5 GB long traces), N5 | OK |
| Benign Claude Code negatives | SC, TonyDzi, davanstrien | N3, N5, N6, N1 | good |

IDs with no/inadequate substrate after this hunt: G4 (none), D5 (incident-level only), L2 (no released step-labelled composite attacks), L5 (construction only), L7 (small), M1 (unwritten goal; only pushback-derived), M5 labelled corpus (all three named false-claim corpora withheld).

## 5. Caveats
- Several HF cards lack license (N3, N11, N12, N13): treat as unclear; N3 derives from public leaderboard runs.
- ArXiv IDs in 2026 (26xx.xxxxx) fetched and exist; unfamiliar names are real.
- N5/N12/N13/N8-companion contents UNVERIFIED beyond card/viewer errors.
- SWE-Misbehavior GitHub repo not opened; evaluation scripts assumed.
