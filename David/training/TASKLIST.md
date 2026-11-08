# Training Build Tasklist

Durable completion plan. Status values: pending, in-progress, blocked, done, superseded.

- Keep current alongside STATUS.md, BUILD-LOG.md, VALIDATION-LOG.md, CONSTRAINTS.md and recaps.
- Never mark a row done from passing unit tests alone when it has a gate: record the gate evidence.
- A `blocked` row names its real external blocker as `blocked [needs: X]`.
- Task IDs are stable and never renumbered. One row is one coherent slice of one or two commits.
- The Spec column lists the TRAINING-SPEC sections the row depends on (task.md 0.1).

## Task Table

| ID | Status | Task | Depends-on | Spec | Evidence | Missing proof | Next action |
|---|---|---|---|---|---|---|---|
| T01 | in-progress | Verify access and launch bounded agent runs. | none | 7.1, 7.3, 8.6, 8.7, 9.1, 11, 12.2 | Scaffolddb7e8d0, access probes, effective100 verified on fresh server, generation reserve76 USD. | Actual task trace launch is waiting for source archive. | Read supervisor state, finish source preparation or redistribute unavailable quota. |
| T02 | done | Freeze shared renderer and exact question interface. | none | 4.2, 6.1, 6.3, 6.4, 6.5, 6.6, 6.7, 12.1 | Codef0239e5; renderer-parity PASS in VALIDATION-LOG;23 tests and mutation evidence; DAVID milestone. | none | Import the frozen shared interface for converter rendering. |
| T03 | in-progress | Patch trainer saves, resume and grouped batching. | none | 9.1, 9.2, 10, 12.1 | Implemented;13 CPU tests pass including real torch checks; grouping mutation red/green. | Real torch and H100 parity gates. | Launch measured GPU work immediately in parallel with T01 and T02. |
| T04 | in-progress | Implement interpolation and run GPU smoke measurements. | none; integrates T03 | 9.1, 9.2, 9.3, 10, 12.1 | Interpolation code is implemented; GPU worker dispatched. | Identity and kernel parity, P and throughput. | Launch persistent H100 smoke and recompute the clock from measurements. |
| T05 | pending | Convert construction bases and visible-label sources. | T02 | 6.1, 6.2, 7.1, 7.2, 7.3, 10, 12.2 | none | Schema validation and source counts. | Dispatch converter workers. |
| T06 | pending | Build constructions and reserved agent generation. | T05 | 7.4, 7.5, 7.6, 8.6, 8.7 | none | Construction checks and spend ledger. | Generate rare-question records first. |
| T07 | pending | Convert remaining sources, replay and long documents. | T05 | 7.1, 7.2, 7.3, 7.7, 12.2 | none | Source counts and secrets scan. | Complete registered source modules. |
| T08 | pending | Collect Sol and Terra votes and resolve diagnostics. | T06, T07 | 4.1, 4.2, 6.3, 7.4, 7.8, 8.1, 8.2, 8.3, 8.4, 8.5, 10, 12.2 | none | Per-question agreement and floors. | Fix planned positive yields before votes. |
| T09 | pending | Cap, group and freeze train split to volume. | T08 | 6.4, 7.8, 7.9, 10, 12.2 | none | Pair integrity and frozen hash. | Run data gates and their fallbacks. |
| T10 | pending | Train one continuation with persistent saves. | T04, T09 | 9.1, 9.2, 9.3, 10, 12.1 | none | Completed run or clock cutoff. | Start no later than latest_training_start. |
| T11 | pending | Label dev, intent slice and long-context pilot. | T10 | 7.9, 8.1, 8.2, 8.3, 9.4, 10, 12.3 | none | Dev floors and pilot disagreement. | Build dev independently during training. |
| T12 | pending | Score candidate saves and fit stock calibration. | T11 | 9.3, 9.4, 9.5, 11, 12.4 | none | Dev scores and calibrated stock baseline. | Score saves as available. |
| T13 | pending | Select and calibrate winner, upload handoff. | T12 | 9.3, 9.4, 9.5, 12.1 | none | Loadable selected directory and transforms. | Apply paired selection rule. |
| T14 | pending | Verify serving parity and demo, record milestone. | T13 | 6.4, 9.5, 12.1, 12.3 | none | Measured parity and demo probabilities. | Test winner and apply pick-order fallback. |
| T15 | pending | Run held-out lift and reported evaluations once. | T14 | 7.9, 12.3, 12.4, 13 | none | RESULTS with measured n and intervals. | Score selected and stock concurrently. |
| T16 | pending | Reconcile claims, write final recap and alert owner. | T15 | 12.1, 12.2, 12.3, 12.4, 14 | none | All handoff and reporting obligations. | Verify artifacts before completion. |

## Next Slices

1. T01, T02, T03 and T04 proceed independently in parallel, per the owner clarification.
2. T02 freezes the shared interface before record rendering.
3. T03 and T04 measure GPU correctness and throughput while source work proceeds.


