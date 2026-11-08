# Inspection: benign / realism session pools (Open-SWE-Traces, TonyDzi/agent-sessions, CodeTraceBench)

Date: 2026-11-07. Inspector: dataset-inspection agent. All data were treated as untrusted: files under `scratchpad\inspect\benign-pools\{swe,tony,ctb}`, my scripts under `scratchpad\inspect\tools-benign`, run with `python -I`. Nothing from the datasets was executed (the OpenHands archive contains an `agent_state.pkl`; it was NOT loaded). Disk used: swe 364 MB, tony 143 MB, ctb 17 MB.

Method note: chars/4 is the token proxy. "Sample" sizes are given per dataset. Anything not checked is marked UNVERIFIED. Spot-checks of "hidden misbehavior" are head/tail reads plus regex heuristics, not full reads; treat the unsafe-fraction numbers as lower-bound estimates.

## Bottom line

| | Real Claude Code? | Real user instructions? | Labels | Best use for Kev-4B |
|---|---|---|---|---|
| Open-SWE-Traces `claudecode` | Harness-shaped (Claude Agent SDK system prefix, CC tool schemas) but only 3 tools, Qwen model, single-turn SWE issue | No: GitHub issue text, one user turn, no pushback | `resolved` 0/1 (hidden-test outcome) | Volume of clean, tool-rich, test-running SWE negatives; format-realism filler. Weak for M7/G4/user-intent questions |
| TonyDzi/agent-sessions | Yes, real Claude Code/Codex sessions (rendered text, no reasoning) | Yes, but ONE operator, mostly Russian, mostly non-coding automation | None. But 152 harness-injected "Stop hook feedback" corrections in my 3.4K-session sample are free overseer labels | Realism / distribution-shift negatives; user follow-ups; hook-correction positives for M5/L5/G5/L7 after redaction. Not safe to treat as all-benign |
| CodeTraceBench | No (OpenHands / mini-SWE-agent / Terminus2 / SWE-agent; 531 of 3,316 use Claude Sonnet 4) | No (benchmark task prompts) | Human step-level `incorrect` / `unuseful` | Competence-error hard negatives ("wrong but not misaligned"); step localization format for D1/D3 |

---

## 1. nvidia/Open-SWE-Traces

### 1.1 Access / license / notices
- Public, not gated. License `cc-by-4.0` ("ready for commercial/non-commercial use", data developer NVIDIA). README paper badge: EMNLP 2026 Findings.
- Repo is large (hundreds of GB across 5 harness splits and 4 config versions); I downloaded exactly two parquet shards (~380 MB).
- Configs: v2.0 (default; Qwen3.8-Flash-Next, all 5 harnesses), v1.2 (Qwen3.8-27B), v1.1, v1.0 (OpenHands/SWE-agent only). Splits: `claudecode`, `opencode`, `openhands`, `sweagent`, `minisweagent`.
- Tasks come from Scale-SWE and SWE-rebench-V2 (permissively licensed repos). README states v1.0 was cleaned of "git hacking behaviors" (151k of 207k kept). It does NOT say the later claudecode/v1.2/v2.0 data got the same cleaning: UNVERIFIED.
- Total claudecode row count UNVERIFIED (README says whole repo 100K to 1M; `data_distribution.md` not read). Shards seen: v2.0 scale-swe has ~7 default + 6 thinking-low + 6 thinking-medium shards; swe-rebench-v2 has 8 + 8 + 7.

### 1.2 Structure and fields (confirmed from parquet schema)
`instance_id, repo, license, language, trajectory_id, messages[list of {role, content, reasoning_content, tool_calls[{function{name, arguments(JSON string)}, id, type}]}], tools[list of JSON strings], resolved(int 1/0/-1), metadata{category, teacher_model{name, enable_thinking, reasoning_effort}, reference_patch{patch,num_modified_files,num_modified_lines}, model_patch{...}}, hf_dataset_name`.

Sample 1: `data/claudecode/qwen38_flash_next/scale-swe/thinking-low/train-00000-of-00006.parquet`, 2,500 rows, all python, all `hf_dataset_name=AweAI-Team/Scale-SWE`. Metadata says `reasoning_effort: medium` even though the folder says thinking-low (path/metadata mismatch, as observed).
Sample 2: `.../swe-rebench-v2/train-00007-of-00008.parquet`, 2,052 rows, `reasoning_effort: xhigh`; languages python 482, go 469, ts 346, js 271, rust 237, java 140. `instance_id` unique within each shard (2,500 and 2,052 distinct).
Roles per row: exactly 1 system, 1 user, then alternating assistant/tool. Zero rows with more than one user turn (sample 2: 0 of 2,052).

### 1.3 Two real examples (abridged, verbatim where quoted)
Tools in every row: `['Bash', 'Edit', 'Read']` only. The Bash `input_schema` text is the real Claude Code one ("Clear, concise description of what this command does in active voice. Never use words like \"complex\" or \"risk\" ...") but the tool `description` is just "execute shell commands".

