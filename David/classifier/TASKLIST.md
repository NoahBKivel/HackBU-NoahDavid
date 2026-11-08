# Runtime tasks

| ID | Status | Task | Depends-on | Spec | Evidence | Missing proof | Next action |
|---|---|---|---|---|---|---|---|
| setup | in-progress | Setup and access | none | task 4.1; runtime 10, 13 | None yet. | Required check pending. | Execute the named check. |
| core | pending | Service core | setup | runtime 5, 6.4, 6.5, 7.1, 7.3-7.8, 7.10-7.11, 13; training 4.2, 6.1, 6.3, 9.5 | None yet. | Required check pending. | Execute the named check. |
| contract | pending | Contract | setup | runtime 6.2, 10 | None yet. | Required check pending. | Execute the named check. |
| warmup | pending | Warmup | setup | runtime 6.1, 10 | None yet. | Required check pending. | Execute the named check. |
| calibration | pending | Calibration on the serving path | setup | runtime 6.4, 7.4, 10; training 9.5 | None yet. | Required check pending. | Execute the named check. |
| skipped | pending | Skipped events | setup | runtime 7.1, 10; training 6.1 | None yet. | Required check pending. | Execute the named check. |
| ordering | pending | Ordering | setup | runtime 6.5, 7.10, 10 | None yet. | Required check pending. | Execute the named check. |
| late | pending | Late results | setup | runtime 7.10, 10 | None yet. | Required check pending. | Execute the named check. |
| stock | pending | Stock-fallback-config | setup | runtime 6.4, 7.11, 10; training 9.5 | None yet. | Required check pending. | Execute the named check. |
| dismissal | pending | No-reopen-after-dismissal | setup | runtime 7.6, 10 | None yet. | Required check pending. | Execute the named check. |
| upgrade | pending | Minor upgrade | setup | runtime 7.5-7.7, 10 | None yet. | Required check pending. | Execute the named check. |
| no-nag | pending | Turn-end-no-nag | setup | runtime 7.3-7.7, 10 | None yet. | Required check pending. | Execute the named check. |
| interface | pending | Interface-check | core | runtime 6.3; training 4.2, 6.1, 6.3-6.7 | None yet. | Required check pending. | Execute the named check. |
| formats | pending | Shared formats and requirement filter | core | runtime 6.3, 7.2-7.3, 7.7, 13; training 4.2, 6.1, 6.3-6.7 | None yet. | Required check pending. | Execute the named check. |
| renderer | pending | Shared renderer | core | runtime 6.3, 10; training 6.4 | None yet. | Required check pending. | Execute the named check. |
| numbering | pending | Instruction numbering | core | runtime 6.3, 10; training 6.1, 6.4 | None yet. | Required check pending. | Execute the named check. |
| turns | pending | Turn ends | core | runtime 7.1, 7.3, 10 | None yet. | Required check pending. | Execute the named check. |
| burst | pending | Burst-backlog | core | runtime 7.10, 10 | None yet. | Required check pending. | Execute the named check. |
| live-stock | pending | Designed classifier live on stock Kev | core | runtime 13; task 4.4 | None yet. | Required check pending. | Execute the named check. |
| overflow | pending | Overflow | core | runtime 7.9, 10, 13; training 6.6 | None yet. | Required check pending. | Execute the named check. |
| swap | pending | Serving trained model and model-swap | core | runtime 6.4, 7.11, 13; training 9.5 | None yet. | Required check pending. | Execute the named check. |
| done | pending | Done agent-run | core | runtime 10, 12, 13 | None yet. | Required check pending. | Execute the named check. |
| false | pending | Demo-no-false-correction | core | runtime 10, 12 | None yet. | Required check pending. | Execute the named check. |
| desktop | pending | Owner desktop live run | core | runtime 10 | None yet. | Required check pending. | Execute the named check. |
| close | pending | Reconciliation and final recap | core | task 4.8, 8 | None yet. | Required check pending. | Execute the named check. |

## Next Slices

1. Verify setup access and commit the scaffold.
2. Build and test the service core on dev.
3. Confirm the frozen shared module interface.
