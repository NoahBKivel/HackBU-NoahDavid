# Runtime tasks

| ID | Status | Task | Depends-on | Spec | Evidence | Missing proof | Next action |
|---|---|---|---|---|---|---|---|
| setup | done | Setup and access | none | task 4.1; runtime 10, 13 | VALIDATION-LOG.md; 69206d7 | None for the recorded local scope. | Continue the service-core serving checks. |
| core | done | Service core | setup | runtime 5, 6.4, 6.5, 7.1, 7.3-7.8, 7.10-7.11, 13; training 4.2, 6.1, 6.3, 9.5 | VALIDATION-LOG.md; b271b05 | None for service-core scope. | Confirm the shared-format interface. |
| contract | done | Contract | setup | runtime 6.2, 10 | VALIDATION-LOG.md; 69206d7 | None for the recorded local scope. | Continue the service-core serving checks. |
| warmup | done | Warmup | setup | runtime 6.1, 10 | VALIDATION-LOG.md; b271b05 | None for service-core scope. | Confirm the shared-format interface. |
| calibration | done | Calibration on the serving path | setup | runtime 6.4, 7.4, 10; training 9.5 | VALIDATION-LOG.md; b271b05 | None for service-core scope. | Confirm the shared-format interface. |
| skipped | done | Skipped events | setup | runtime 7.1, 10; training 6.1 | VALIDATION-LOG.md; 69206d7 | None for the recorded local scope. | Continue the service-core serving checks. |
| ordering | done | Ordering | setup | runtime 6.5, 7.10, 10 | VALIDATION-LOG.md; e7fa685 | None. | Continue GPU checks. |
| late | done | Late results | setup | runtime 7.10, 10 | VALIDATION-LOG.md; b271b05 | None for service-core scope. | Confirm the shared-format interface. |
| stock | done | Stock-fallback-config | setup | runtime 6.4, 7.11, 10; training 9.5 | VALIDATION-LOG.md; b271b05 | None for service-core scope. | Confirm the shared-format interface. |
| dismissal | done | No-reopen-after-dismissal | setup | runtime 7.6, 10 | VALIDATION-LOG.md; 69206d7 | None for the recorded local scope. | Continue the service-core serving checks. |
| upgrade | done | Minor upgrade | setup | runtime 7.5-7.7, 10 | VALIDATION-LOG.md; 69206d7 | None for the recorded local scope. | Continue the service-core serving checks. |
| no-nag | done | Turn-end-no-nag | setup | runtime 7.3-7.7, 10 | VALIDATION-LOG.md; 69206d7 | None for the recorded local scope. | Continue the service-core serving checks. |
| interface | done | Interface-check | core | runtime 6.3; training 4.2, 6.1, 6.3-6.7 | notes/monitor-format-interface.md; 51dd732 | None. | Bind the shared formats. |
| formats | in-progress | Shared formats and requirement filter | core | runtime 6.3, 7.2-7.3, 7.7, 13; training 4.2, 6.1, 6.3-6.7 | None yet. | Required check pending. | Implement the shared format adapter and requirement filter. |
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
| session-store | done | Session store | setup | runtime 6.5, 13 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| event-intake | done | Event intake and skip rules | setup | runtime 7.1, 13; training 6.1 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| model-loading | done | Selected model and calibration loading | setup | runtime 6.4, 7.11, 13; training 9.5 | VALIDATION-LOG.md; b271b05 | None for service-core scope. | Confirm the shared-format interface. |
| question-runner | done | Unrounded question runner | setup | runtime 6.4, 13; training 6.3, 9.5 | VALIDATION-LOG.md; b271b05 | None for service-core scope. | Confirm the shared-format interface. |
| firing-rules | done | Calibrated firing rules | setup | runtime 7.4, 13 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| finding-lifecycle | done | Findings and diagnostics trigger | setup | runtime 7.5-7.6, 13 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| action-selection | done | Action selection on fixed probabilities | setup | runtime 7.7, 13; training 6.5 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| pane-readings | done | Pane field formulas | setup | runtime 6.2, 7.8, 13 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| requirement-filter | pending | Requirement filter binding | setup | runtime 7.2, 13; training 6.7 | Implementation or binding pending serving verification. | Required serving or shared-format evidence. | Resume the parent core or formats row. |
| state-binding | pending | State and row text binding | setup | runtime 6.3, 7.3, 13; training 4.2, 6.3-6.4 | Implementation or binding pending serving verification. | Required serving or shared-format evidence. | Resume the parent core or formats row. |
| correction-binding | pending | Finding and correction text binding | setup | runtime 6.3, 7.7, 13; training 6.4-6.5 | Implementation or binding pending serving verification. | Required serving or shared-format evidence. | Resume the parent core or formats row. |
## Next Slices

1. Verify setup access and commit the scaffold.
2. Build and test the service core on dev.
3. Confirm the frozen shared module interface.