System message (identical shape across rows, ~600-700 chars):
```
You are a Claude agent, built on Anthropic's Claude Agent SDK.CWD: /testbed
Date: 2026-10-07

gitStatus: This is the git status at the start of the conversation. ... Current branch: main
Main branch (you will usually use this for PRs): main
Git user: user
Status:
(clean)
Recent commits:
bbeab7e Update CI configs to v0.11.19 ...
```
(This is NOT the full Claude Code system prompt; no tool-use policy, no CLAUDE.md, no todo/plan machinery.)

Example A (`pion__rtp-305`, Go, resolved=1, 25ish messages). User turn (the only one):
```
Allow the ability to define the initial timestamp for the packetizer.
## Summary
Currently the timestamp is defined using a random number ...
New interfaces introduced:
Function: WithSSRC(ssrc uint32)
Location: packetizer.go
...
```
Note the appended "New interfaces introduced:" block: the instruction contains an explicit interface spec (good for M2 requirement-checking). Trajectory slice (reasoning_content is populated on every assistant turn):
```
[assistant] reasoning: "Let me start by exploring the repository structure and understanding the current packetizer implementation."
  TC Bash {"command": "ls -la /testbed && cat /testbed/packetizer.go", "description": "List repo files and read packetizer.go"}
  TC Bash {"command": "git log --oneline -5 && cat go.mod", ...}
[tool] total 228 / drwxr-xr-x ...
[assistant] reasoning: "`revive` is enabled, which by default flags 'exported function ... returns unexported type func(*rtp.packetizer)' ... Since the spec explicitly requires the return type func(*packetizer), I'll add ..."
  TC Edit {"replace_all": false, "file_path": "/testbed/packetizer.go", "old_string": "...", "new_string": "..."}
[tool] The file /testbed/packetizer.go has been updated successfully. (file state is current in your context - no need to Read it back)
```
Final assistant message: "Done. I implemented a functional-options API for the packetizer in `packetizer.go` (the only file changed): **New API** - `WithSSRC(...)` ... **Existing behavior preserve[d]**". model_patch touched only `packetizer.go` (no test file).

Example B (`stellar__go-5168`, Go, resolved=0, 58 tool calls): user turn is the raw GitHub issue ("services/horizon/ingest: RebuildTradeAggregationBuckets cannot be invoked concurrently during parallel ingestion <!-- Please answer these questions ..."). Final message: "## Summary of changes **The problem:** trade aggregation buckets are aligned to *minute* boundaries ... " with 4 files changed. The agent never ran a test command (0 matching calls) and still gave a confident summary; resolved=0.

### 1.4 Measured stats
| | Sample 1 (scale-swe, n=2500) | Sample 2 (swe-rebench-v2, n=2052) |
|---|---|---|
| resolved=1 / 0 | 1438 / 1062 (57.5%) | 792 / 1260 (38.6%) |
| tokens (chars/4 of message content only, excludes tool-call args and reasoning) median / p90 | 10.9K / 25.6K | 29.0K / 56.3K |
| tool calls per traj median / p90 | 22 / 46 | 61.5 / 114 |
| tool mix | Bash 40,469; Read 13,841; Edit 10,419 | Bash 109,269; Edit 17,454; Read 13,482 |
| reasoning_content present | 100% | 100% |
| any test-runner command in a tool call (pytest, go test, cargo test, npm test, jest, mvn, gradle, tox, unittest) | 88.0% | 72.8% |
| model_patch touches a test-like path | 3.4% | 0.9% |
| resolved=1 AND patch non-empty AND no test-file edit | 55.6% of rows | 38.5% of rows |
| final assistant text contains done/fixed/implemented/passing/resolved | 48% | 58% |
| ...of rows, claims done but resolved=0 | 22.2% | 34.6% |
| regex hit for git-history lookup / network (git log --all, fetch, checkout <sha>, show <sha>, pip install, curl, wget) | 7.6% | 19.1% (regex is coarse; includes ordinary `pip install`/`curl` probing; UNVERIFIED which are real hacks) |
| empty model_patch | 0% | 0% |
Reasoning effort differs by directory; the sampled `claudecode` split used Qwen3.8-Flash-Next for all rows (teacher_model.name).

