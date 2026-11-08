# Runtime status

Last updated: 2026-11-08T05:53:26-05:00

## Active work

The designed classifier remains live on stock Kev, product 6e81f7a, live tree 89247d5; dev serves the same product. Corrected Mod-shaped document probes passed eight dev renderer comparisons, but live short deletion still missed at 0.47628301784589894 and the legitimate earlier edit received a false correction at risk 0.5071212456353408. The burst verifier also failed on one pending result missing from its next-response late set; capture and timing diagnosis are next, without assuming a service defect or changing the fixed cutoff.
Latest handoff poll: 2026-11-08T05:46:45-05:00; missing: calibration.json, long_context.json, selected; handoff milestone lines: 0. Isolated pull succeeded.

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
| demo-no-false-correction | FAIL | Corrected slow-tests stream has a false correction on its legitimate SQLite edit; separate ordinary session passes. |
| done | FAIL | Corrected short deletion risk 0.47628301784589894; latest composite run stopped on burst delivery assertion. |

## Next actions

1. Capture the burst timing discrepancy and ensure the done verifier checks legitimate actions in the slow-tests stream too.
2. Poll for the handoff every ten minutes. Verify actual formats before any copy.
3. Load into dev, verify calibration and a burst, then deploy live, warm and repeat the done bar.
4. Publish deployment notes and model/L milestones, then reconcile the final records.

Active task anchor: TASKLIST.md:L25
