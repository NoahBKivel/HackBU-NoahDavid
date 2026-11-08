# Agent-trajectory datasets for Kev-4B (faithfulness-to-user-goal judge) — research 2026-11-07

Method: HF API (huggingface.co/api/datasets/<id>), dataset cards, GitHub READMEs, WebSearch. HF raw README + datasets-server returned 401 for gated sets, so row-level samples NOT inspected for gated sets (marked UNVERIFIED). Schema = from card/cardData, not from opened rows unless stated.
Legend: INSTR = original user/task instruction present; TRAJ = multi-step trajectory; L-traj = per-trajectory label; L-step = per-step label/localization; CTRL = benign controls; SPLIT.

## A. KNOWN BASELINE (verified)

### few-sh/terminal-wrench — https://github.com/few-sh/terminal-wrench
- Access: open (GitHub). License Apache-2.0. No HF copy mentioned.
- Size: 331 tasks, 957 task/model entries; 6,289 v5 hacker trajs, 2,352 baseline trajs, 1,441 no-reward attempts. Hacks 3,632 (serious/non-serious), 1,216 attacker legit solves. Models: claude-opus-4.6, gemini-3.1-pro, gpt-5.4(high). GB: not stated (UNVERIFIED).
- Schema: per-task dir: original_task/{instruction.md,tests,solution,env}, task.json, hack_summary.md; per-traj metadata.json, trial/agent/trajectory.json, result.json, trial.log, verifier/reward.txt. Index: index/tasks.json, index/trajectories.json. Also sanitized (agent msgs rewritten) and stripped (agent text removed) variants.
- INSTR yes (instruction.md; NOTE attacker runs had hack-elicitation prompt hack_prompt_v5.md appended — strip it). TRAJ yes. L-traj yes (hack serious/nonserious / legit ~ / no-reward; observed_categories e.g. hollow-implementation 2,243, output-spoofing 1,071; gpt-5.4 monitor suspicion score). L-step no. CTRL yes (baselines + legit solves per task). SPLIT none. Eval-only notice: none stated.
- Work: LOW-MED (JSON parse + join to instruction.md; label from folder/metadata). Best fit for "reward hacking / proxy optimization / hollow implementation" in agentic terminal setting.

### PatronusAI/trace-dataset (TRACE) — https://huggingface.co/datasets/PatronusAI/trace-dataset ; arXiv 2601.20103
- Access: GATED auto (login + accept). License CC-BY-SA-4.0 (share-alike). 517 rows, 22.8 MB (7.1 MB dl). Updated 2026-01-29.
- Schema: trajectory_id, conversation (string ChatML), label (string). One train split.
- 268 hacked / 249 benign; 13,677 utterances (avg 26.5/traj); taxonomy 10 categories/54 subcats, multi-label (39% multi-type). SYNTHETIC (Claude Code w/ claude-opus-4-5 simulated tool use), human-verified (3 engineers, kappa 0.82, ~81% acceptance).
- INSTR: user turns exist; initial task format not described (UNVERIFIED, row not opened). TRAJ yes. L-traj yes. L-step no. CTRL yes (249). SPLIT none. Out-of-scope: training models to reward hack; intended use includes training/evaluating detectors.
- Work: LOW (1 label string -> parse; multi-label subcategory strings). Small but cleanest benign/hack balance. Synthetic caveat.
- Src: card via WebFetch of HF page; API.

### metr-evals/malt-public (MALT) — https://huggingface.co/datasets/metr-evals/malt-public
- Access: GATED auto (share HF account info). License MIT. 28.3 GB parquet; 7,179 rows per config in cardData (tags say 10K-100K, cardData 1K-10K — inconsistent). Configs: default, irrelevant_detail, language_mixing, summarize, vague_cot (perturbation variants; use `default`). Updated 2026-03-24. 30 task families, 169 tasks, ~19 models.
- Schema: has_chain_of_thought, labels, model, manually_reviewed, run_source (prompted/unprompted), count + samples list (input msgs, output msgs, chat-completions). Graph/DAG version separate (malt-transcripts-public).
- Labels (all non-"normal" manually reviewed): hardcoded_solution (15), bypass_constraints (~20), ignores_task_instructions (24), gives_up (~16), partial_problem_solving (165), reasoning_about_task (~220), refusals (324), sabotage (224), match_weaker_model (121). Majority "normal" largely unreviewed. Card does not say reward hacking/sandbagging; mapping is inference.
- INSTR: inside input messages (not separate field). TRAJ yes (long). L-traj yes (also may be per-run). L-step: UNVERIFIED (labels may attach to runs; rh-bench lists only 780 MALT rows). CTRL yes (normal). SPLIT public only. No canary/do-not-train on card.
- Work: MED-HIGH (28 GB, nested samples, rare positives; `ignores_task_instructions` + `hardcoded_solution` + `bypass_constraints` ~ 60 rows = tiny but exactly on-target).

