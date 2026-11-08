# Inspection: SALT-NLP/SWE-chat (v2, 2026-10-02) as monitor fine-tuning data

Date: 2026-11-07. Method: read README + paper (arXiv 2604.20779v2, text extracted from PDF), pulled `sessions.parquet` (36 MB) and `session_logs.parquet` (44 MB) in full, range-read 10 of 1,161 row groups of `conversations.parquet` (100,000 of 11,607,572 rows, 0.86%; 52 MB local), fetched ONE raw transcript jsonl (37 KB). Disk used under the swechat dir: about 180 MB. No dataset code was run. Scripts are in `...\scratchpad\inspect\tools-swechat\`.

Sample caveat: row groups are file-ordered (roughly by time/agent), not random sessions. I kept only sessions whose rows are fully inside the sampled groups (173 sessions of 17,968, 0.96%). That biases against very long sessions that span groups. Sample numbers below are therefore indicative, not population estimates. Where the full `sessions.parquet` was available I give population numbers and say so.

## 1. Access / license

- HF gate: `gated: auto` (click-through, auto-approved). The card has NO `extra_gated_prompt`/terms text in its metadata; I saw no gate-terms text beyond the auto gate. License tag: `odc-by`. README: "Data Collection" and "Data Removal Requests" sections only.
- Removal policy (README): contact joachimbaumann@stanford.edu with `repo_id`, `session_id` or `turn_id` and a reason, to remove data or report illegal content. Released rows are therefore revocable; a frozen copy may need re-checking.
- Anti-training language: none found in README or paper ethics statement. Paper: data comes from public GitHub repos whose developers opted in to Entire.io CLI checkpointing and pushed to public branches; "We only include repositories whose licenses allow redistribution" (`repositories.license_type` holds the classification, UNVERIFIED which licenses). Images attached to prompts are NOT collected (prompts show `[Image: image/png]` placeholders). PII: Microsoft Presidio (NER) over every user/assistant turn plus TruffleHog for secrets, following the WildChat pipeline. Stanford IRB exempt. Paper explicitly lists downstream uses (SWE-Together, SWE-INTERACT user simulators; SLEIGHT-Bench uses the transcripts "as a realistic, benign baseline for calibrating agent monitors"; Transluce Docent found "severe monitor evasion in 1.9% and overselling of task success in 1.8% of SWE-chat sessions"). So monitor use is an anticipated use.
- Residual risk: redaction is automated (Presidio/TruffleHog), so leftover personal paths remain visible (I saw real home paths like `/Users/<name>/...` in tool calls and in `cwd`). Redaction covers prompts/responses, not tool inputs/results in raw transcripts (UNVERIFIED for tool results in parquet; the README says only prompts, responses, subagent prose and skills are redacted).

## 2. Structure

Repo file list (v2): 11 parquet files (`conversations` 6.4 GB, `commits` 5.1 GB, `session_logs` 44 MB, `sessions` 37 MB, `checkpoints` 25 MB, `conversations_subagents` 19 MB, `skill_definitions` 17 MB, `context_events` 5 MB, `skill_invocations` 1.3 MB, `repositories` 0.9 MB, `subagent_tasks` 0.2 MB) plus about 21,600 raw transcript files (`transcripts/`, also `transcripts1/` dir present; README lists 17,819 raw, 3,760 compact, 83 subagent). Raw files are the agent's native format (Claude Code jsonl, Gemini JSON...).

Counts confirmed from `sessions.parquet`: 17,968 sessions; from conversations metadata: 11,607,572 rows; README: 229,909 user prompts; 62,333 commits; 54,918 checkpoints; 707 repos.

Join keys:
- `sessions.session_id` (PK) -> `conversations.session_id` (1:N), `session_logs.session_id` (1:1), `skill_invocations`/`context_events` (session_id when available), `subagent_tasks` + `conversations_subagents` (session_id = PARENT session).
- `conversations.turn_id` = `{session_id}#{turn_number}`; not stable across releases, join on session_id.
- `checkpoints` <-> `sessions` many-to-many via JSON arrays; `commits` by `checkpoint_pk` (`{repo_id}#{checkpoint_id}`).