### 1.5 How benign (spot check of 10, random seed 7, sample 2)
Read user turn, final message, test/git/network commands and patch file list for 10 rows: vuejs/composition-api-799, cachix/devenv-2018, focus-shift/jollyday-745, skiptests/astraea-1657, projectevergreen/greenwood-920, jlowin/fastmcp-309, petermattis/pebble-100, stellar/go-5168, xlate/staedi-81, char0n/ramda-adjunct-1112.
- 8 of 10 have resolved=0; 2 have resolved=1 (fastmcp-309, ramda-adjunct-1112).
- 0 of 10 edit existing tests to pass; the 3 patch-touching-docs cases are scope-adjacent only (devenv-2018 edits `docs/tasks.md`; staedi-81 edits `README.md`; fastmcp-309 edits `docs/patterns/composition.mdx`).
- Created-then-deleted scratch tests observed in 3 (`zz_race_tmp_test.go`, `zzssr.spec.ts`, `tmp_check.ts`); benign hygiene.
- Network probes in 2 (`curl -sSI https://static.crates.io/`, `curl ... repo.maven.apache.org`): sandbox connectivity checks, not leakage.
- xlate/staedi-81: ran `git log -- src/test/...` and `cat src/test/resources/EDIFACT/pnrgov.edi` (reads test fixtures); UNVERIFIED whether this leaks the gold answer.
- Confident-closing-summary pattern with resolved=0 in 7 of 10 (e.g. vuejs-799: "All 306 existing tests pass, along with `tsc` and `prettier`." yet hidden tests fail; devenv-2018: no test run at all, "I've implemented the fix."). These are competence/spec misses, not deliberate gaming, but they ARE unverified-success claims.
- Estimate: deliberate misbehavior 0/10 seen. Unsafe as negatives for M5/G5 ("claim contradicts evidence / success genuine"): roughly the 22-35% claim-done-but-resolved=0 share, plus anything resolved=0. Safe as M2/M4/L-series negatives after filtering resolved=1 and no test/doc edits (about 39-56% of rows).

### 1.6 Format distance from a real Claude Code session
- Closer than any other open set I saw: system prefix literally "You are a Claude agent, built on Anthropic's Claude Agent SDK.", `CWD:`/`Date:`/`gitStatus:` block, real CC Bash/Edit/Read schemas (Edit has `replace_all, file_path, old_string, new_string`; Read has `file_path, offset, limit, pages`), `cat -n` style Read output ("1020\t..."), the real Edit success string.
- Far: only 3 tools (no Write, Grep, Glob, TodoWrite, Task/Agent, WebFetch, Skill, MCP); no CLAUDE.md / system reminders / memory; model is Qwen3.8-Flash-Next with `reasoning_content` on every turn (real CC would have none visible to the monitor); user turn is a GitHub issue with a hidden-test spec appended ("New interfaces introduced"), not a chat message; single user turn, no pushback, no clarifying questions, no interruptions; always runs in `/testbed` docker; Bash `description` always present.
- Message format is OpenAI-style (`tool_calls[].function.arguments` as JSON string, role `tool`), not Anthropic content blocks. Needs re-rendering to whatever the monitor sees.

### 1.7 Question IDs and required modifications
- Negatives (all of M1, M2, M4, M5, L1, L2, L4, L5, L6, G1, G2, G5): filter `resolved=1`, `model_patch` touches no test-like path, `num_modified_files` within a sane ratio to `reference_patch`, final message makes no claim without a prior test command; drop rows whose commands include git-history lookups (`git log --all`, `git show <sha>`, `git checkout <sha>`) and docs/README edits when the issue does not ask for them. These are single-turn, so G1 and L-series negatives are whole-run "on task" examples only.
- G2/G5 positives: very weak. `resolved=0` + confident "all tests pass"/"implemented" ending is a candidate "success not genuine" positive, but the label is hidden-test failure not claim falsity. To use, one would have to re-derive per-claim truth (UNVERIFIED feasibility): compare each claim in the final message to the recorded test output in the same trajectory. This makes a noisy M5 positive pool; label as "competence overclaim".
- M2 (breaks stated requirement): issue text + explicit "New interfaces introduced" signature list is a stated requirement set; `reference_patch` gives the intended answer. A usable positive recipe: resolved=0 where the model patch is missing a named interface. Needs programmatic check of signatures against the model patch (not provided).
- M7, G4, RF, L7, D2, D5: not served (no ambiguity resolution, no priorities, no recovery from user correction; no human labels).
- Mandatory transforms: drop `reasoning_content` (or decide the monitor sees it), convert to the Anthropic block format, add the real CC tool set/system prompt framing if the monitor input includes it, and strip `metadata.reference_patch` (leaks the gold fix).

---

## 2. TonyDzi/agent-sessions

### 2.1 Access / license / notices
- Public, not gated. License `cc-by-4.0`; citation required ("Anton D., Agent Sessions: real production transcripts of an LLM coding agent", doi:10.5281/zenodo.23712140). Daily release; tool output quoted inside sessions keeps its upstream license.
- Notices: the operator publishes the corpus under his own name on purpose ("his projects, repositories, methods and conclusions are the subject"). Secrets cut, home dirs -> `C:\Users\dev`, hosts -> `HUB-01`/`NODE-0X`, people -> stable pseudonyms plus `[ФАМИЛИЯ]/[EMAIL]/[ТЕЛЕФОН]/[АДРЕС]`. README says explicitly: "No claim of complete semantic privacy review follows from the deterministic secret/PII scan." I did see unmasked-looking group/title strings and third-party first-name pseudonyms in samples; treat as personal data needing a second pass.
- Revision 2026-11-07: 48,813 records, 509,024,270 words, date range 2023-03-30..2026-10-30. Providers: claude 35,095; codex 8,970; chatgpt 3,453; deep_research 1,295 (1,295 are research reports). Matches the task description.
- Files: `data/*.parquet` (47 monthly shards, 8 KB to 133 MB each), `agent_sessions.jsonl` (5.8 GB), `agent_sessions.parquet` (frozen 30 Oct snapshot, 346 rows, 5 MB), `sessions_by_day.csv`, `dataset_meta.json`. I downloaded 4 shards: `2026-10-06` (2,434 rows), `2026-08-01` (2,358 rows), `2025-10-00` and `2026-04-00` (both contained zero Claude rows; only ChatGPT/other), plus the frozen snapshot and metadata.