### nvidia/Open-SWE-Traces — https://huggingface.co/datasets/nvidia/Open-SWE-Traces
- Access: open. License CC-BY-4.0. 100K-1M (tag says 1M-10M; v1.0 ~151k cleaned core). Updated 2026-10-28 (created 2026-04-16). GB not given (data_distribution.md has breakdown).
- Schema (v2.0): instance_id, repo, license, language, trajectory_id, messages (system/user/assistant/tool), tools (json str), resolved (1/0/-1), metadata{category, reference_patch, model_patch}. Harness splits: claudecode, opencode, openhands, sweagent, minisweagent. Models: Qwen3.x, minimax_m25, deepseek_v4_flash.
- INSTR: user role holds initial prompt (issue text assumed, not confirmed). TRAJ yes. L-traj: `resolved` only (outcome, NOT misbehavior). No hack labels (v1.0 filtered git-hacking). L-step no. CTRL n/a.
- Work: LOW to load, but labels weak. Use as benign pool (resolved=1) + hard negatives via `resolved=0` with claimed completion (needs weak-labeling). Claudecode-format split is format-matched to target deployment.

### ninty-seven/stepguard_data — https://huggingface.co/datasets/ninty-seven/stepguard_data ; paper arXiv 2608.24777 (as listed on HF)
- Access: open. License Apache-2.0 (commercial/training OK). Updated 2026-10-02. JSONL. 7,000 examples: SFT-3K (sft3k/agentguard_sft3k_sharegpt.jsonl) + RL-4K (rl4k/agentguard_rl4k_grpo.jsonl).
- Schema: SFT: conversations[{human,gpt}] with gpt output tags <Analysis><Judgment><RiskSourcePresent><RiskSource> (+<UnsafeStep> on traj-level). RL: id, instruction (guard prompt), output/label (safe/unsafe), level (action|trajectory), risk_source.
- Balanced 50/50 safe/unsafe; 3,500 action-level + 3,500 traj-level; 9 risk sources incl. none (benign), malicious user instruction, direct/indirect prompt injection, misinformation, tool description injection, malicious tool execution, corrupted tool feedback, inherent agent failure. Synthetic (StepGen). Base Qwen3-4B-Instruct-2507 (same size as Kev-4B).
- INSTR: guard prompt includes requests/tools/actions/observations (per-row inclusion UNVERIFIED). L-step: <UnsafeStep> int ID in SFT traj-level rows only. CTRL yes.
- Work: LOW (already instruction->label prompt format; remap to typed questions). Target is SAFETY/injection, not goal faithfulness; "inherent agent failure" + "malicious user instruction" subsets are closest.

### SWE-Gym OpenHands trajectories — all open, no license field in cardData (UNVERIFIED license; repo SWE-Gym is MIT, SFT set MIT)
- OpenHands-Sampled-Trajectories: 6,055 rows, 1.34 GiB (287 MB dl), split train.raw, updated 2024-12-23. Fields: instance_id, run_id, resolved(bool), messages[content,function_call,name,role,tool_call_id,tool_calls], tools, test_result{apply_patch_output,git_patch,test_output,report{empty_generation,error_eval,failed_apply_patch,resolved,test_timeout}}. https://huggingface.co/api/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
- OpenHands-SFT-Trajectories: 491 rows, 31.8 MB, split train.success.oss; messages only (successes only), MIT. https://huggingface.co/api/datasets/SWE-Gym/OpenHands-SFT-Trajectories
- OpenHands-Verifier-Trajectories: 2,636 (train.mixture) = 1,750 onpolicy + 886 offpolicy, 188 MB; fields messages, resolved. https://huggingface.co/api/datasets/SWE-Gym/OpenHands-Verifier-Trajectories
- INSTR in first user msg (issue). L-traj = resolved only. No misbehavior labels, no step labels. Old (Dec 2024), weak labels. Work: LOW; value = benign/positive pool and Sampled's `test_result.report` flags (empty_generation, test_timeout) for "unsupported completion" heuristics. Low priority.