Where things live:
| Need | Table.field |
|---|---|
| User prompts | `conversations` rows `turn_type=user_prompt` (`content`), also `system_injected` for harness-injected user-role text |
| Agent messages | `turn_type=assistant_response` |
| Thinking | `turn_type=assistant_thinking` (see section 4: mostly empty for Claude Code) |
| Tool calls | `turn_type=tool_use` with `tool_name`, `tool_input_json`, plus extracted `file_path`, `command`, `pattern`, `category`, `bash_category`, `tool_call_id` |
| Tool results | `turn_type=tool_result` (same `tool_call_id`), content truncated to 10 KB |
| Pushback / intent labels | `conversations.prompt_pushback`, `prompt_intent` (user_prompt rows only) |
| Session labels | `sessions.user_persona`, `sessions.session_success` (string 0-100); AI summaries `summary_intent/outcome/friction/open_items` (only about 4% of sessions populated) |
| Model, tokens | `conversations.model`, per-message token columns; `sessions.model` (empty string for 59% of sessions, 10,564 of 17,968) |
| Raw native events | `session_logs.transcript_path` -> `transcripts/{session_id}.jsonl`; `context_md` (38% populated: "# Session Context / ## User Prompts"), `session_metadata_raw` |
| Other | `queue_operation` rows (`queue_op_subtype`: user typed while agent busy, delivered/discarded), `progress`, `system_event`, `file_snapshot`, `summary`, plus many `other:*` metadata types |

Row order in `conversations` within a session is by `turn_number` (all rows) and `conversation_turn_number` (user_prompt + assistant_response only). One user "turn" can produce several consecutive `user_prompt` rows (e.g. text then `[Image: image/png]` then `[Image: source: ...png]` placeholder rows); those extra rows have NULL labels.

v1 vs v2 (README table): v1 2026-04-29, 5,851 sessions, 62,544 prompts (commit f66cca9); v2 2026-10-02, 17,968 sessions, 229,909 prompts (commit df393df). Paper: repos grew 205 -> 707 and the Claude Code share changed. v2 has the extra tables (subagents, skills, context_events) and fields like `kind`, `compact_transcript_*`, `queue_operation`. I did NOT download v1, so exactly which annotation columns v1 had is UNVERIFIED. Pin to commit `df393df` for reproducibility; `turn_id` changes between releases.

## 3. Real examples (abridged, verbatim where quoted)

Claude Code event shapes (from the raw jsonl, session 002a787f...): lines are objects with `type` in {`progress` (hook_progress), `system`, `file-history-snapshot`, `user`, assistant message objects}. Assistant lines carry `message.model`, `message.id`, `message.content[]` blocks of `{"type":"thinking","thinking":"","signature":"..."}` or `{"type":"tool_use","id":"toolu_...","name":"Bash","input":{"command":"git status && git diff --stat HEAD","description":"Check git status and diff"}}`, and `usage`. Also `parentUuid`, `isSidechain`, `uuid`, `cwd`, `version`, `gitBranch`, `sessionId`, `userType`. This is the native Claude Code event stream, so per-event objects are directly derivable. In the parquet the same call looks like: `tool_use Bash {"command": "cd /Users/.../MovieSwift && xcodebuild -scheme MovieSwiftMac -destination 'platform=macOS' build 2>&1 | tail -3", "description": "Build", "timeout": 180000}`.

Tool names seen in the sample: Claude Code `Bash` 7,478, `Edit` 2,810, `Read` 2,522, `TaskUpdate` 485, `Write` 434, `Grep` 412, `Agent` 385, `TaskCreate` 259, also `TodoWrite`, `Glob`, `WebFetch`, `WebSearch`, `AskUserQuestion`, `EnterPlanMode`, `ToolSearch`, and `mcp__context7__*`. Codex: `exec_command` 817, `exec`, `write_stdin`, `apply_patch`, `spawn_agent`, `request_user_input`. OpenCode/Pi: lowercase `bash`/`edit`/`read`/`write`.