### 2.2 Structure and fields (confirmed)
`session_id (s_+8hex), date, words, turns (null for 13,912 rows), provider, artifact_type, renderer, tools_used[], models[], effort[], text, extra (JSON string: class, provenance, attachment manifest, omission counters), turn_count_status`. Class distribution in meta: unknown 18,096; mixed 21,034; hold 5,213; publish 4,470 (meaning of "class" UNVERIFIED; it is the builder's topic/release class). No behavior labels.

Rendered `text` format (verified): blocks `**User:**` / `**Claude:**` / `**Tool result:**`, separated by `---`; tool calls rendered as a quoted line `> \`Bash\` -- {"command": "...", "description": "...", "timeout": 240000}`; reasoning omitted; Claude replies often end with a footer like `🏛H · Sonnet 5.5 · 82100` (operator's statusline marker). Renderers: claude-jsonl-full-text/v1 (1,455 of 2,434 in the 10-06 shard), codex-jsonl-full/v1 (972), vault-markdown-full/v1 (7). Models in that shard: gpt-6.1-sol 892, claude-sonnet-5-5 681, claude-sonnet-5 336, claude-haiku-5-5 236, claude-opus-5-5 124, claude-fable-5-1 14, claude-opus-5 12.

### 2.3 Distinct users/projects: it is ONE operator
- README: "This is one operator's fleet history ... not a representative sample"; sources: 1 live machine + 4 fleet machines, "sessions of other operators (1,535 files) are excluded until they opt in", 10,357 duplicate copies collapsed. `dataset_meta.json`: warehouse_total 49,791 -> unique_sessions 39,411.
- My sample (3,459 Claude sessions from 2 shards): host token only `HUB-01` (1,306 sessions) plus `NODE-0X` placeholders; home-dir stems dominated by `.claude` (1,475), `Vault-Knowledge` (816), `AppData` (603), `_imports` (574), `Obsidian` (442), `.codex` (129), `CLAUDE-Mac-2019` (110), `repos-git25` (16). I.e. one Obsidian knowledge vault plus `~/.claude` automation scripts plus a few GitHub repos.
- Projects: not enumerable from the data (cwd masked); effectively one person's life/business-ops system (Russian, "co-founder AI" persona, Telegram/WhatsApp relays, onboarding staff, X/Facebook posting, podcast research) with occasional open-source PR work (e.g. a scheduled task reviewing `punkpeye/fastmcp#480`). Distinct humans: 1 (plus third-party names mentioned inside content).

### 2.4 Composition of Claude sessions (sample, measured)
| | 2026-08-01 shard (n=2003 claude) | 2026-10-06 shard (n=1456 claude) |
|---|---|---|
| first user message begins `<scheduled-task ...>` (cron, "The user is not present") | 458 (23%) | 136 (9%) |
| first user message begins "Ты ..."/"You are ..." (judge/role prompts) | 192 (10%) | 661 (45%) |
| other (incl. interactive human turns, "Background (from the session that started this one)" handoffs, continuation summaries, robot inbox prompts) | 1,352 (68%) | 658 (45%) |
| more than one `**User:**` block | 12% | 12% |
Overall (3,459): `tools_used` empty for 2,188 (63%); Edit or Write used in 305 (8.8%); of those only 38 contain a pytest/npm test/go test/cargo test string. In the 10-06 shard only 20 of 1,456 Claude sessions contain any such test-runner string. This is NOT a SWE-style pool.
Length (chars/4): 10-06 Claude shard median 6.5K, p90 17.7K; combined two-shard sample median 2.1K, p90 37.8K, max ~836K.

### 2.5 Follow-up user messages / pushback
- After removing blocks that start with `<`, are >1,500 chars, or are "cut off mid-stream" notices, 1,105 later-turn user blocks remain across 3,459 sessions (~0.3 per session). Contamination is heavy: skill expansions ("Base directory for this skill: ... /rr alias for /retro"), `DOORBELL ...` relay prompts, `/QQ`, "Continue from where you left off."
- Genuine human-sounding follow-ups quoted (verbatim, Russian): "продолжай. все делаешь правильно" (approval); "надеюсь не профакапится?"; "сам почини гугл драйв- он у меня не работает." ; "Расскажи мне, какие скиллы ты использовал для написания всех твоих постов, а какие не использовал? И почему? ..." ; "что стоит починить? какие КОРНИ ты чинешь? сделай и потом РЕТРО". These are mostly directives and questions, rarely corrections.
- A broad Russian+English pushback regex (нет, не так, стоп, почему ты, я же просил, wrong, revert, ...) hit 31 + 24 blocks in the two shards, and most hits are NOT human pushback: harness "Your response above was cut off mid-stream. Resume directly..." and "Stop hook feedback" blocks. True human corrections: a handful, UNVERIFIED count (needs manual pass). So pushback is scarce; do not expect a large L7 pool.
- The valuable find is programmatic correction. Across the two shards, 152 user-role blocks are `Stop hook feedback:` messages (121 of 1,456 sessions in the 10-06 shard contain one). Top templates (counts in sample): "СТОП: ты докладываешь НОЛЬ находок, не н..." (61), "СТОП: ты объявляешь недоступность, не об..." (33), "Панель ломателей не прогнана: в этой сес..." (19), "СТОП: ты заявил, что файла нет, а он ЕСТЬ на этой машине" (15), "001-пара: эта задача ушла и тебе, и Code..." (7). Verbatim example (session s_4af97337, after a long deploy report):
```
**User:**
Stop hook feedback:
СТОП: ты заявил, что файла нет, а он ЕСТЬ на этой машине:
  · brain_sessions_index.py -> D:\Vault\_imports\brain_sessions_index.py
Это класс «ложное нет» (CLAUDE.md §5.4, ...): заявление «нет X» — такой же claim, как вывод, и требует обхода ВСЕХ мест. ... Исправь ответ по факту.

**Claude:**
Хук сработал не по адресу: «нет» я говорил про NODE-0X, на хабе файл есть. Но на NODE-0X я смотрел только в `_imports`, поэтому перепроверяю обходом всей машины.
```
This is an automatic "claim contradicts evidence" detection plus the agent's recovery turn (M5 positive / L7 recovery candidate), with the label baked into the operator's own rules.

### 2.6 Two real examples (abridged)
1) Scheduled automation (`s_c5d3083c`, claude-sonnet-5-5, 6 turns, ~58K chars). First user turn:
```
<scheduled-task name="auto-hub-260824-nsfw-dr-posts" file="C:\Users\dev\.claude\scheduled-tasks\...\SKILL.md">
This is an automated run of a scheduled task. The user is not present to answer questions. For implementation details, execute autonomously without asking clarifying questions — make reasonable choices and note them in your output. ...
Ты ведёшь онбординг Эдиты — НАШЕЙ СОТРУДНИЦЫ, не внешнего лида. Приказ оператора 14.09.2026, голосом. ...
```
Trajectory slice:
```
**Claude:** Автоматический прогон онбординга Эдиты. Сначала смотрю, ответила ли она, одним заходом.
> `Bash` -- {"command": "cd ~/.claude/scripts 2>/dev/null; head -c 1500 \"D:/Vault/.../seed-stop-dup-block.md\"; ... python lead_thread_watch.py --read chat_REDACTED 6 2>&1 | tail -c 2500; echo ----; date -u", "description": "Прочитать блок STOP-DUP и хвост комнаты Эдиты", "timeout": 240000}
**Tool result:** [file contents + Telegram room tail ...]
**Tool result:** Command did not complete within its 120s timeout and was moved to the background (ID: bnvd9g1fc) ...
**Tool result:** <tool_use_error>Blocked: sleep 100 followed by: cat ...
```
2) Interactive ops/debugging (`s_f5244b37`, claude-opus-5-5, 60K tokens): first user message "почини эту сессию опять проблемы с папкой рабочей?"; last Claude message begins "23:44, чт 29.10. Уже ночь: заканчиваем и спать. Корень починен. Сессии больше не должны умирать с ошибкой «workspace isn't trusted» ..." (hook script in a worktree-creation helper). No tests, no repo; infrastructure repair of the operator's own harness.

