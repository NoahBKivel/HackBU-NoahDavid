# Training Build Status

Last updated: 2026-11-08 00:51:35 EST

Active work: T02 renderer is complete and T03/T04 GPU smoke work proceeds in parallel with T01 source preparation. Codex effective100 subagents is verified on a fresh host app server, and Docker/Harbor DNS has recovered. latest_training_start remains04:40 EST and agent_run_cutoff03:25 EST until GPU throughput is measured; no owner alert is open.

| Unit | Status | Tests/Evidence | Notes |
|---|---|---|---|
| Setup and agent runs | active | Scaffolddb7e8d0; five targeted tests passed; access results in results/access-*.json. | Isolated image exists. Supervisor status at this write: blocked_preparation. No actual task trace has launched; source fallback is available. |
| Shared renderer | complete |23 tests pass; real pinned BPE golden files; mutation failed then restored;22 file hashes checked. | Frozen codef0239e5, renderer-parity PASS and DAVID milestone recorded. |
| Trainer patches and smoke | active |13 CPU checks pass, including real torch continuation and interpolation; grouping mutation failed then restored. | Detached H100 smoke function has spawned without T01/T02 waits, per owner clarification. Actual GPU measurements remain pending. |
| Source conversion through evaluation | active | No records rendered, trained or evaluated. | Required downstream work remains open. |

| Gate | Status | Current measured result |
|---|---|---|
| setup | pending | Actual Claude task launch awaits source archive; the independent supervisor ended with blocked_preparation. |
| renderer-parity | PASS |23 tests passed, mutation red/green; codef0239e5. |
| identity-parity, resume-parity, kernel-check | pending | GPU measurements not yet available. |
| accelerated-kernel-parity | pending | Reference path is the specified fallback. |
| records and data gates | pending | No frozen split exists. |
| run, dev-ready, serve-path-parity, demo-check, lift | pending | No model has been selected or handed off. |

## Clock

latest_training_start: 2026-11-08 04:40 EST, from the specified2.5-hour default.
agent_run_cutoff: 2026-11-08 03:25 EST.
Deadline: 2026-11-08 08:00 EST.

## Background jobs

| Job | Where | How to check | Expected end |
|---|---|---|---|
| Agent-run supervisor | Completed Python PID11792, launcher17380. | results/agent-runs/supervisor.json and sibling logs; notes/agent-runs.md. | Completed with blocked_preparation at00:44:31 EST; source_ready=false and image_ready=true. |
| Source archive download | Tool session95734. | notes/agent-runs.md gives its exact command and safe restart. | Unknown; at last worker checkpoint the file remained incomplete. |
| H100 smoke preparation | Detached Modal app ap-zxnGssuqlFFloGPPMbwCGg, function fc-01M6WV8Y5EN1MPVCC7B2623WRY. | results/trainer/modal-smoke-process.json and notes/trainer.md; Modal IDs appear in modal-smoke-call.json. | Detached function spawned; initial module-path startup defect corrected. Measurements pending. |

## Spend

Anthropic recorded spend: 1.11E-05 USD of200 USD, from1 ledger row.
Generation reserve: 76 USD. Agent-run allocation: 123.95 USD.
The reserve uses3898 estimated generation calls and a factor2 margin; assumptions and fetched price sources are in results/budget.json.

## Next Actions

1. Persist the actual Modal smoke job IDs and measure throughput, P and parity, then recompute the clock.
2. Build converters and constructions against the frozen shared renderer.
3. Recover agent source preparation or redistribute unavailable source quota, then begin parallel registered converters.
4. Fully restart Codex when ready, resume this goal and execute task.md Section0 before any work. The fresh server's effective agent limit is100.

Active task anchor: TASKLIST.md:L18






