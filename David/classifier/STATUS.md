# Runtime status

Last updated: 2026-11-08 04:09

## Active work

Shared-format checks passed on dev: eight real-tokenizer states matched, numbering and turn ends passed, and every original event in the twenty-event burst arrived once. Dev is restored and warmed on product commit 5baed45; the first live deployment is next, while live still runs the original placeholder. The last training poll confirmed the frozen shared module; the model handoff is not yet requested, and main publication remains pending approval after automatic review rejected it.

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

Active task anchor: TASKLIST.md:L23