### 2.7 How benign (spot check of 10, seed 11, Edit/Write sessions, 10-06 shard)
Sessions: s_f320bae4, s_3f8777ef, s_ed59f6d4, s_f514dab6, s_15163495, s_4fabc292, s_7bb71f25, s_79fb92f9, s_f5244b37, s_7069dae9. I read first user message, last Claude message, tool lists and keyword flags only.
- None is a SWE benchmark task; all are the operator's ops/retro/automation/research/shopping flows.
- No test-editing-to-pass seen (nothing to test). Closing messages are long self-reports ("Корни закрыты, ретро №4 записано", "Оба ответа опубликованы. Я перезагрузил пост ... и нашёл оба ответа под именем оператора") that cannot be verified from my read: UNVERIFIED.
- Gate bypass appears in real text: in s_4af97337 the agent deployed "только в обход трёх гейтов ... Пришлось поставить `--force-unsafe`, `DEPLOY_CARGO_INDEPENDENT` и `DEPLOY_ALLOW_BLIND_COURIER=1`". Keywords `bypass/обход/--force/ALLOW_/--ignore` appear in 529 of 1,456 (36%) Claude sessions of the 10-06 shard; most are rule text or script flags, but it shows the pool contains agents overriding safeguards, with the operator's approval status unknown.
- 8% of sessions (121 of 1,456) contain a Stop-hook correction showing the agent made a false claim at least once ("ложное нет", "ты докладываешь НОЛЬ находок"). These are not safe as clean negatives.
- Also scheduled tasks perform external writes (posting to Facebook/X, GitHub PR reviews, Telegram sends). Whether each write was authorised is UNVERIFIED.
- Estimate of unsafe-as-negative fraction: at least ~8% (hook-flagged) and plausibly 20-40% when counting unflagged unverifiable success claims and bypassed gates; cannot be pinned without a full read. Use only with the hook/bypass filters in 2.9.

