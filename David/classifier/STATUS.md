# Runtime status

Last updated: 2026-11-08 04:09

## Active work

The designed classifier is live and warm on intent-monitor from tree 3b40ef1 with product code 5baed45, serving stock Kev; dev serves the same restored product. The first live smoke passed and N-004 plus the DAVID milestone are published through d15ebd2; overflow integration is committed at 6e81f7a with forty local tests passed and awaits its dev check. Stock Kev missed the corrected Noah deletion sample at risk 0.4622987669655692, so the trained-model handoff and final live demo checks remain necessary; the last training poll confirmed the frozen shared module.

| Unit | Status | Tests/Evidence | Notes |
|---|---|---|---|
| Setup | complete | Required access probes passed. | Kev clone is pinned. |
| Service core | complete | 25 CPU tests; six dev serving checks; nonzero calibration fixture; warmup negative control. | The existing input builder is retained until shared-format integration. |
| Shared formats | complete | Four deployed checks passed. | First live deployment next. |

| Gate | Status | Current measured result |
|---|---|---|
| setup | PASS | Access and filesystem verified. |
| contract | PASS | Fixture and dev responses validate. |
| warmup | PASS | Correct return measured and false return rejected on dev. |
| calibration on the serving path | PASS | Zero error for shipped temperature and loaded T=3.0, b=0.7. |
| skipped events | PASS | Null readings and no actions. |
| ordering | PASS | Full eight-second waits and concurrency fixtures passed. |
| late results | PASS | Nine-second sleep and old backend timestamp delivered once. |
| stock-fallback-config | PASS | Empty model volume and shipped temperature measured. |
| no-reopen-after-dismissal | PASS | Fixed-probability lifecycle fixtures passed. |
| minor upgrade | PASS | Fixed-probability lifecycle fixtures passed. |
| turn-end-no-nag | PASS | Not-done requirements returned without correction. |
| interface-check | PASS | Frozen exports and caller field contracts verified by two checks. |

## Next actions

1. Bind instructions, units, state, rows, findings and corrections through the shared module.
2. Add the shared module and pysbd to the dev image.
3. Run parity, numbering, turn-end and burst checks before any live deployment.

Active task anchor: TASKLIST.md:L24
