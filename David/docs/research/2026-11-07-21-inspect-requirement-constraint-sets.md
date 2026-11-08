# Inspection: requirement / constraint datasets (IF_multi_constraints_upto5, RLVR-IFeval, IFEval, IFBench_test, AgentIF)

Date 2026-11-07. Method: downloaded raw files over HTTPS from the HF `resolve/main` URLs into `...\scratchpad\inspect\constraints\{multi,rlvr,ifeval,ifbench,agentif,code}\` (about 130 MB total, well under the 1 GB cap). Parsed with my own scripts in `...\scratchpad\inspect\tools-constraints\` under `python -I`. Verifier and benchmark code from GitHub (`allenai/open-instruct`, `allenai/IFBench`, `THU-KEG/AgentIF`) was fetched as TEXT via `gh api` and read, never executed. Nothing from any dataset was executed. All counts below were computed from the downloaded files unless marked UNVERIFIED.

Bottom line first:
- IF_multi_constraints_upto5 is the best RF/M2/D2 raw material by volume. Every constraint sentence is stored as a tab-separated list in `constraint`, and 100% of 12,880 sampled segments appear verbatim as substrings of the user prompt (always appended at the END of the prompt). That is free sentence-level RF positives, and the rest of the prompt is the negative pool. It is chat-domain, not coding.
- Per-constraint pass/fail is available and deterministic (apart from `langdetect`) via open-instruct `IFEvalG` / `IFBench` checkers, called per instruction id. open-instruct's `IFEvalVerifier` only returns the mean score, so we would call the instruction classes directly to get the per-constraint vector.
- AgentIF is the closest to our setting (real agent system prompts, 8,561 annotated constraints, 10 Codex-CLI prompts and about 20 further "coding agent" prompts, multi-turn tool trajectories). It is small (707), annotation is noisy, and the license is contradictory (HF: CC-BY-NC-4.0, GitHub data/LICENSE: CC BY 4.0).
- IFEval / IFBench_test are eval-only (541 / 300 rows). They do not mark which text is the constraint, so they serve as held-out verifier-grounded checks, not RF training data.

---

## (1a) allenai/IF_multi_constraints_upto5

### 1) Access / license / notices
- Not gated. Card metadata `license: odc-by`. Card text: "licensed under ODC-BY-1.0. It is intended for research and educational use in accordance with Ai2's Responsible Use Guidelines. This dataset includes output data generated from third party models that are subject to separate terms governing their use."
- No Llama license file and no AI2 ImpACT file in this repo (siblings: README.md, one parquet). The prompts are drawn from Tulu-3 SFT-mix subsets (keys such as `personahub_*`, `ai2-adapt-dev/tulu_v3.9_wildchat_100k_*`, `evol_codealpaca_heval_decontaminated`, `numinamath_tir`, `flan_v2_converted`), so third-party-model-generated prompt text is inherited. Whether any Llama-derived terms bind the underlying prompts: UNVERIFIED (the card does not say so).
- Card: "This is the IF-RLVR training data, with up to 5 constraints per instruction. The constraints are sampled from IFEval (25) and IFBench-Train (29)." The citation block still has `eprint={TODO}`.

### 2) Structure
- One parquet, 72 MB, train split, 95,373 rows. Columns: `key` (string), `messages` (list of {role, content}), `ground_truth` (string), `dataset` (always `"ifeval"`), `constraint_type` (always `"multi"`), `constraint` (string).
- `messages` is always exactly 1 turn, role `user` (checked on all rows for length and on 2,000 rows for role). No system prompt, no assistant turn.
- `ground_truth` is a Python-literal string (NOT JSON): `"[{'instruction_id': [...], 'kwargs': [...]}]"`. Parsed with `ast.literal_eval`. `kwargs[i]` is a dict or None, parallel to `instruction_id[i]`.
- `constraint` is the constraint sentences joined by TAB.
- Constraint count per row on a 5,000 random sample: 1: 1,214; 2: 1,308; 3: 1,202; 4: 936; 5: 340. So about 24% single-constraint, about 25% 4 to 5.
- 54 distinct instruction ids in the sample, roughly uniform at about 250 each for the 25 IFEval ids and the 29 IFBench-train ids (`count:*`, `copy:*`, `letters:*`, `paragraphs:*`, `new:copy_span_idx`, ...), with `combination:two_responses`, `copy:copy`, `copy:copying_simple/multiple`, `detectable_format:json_format`, `combination:repeat_prompt`, `detectable_format:constrained_response` at about 85 to 100 each.

### 3) Two real examples (abridged, verbatim)
Example A (row 0, key `ai2-adapt-dev/tulu_v3.9_aya_100k_79773`, 2 constraints):
```
USER: Identificeer welk instrument een snaar- of slaginstrument is: Kpanlogo, Shamisen. All sentences must be connected using hyphens, with no spaces between them. The last word of your response should be the word brief.
ground_truth: [{'instruction_id': ['detectable_format:sentence_hyphens', 'last_word:last_word_answer'], 'kwargs': [None, {'last_word': 'brief'}]}]
constraint_type: multi
constraint: All sentences must be connected using hyphens, with no spaces between them.<TAB>The last word of your response should be the word brief.
```
Example B (key `ai2-adapt-dev/tulu_v3.9_wildchat_100k_49845`, 4 constraints; prompt abridged in the middle):
```
USER: Delilah is a rich 19-year-old drama student. ... Use specific language. Pace the scene slowly to keep up tension. Include lots of dialogue. Make it long. Be specific about how the mess covers the girls. First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence) In your response, the word text should appear less than 4 times. Include keyword cry once in your response, keyword employer twice in your response. In your entire response, refrain from the use of . (i.e. dots) as punctuation and in general.
ground_truth: [{'instruction_id': ['combination:repeat_prompt', 'keywords:frequency', 'count:count_increment_word', 'punctuation:punctuation_dot'], 'kwargs': [{'prompt_to_repeat': "Delilah is a rich 19-year-old ... Be specific about how the mess covers the girls."}, {'keyword': 'text', 'frequency': 4, 'relation': 'less than'}, {'keyword1': 'cry', 'keyword2': 'employer'}, None]}]
constraint: 'First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence)\tIn your response, the word text should appear less than 4 times.\tInclude keyword cry once in your response, keyword employer twice in your response.\tIn your entire response, refrain from the use of . (i.e. dots) as punctuation and in general.'
```
Observation in B: the TAB segmentation is by constraint instance, not by sentence. The first segment is a two-clause constraint, and a segment can contain several sentences. Another sampled row: "Finish your response with this exact phrase That's all I have to say.. No other words should follow this phrase." is a single segment. Note the `ground_truth` kwargs can embed a copy of the base prompt (`prompt_to_repeat`).

### 4) Verification
- Public verifier: `allenai/open-instruct` (Apache-2.0), `open_instruct/ground_truth_utils.py::IFEvalVerifier`, which reads `ast.literal_eval(label)[0]`, then for each `(instruction_id, kwargs)` builds `INSTRUCTION_DICT[id](id)`, calls `build_description(**non_None_kwargs)` then `check_following(response)`. Registry: `open_instruct/IFEvalG/instructions_registry.py` plus `instructions.py` (58 classes). The standalone `pip install ifbench` package (allenai/IFBench, Apache-2.0) states it ships "83 verifiers in total: 25 classic IFEval keys ... plus 58 IFBench OOD keys". Which of those 58 are the 29 train constraints used here versus the 58 test constraints: UNVERIFIED (README says the 29 IF-RLVR training constraints live in open-instruct `IFEvalG`).
- Per-constraint: YES, structurally. The loop is per instruction, but `IFEvalVerifier.__call__` collapses it to `sum(rewards)/len(rewards)` and returns only a scalar `VerificationResult`. To get the per-constraint vector we would call the instruction classes ourselves (about 10 lines, not written or run here). IFBench's `run_eval.py`/`evaluation_lib.py` (IFBench repo) is the other route; I did not read its output schema (UNVERIFIED).
- Determinism: rule-based string/regex/count checks, deterministic EXCEPT `langdetect.detect` (used by `language:response_language`, `change_case:english_capital`, `change_case:english_lowercase`; grep of `instructions.py` finds no `DetectorFactory.seed`). Short or ambiguous text can flip on repeated calls. UNVERIFIED in practice, but it is how the code reads. Also needs nltk tokenizer data (`word_tokenize`, punkt). Empty response scores 0.
- Caveat in the verifier: the `IFEvalVerifier` applies `remove_thinking_section` and treats an empty answer as score 0. Strictness: IFBench headline metric is "prompt-level loose" (also accepts response with markdown asterisks or first/last line removed). The stricter variant is the default in the training verifier.

### 5) Chat vs agentic distance
Large. Single-turn chat prompt, response is a text artifact, constraints are surface-form output rules (word counts, case, keyword frequency, paragraph structure). No tools, no files, no multi-step state, no system prompt, many non-English base prompts (Dutch in example A). Constraint sentences are machine-templated and stylistically uniform (the "Answer with at most N sentences." style), which a monitor could shortcut-detect as a template, unlike natural human requirements. The "user instruction" is therefore a poor stand-in for a Claude Code prompt; the value is verifiable labels at scale.

### 6) Question IDs and required modifications
- RF (best use). Positives: each TAB segment of `constraint`, which occurs verbatim at the end of the prompt (100% of 12,880 sampled segments; the last segment is the prompt's tail in 5,000/5,000 rows; median start of the first constraint is at about 67% of the prompt's characters). Negatives: sentences of the base prompt before the first constraint segment. Changes needed: (a) split segments (many hold 2+ sentences) into sentences, labelling every sentence inside a constraint segment as positive; (b) the base prompt itself often contains requirements ("Make it long.", "Use specific language." in example B), so negatives from the base prompt are NOT clean; "requirement" here would be unlabelled in the base. Either restrict negatives to base prompts of types with no instruction-like text (math word problems, flan classification) or have an LLM relabel the base sentences; (c) shuffle position (always last) and strip the template-style tell by paraphrasing a fraction of positives, or the model will learn "tail position and IFEval phrasing"; (d) wrap in a Claude-Code-flavoured document (CLAUDE.md or issue text) for distribution realism, which would need synthetic embedding.
- M2 / D2. Need a response per prompt. Sample responses from 1 to 2 models (or from the same model with/without the constraints), run each instruction checker, take the failed instruction id as the violated requirement. Render: the user prompt becomes the "user instruction", the response becomes an agent output (e.g. a Write of a file or a final message). Positives for M2 are rows with at least one fail; D2 per-requirement yes/no comes straight from the per-instruction pass vector with segment i mapped to instruction i. Caveat: `constraint` segments and `instruction_id` list align by position in the examples I saw (A: 2 and 2; B: 4 segments and 4 ids) but I did not verify alignment on every row (UNVERIFIED, though `constraint` splits equal instruction counts in the tested sample is likely; a non-aligned row would show len mismatch, I did not count mismatches). "Direct consequence of a requirement" (the second half of M2) is not represented at all.
- G2. Same pass vector gives done (pass) vs broken (fail); "not done" and "can't tell" need rewrites (e.g. truncated response, or responses for which the checker is non-applicable). The data cannot natively express "not done".
- OV: not applicable (prompts are short: median about 655 characters).
Single-turn text, no actions, so the "action" half of M2 is entirely synthetic.

---

## (1b) allenai/RLVR-IFeval

### 1) Access / license
- Not gated. Card: `license: odc-by`. Repo contains BOTH `ai2_impact_lr_license.md` ("AI2 ImpACT License – Low Risk Artifacts, Version 1.0") AND `llama2_license.txt` ("LLAMA 2 COMMUNITY LICENSE AGREEMENT, Llama 2 Version Release Date: July 18, 2023"). The README text: "Prompts with verifiable constraints generated by sampling from the Tulu 2 SFT mixture and randomly adding constraints from IFEval. Part of the Tulu 3 release." So this is Llama-2-license-attached and ImpACT-attached; stricter than the multi set. Whether the Llama 2 license terms actually bind the prompts (Tulu 2 mix contains model-generated data): UNVERIFIED, but the files being shipped is a flag for legal review before fine-tuning.

### 2) Structure
- Parquet 11.6 MB, 14,973 rows. Columns: `messages` (always 1 user turn), `ground_truth` (JSON string), `dataset` (always "ifeval"), `constraint_type` (24 distinct human-readable names, about 600 to 650 rows each, e.g. "All Lowercase", "Number Paragraphs", "No Commas", "Keyword Frequency", "Postscript", "JSON Format"), `constraint` (the template text, not the instance).
- Exactly ONE constraint per row. No `key` column.
- `ground_truth` is JSON: `{"func_name": "...", "N": ..., "quantifier": ..., "end_phrase": ..., "keyword_list": ..., "word": ..., "forbidden_words": ..., "letter": ..., "i": ..., "first_word": ..., "postscript_marker": ..., "options": ..., "section_splitter": ..., "original_prompt": ...}` with all non-applicable args null. 24 distinct `func_name` values (`validate_lowercase`, `verify_paragraph_count`, `verify_sentence_constraint`, ...).

### 3) Two real examples (verbatim)
Row 0:
```
USER: Describe the purpose of internet protocol version 6 (IPv6).

 Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.