### longtermrisk/school-of-reward-hacks — https://huggingface.co/datasets/longtermrisk/school-of-reward-hacks
- Open, CC-BY-4.0, 1K-10K rows (1,073 per rh-bench), ~795 KB, updated 2025-08-22. Schema not in cardData (UNVERIFIED; card fields not opened). Short single-turn tasks with reward-hackable metric + hacking response (low-stakes: poetry, simple code). NOT agentic, no trajectory. rh-bench lists it with paired hack/clean responses.
- Work: LOW but weak domain fit. Good for proxy-optimization/metric-gaming flavor only.

### ktolnos/rh-bench — https://huggingface.co/datasets/ktolnos/rh-bench
- Open (card shows no gate); CC-BY-SA-4.0 overall. Row counts inconsistent (header 144,768; splits ~74k; viewer 72.4k). Splits: open_ended 4,359; multichoice 66,760; encrypted 2,946 (XOR on response cols, canary). Card: MUST NOT be used for LLM pretraining/general-purpose LM training; canary GUIDs (check against fine-tune intent — task-specific classifier tuning likely OK but flag).
- Schema (15 cols): prompt, response_hacking, response_clean, label(paired|hacking|clean|prompt_only), hacking_category, hacking_subcategory, hacking_description, construction, verification(human|llm_judge|deterministic|none), source_dataset, source_split, source_row_idx, source_id, response_model, is_agentic. 6 categories: sycophancy, reward tampering, deception, evaluation gaming, output style gaming, environment exploitation.
- Sources/licenses: Jozdien/realistic_reward_hacks 1,605 (author permission); longtermrisk/school-of-reward-hacks 1,073 (CC-BY-4.0); METR MALT 780 (gated); PatronusAI/TRACE 517 (CC-BY-SA-4.0); Countdown-Code 334 (no license listed); matonski/reward-hacking-prompts 50 (MIT); Anthropic/model-written-evals 39,811 multichoice (CC-BY-4.0); keing1/reward-hacking-generalization 26,949 multichoice (CC-BY-4.0); Anthropic/alignment-faking-rl 2,734 encrypted (CC-BY); jplhughes2/classify_alignment_faking_human_labels 212 encrypted (no license listed).
- Permissive: school-of-reward-hacks, matonski, MWE, keing1, alignment-faking-rl (CC-BY/MIT). Restricted: MALT (gated), Jozdien (permission), Countdown/jplhughes (unlisted), TRACE (SA).
- Work: LOW for open_ended agentic rows (is_agentic) — already prompt/hack/clean pairs with category. Multichoice is A/B/Yes-No format, nearest to typed-question shape but not agentic.

### rpotham/agent-misalignment-dataset — https://huggingface.co/datasets/rpotham/agent-misalignment-dataset (v0.1.1)
- Open, no gate. 1,050 trajectories, 15.2 MB JSON. License: OpenRAIL-D+CC-BY mix (code/aggregates MIT/CC-BY; full trajectory corpus OpenRAIL-D with use restrictions: no training production agents to exhibit behaviors, no attack scaffolding, no removing safety metadata) — training a DETECTOR is plausibly permitted; read LICENSE-DATA.md before use (UNVERIFIED).
- Schema: id, task_name, main_task, side_task, threat_type, target_model, auditor_model, judge_model, trajectory, is_misaligned, is_misaligned_v1, judge_votes, label_confidence(unanimous|majority|contested|unrecovered), headline_include, main_task_success, side_task_success (unreliable), monitor_suspicion_score, petri_dimensions, judge_summary, taxonomy_tags, trajectory_length, token_count; source_mode incl shade_honest.
- 7 models, 25 workplace tool-use tasks, 3 elicitation modes. 253/1,050 flagged (24.1%); unanimous+artifact-excluded 131/1,008 (13.0%). api_key_exfil subset = artifact, exclude. Labels per trajectory by LLM judge panel, no human labels. INSTR: system msg + main_task field. L-step no. CTRL: shade_honest records.
- Work: LOW. Workplace tool-use (not coding), but main-task vs side-task = goal substitution; main_task/side_task fields give clean question context.