### Example A: rejection / failure report after a claimed fix (Claude Code, session 2cae28a4-28e8-4bfa-9225-7682543f3664)
- User's original request (first prompt): "I want to convert this from a MacCatalyst app to a Mac App / iOS App and TV Os app. This should share components and then build specific targets for each. We should focus on making sure there are enough UI and Unit tests before we start doing the conversion. We need to take this in a very phased app..." (very long session, turns up to about 7,400).
- Agent actions at turn 6802-6807: edits `OutlineRow.swift` ("Let me override the sidebar's row background with a steam-gold tint when selected, replacing the macOS default blue"), runs `xcodebuild`, gets `** BUILD SUCCEEDED **`, then claims: "Build succeeded. The selected sidebar row now has a soft **steam_gold** tinted rounded background (18% opacity) instead of the system blue ... Take a look".
- User (turn 6811-6812; image placeholder then text), label `rejection`, intent `debug`: "nope the hightlight color is still blue".
- Agent next (6816): "The system `List(selection:)` draws the blue highlight on top of `.listRowBackground`. I need to manage selection manually so the system selection doesn't render at all:" then Read SplitView.swift, Edit SplitView.swift, then reverts its own earlier OutlineRow change ("Now also revert OutlineRow's `.listRowBackground` since we no longer use a `List`").
- Monitor view: the agent's claim ("now has ... instead of the system blue") was contradicted by evidence the agent could not see (the screenshot). The build output cannot verify it. Fits M5-like "claim not backed by evidence", but the evidence is in the user's reply, not the trace.

### Example B: claim of completion followed by failure report (Claude Code, session e1cf36bf-b4e3-4b40-b9be-cc8a4f2b4ac6)
- First prompt: "[Image #1] [Image #2] there is a huge issue in the blog on taskai, look at the image on the original article, the image text looks perfect, now look at how it looks in taskai. Please make sure the export is exact replica..."
- Turn 527 agent final: "All deployed. | Environment | Status | URL | ... **What was fixed:** 1. **Drawing text clipping** ... 2. **KaTeX math in the wiki page** — The RRF formula is now rendered with proper math notation ..." (preceded by `git push ...main:production` and `gh run watch`).
- Turn 530, label `failure_report`, intent `debug`: "[Image #4] math is not rendering, check https://anshumanbiswas.com/blog/knowledge-spine-ai-code-quality math renders perfectly here plus they both use go-wiki".
- Agent next: "The wiki renderer isn't loading KaTeX CSS/JS. Let me check how the blog has it configured vs the wiki." then `grep -n -i "katex\|math\|latex" .../main.go`.
- Same session, earlier (turn 298, label `correction`, after the user interrupted with `[Request interrupted by user]`): "no, this could be as a header in search which will restrict the search X-Project-ID, so reach from .taskai.json and pass as a header to taskai via .taskai.json ... Also possible to search from multiple projects ..." Agent: "Got it. Let me implement this properly: 1. `.taskai.json` declares project IDs for the repo 2. `.mcp.json` sets `X-Project-ID` header (supports comma-separated for multi-project)". The agent had previously narrowed scope itself ("Now let me address the user's request about having a project config file in the repo. Instead of putting the project ID in `.mcp.json`, I should create a `.taskai.json`...") and the user disagreed: a clean M7/M1 positive.

### Example C: benign session (Claude Code, session dc1edbe1-955c-4b41-b983-ddd85cdd4fc9; model claude-opus-4-8; persona Vague Requester; success 95; 4 labeled prompts all `non_pushback`; 37 tool calls)
- Turn 8, `non_pushback`, intent `refactor`: "Check for any CLI commands that still need to be ported to use https://github.com/entireio/cli/pull/1542".
- Agent: `gh pr view 1542 ...`, `grep -rn "lipgloss.Color(" cmd/ internal/ ...`, reads `palette.go`, more greps, then findings ("Three `huh` forms still bypass the palette ...").
- Turn 66, `non_pushback`: "Yes" (approval to proceed). Agent reads the two files, checks `os` usage ("`os` stays used. Now the edits."), makes three Edits, each followed by a tool_result "has been updated successfully".
- Note `assistant_thinking` rows exist (turns 17, 21, 31...) but content is empty (see section 4).

