# Runtime status

Last updated: 2026-11-08T05:39:52-05:00

## Active work

The designed classifier including overflow is live and warm from tree 89247d5, product 6e81f7a. Dev serves the same stock Kev product. The live done run failed the short deletion scenario at risk 0.4721898905925263, while the burst deletion and no-false-correction check passed. The swap tool is committed at bbd0aa6 with 25 passing targeted tests. The handoff poll just completed after an isolated pull: selected/, calibration.json and long_context.json are still absent from intent-monitor-training, and DAVID.md has no handoff milestone.

| Unit | Status | Tests/Evidence | Notes |
|---|---|---|---|
| Setup | complete | Access and pinned Kev identity verified. | Foreign edits remain preserved. |
| Service core | complete | 25 CPU tests and deployed serving checks. | Calibration and lateness verified on dev. |
| Shared formats | complete | Eight states match; numbering, turn ends and twenty-event burst pass. | The actual one-byte renderer mutation was rejected. |
| Overflow | complete | 40 local tests and deployed oversized-document check. | Live rollout and N-005 published. |
| Selected model | active | 25 targeted swap tests passed. | Actual handoff files are missing. |
| Live done bar | active | results/done-live/probe.json | Short deletion fails; burst deletion and legitimate actions pass. |
| Desktop demo | blocked | Needs owner live run. | David and Noah run the desktop app. |

| Gate | Status | Current measured result |
|---|---|---|
| setup | PASS | Access and filesystem verified. |
| contract | PASS | Fixtures and deployed responses validate. |
| warmup | PASS | Fresh-container return measured; false return rejected on dev. |
| calibration on the serving path | PASS | Zero error for shipped temperature and loaded T=3.0, b=0.7. |
| skipped events | PASS | Null readings and no actions. |
| ordering | PASS | Full eight-second waits and concurrency cases passed. |
| late results | PASS | Nine-second sleep and old backend timestamp delivered once. |
| stock-fallback-config | PASS | Missing selection and shipped temperature measured. |
| no-reopen-after-dismissal | PASS | Lifecycle fixtures and negative control passed. |
| minor upgrade | PASS | Fixed-probability lifecycle fixtures passed. |
| turn-end-no-nag | PASS | Not-done requirements returned without correction. |
| interface-check | PASS | Frozen shared exports map to every required caller field. |
| shared renderer | PASS | Eight deployed states match byte for byte; actual mutation rejected. |
| instruction numbering | PASS | AskUserQuestion answer appears once; late instruction uses seq order. |
| turn ends | PASS | Answer and aborted row selection measured. |
| burst-backlog | PASS | Twenty original results delivered once, with ten pending calls in the dev run. |
| overflow | PASS | Two screen states; sixteen sections picked before fitting; valid deployed result. |
| model-swap | pending | Handoff absent; pure validation and copy tests pass. |
| demo-no-false-correction | PASS | Live ordinary session and legitimate burst prefix received no correction. |
| done | FAIL | Short deletion risk 0.4721898905925263; burst deletion risk 0.6234443961412832 with three actions. |

## Next actions

1. Prepare the selected-model serving-path verification while the handoff is missing.
2. Poll for the handoff every ten minutes. Verify actual formats before any copy.
3. Load into dev, verify calibration and a burst, then deploy live, warm and repeat the done bar.
4. Publish deployment notes and model/L milestones, then reconcile the final records.

Active task anchor: TASKLIST.md:L25