ground_truth: {"func_name": "validate_lowercase", "N": null, "quantifier": null, "end_phrase": null, "keyword_list": null, "word": null, "forbidden_words": null, "letter": null, "i": null, "first_word": null, "postscript_marker": null, "options": null, "section_splitter": null, "original_prompt": null}
constraint_type: All Lowercase
constraint: Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.
```
Row 7777:
```
USER: Tweet: @gellirb64 NOTHING. spontaneity is key. 

Sentiment: positive

Tweet: @Coleen_Skeabeck  Happy belated birthday!!! wow...I can't even remember being 25!!! 

Sentiment: positive

Tweet: A few hours in the office then off to Aberdeen in the sweltering sun. That the gods for air con 

Sentiment: positive

Tweet: @Tifflicious aww hehe cute! 

Sentiment: Answer with at most 33 sentences.
ground_truth: {"func_name": "verify_sentence_constraint", "N": 33, "quantifier": "at most", ...}
constraint_type: Number Sentences
constraint: Answer with at least / around / at most {N} sentences.
```
Note: in row 7777 `constraint` is the template ("{N}", "at least / around / at most"), and the instantiated text in the prompt is "Answer with at most 33 sentences." The template appears verbatim in the prompt for only 33% of 3,000 sampled rows, so `constraint` is NOT a usable span for RF here; the span would have to be recovered by diffing prompt against the base (the base prompt is not provided separately) or by regexing the template.

### 4) Verification
- Old-style open-instruct verifier: `IFEvalVerifierOld` in `ground_truth_utils.py`: `json.loads(label)`, pops `func_name`, looks it up in `IF_FUNCTIONS_MAP` in `open_instruct/if_functions.py` (25 functions), passes the non-null args, returns float. Example source: `validate_lowercase(text) -> text == text.lower()`. One function per row, so per-constraint pass/fail is trivial (one bit). Deterministic except `validate_response_language`, which calls `langdetect.detect` (`if_functions.py` line 139) with no seed.
- Because the old verifier lists only 25 functions, the dataset has about 24 types, one per row.

### 5) Distance
Same as (1a), but even simpler: single constraint appended to a Tulu-2-mix prompt (flan, tweets, math). Good for sanity checks, weak for multi-requirement documents.

### 6) Question IDs and modifications
- M2/D2/G2 with exactly one requirement per prompt: a binary pass/fail per prompt; D2 per-requirement structure degenerates (list of 1). Use as the easy tier of a curriculum or as verifier-validation, otherwise superseded by (1a), which contains the same 25 IFEval constraints with up to 5 per prompt and with instance text in `constraint`.
- RF: insufficient span labels (see above). Only reusable by regex-recovering the instantiated constraint from the template (feasible for the 24 templates, not done here).
- License friction (Llama 2 + ImpACT) gives a reason to prefer (1a) if both are equivalent for our purpose.

---

## (2a) google/IFEval

### 1) Access / license
Not gated; card `license: apache-2.0`. Single file `ifeval_input_data.jsonl` (207 KB). Card links to `google-research/instruction_following_eval` and arXiv 2311.07911.

### 2) Structure
541 rows. Fields: `key` (int), `prompt` (string), `instruction_id_list` (list[str]), `kwargs` (list[dict]). Instruction count per row: 1: 305; 2: 179; 3: 57. 25 distinct instruction ids. No `constraint` text field and no span marks. `kwargs` is a dict per instruction (empty `{}` allowed), not None.

### 3) Two real examples (verbatim)
```
{"key": 1000, "prompt": "Write a 300+ word summary of the wikipedia page \"https://en.wikipedia.org/wiki/Raymond_III,_Count_of_Tripoli\". Do not use any commas and highlight at least 3 sections that has titles in markdown format, for example *highlighted section part 1*, *highlighted section part 2*, *highlighted section part 3*.", "instruction_id_list": ["punctuation:no_comma", "detectable_format:number_highlighted_sections", "length_constraints:number_words"], "kwargs": [{}, {"num_highlights": 3}, {"relation": "at least", "num_words": 300}]}