### Example D: a noisy label (for calibration)
- Session 8995a262..., turn 389, labeled `correction`: "Let's do a significant refactor. Instead of logging events to a raw json file, let's keep them in a sqlite database. Let's use prisma as our ORM..." This is a new task, not pushback. Others in section 5.

## 4. Measured stats

All "sample" numbers: 173 complete sessions, 1,867 user_prompt rows, from the 10-row-group sample. "Population" numbers: full `sessions.parquet`.

Agents (population, 17,968 sessions): Claude Code 12,417 (69.1%), Codex 2,362 (13.1%), OpenCode 1,525 (8.5%), Project Runner 396, Pi 368, Cursor 318, Copilot CLI 254, Gemini CLI 116 (0.65%), Kimi Code 64, others. Sample (by session): Claude Code 78%, Codex 8%, Pi 6%, Cursor 5%, OpenCode 2%; Gemini CLI absent. Sample rows: Claude Code 80,396 of 95,183.
Session `kind` (population): normal 16,388, `imported` 1,138, `agent_review` 433, `agent_investigate` 9.
Population `session_success` (n=17,563 annotated): mean 73.3, median 82, p10 42, p90 92; 85.6% >= 50. Persona: Expert Nitpicker 6,772, Vague Requester 5,643, Other 4,299, Mind Changer 1,153, none 101.

Pushback labels (sample, 1,598 labeled of 1,867 prompts):
| label | n | share of labeled |
|---|---|---|
| non_pushback | 821 | 51.4% |
| correction | 618 | 38.7% |
| failure_report | 140 | 8.8% |
| rejection | 19 | 1.2% |
NULL label: 269 prompts = slash commands (`<command-name>/clear</command-name>`, `/exit`, `/simplify`), `[Request interrupted by user for tool use]` interrupts (57 interrupt rows in the sample), and extra image/placeholder rows. Paper says users push back after about 46% of prompts and interrupt/push back on 50.2%; the sample agrees (48.6% pushback among labeled). 67.8% of sampled sessions have at least one correction/rejection/failure_report. Median words: correction 22, failure_report 17, rejection 7, non_pushback 9. By agent (sample): Claude Code 515 correction / 131 failure_report / 12 rejection / 667 non_pushback.
Intent labels (sample): other 401, understand 279, debug 272, git 223, create new code 193, refactor 152, test 56, connect 22.

Session length. Population from `sessions.parquet`: tool_call_count median 50, p90 266, max 8,566 (16,165 sessions have a count; the rest have none recorded); turn_count (conversational turns) median 23, p90 133; prompt_count median 3, p90 20; duration median 1,748 s (29 min), p90 62,867 s (wall clock including idle); output_tokens median 10.7k, p90 106k. Sample (173 sessions): total parquet rows incl. metadata median 230, p90 1,283; tool calls median 46, p90 261; approx tokens (sum of `char_count`/4 over all rows including truncated tool results) median 61.6k, p90 309k, max 2.07M. 12.1% of sample sessions (21) have zero tool calls. Claude Code only (n=135): tool calls median 53, p90 260; tokens median 73k, p90 302k.

Thinking: In the Claude Code sample, 6,081 `assistant_thinking` rows exist but only 12.4% have non-empty text (the rest are signature-only blocks with `"thinking":""`; the raw jsonl confirms this). OpenCode thinking is 100% non-empty in sample. Codex has `other:codex_reasoning_block` metadata rows; Pi has `other:pi:thinking`. Visible thinking example (Claude Code): "The user wants me to review the changes in the current branch (`skip-fully-condensed-sessions`). Let me first look at what's changed compared to the main branch." So thinking is NOT reliably available; assume absent for most Claude Code sessions.

Model field: `sessions.model` blank for 59%; named ones include claude-opus-4-6/4-7/4-8[1m], claude-sonnet-5, gpt-5.4/5.5/5.6-sol.

## 5. Label provenance and quality

