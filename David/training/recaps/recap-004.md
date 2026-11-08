# Recap 004: Restart checkpoint with detached H100 smoke

## What was accomplished

The next Codex launch loads an effective limit of 100 spawned subagents.
A fresh process of the installed host app server verified that setting and
its user configuration source. DNS and HTTPS now work from both host and
container, and an authenticated Harbor request succeeded. No network
settings were changed.

The shared renderer is frozen and its gate passed. All 23 exact-tree tests
passed, the planted byte mutation failed, and restoration passed. The runtime
milestone is in DAVID.md. After the required pull and rebase, the renderer's
publication hash is f0239e5 and the scaffold's is db7e8d0. Scoped Git diffs
confirmed that both tested trees are unchanged from their earlier hashes.
Earlier recaps and validation rows retain those historical hashes.

## State of each step

Setup remains active with its source-run fallback. Renderer work is done.
Trainer patches and interpolation now have 13 passing CPU tests, including
the actual torch optimizer, scheduler, random-state continuation and merged
endpoint checks. H100 smoke is detached and running independently.
Records and labels have not been built. Training, selection, calibration
and evaluation remain pending. The goal remains active and incomplete.

## Key intelligence and live work

The current detached Modal smoke app is ap-zxnGssuqlFFloGPPMbwCGg and its
function call is fc-01M6WV8Y5EN1MPVCC7B2623WRY. The IDs are saved in
results/trainer/modal-smoke-call.json. The host launcher was PID 9392 and
its logs are results/trainer/modal-smoke-retry-stdout.log and the matching
stderr file. The detached remote call continues when the host launcher exits.
Use notes/trainer.md for the result retrieval and next GPU checks.

An earlier app failed before smoke computation because the remotely imported
module had a flat source path. That local-versus-container path defect is
fixed. It was not a training crash and does not consume the run retry.
Actual identity, resume, kernel and pass-cap GPU measurements are still pending.

The prior local torch installation has been repaired. The worker reports all
13 CPU extension tests passing in 5.00 seconds. The pinned tokenizer is cached
at data/tokenizer. The renderer caller contract is notes/renderer.md.

Agent source preparation did not finish within its supervisor's 300-second
wait. The completed supervisor wrote blocked_preparation, with image_ready
true and source_ready false. It produced no Claude task trace. Check source
download session 95734 before retrying the exact command in notes/agent-runs.md.
If unavailable, redistribute those quotas within the same objective. Do not
hold T02, T03 or T04 for source runs: owner MSG005 explicitly removed that wait.

## Clock and spend

Until H100 throughput is measured, latest_training_start is 04:40 EST and
agent_run_cutoff is 03:25 EST on 2026-11-08. The selected calibrated handoff is
due at 08:00 EST. Recompute the two clock values from measured throughput.

The recorded Anthropic probe spend is 0.0000111 USD. The generation reserve
is 76 USD and agent-run allocation is 123.95 USD. Every spend writer must
use results/spend.lock. No agent trajectory API job has completed.

## Immediate next steps

Resume the existing goal after fully quitting and reopening Codex. Execute
task.md Section 0 completely before any other action, including the MESSAGES
gate. All owner messages through MSG005 are handled and must not be replayed.
Read the anchored row, retrieve the detached smoke result and finish measured
GPU parity and throughput. In parallel, fan out registered source converters
and constructions against the frozen renderer, then the prescribed Sol and
Terra teacher batches. Keep the training clock ahead of source polishing.

No selected checkpoint, calibration.json or long_context.json handoff exists
yet. Do not mark this goal complete until every handoff and measured report
obligation in task.md has been satisfied.

Active task anchor: TASKLIST.md:L18