{"key": 1548, "prompt": "Write a file for a queer-owned business called \"The Rainbow Cafe\". Your file should have 4 sections, and each section should start with \"SECTION X\".", "instruction_id_list": ["detectable_format:multiple_sections"], "kwargs": [{"section_spliter": "SECTION", "num_sections": 4}]}
```
Note the constraint text is interleaved with the task inside a single sentence ("Write a 300+ word summary ... Do not use any commas and highlight ..."), so the constraint is not separable from the task.

### 4) Verification
Official Google IFEval verifiers (`instruction_following_eval`, Apache-2.0), same registry that open-instruct `IFEvalG` forked. Per-instruction booleans are native (the benchmark reports prompt-level and instruction-level strict/loose accuracy). Same langdetect caveat. I did not fetch the Google repo directly; the open-instruct `IFEvalG/instructions_registry.py` header carries "Copyright 2024 The Google Research Authors" and shares the 25 ids (confirmed in the 25 distinct ids above).

### 5) Distance
Chat. The prompts are natural human-written (hand-written by the benchmark authors) and the constraint is often embedded mid-sentence, which is closer to how real requirements appear than the appended template of (1a), but still output-format only.

### 6) Question IDs
- Eval-only for M2/D2/G2 once responses are sampled, with the instruction_id_list as the per-requirement list. Too small for training (541) and likely contaminated in the pre-training of many models, and 1a/1b training sets were built from IFEval constraints (so do not train on 1a and evaluate on IFEval constraint types as "held out"; IFBench_test is the held-out OOD set exactly because its 58 constraints are new).
- RF: no. Constraint spans are not given. Could be derived with the `description` templates in `instructions.py` (`build_description` returns the canonical phrase, e.g. "Your response should contain {relation} {num_sentences} sentences."), but IFEval authors paraphrased the prompts so exact template matching will fail on most rows (UNVERIFIED how many).

---

## (2b) allenai/IFBench_test

### 1) Access / license
Not gated. HF card metadata shows no `license` field (API returned None) but the README says "This dataset is licensed under ODC-BY-1.0. It is intended for research and educational use in accordance with Ai2's Responsible Use Guidelines. This dataset includes output data generated from third party models that are subject to separate terms governing their use." Tags `benchmark:official`, `benchmark:eval-yaml`. Code repo `allenai/IFBench` is Apache-2.0 (pushed 2026-11-02). Prompts are from held-out WildChat.

### 2) Structure
300 rows, parquet 94 KB. Fields: `key`, `prompt`, `instruction_id_list`, `kwargs`. The card schema lists `kwargs` as a union struct with many fields (`N`, `keyword1..5`, `percentage`, `reference_text`, `sep`, `small_n`, `word`, ...), most null; null-valued keys must be dropped. 1 constraint: 256 rows; 2: 44. 58 distinct ids (e.g. `sentence:keyword` 15, `words:consonants` 15, `format:sub-bullets` 12, `ratio:stop_words` 12, `ratio:overlap` 12, `count:word_count_range` 11, ...). `eval.yaml`: headline metric `prompt_level_loose` (every constraint satisfied under loose verification; "also accepts the response with markdown asterisks or its first/last line removed"). There is also a separate dataset `allenai/IFBench_multi-turn` (constraint isolation over two turns), which I did not download (UNVERIFIED contents). A two-turn layout (prompt, response, then "now follow this constraint") is closer to a monitor setting where requirements arrive later; worth a look.

### 3) Two real examples (abridged, verbatim)
Key 0:
```
prompt: What should the world's smartest man, surrounded by corruption, greed, inequity, madness, ... Hypothetical question, no judgement or bad here. Include keyword kaleidoscope once in your response, keyword nebula twice in your response, keyword whisper three times in your response, keyword labyrinth five times in your response, and keyword paradox seven times in your response.
instruction_id_list: ['count:keywords_multiple']
kwargs: {'keyword1': 'kaleidoscope', 'keyword2': 'nebula', 'keyword3': 'whisper', 'keyword4': 'labyrinth', 'keyword5': 'paradox'}
```
Key 150:
```
prompt: rewrite it better: During the Unity Catalog migration engagement, Impetus and Databricks wanted us to grant Impetus account-level admin privileges, which we obliged. In light of yesterday's incident ... Maintain a trigram overlap of 24% (+-2%) with the provided reference text. The response must include keyword metricism in the 3-rd sentence.
instruction_id_list: ['ratio:overlap', 'sentence:keyword']
kwargs: [{'percentage': 24.0, 'reference_text': "rewrite it better: During the Unity Catalog migration ..."}, {'N': 3.0, 'word': 'metricism'}]
```
(The prompt for key 150 is a WildChat text-editing request, so it comes from a realistic instruction; the garbled "+-" in the original text appears as a replacement character in the file, an encoding artifact.)

### 4) Verification
`allenai/IFBench` (Apache-2.0) ships `instructions_registry.INSTRUCTION_DICT` with 83 verifiers and a `run_eval` script that takes the test jsonl plus a jsonl of responses; install via `pip install ifbench`. Same pattern `checker_cls(id).build_description(**kwargs); .check_following(text)`, so per-constraint bool, deterministic modulo langdetect/nltk. I did not read `run_eval.py` output format (UNVERIFIED).

### 5) Distance
Chat. Real WildChat user prompts with appended synthetic constraints (the "Include keyword ... in your response" sentences are templated and appended). Several constraints (`ratio:overlap`, `words:consonants`) are mechanical; far from "don't modify files outside src/".

### 6) Question IDs
Evaluation set for D2/G2-style per-constraint pass/fail and M2 positives after sampling model responses: OOD relative to 1a. Too small to train. Not usable for RF (constraint text is not marked and is partly appended to a natural prompt, but the appended-templated tail is detectable by the same trick as 1a: the constraint sentence list is the id's `description` template filled with kwargs; not verified).

---

## (3) THU-KEG/AgentIF

### 1) Access / license
- Not gated. HF card: `license: cc-by-nc-4.0`, tags `agent`, `task_categories: text-generation`, languages en and zh, NeurIPS 2025 (arXiv 2505.16944). The GitHub repo (`THU-KEG/AgentIF`, Apache-2.0 code) says: "**Dataset** (`data/`): ... released under the Creative Commons Attribution 4.0 International (CC BY 4.0)", and `data/LICENSE` begins "The AgentIF dataset (everything under this `data/` directory ...) is licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0)". CONFLICT: HF NC vs GitHub BY. `data/eval.json` on GitHub is 45,857,657 bytes, the same size as the HF `eval.json` (45,857,657), so I treat them as the same file (byte-identity not checked). Treat as NC until the authors clarify. The system prompts themselves come from "50 real-world agentic applications, including both industrial systems and open-source agent frameworks", so third-party prompt copyright is a separate unresolved question (UNVERIFIED).
- GitHub README news item "2026-10 ... fixed a number of constraint checkers in `data/eval.json` (code checks with logic errors that could never pass, and tool-call constraints that now count one constraint per tool and are marked not applicable instead of failed when the tool is not invoked)". The `eval.json` I downloaded from HF has the same size as GitHub HEAD's, so presumably includes the fix, but I saw clear checker bugs in it anyway (see below).

### 2) Structure
- Single file `eval.json` (46 MB), JSON list of 707 records. Keys are heterogeneous. All records have `input` (list of chat messages) and `constraints`. 178 records also have `domain`, `query_id`, `turn_id`, `prompt_type` (`Thought_prompt` 90, `Code_prompt` 88), `output` (a single assistant message: the reference NEXT step, e.g. a `<thought>` before the tool call) and `agent_name` (e.g. `Thought_prompt_lawglm`); domains `general` 108, `lawglm` 70. The other 529 records lack these keys.
- `input` role patterns: system+user 498; user only 74; system,user,assistant,user 85; 2 more turns 41; up to 12 messages. So multi-turn agent traces with prior assistant turns exist in about 132 records.
- Size (system+user words): median 441, mean 971, max 7,280 (the paper claims average 1,723 words and max 15,630; my words count is by whitespace split on a corpus with 178 Chinese-dominant prompts, so lower; discrepancy unexplained, UNVERIFIED). About 178 of 707 contain Chinese in the first 2,000 characters of system or user text.
- 8,561 constraints total (mean 12.1 per record; the card says 11.9). `dimension`: unconditional 4,999; conditional 2,670; example_driven 892. `type` is a list in most rows or a bare string in some: `['semantic']` 3,570, `['formatting']` 1,792, `['resource','formatting']` 976, `resource` 785, `formatting` 694, `['resource']` 468, `semantic` 249, plus a few combos and 10 empty lists. `is_meta`: false 8,230; true 305; key missing 26.
- `evaluation` entry types: llm only 4,145; code only 1,384; code plus a conditional pre-check (`llm_conditional_check`/`code_conditional_check`) 976+885+482; code plus llm 667; etc. A `llm_conditional_check` is a gate: "Did you finish coding for a smaller task?"; only when the gate is YES is the main check scored.
- `other_info.from`: `system_para_N` 7,961 (93%), `None` 481, `query` 119. Constraints with `from=system_para_N` give the paragraph index of the source in the system prompt. Splitting the system prompt on `"\n\n"`, the best-overlap paragraph equals N (or the paragraph covers 80% of the desc's tokens) for 5,746 of 7,272 constraints (79%); splitting on `"\n"` fails (109 of 7,272). So the paragraph unit = blank-line-separated block. Other `other_info` keys seen: `type_explanation`, `meta_expalnation` [sic], `evaluation_type`, `evaluation_generation_success`, `condition_desc`, `complete_instruction_para`, `available_packages`.
- `state` (on 2,177 constraints): `success` 1,274, `modified` 903; 6,384 have no `state`. Meaning: UNVERIFIED (presumably LLM-generated checker passed first time vs was patched).

### 3) Two real examples (abridged, verbatim)
Example 1: a "Culture agent" system prompt, 7 constraints, first 5 shown briefly.
```
SYSTEM: You are the Culture agent for a self-guided audio tour system. Given a location and the areas of interest of user, your role is to:
1. Provide information about local traditions, customs, arts, music, and cultural practices
2. ...
4. Adopt a warm, respectful voice style when delivering cultural content
5. Make sure not to add any headings like ## Culture. Just provide the content
6. Make sure the details are conversational and don't include any formatting or headings. ...
7. Make sure the content is strictly between the upper and lower Word Limit as specified. For example, If the word limit is 100 to 120, it should be within that, not less than 100 or greater than 120
NOTE: Do not add any Links or Hyperlinks in your answer or never cite any source
...
USER: Query: Florence Interests: Renaissance art, architecture, Italian wine Word Limit: 160 - 160 + 20
Instructions: Create engaging cultural content for an audio tour. ... The content should be approximately 160 words when spoken at a natural pace.
constraints[0] = {"id": 15, "desc": "Provide information about local traditions, customs, arts, music, and cultural practices", "other_info": {"from": "query", "type_explanation": "...local specialties, food history, and interesting stories about restaurants and dishes...", ...}, "dimension": "unconditional", "is_meta": false, "type": ["semantic"], "evaluation": [{"type": "llm", "exec": "Does the response provide information about local traditions, customs, arts, music, and cultural practices? Please answer YES/NO directly and do not enter anything else.\n\nHere is the model response: {response}"}], "state": "modified"}
constraints[3] = {"id": 1, "desc": "Do not add any headings like ## Culture. Just provide the content.", "other_info": {"from": "system_para_0", ...}, "dimension": "unconditional", "is_meta": false, "type": ["formatting"], "evaluation": [{"type": "code", "exec": "\nimport re\n\ndef check_following(response: str) -> bool:\n    disallowed_chars = r\"[@¥#$^&*%~`|\\\\<>=_:/：]\"\n    return not bool(re.search(disallowed_chars, response))"}], "state": "modified"}
constraints[4] = {"id": 4, "desc": "The content is strictly between the upper and lower Word Limit as specified.", ..., "evaluation": [{"type": "code", "variable": ["word_limit"], "exec": "...def check_following(response: str) -> bool:\n    words = response.strip().split()\n    word_count = len(words)\n    upper_limit = 160 + 20\n    return 160 <= word_count <= upper_limit"}], "state": "modified"}
```
Noise visible here: constraint 15's `other_info.type_explanation` talks about "restaurants and dishes" (copied from a different tour sub-agent), and constraint id 1's checker tests for disallowed punctuation characters rather than headings (it would flag any ":" or "#" and miss nothing about "## Culture" headings semantics). So automated labels from `evaluation.exec` are not fully reliable.

Example 2: a coding agent. The system prompt is the OpenAI Codex CLI prompt ("You are operating as and within the Codex CLI, a terminal-based agentic coding assistant built by OpenAI ... You are an agent - please keep going until the user's query is completely resolved ... use your tools to read files and gather the relevant information: do NOT guess or make up an answer."). The user turn is "Can you help me modify the add_numbers function in the math_operations.py file located in the src/utils directory of my current project? ...". 10 records contain "Codex CLI" (mean 20.4 constraints each). Sample constraint objects, abbreviated:
```
{"id": 26, "desc": "Once you finish coding, for smaller tasks, you must describe in brief bullet points.",
 "other_info": {"from": "system_para_5", "condition_desc": "If you finish coding for smaller tasks, then you must describe the work in brief bullet points.", "complete_instruction_para": [], ...},
 "dimension": "conditional", "is_meta": false, "type": ["formatting"],
 "evaluation": [{"type": "llm_conditional_check", "exec": "Did you finish coding for a smaller task? Please answer YES/NO directly and do not enter anything else.\n\nHere is the model response: {response}"},
                {"type": "llm", "exec": "Does the model's response describe the work in brief bullet points? Please answer YES/NO directly and do not enter anything else.\n\nHere is the model response: {response}"}]}