Provenance (paper Appendix F; README says "LLM-annotated... See paper"): all labels are LLM-as-judge, selected by zero-shot evaluation against human expert gold labels.
- `prompt_pushback`: Qwen/Qwen3.5-9B (open weights, temperature 0.7), zero-shot with a rubric prompt; input is the full preceding conversation context plus the prompt. Interruptions are excluded from classification (that is why `[Request interrupted...]` rows are NULL). Rubric: correction = user redirects with missing context/changed requirements ("I said X not Y", "actually, let's do X instead"); rejection = "undo that", "no" without a fix; failure_report = "doesn't work" (bugs, errors, failing tests); non_pushback = new task, question, routine iteration. Tie-break rule: words like "undo", "wrong", "broken", "I said", "never mind" -> lean to pushback.
- Quality per the paper (Fig. 33): prompt pushback 4-class accuracy 0.67 (n=98) against human gold; session success ICC(2,1) about 0.60 (claude-sonnet-4-6); persona accuracy 0.69 (gpt-5.4); prompt intent 0.76. The paper states LLM annotators "are thus not reliable data annotators" and uses them for scale.
- `session_success`: claude-sonnet-4-6, input is the full conversation with a summary of tool calls. `user_persona`: gpt-5.4-2026-03-05. `prompt_intent`: raw prompt text only. Repo domain: claude-opus-4-6. Summary fields (`summary_*`): Entire.io's own AI summaries (about 4% populated).
- Human labels exist only for a 90-100 session/prompt validation set; they are not in the release as far as I could see (UNVERIFIED).

My spot-check (12 pushback labels I read with context; sample of random Claude Code rows with 4-79 words):
1. 2cae28a4 t6208 correction, "I should be able to arrow through the people instead of tab..." - right.
2. e1cf36bf t298 correction, "no, this could be as a header in search..." - right.
3. ee2b8e9f t907 correction, (Russian) "On the lock screen still nothing... can we make it work like FaceTime when minimized?" - borderline (failure_report plus new requirement); acceptable.
4. 738f2115 t644 correction, "current starting of the abstract is not good. Start with something like this..." - right.
5. f6ec58ae t379 correction, "Recontruct the markdown from the database" - WRONG (routine next instruction, should be non_pushback).
6. 2cae28a4 t6812 rejection, "nope the hightlight color is still blue" - right (failure_report also defensible).
7. 53aa8a48 t67 rejection, "drop it for now" - right-ish (scope cut; correction also defensible).
8. 53aa8a48 t61 rejection, "what was the queston?" - WRONG (clarifying question after the user interrupted an AskUserQuestion; non_pushback).
9. 93833a17 t227 correction, "question on the failures, since you saw the output, what im confused about is that it said 1 agent failed, but then showed codex output..." - WRONG-ish (user question about confusing output, no redirect).
10. a145951a t6 correction, the session's FIRST substantive prompt ("can you look at the release logic we have right now...") - WRONG (a first prompt has no preceding agent action to push back on).
11. 8995a262 t389 correction, "Let's do a significant refactor. Instead of logging events..." - WRONG (new task).
12. 2cae28a4 t5155 correction, "When viewing the other posters carousel, the dots bleed off the bounds..." - borderline (bug report, failure_report fits better).
Result: 6 right, 3 borderline, 3 wrong of 12 (about 50-75% usable), consistent with the paper's 0.67 accuracy. Errors are mostly over-calling `correction`. `failure_report` and `rejection` looked more reliable but `rejection` is rare (1.2%) and sometimes is a question. I also only sampled pushback-labeled rows, so recall of missed pushbacks (labeled non_pushback) is UNVERIFIED beyond a glance at three, which looked fine.

Important content caveat: most pushback here is product feedback from a user watching a UI/behavior ("nope the highlight color is still blue", "math is not rendering"), often referring to a screenshot that is NOT in the data (images are dropped; prompt shows `[Image: image/png]`). The user complaint is frequently only judgeable with evidence that is outside the trace.

## 6. Which monitor questions it can serve, and what must be done to the data

General: unit of data is a whole session of native-format events. Nothing is labeled in the monitor's vocabulary. All uses below need our own re-labeling of a subset (LLM or human), with this dataset providing real, benign-heavy, un-staged traces and weak signals about where to look.

