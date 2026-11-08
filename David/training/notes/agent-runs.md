# Isolated Claude Code runs

The implementation-task metadata has columns `instance_id`, `namespace`, `completion_path`, `new_completion_path`, `project_path`, `function_name`, `prompt` and `need_read`. The prompt is a list of variants. Inspection used the first variant of each of the first three actual rows. No dataset code was executed. The required archive is `Source_Code.tar.gz` in `duc-anh-2002/SWE-Misbehavior`.

The ambiguity data is a JSON list. Exactly 100 downloaded rows have `dataset = SWE-Bench Pro`. Its task identifiers are in `original_task`; the variant identifier is separate. The removed values and expected questions are in `removed_segments` and `expected_questions`. Actual coding rows were inspected separately from the noncoding rows. The official upstream metadata at <https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro> includes `docker_image` and `dockerhub_tag`; `scripts/agent_run_lhaw_prepare.py` joins exact task identifiers without running dataset scripts.

## Durable state at 00:39 EST

The Docker image `intent-agent-run:latest` built successfully from cached `node:22` and installed the official `@anthropic-ai/claude-code` package. Initial image pulls failed on registry DNS. The cached build and the independent cached-image install later succeeded after npm took about four minutes. The independent image-install container is named `intent-agent-image` and exited successfully; it contains no host mounts or credentials.

The source archive first failed in Hugging Face Xet's CDN request. A standard HTTPS retry with Xet disabled is active in command session `95734`. At 00:39:54 EST its incomplete cache file remained zero bytes. No source extraction marker exists yet. The exact command is:

```powershell
& scripts/with_keys.ps1 -EnvFile 'C:/Users/david/Documents/GitHub/classifier-for-metagaming/.env' -Program '.venv/Scripts/python.exe' -ProgramArgs @('-I','scripts/agent_run_prepare.py')
```

The detached supervisor has launcher PID `17380` and Python PID `11792`. Its actual state is `results/agent-runs/supervisor.json`; output and errors are `supervisor.stdout.log` and `supervisor.stderr.log` beside it. It waits at most 300 seconds for the already running preparation. If both image and safe extraction marker exist, it prepares actual SWE workspaces and starts 20 workers. If preparation remains unavailable it writes `blocked_preparation` and exits. This is a supervisor launch, not a successful Claude task launch. At this checkpoint no task trace exists and agent-run API spend is zero.

Restart after correcting source access with:

```powershell
& scripts/agent_run_start.ps1
```

The launcher uses an explicit PowerShell `ProgramArgs` array through `agent_run_supervisor.ps1`. Passing `-I` as an array through the command-line `-File` boundary was tested and failed as an ambiguous PowerShell parameter; that failed launch did not run a job. The corrected launcher produced the Python state file successfully.

Each actual task receives a new isolated work directory and its own home directory, with no host-sensitive mounts or Docker socket. The API key is inherited from process memory using Docker's variable-name forwarding. Jobs alternate Haiku 5.5 and Sonnet 5.5, reserve USD 0.50 before launch, and use 12 turns, 600 seconds and the 03:25 EST cutoff. Jobs retain `stdout.jsonl`, native session files beneath `home/.claude/`, before/after hashes, textual diffs and AST boundary evidence. Ledger changes use `filelock.FileLock` on the shared `results/spend.lock`. Unknown billing retains the whole reservation conservatively.

The function checker compares all text outside the target function body and all changed file names. Signature and surrounding-context changes fail. Unsupported or unparseable targets produce an unknown result instead of a fabricated clean label. The archive extractor rejects traversal, symlinks, hardlinks, absolute paths, backslashes and Windows drive syntax.

## Validation

The command `.venv/Scripts/python.exe -I -m unittest discover -s tests -p test_agent_runs.py -v` passed 3 tests at this checkpoint. They demonstrate function-body edits passing while context and signature mutations fail, unsafe archive members being rejected, and concurrent reservations respecting the cap while unused credit is released. No live Claude trajectory validation has passed yet.

The lhaw environment join failed with elevated host DNS error `getaddrinfo failed` before downloading upstream metadata. Its container path remains unavailable. Do not substitute a generic container or manufacture a continuation. If source or environment access stays blocked, redistribute the measured missing quota through the orchestrator.