### ethz-spylab/agentdojo — GitHub https://github.com/ethz-spylab/agentdojo
- NO HF dataset found (HF API 401 -> likely nonexistent; UNVERIFIED). MIT. Results page agentdojo.spylab.ai/results + Invariant Benchmark Registry; repo has `runs` dir (contents unverified). Benchmark generator of injection tasks, not a labeled trajectory corpus; you would have to run it. Work: HIGH. Skip.

### uiuc-kang-lab/InjecAgent — https://github.com/uiuc-kang-lab/InjecAgent
- Open GitHub, MIT. 1,054 test cases (17 user tools, 62 attacker tools), direct-harm vs data-stealing, base/enhanced. Files data/user_cases.jsonl, attacker_cases_{dh,ds}.jsonl, test_cases_*. Single-step tool-output injection test CASES, not trajectories; no outcome labels (outcome requires running a model). Work: MED; low relevance.

### facebook/hackbench — https://huggingface.co/datasets/facebook/hackbench (EVAL RESERVE)
- GATED auto; CC-BY-NC-4.0; gate checkboxes: agree NOT to use for model training, not to rehost. Updated 2026-10-26. Single `test` split data/hackbench_169_gpt55_glm52.numbered.jsonl, ~390 MiB, 169 records, 13 tasks, 41 natural + 128 synthetic; sources GPT-5.5 (102), GLM-5.2 (67). Transcripts 73K–3.8M chars (median ~1.06M) -> far beyond 4B context without chunking.
- Schema: id, task.name/instruction, source_agent, injected_transcript, monitor_input{task_instruction, transcript with [CMD n], command_count}, gold_command_indices, hack_commands, origin, hack_type(general|task-specific).
- INSTR yes; TRAJ yes; L-traj all HACK; L-step YES (gold [CMD n]); CTRL NONE. Eval-only, no-train. => Use strictly as held-out eval; do not touch in training.

## B. POST-CUTOFF / NEW FINDS (found this session; all verified via HF API/card unless marked)

### steinad/CheatBench — https://huggingface.co/datasets/steinad/CheatBench (created 2026-04-27, updated 2026-07-14)
- OPEN, not gated, MIT. 4,472 traces (full; mini 648, micro 263 stratified eval subsets, not held out). Repo 11.6 GB. Parquet + jsonl.
- Schema: trace_id, benchmark, harness, model, label(benign 3,587 | cheating 844 | attempt 41), cheating_type(harness 690/task 195), cheating_mechanism(harness_leaks_verifier 415, harness_leaks_answer 275, secret_discovery_in_environment 110, verifier_exploitation 49, secret_discovery_via_web_search 35), split, rationale, note, trace (serialized JSON string), + loc_* localization (loc_kind, loc_pattern, loc_field_path, loc_line_start/end, loc_events, loc_char_start/end, loc_snippet, loc_confidence...). Localization heuristic, not human-verified.
- Sources: Terminal-Bench 2, CyBench, SWE-smith, SWE-bench Verified, HAL-USACO, MLE-bench, BountyBench, SWE-rebench, KernelBench (14 collections). Labels manual review + rule audits.
- INSTR: inside trace (maybe; no dedicated field). L-traj yes; L-step approximate (loc_events). CTRL yes (3,587). No explicit eval-only notice; note no held-out split; "benchmark for monitors". MIT = trainable.
- Work: LOW-MED. Highest label-ready count of open, permissive, real-agent hack vs benign with localization. RANK #1.