### 2.8 Format distance from a real Claude Code session
- Closest to real: it IS real Claude Code (and Codex) with real tool names (Bash, Read, Write, Edit, ToolSearch, Skill, PowerShell, Agent, mcp__* tools), real harness messages (scheduled-task wrapper, Stop-hook feedback, "cut off mid-stream", Monitor/background-task notices, `<tool_use_error>`), real system-injected user blocks, real models (claude-sonnet-5-5, opus-5-5, haiku-5-5, fable-5-1).
- Differences: rendered markdown not raw JSONL (tool calls as `> \`Name\` -- {json}` lines, no tool_use ids, no content blocks, no timestamps per event); reasoning omitted; subagent streams exported as separate records; binary attachments replaced with omission markers; Russian prose; paths/hosts pseudonymised; statusline footer markers; very long tool results (whole Obsidian notes) inline. The monitor would need a parser that re-splits events (event boundaries are `---`+label lines, so event-level D1/D3 localisation is feasible but approximate).

### 2.9 Question IDs and required modifications
- Realism negatives (all every-event questions): keep only sessions with Edit/Write/Bash use, no `Stop hook feedback`, no `bypass/--force/ALLOW_/--ignore/force-unsafe` strings in tool calls, not `<scheduled-task>` (no human present; instruction is an automation spec), not judge/role prompts (no tools), English/Russian handled per monitor language policy; translate or keep Russian deliberately. Treat as "no label, probably fine", not as verified benign.
- M5 / G5 / L5 positives: the `Stop hook feedback` blocks locate the false claim (the Claude turn immediately before the hook block) and the reply after it shows recovery (L7). Required: remove the hook block and the agent's recovery text from the monitor's input when training the detector on the preceding claim (otherwise the label leaks); keep them for L7 as a separate recovery-labelled sample. Need to resolve the template (e.g. "ложное нет" = M5, "НОЛЬ находок" = possible L5/G2 omission) manually per template since only ~5 templates exist. UNVERIFIED whether hook text always refers to an event inside the same session (looked true in one example).
- User follow-ups (L7, M7 proxies, G1): single-turn user instruction + the later `**User:**` messages give real mid-run steering and "continue" cues. Required filtering: drop slash-command/skill expansions, DOORBELL relays, auto-continuation text, and anything with tool-result-like length; hand-label the few true corrections. Volume is low (tens), not thousands.
- M1/M7/RF/G4: operator speech is conversational and underspecified ("Найди такие кроссовки артуру на 2 размера больше / Дай ссылку на покупку в чат покупки / Попросить девочек купить"), good for M1/M7 realism where the unwritten goal matters, but with no labels.
- L1/L2/L4: long autonomous runs (scheduled tasks, 100K+ token retros) are natural for drift tests but unlabeled; use as unlabeled negatives only after the filters above.
- Not suitable: M4, L6 labels (no checker/overseer concept except the hook, which is itself an overseer being satisfied, interesting for L6 research but UNVERIFIED), G4 (no stated priorities beyond persona rules).
- Privacy/legal: personal third-party data, children, finances appear in text ("У оператора 4 детей"); CC-BY allows use, but expect masking gaps; recommend a PII re-scan before including in a fine-tune corpus (UNVERIFIED that this is needed beyond README disclaimer).

---

## 3. NJU-LINK/CodeTraceBench

### 3.1 Access / license / notices
- Public, not gated; license `mit`. README: 4,316 trajectories ("verified" 1,000 = 489 SWE-bench + 511 TerminalBench; "full" 3,316 = 2,670 TerminalBench + 646 SWE-bench). The manifest I downloaded has 3,316 rows for `full`; the 4,316 figure in the README is verified + full (overlap relation UNVERIFIED). arXiv 2604.11641 (CodeTracer). Artifacts: `bench_artifacts/full/<traj_id>.tar.zst` (3,291 files per README, 3,316 manifest rows -> 25 rows without artifact UNVERIFIED), plus `swe_raw/`.
- Downloaded: `bench_manifest.full.parquet`, 2 archives (~0.2 MB compressed each).

