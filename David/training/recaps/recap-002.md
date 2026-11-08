# Recap 002: Verified concurrency and recovered service access

## What was accomplished

The saved Codex limit is100. A fresh instance of the installed host app server
confirmed that effective value through config/read with the correct user layer
and no project override. Fully quitting and reopening Codex activates that
configuration. This running conversation still advertises seven total slots.
The verification is in results/agent-limit-verification.json and
notes/agent-concurrency.md.

Docker and actual Harbor API DNS plus HTTPS passed on the host and in a
cached container. An authenticated Harbor Hub request returned valid JSON.
SQ01 closed in under two minutes without changing network settings.
See notes/dns-repair.md and results/dns-host.json.

The spec bundle is committed and pushed as d975a45. The initialized scaffold
and isolated-run code are committed as850ebae. The five targeted safeguards
passed, compilation passed and the staged22-file secret scan found no matches.
The initial push review rejection was resolved by proving that origin exactly
matches the public repository named in CONTRACT and that task.md explicitly
requires pushing this bundle.

## State of each step

1. Setup remains active. Access probes, spend reservation and the agent-run
   image exist. The independent supervisor has launched, but no actual Claude
   task trace exists yet because source extraction is not ready.
2. The renderer has23 passing tests on the pinned BPE tokenizer and an actual
   red/green byte mutation. All22 tested file hashes match. Code commit,
   logged gate and the DAVID milestone remain to be written.
3. Trainer patches and interpolation are implemented. Eleven CPU tests pass,
   two torch-dependent tests remain skipped, and grouping mutation evidence
   exists. The worker is creating the Modal image and H100 smoke now.
4. Registered converters and constructions have not started.
5. No labels or frozen train split exist.
6. Training has not started.
7. Dev and held-out preparation have not started. No held-out set was scored.
8. No model has been selected or calibrated.
9. No evaluation result exists.
10. Final handoff and reconciliation remain open.

## Key intelligence

Owner MSG005 removes all T01/T02 waits from T03/T04 and removes the T01 wait
from T02. These rows proceed independently in parallel. Do not revive the
earlier orchestrator-imposed wait for an actual agent trace before GPU work.
The corresponding TASKLIST dependencies have been corrected.

The pinned tokenizer exists at data/tokenizer. Its actual tokenizer.json is
usable through tokenizers directly. The local torch install was interrupted,
so importing transformers can currently fail at torch._strobelight. GPU
validation belongs in the pinned Linux image and must not wait for that local
installation. See notes/renderer.md and notes/trainer.md.

The agent-run image is intent-agent-run. Detached supervisor Python PID11792
has launcher PID17380. Read results/agent-runs/supervisor.json before acting.
It waits at most300 seconds from00:39:44 EST, then launches the prepared
manifest or records blocked_preparation. Archive download session95734 is
tool-bound and may need restarting after Codex quits. notes/agent-runs.md
contains the exact commands. The supervisor is not proof of a successful
task trace. Do not invent one or count metadata as a trajectory.

Impossible-SWE returned403 and the secondary dxlong release returned404.
Unavailable sources redistribute within their objective. SWE-chat, TRACE,
lhaw metadata and primary SWE-Misbehavior file reads passed. HVTB can now
be queried through recovered authenticated access.

## Clock and spend

The default latest_training_start is04:40 EST and agent_run_cutoff03:25 EST
on2026-11-08. The selected calibrated handoff is due08:00 EST. These values
must be recomputed as soon as the H100 smoke measures throughput.

The spend ledger contains one tiny CLI probe costing0.0000111 USD.
The generation reserve is76 USD and agent-run allocation123.95 USD.
Both are in results/budget.json. Every writer shares results/spend.lock.

## Immediate next steps

Keep T03/T04 Modal smoke moving immediately and record the app/object IDs for
restart recovery. Close the tested renderer slice with its code hash and
DAVID milestone. Resume source preparation from its actual current state,
then fan out converter and teacher work with the activated concurrency.

On any context rollover or new session, execute task.md Section0 completely,
including the MESSAGES gate, before tools or file mutations. Owner MSG001
through MSG005 are handled and must not be replayed from a visible old prompt.

Active task anchor: TASKLIST.md:L18
