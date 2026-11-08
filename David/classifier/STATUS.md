# Runtime status

Last updated: 2026-11-08 04:09

## Active work

The service-core checks passed on intent-monitor-dev. Dev runs stock Kev with product code from 69206d7; verifier b271b05 measured zero calibration error for both shipped temperature and a loaded nonzero offset fixture. The fixture files are removed and stock fallback is warmed after an explicit rollover. Live intent-monitor remains the pre-existing stock placeholder, unchanged by this build. The shared interface check passed and its mapping is in notes/monitor-format-interface.md. Shared-format binding is locally tested at 5baed45 with 32 passing CPU tests; deployment and real-tokenizer parity checks are next. Publication to main remains pending explicit branch approval after auto-review rejected the checkpoint push.

| Unit | Status | Tests/Evidence | Notes |
|---|---|---|---|
| Setup | complete | Required access probes passed. | Kev clone is pinned. |
| Service core | complete | 25 CPU tests; six dev serving checks; nonzero calibration fixture; warmup negative control. | The existing input builder is retained until shared-format integration. |
| Shared formats | active | Frozen milestone previously observed. | The adapter and requirement filter are built; deploy and verify the real class next. |

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

Active task anchor: TASKLIST.md:L18