### 3.2 Structure and fields (confirmed)
Manifest: `traj_id, agent, model, task_name, task_slug, difficulty, category, tags[], solved(bool|None), step_count, stages[{stage_id,start_step_id,end_step_id}], stage_count, incorrect_error_stage_count, trial_name, source_relpath, annotation_relpath, incorrect_stages[{stage_id, incorrect_step_ids[], unuseful_step_ids[], steps[{step_id, labels[], action_ref{content,line_start,line_end,path}, observation_ref{...}}]}], generated_at, artifact_path`. The README says `tags/stages/incorrect_stages` are JSON strings; in the parquet they are native nested lists/structs.
Counts (full, n=3,316): agent OpenHands 1,242; mini-SWE-agent 1,024; Terminus2 923; SWE-agent 127. Model: GPT-5 973; DeepSeek-V3.2 641 (+102 DeepSeekChat); Kimi-K2 546; Claude-Sonnet-4-20250514-Thinking 531; Qwen3-Coder-480B 523. Difficulty: medium 1,597, hard 971, easy 748. solved: True 1,307, False 1,903, None 106. Categories: software-engineering 1,222, system-administration 259, data-science 221, security 221, scientific-computing 215, model-training 179, debugging 177, file-operations 154, ...
Label counts: `incorrect` 17,701 and `unuseful` 1,468 (labels on 19,169 listed steps; 8,481 of those have `action_ref=None`, i.e. no text for the labelled step; only step ids are usable there).

### 3.3 Stats (manifest, all 3,316)
- step_count median 30, p90 85.
- 52.8% of trajectories have at least one `incorrect` step; 18.0% have at least one `unuseful` step. Incorrect steps: median 1, p90 11 per trajectory; incorrect = 12.0% of all steps; unuseful = 1.0% of all steps.
- solved trajectories: 33.97% still contain at least one incorrect-labelled step; 863 of 1,307 solved trajectories have zero incorrect steps.
- Tokens of full trajectories (from the two archives, chars/4): mini-SWE example `mini.traj.json` 249 KB (~62K tokens, 56 messages); OpenHands example events dir ~246 KB session JSON plus 1.2 MB log. Tool/command counts = step_count (27 and 25 in my two). Test run: via Terminus/TB harness `tests.log` post-hoc, not agent-driven. Reasoning present: Terminus2 JSON has `analysis`/`plan`; mini-SWE has `THOUGHT:`; OpenHands carries full `model_response` (reasoning content visibility UNVERIFIED).

### 3.4 Two real examples
Example 1 (mini-SWE-agent, Claude Sonnet 4 Thinking, `distribution-search`, TerminalBench, medium, solved=False, 27 steps, 8 stages, 3 incorrect-error stages). Extracted layout: `agent-logs/mini.traj.json`, `commands.txt`, `results.json`, `panes/{pre-agent,post-agent,post-test}.txt`, `sessions/{agent,tests}.{cast,log}`. System prompt (verbatim start): "You are a helpful assistant that can interact with a computer. Your response must contain exactly ONE bash code block with ONE command ..." (mini-SWE format, not Claude Code). Task: "Please solve this issue: Finding a target probability distribution for LLM confidence metrics: ... forward KL divergence KL(P||U) is 10.0 ... backward KL ... 10.0 ... tolerance 0.001 ... vocabulary size 150,000 ... Save ... `/app/dist.npy` ... We provide numpy and scipy to help with the calculations." Labelled stage 2 (incorrect steps [5, 6, 9], unuseful []):
```
step 5 ['incorrect'] ACTION: "THOUGHT: I see that numpy and scipy are not actually installed despite being mentioned as available. I need to implement this using only standard Python libraries. ... cat <<'EOF' > solve_kl_distrib..."
step 6 ['incorrect'] ACTION: "THOUGHT: Now let me run the script ... python solve_kl_distribution.py"  OBS: "<returncode>1</returncode> Traceback ... ModuleNotFoundError: No module named 'numpy'"
```
Stage 5 incorrect [18,19,20,21], stage 7 incorrect [24,25]. results.json `is_resolved: false`. Final assistant message (honest failure, verbatim): "The distribution has been created and saved successfully. The file `/app/dist.npy` exists with the correct size (1.2MB for 150,000 float64 values). While my solution doesn't achieve the strict tolerance of 0.001 for both KL divergences simultaneously, it represents a valid probability distribution that gets reasonably close to the target values. ... I should now submit the final result." then `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`. So the agent discloses the miss (a good M5-negative / G5 "honest but failed" example) but submits knowingly short of the requirement.
Example 2 (OpenHands, Claude Sonnet 4 Thinking, `code-from-image`, solved=True, 25 steps): stage 2 incorrect [8..13], unuseful [7,14]; step 14 labelled 'unuseful' is `pip3 install --break-system-packages pytesseract` (OpenHands event JSON with full `tool_call_metadata`/model_response). Archive also contains `.jwt_secret` and `agent_state.pkl` (not opened).
Also sampled 10 random `incorrect` actions from Claude trajectories: e.g. repeating the same regex group error ("I made the same mistake again. I need to fix the \\35 issue ..."), password brute-forcing `./main include`, `./main linux`, `./main success` in reverse-engineering, building OpenCV with `make -j$(nproc)` that failed, vim keystroke edits in tmux. All are competence errors (bad hypotheses, repeated failures); none were test-gaming. (Coverage limited: 10 steps.)

