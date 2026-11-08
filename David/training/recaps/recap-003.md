# Recap 003: Shared renderer frozen and independent GPU smoke started

## What was accomplished

The renderer interface is frozen in code commit1c77479. The parent ran the
complete exact-tree suite:23 tests passed in4.34 seconds. The worker's planted
heading mutation exited1, and the restored suite exited0. The worker's22
tested file hashes matched. The committed23-file slice adds fixture byte
attributes and passed the staged secret scan with zero findings.
VALIDATION-LOG records the renderer gate with its code hash, and DAVID.md
carries the module interface milestone. T02 is done.

The concurrency100 setting remains verified by a fresh host app-server
config/read. DNS is working on both host and container paths, including an
authenticated Harbor request. Neither issue requires more repair work.

## State of each step

Setup is active because the actual source-backed Claude task run is still
unavailable. Renderer work is complete. Trainer patches and interpolation are
implemented and GPU smoke is now independent of both setup and rendering.
Records, labels, training, selection and evaluation have not started.
No checkpoint or calibration handoff exists, and the goal remains active.

## Key intelligence

Owner MSG005 explicitly removes the earlier dependency waits. T02, T03 and
T04 must proceed independently of the agent-run source blocker. Do not
reintroduce that wait on recovery. The trainer note has been corrected.

The hidden persistent smoke launcher is PID31068. Its exact command is
`python -m modal run --detach src/intent_training/modal_app/trainer.py`.
Read results/trainer/modal-smoke-process.json and the stdout/stderr paths
there before relaunching anything. At the parent check, the pinned Linux image
was saving. The actual Modal app and function call IDs are to be written to
results/trainer/modal-smoke-call.json immediately after spawn. The remote
job will use only app and volume intent-monitor-training. Do not modify
the runtime deployment or its weights volume.

The agent supervisor PID11792 ended with blocked_preparation at00:44:31 EST.
Its source_ready flag is false and image_ready is true. It produced no task
trace. Source archive session95734 may still be alive; check before retrying
the exact command in notes/agent-runs.md. A stalled source takes the specified
same-objective quota redistribution. This does not delay renderer or GPU work.

The local torch package was left incomplete by an interrupted installation.
The renderer gate uses the actual pinned tokenizer.json directly and passes.
Resolve GPU checks in the Linux image rather than waiting on local torch.

## Clock

The default latest_training_start remains04:40 EST and agent_run_cutoff03:25 EST
on2026-11-08. Recompute both from the measured H100 throughput as soon as it
arrives. The selected calibrated handoff is due08:00 EST.

Recorded Anthropic spend is0.0000111 USD. Generation reserve is76 USD and the
agent-run allocation is123.95 USD. The shared spend lock is results/spend.lock.

## Immediate next steps

Recover the persistent Modal smoke job, record its app/call IDs and finish the
identity, resume, kernel and pass-cap measurements. Build registered converters
against the frozen renderer in parallel. Continue source preparation only
within its bounded recovery, then use same-objective fallbacks when needed.

A full Codex restart is now safe for the saved code and worker checkpoints.
On resume, execute task.md Section0 completely before any action, including
the MESSAGES gate. All owner messages through MSG005 are handled. The goal
must remain active until the trained handoff and every measured report exist.

Active task anchor: TASKLIST.md:L18