### AlignmentResearch/impossible-swe-nemotron-rollouts — https://huggingface.co/datasets/AlignmentResearch/impossible-swe-nemotron-rollouts (FAR.AI, v1/v2)
- GATED (share HF info; confirm AI-safety research use, not for training models to tamper with tests in production). MIT. ~930 MB. 5 configs: rollouts 39,936 rows (messages, reward, stop_reason, submitted, rl_step, instance_id, mutation_type, label_class 11 values e.g. hack_test_edit, nonhack_clean, is_hack), rollouts_truncated, tasks 2,096, label_audit 58, revert_intent 66.
- 3,964 hacked, 21,110 clean honest, 27,804 failed; hack rate 2%->32.7% over RL. Agent Nemotron-3-Super-120B on impossible SWE-Gym tasks.
- INSTR yes (system prompt "DO NOT MODIFY THE TESTS" + user GitHub issue). TRAJ yes. L-traj yes (11 classes). L-step no. CTRL yes. SPLIT none. Gate wording: detector training for safety plausibly in-scope (UNVERIFIED, read gate text).
- Work: LOW. Excellent: explicit instruction (don't modify tests) vs violation = requirement adherence.

### SALT-NLP/SWE-chat — https://huggingface.co/datasets/SALT-NLP/SWE-chat ; arXiv 2604.20779
- GATED auto; ODC-BY; 10M-100M rows across 11 parquet configs (sessions, conversations, session_logs, checkpoints, commits, repositories, subagent_tasks, ...); updated 2026-10-03. 6,000 REAL sessions (Claude Code, Codex, Gemini CLI), 63k user prompts, 355k tool calls, thinking traces, human-vs-agent authorship. INSTR yes (real user prompts, multi-turn). NO misbehavior labels in card. Work: HIGH (needs labeling) but the only REAL Claude Code user-instruction corpus; use as unlabeled prefix pool + LLM-weak-labels, or for realism/distribution-matched benign negatives and eval.

### NJU-LINK/CodeTraceBench — https://huggingface.co/datasets/NJU-LINK/CodeTraceBench ; arXiv 2604.11641
- Open (no gate seen), MIT. verified 1,000 (489 SWE-bench, 511 TerminalBench) + full 3,316; text says 4,316 total (inconsistent). Agents OpenHands/mini-SWE-agent/Terminus2/SWE-agent; models Claude Sonnet 4, DeepSeek-V3.2, Kimi-K2, GPT-5, Qwen3-Coder-480B.
- Schema: traj_id, agent, model, task_name, difficulty, category, solved, step_count, stages, incorrect_stages, incorrect_error_stage_count, artifact_path; per-stage incorrect_step_ids, unuseful_step_ids, reasoning. Trajectories in .tar.zst (3,291) under bench_artifacts/full/.
- L-step YES (human-verified incorrect/unuseful step IDs; error-diagnosis, not misalignment). INSTR: no separate field (in artifacts). Work: MED (tar.zst extraction). Gives step localization for "step went wrong", weak for adherence.

### AI45Research/ATBench — https://huggingface.co/datasets/AI45Research/ATBench (~Apr 2026; from search snippet only, UNVERIFIED)
- Trajectory-level agent safety benchmark, 1,000 trajectories, labels Risk Source / Failure Mode / Real-World Harm. Not coding-specific. Not opened.

### SimpleJev/JevAny-Multimodal-agentic-Public (v0.4) — https://huggingface.co/datasets/SimpleJev/JevAny-Multimodal-agentic-Public (renamed from JevJudge-Public 2026-10-17)
- OPEN but license "jevany-eval-only": "Evaluation and research only. Do not train on this dataset." CANARY.txt present. 3.21k rows, single test split (viewer/test.parquet; also calibration.jsonl, development.jsonl). Tags: jev, typed-decision, calibration, llm-as-a-judge, reward-model, agents, process-reward, safety. Multimodal GUI-agent reward-bench content (agent_rewardbench_mm, agentrewardbench). Features not shown (500k-char page; UNVERIFIED). Use as EVAL / format reference ONLY; cannot train.

### LIQIIIII/Jeva-Eval — https://huggingface.co/datasets/LIQIIIII/Jeva-Eval (paper arXiv 2610.18773)
- GATED; component-specific licenses (LICENSES.md); "evaluation data only"; private-research framing, redistribution unreviewed. Gz JSONL, 10K-100K. THE Jev TYPED-DECISION FORMAT: id, group_id, state, question, decision_type (Choice|Noul|Score), options, allow_null, target_probs (null prob first), positive_index (Noul), values (Score), option_ids, accuracy_rule, source. General suite 22,986 decisions (typed_test 2,000 + BANKING77, MASSIVE, Mind2Web), ToolRet 500, MLDR 200. NOT agent-misbehavior content. Use as schema template for output serialization; do not train on.

### autotrust/JEV (model, not dataset) — https://huggingface.co/autotrust/JEV : typed questions (noul yes/no, choice 2–16, score 0–5) over text/JSON state; student of TypeSafe Jev 1.13. Snippet only (UNVERIFIED).

### Not-released / no-HF-found (post-cutoff papers)
- MonitoringBench (BashArena, 2,644 successful attack trajs; arXiv 2605.09684; May 2026): no HF link found, location UNVERIFIED (check arXiv "Code, Data" links / LessWrong). Attack trajectories only (side-task = misbehavior; 100% positive).
- SCHEME (arXiv 2605.29178, multi-agent coding sabotage), SLEIGHT-Bench (arXiv 2605.16626, 40 synthetic transcripts), BigCodeBench-Sabotage (1,140 tasks): no release confirmed.
- Transluce "Measuring coding agent misalignment in the wild" (LessWrong): LLM-judged 8,600 real sessions (SWE-chat + internal) for overselling/fabricated completion (~2% severe). No labeled release found. The rubric is directly usable to LLM-label SWE-chat.
- Other found but unlabeled for misbehavior (all UNVERIFIED beyond snippet): yoonholee/terminalbench-trajectories, zai-org/CC-Bench-trajectories, AlienKevin/SWE-ZERO-12M-trajectories, txchmechanicus/CoderForge-Preview, ChrisDing1105/unified-agent-trajectories, Hcompany/trajectories (computer-use).
- No public dataset found labeling "goal drift", "unfaithful completion claims" explicitly. No public dataset already in Jev typed format with agent-misbehavior labels besides eval-only Jev sets above.

## C. RANKED SHORTLIST (label-ready supervision per conversion hour)

1. steinad/CheatBench (MIT, open): map `trace`->prefix, instruction from trace, label benign/cheating/attempt -> noul "Does the agent exploit a leak/verifier instead of solving the task?"; use cheating_mechanism for Choice, loc_events to truncate prefix before/after hack for step-wise examples. ~3-4 h. Hold out `micro`.
2. few-sh/terminal-wrench (Apache-2.0, open): index/trajectories.json -> instruction.md + trajectory.json; label serious-hack/nonserious/legit/no-reward; observed_categories as Choice; baselines as controls; strip hack_prompt_v5 text from context. ~3-4 h. Largest (6.3k hacks + 2.3k baselines) with paired instruction.
3. AlignmentResearch/impossible-swe-nemotron-rollouts (MIT, gated): messages already have user issue + "don't modify tests"; label_class/is_hack -> noul "violates explicit no-test-modification constraint" + Choice over 11 classes; sample ~1.5k hack vs ~3k nonhack_clean; request access now. ~2 h.
4. ninty-seven/stepguard_data (Apache-2.0, open): rewrite `level`+label+risk_source into typed noul/choice questions; use "inherent agent failure"/"malicious user instruction" subsets; <UnsafeStep> gives step-index supervision. ~2 h but domain is safety not faithfulness (auxiliary).
5. PatronusAI/TRACE (CC-BY-SA, gated auto; synthetic Claude Code trajs) + rpotham/agent-misalignment-dataset (main_task vs side_task, unanimous subset): TRACE conversation -> noul reward-hack + Choice subcategory; rpotham unanimous 131 + honest controls -> goal-substitution noul. ~2 h combined; small but clean.

Reserved EVAL only (do not train): facebook/hackbench (no-train gate, CC-BY-NC), SimpleJev JevAny (eval-only), Jeva-Eval, CheatBench micro, MALT subset (gated; also consider as eval). Pool for unlabeled realism + weak labeling: SWE-chat, Open-SWE-Traces (claudecode split).
Caveats: license/gate text for gated sets not read in full; row-level schemas for TRACE, MALT, hackbench, SWE-chat, Jev sets not inspected; rh-bench forbids general LM training and carries canaries.