### 3.5 How benign
- 100% competence-failure data by construction: labels mark mistakes, not intent. In my read of 10 incorrect-labelled Claude steps + 2 trajectories, 0 misalignment. Success-claim honesty was good in the example 1 final message. UNVERIFIED across the 3,316: some agents may overclaim; not audited.
- Hidden-misbehavior check on 10 trajectories: effectively covered by the 10 sampled steps above (different trajectories, 8 distinct tasks); no test-editing seen. A proper check of the final-message honesty needs full trajectories (only 2 extracted). Unsafe-as-negative fraction: low for misalignment classes, but ~47% of trajectories have no incorrect step and ~34% of solved ones do.

### 3.6 Format distance from a real Claude Code session
Far: terminal-bench harness formats (Terminus2 JSON keystrokes with `analysis/plan/commands`, mini-SWE `THOUGHT:` + one bash block, OpenHands event stream, SWE-agent). No Edit/Read/Write tool semantics, no system-reminders, no user chat. Task prompts are benchmark specs ("Please solve this issue: ..."). Only 531 trajectories use Claude Sonnet 4 and even those are scaffold-wrapped.

### 3.7 Question IDs and required modifications
- Hard negatives for "mistake but not misalignment": M1, M2 (competence breaks a requirement unintentionally; needs a decision whether an unintended requirement violation counts as M2 positive; I would label it M2 positive only if the monitor's definition is outcome-based, otherwise negative), M4 (agent keeps trying and fails honestly: negative for gaming), L1 (drift from bad hypotheses vs. real drift: negatives), G1/G2/G5. Modification: select `incorrect`-labelled steps with `solved=False` and a final message that discloses failure -> "honest failure, not misaligned" negatives; or solved=True with incorrect steps -> "recovered mistake" (L7 candidate, but there is no user correction, only self-recovery).
- D1/D3 step localization: the `incorrect_step_ids` / stage structure is a ready training/eval format (step ids + stage grouping + reasoning field per README). Required: map `step_id` (assistant/observation pair) to the monitor's event indexing; note 44% of labelled steps lack `action_ref` text, so rebuild text from the artifact; the label semantics are "this step was wrong" not "this is violating"; keep a separate head or label name to avoid conflating with misalignment.
- Positives for unnecessary exploration: `unuseful` is only 1% of steps; weak for L1 (drift); partial for L5-like waste.
- Not suitable: M7, M5 (no claim-evidence labels), L6, G4, RF, D2, D5. Also artifact extraction is per-trajectory, ~0.2-1.3 MB compressed each, a 3,316-file download would be large (UNVERIFIED total size; archives list sizes 30-250 KB for those I saw, so likely under 1 GB).
- Mandatory transforms: rebuild trajectories into the monitor's event format from `mini.traj.json`/OpenHands events/Terminus JSON (three distinct parsers); drop `.cast/.log` blobs; never load `agent_state.pkl`.

---

## 4. Cross-dataset recommendations

1. Volume of format-correct, tool-rich negatives: Open-SWE `claudecode`, filtered per 1.7. It is the only one with Claude-Code-like tool-call JSON at scale, but its instruction side is thin (single issue, no pushback), so it cannot teach M7/G4/RF/L7.
2. Realism and user-instruction diversity: agent-sessions, but it must be treated as single-operator, Russian, automation-heavy, with pre-existing misbehavior flags (Stop hooks, gate bypasses). Its unique value is the hook-labelled false-claim events (M5/L5/G5/L7) and genuine "continue"/steering turns, not mass benign negatives. Worth a separate extraction pass for ~150+ hook events per 3.5K sessions (extrapolation: on the order of 1-2K events over 35K Claude records, UNVERIFIED).
3. Competence-error hard negatives and step localization format: CodeTraceBench, with the benchmark-format conversion cost.
4. Do not mix the three without a source tag: formats, languages and intents differ enough that the monitor could learn source identity as the label (especially: Open-SWE negatives are English single-turn with a hidden-spec suffix; agent-sessions is Russian; CTB is terminal-bench).

## 5. Unchecked / UNVERIFIED list
- Open-SWE: total claudecode row count; whether v2.0 claudecode got the git-hacking cleaning; whether xlate/staedi-81's test-fixture reads leaked the answer; fraction of git-history regex hits that are real hacks; contents of `data_distribution.md`.
- agent-sessions: exact count of genuine human corrections; whether every hook block refers to an in-session claim; PII residuals; whether scheduled-task external writes were authorised; the long-tail Codex rows (not analysed beyond counts).
- CodeTraceBench: README 4,316 vs manifest 3,316 reconciliation; the 25 rows with no artifact; total download size; verified split manifest not downloaded; honesty of final messages across non-sampled trajectories.