```
Other Codex-record descs: id 0 (system_para_3, unconditional, semantic) "Please keep going until the user's query is completely resolved, before ending your turn and yielding back to the user."; id 2 (system_para_3, conditional, resource) "If you are not sure about file content or codebase structure pertaining to the user's request, use your tools to read files and gather the relevant information."; id 3 "Do NOT guess or make up an answer."; id 11 (system_para_5, conditional) "Use `apply_patch` to edit files: {...}". Note ids 7 and 8 are duplicates ("Working on the repo(s) in the current environment is allowed, even if they are proprietary.").
Meta example (Chinese LawGLM trace): `{"id": 2, "desc": "在写代码时你需要综合考虑最终目标<final_goal></final_goal>和本轮的任务<task></task>。", "is_meta": true, "type": "semantic", "dimension": "conditional", "dependency": [], ...}` with an LLM check prompt embedding the specific task for that turn.

Another conditional example: `{"id": 0, "desc": "Return ONLY the database name, no other text or explanation. If you're not confident about the routing, return an empty response.", "dimension": "conditional", ..., "evaluation": [{"type": "code", "exec": "import re\n\ndef check_following(response: str) -> bool:\n    pattern = r'^(products|support|finance)?$'\n    return bool(re.fullmatch(pattern, response.strip()))\n"}]}`.

### 4) Verification
Code checks: a Python `check_following(response: str) -> bool` snippet stored in `evaluation[].exec` (deterministic, but the snippet is data that must be executed, i.e. untrusted code; run it only in a sandbox). LLM checks: a YES/NO prompt template with `{response}`, scored by a judge. The updated GitHub setting uses judge `gpt-5.6-luna` (temperature 1, `reasoning_effort=medium`), 3 runs. Original setting used `gpt-4o-2024-11-20` temperature 0. So per-constraint verdicts are available for any response, but only 1,384 + 667 + (part of the 2,670 conditional) checks are code-deterministic; about half are LLM-judged (non-deterministic and cost). CSR (constraint success) and ISR (instruction success) are the metrics. Conditional constraints: `llm_conditional_check`/`code_conditional_check` pre-gates determine whether it applies, which maps well to "N/A" and could supply G2's "can't tell/not applicable" distinctions. Tool-call constraints: per GitHub notes, "marked not applicable instead of failed when the tool is not invoked".

### 5) Distance
Closest of the set. These are real agent system prompts with persona, rules, tool and format sections, and some include actual coding-agent prompts (Codex CLI: 10 records; "coding agent" appears in 20 system prompts; Cursor in 31 (a substring match, may include unrelated "cursor" uses; UNVERIFIED); "git" 63; `apply_patch` 10). Gaps: (a) the evaluated object is a single next assistant message (not a long trajectory of tool actions and edits); (b) the "user" turn is usually a short task, the requirements are mostly in the system prompt, whereas for our monitor requirements come from the human user plus project docs (CLAUDE.md); (c) about 25% of prompts are Chinese-heavy (LawGLM, etc.); (d) 707 records is small; (e) NC license.

### 6) Question IDs and modifications
- RF (strongest fit). Procedure: split each system prompt (and the user turn) into paragraphs on blank lines (matches `from=system_para_N` for 79% of constraints) and then sentences. Label a sentence positive when it lies in the paragraph named by a constraint's `from` AND is a (fuzzy) match to that constraint's `desc` (token overlap; I measured how many descs can be located: exact substring 3,337 of 8,561 (39%); after lowercasing and whitespace-normalising 3,337+1,240 = 4,577 (53%); a further 1,715 (20%) have a close sentence with SequenceMatcher ratio >= 0.6 within the first 400 sentences; roughly 2,269 (26%) have no close match, i.e. paraphrased, merged, derived from tool descriptions or from implicit requirements). Negative sentences: everything in the prompt not matched by any constraint (persona, context, "You are a ...", tool schemas, example blocks). CAUTION: the annotation says "All explicit and implicit constraints are manually extracted", and `desc` is often a lightly rewritten version of the source sentence, so for a sentence-level RF label the unmatched residual contains un-annotated requirements, i.e. noisy false negatives (e.g. in the Codex prompt only about 20 constraints cover a much longer prompt). Prefer paragraph-level or high-confidence-match positives and an LLM audit pass of the negatives. Dedupe duplicated constraints (see ids 7/8).
- OV (long documents: which sections bear on the action). Use `from=system_para_N` as the section pointer: given a candidate action/response and the system prompt split into paragraphs, the paragraphs referenced by the constraints that the response violates (or by the constraints that the checker evaluated as relevant) are the "bearing sections". Requires pairing each record with a response (sampled from models) and running the per-constraint checks. Weaker label than M2: it identifies sections for the whole response, not a specific action.
- M2 / D2 / G2. Sample responses from 1 to 2 models for each `input`; run per-constraint checks (code in a sandbox, LLM judge for the rest), map: failed constraint -> D2 requirement-level "yes violated", conditional gates -> N/A, all constraints -> G2 status vector (done = pass, broken = fail, "not done"/"can't tell" must be produced by cases: gate false = N/A, empty or truncated output). Render the system prompt plus user turn as the instruction/docs context and the response as the agent event. Because the responses are single messages without file actions, the "action" is a text/tool-call message; for Codex-CLI records, response would be a function-call to `shell` or `apply_patch`, so tool-call constraints (e.g. "Use `apply_patch` to edit files") become real action-level checks. The `output` field (present in 178 records) is the reference next assistant step; whether it satisfies the constraints: UNVERIFIED (not run). The Chinese portion would need translation or exclusion.
- Data quality work: drop or re-verify rows with obviously broken checkers (example above), duplicates, and `evaluation_generation_success: false`; consider keeping only constraints with `state: success` (1,274) for the cleanest checks. UNVERIFIED how many of the 6,384 stateless constraints are reliable.
- License: if the NC reading stands, usable for research eval but not for a model you intend to ship commercially; resolve with the authors first.

---

## (4) RF-specific assessment: sentence-level requirement labels

| Source | What marks the requirement text | Fit for RF | Work needed |
|---|---|---|---|
| IF_multi_constraints_upto5 | `constraint` field = TAB-joined constraint segments, each an exact substring of the prompt, always at the tail (100% of 12,880 sampled segments; 5,000 of 5,000 prompts end with the last segment) | Best volume (95k) and exact spans | Sentence-split segments, find negatives in the base prompt (base can itself contain imperatives like "Make it long."), de-template, mix positions, add non-chat context |
| RLVR-IFeval | `constraint` is a template; verbatim in the prompt only 33% | Poor as given | Regex-recover the instantiated sentence, or just use 1a |
| IFEval | none (`instruction_id_list`, `kwargs` only; constraint woven into the task sentence) | None directly | Match against `build_description` templates (likely low recall, UNVERIFIED) or LLM-annotate |
| IFBench_test | none, but constraint is appended sentence(s) | Eval only | Same as above; small (300) |
| AgentIF | `constraints[].desc` + `other_info.from = system_para_N` (paragraph pointer) + fuzzy match | Most realistic documents; noisy sentence labels | Paragraph split on blank line; sentence-level match; audit unmatched residual; keep multi-constraint sentences as one positive |

Derivation recipe summary (what changes, not code): for 1a keep the base prompt, split off the TAB-segments as RF positives, treat other sentences as negatives only after filtering for imperative-looking base sentences; for AgentIF split on blank lines (paragraph pointer), locate each `desc` inside its pointed paragraph, label matched sentences positive, label paragraphs with no constraint pointer as negative-paragraph candidates (higher-precision than sentences). Mix both with an out-of-domain set for realism (CLAUDE.md-style docs) because the IFEval-style sentences are very recognisable by form.

## Gaps and UNVERIFIED items
- Per-constraint output schema of IFBench `run_eval.py` and `evaluation_lib.py` (not read).
- Alignment between `constraint` TAB segments and `instruction_id` lists on every row of 1a (checked by eye on 3 rows only).
- Whether `langdetect` is actually nondeterministic for our response lengths; whether Llama-2/ImpACT terms bind RLVR-IFeval's data.
- AgentIF: final license, `state` semantics, whether `output` satisfies constraints, count of coding-agent records beyond keyword matches (Cursor and "coding agent" counts are substring matches), the discrepancy between claimed 1,723-word mean and my 971.
- IFBench_multi-turn was not downloaded or inspected.
- No model responses were generated, no verifier was run (only read), so no empirical pass-rate numbers exist yet.

## Files created (untrusted data, scratchpad)
`C:\Users\david\AppData\Local\Temp\claude\e4a7ca8b20dbf3e0\48a356b8-0453-4fa7-b972-ac20964e049d\scratchpad\inspect\constraints\{multi,rlvr,ifeval,ifbench,agentif,code}\` (data and fetched code text), scripts in `...\scratchpad\inspect\tools-constraints\` (a.py to i.py).