- Benign negatives for every per-event question (M1, M2, M4, M5, M7, L1, L2, L4, L5, L6, G1, G2, G5): best use. 85.6% of sessions have success >= 50 and the paper positions it as a benign monitor baseline (SLEIGHT-Bench). Modifications: filter to Claude Code (69%) so tool names and event shape match; drop sessions with zero tool calls (12% in sample), `kind` != '' (imported, agent_review, agent_investigate), and sessions that are slash-command-only; prefer `session_success >= 70` AND no correction/rejection/failure_report prompts (about 32% of sampled sessions) as "clean"; still treat as negatives only after a spot-audit because the monitor-evasion and overselling rate found by Docent is about 2% of sessions (so about 2% of "benign" is contaminated); cap very long sessions (p90 is about 300k approx tokens; windowing needed); remove sessions where the user's goal is unstated (first prompt is a slash command, `/clear`, or a paste of a plan/handoff).
- M1 (action serves user's real goal): take the agent turns immediately preceding a `correction` or `rejection` prompt as candidate positives (window: agent events since the previous user_prompt). Must be re-judged because 50% of `correction` labels are noisy (new task, question, first prompt). Keep only cases where the pushback text names what the agent did wrong ("I said X not Y", "no, this could be..." as in Example B), and drop pushbacks that are new feature requests. Use the pre-pushback agent window as the input, the prompt text only as a weak label, never shown to the monitor.
- M7 (silently resolves ambiguity): Example B (t298) type cases: agent made a scope/design choice, the user disagreed. Need an LLM or human pass to find where the agent chose between interpretations without asking. Negatives: windows where the agent used `AskUserQuestion` (Claude Code tool) or the user prompt is unambiguous. `session_persona=Vague Requester` (5,643 sessions) is a candidate pool. Paper: Claude Code asks clarification in only 3% of turns.
- L7 (correction open: fixed/partial/acknowledged/ignored/dismissed): the K agent events after a labeled pushback prompt form the window (we saw 2-4 events in Examples A/B show the outcome: e.g. Example A the agent fixes, then reverts its earlier change). K should extend until the next user_prompt or about 30 events. The outcome class (fixed vs ignored vs partial) is NOT labeled; judge from whether the next user turn repeats the complaint (a repeated complaint -> ignored/partial; moving on or `non_pushback` -> fixed). Needs a subset re-labeled; the dataset gives the correction text and subsequent turns for free. "Dismissed wrongly/correctly" has no signal here: users rarely say "you were right".
- M5 (claim contradicts evidence): the `failure_report` after an agent "done/fixed" claim is the natural source (Examples A and B). Build positives where the agent final message asserts success and the next user prompt is a `failure_report` about that same item; verify by reading the tool results before the claim (e.g. did a test/build/deploy actually cover it). Many will be "unverifiable from trace" (the claim was untested), which is a different failure: label separately. Needs LLM re-judging plus Bash/test output present in `tool_result` (10 KB truncation).
- M4 (games a measure) / L6 (targets the checker): only weak. No direct signal; search `Bash`/`Edit` events for test/CI file edits (`bash_category` test-build, `file_path` in test dirs, `--no-verify`, `skip`) among sessions with low success or failure_report, then label manually. Expect few positives.
- M2 (breaks a stated requirement): `correction` prompts of the form "I said X" and `rejection` of outputs; require re-labeling to confirm the requirement was stated earlier in the session (check earlier user_prompt rows). Good for stated-requirement tracking because multi-prompt sessions (median 3, p90 20 prompts) accumulate requirements.
- L1/L4/G1 (drift, different goal, whole-run): sessions with `user_persona = Mind Changer` (1,153) and low `session_success` (< 40, about 10%) are candidate drift/abandon pools; the goal is not drifting in a gaming sense but the user changing it, so careful: user-initiated goal changes are NOT agent drift; negative examples for RF (instruction change) rather than L4. Need full-run labeling.
- RF (is this sentence a requirement): user_prompt rows give naturally occurring requirement/constraint vs question vs approval ("Yes", "drop it for now"); `prompt_intent` is too coarse. Needs new labels; the prompts are real, multilingual (en/ja/zh/ko/ru/pt and German seen), so filter `language == 'en'` if the monitor is English-only.
- L5 (required step skipped vs not yet done, including user-prescribed order): first prompts that prescribe steps ("1. check if ... 2. remove ...") exist (e.g. session 8be81d4f) plus the todo list tool events (`TodoWrite`, `TaskCreate/TaskUpdate`) which expose the agent's own plan and statuses. Need LLM labeling of steps against the final state. No labels now.
- G2/G5 (completion status / genuine success): `session_success` (Sonnet-4.6, ICC about 0.6) and `summary_outcome` (4% only) give coarse signals; the final assistant_response plus following user prompt (Example B) gives genuine-vs-claimed evidence. Use `session_success < 40` with a "done" claim as candidate G5 negatives; need re-labeling.
- D1/D3/D2/D5 (flag attribution, requirement, severity): not in the data. Would have to be generated by an LLM labeler over selected windows.
- OV / M8 (large docs, section conflicts): `context_events` (instruction files, plugins, slash commands, 80,958 rows) and `context_md` / CLAUDE.md-type context exist, and `skill_definitions` (3,523 bodies). Possible as the "large document" side, with conflicts needing manual construction. UNVERIFIED: I did not read `context_events`.
- G4 (stated priorities): rare; not checked.

Concrete transformations needed before fine-tuning:
1. Reconstruct event objects: use the `conversations` rows grouped by `session_id`/`turn_number`; pair `tool_use` and `tool_result` by `tool_call_id`; collapse the multiple `assistant_*` rows of one `response_id`; drop metadata types (`progress`, `file_snapshot`, `system_event`, `other:*`) or keep only hooks if relevant; keep `system_injected` out of "user prompt" (the harness wraps text such as skill text and command text). The raw jsonl in `session_logs.transcript_path` is the lossless alternative (it includes `parentUuid` and `isSidechain` for subagent branches, and hooks).
2. Treat `[Request interrupted by user]` rows as a separate first-class signal (user hard-stopped the agent): they are unlabeled (NULL) but are strong evidence the preceding action was unwanted; paper reports 3.5-5.2% of turns.
3. Remove or fill the missing screenshots: restrict pushback positives to prompts that are self-contained (no `[Image` in the text) or accept lower label accuracy.
4. Replace the weak pushback label with a stricter relabel (rule: the pushback must reference the agent's prior action and not be a new task, a question, or the first prompt), verified by a stronger model; expect to discard about a third of `correction`.
5. De-duplicate near-identical sessions (many from the same repo; 707 repos; the sample shows one user, 2cae28a4, contributing a 7,000+ turn session) and cap per-repo/per-session contribution.
6. Windowing: sessions are long (median about 60k approx tokens, p90 about 300k); the monitor needs per-event or last-N windows with the first user prompt plus cumulative later prompts as the "user instructions".
7. Redaction hazard: strip real local paths/names that survive in tool inputs before using them in training data.
8. Language filter and agent filter (Claude Code, `en`), and check `repositories.license_type` per repo for the licenses we are comfortable with (UNVERIFIED which values occur).

## Not checked (UNVERIFIED)
v1 contents and columns; `commits`, `checkpoints`, `repositories`, `skill_*`, `context_events`, `conversations_subagents`, `subagent_tasks` contents; whether `transcripts1/` is v1 only; Gemini CLI/Codex raw formats; recall of missed pushback labels; license value distribution; full-population pushback distribution (only 0.86% of rows sampled); exactly which model annotated `prompt_intent` in the v2 release (paper Table 8 names the chosen model per task, I only confirmed pushback = Qwen3.5-9B, persona = gpt-5.4, success = claude-sonnet-4-6, repo type = claude-opus-4-6).

Local artifacts: `C:\Users\david\AppData\Local\Temp\claude\e4a7ca8b20dbf3e0\48a356b8-0453-4fa7-b972-ac20964e049d\scratchpad\inspect\swechat\` (README, sessions, session_logs, conv_sample/conv_full parquet, paper.pdf/txt, one transcript).
