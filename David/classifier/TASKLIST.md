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
| formats | done | Shared formats and requirement filter | core | runtime 6.3, 7.2-7.3, 7.7, 13; training 4.2, 6.1, 6.3-6.7 | VALIDATION-LOG.md; d65fd4b | None. | First live deployment. |
| renderer | done | Shared renderer | core | runtime 6.3, 10; training 6.4 | VALIDATION-LOG.md; d65fd4b | None. | First live deployment. |
| numbering | done | Instruction numbering | core | runtime 6.3, 10; training 6.1, 6.4 | VALIDATION-LOG.md; d65fd4b | None. | First live deployment. |
| turns | done | Turn ends | core | runtime 7.1, 7.3, 10 | VALIDATION-LOG.md; d65fd4b | None. | First live deployment. |
| burst | done | Burst-backlog | core | runtime 7.10, 10 | VALIDATION-LOG.md; d65fd4b | None. | First live deployment. |
| live-stock | done | Designed classifier live on stock Kev | core | runtime 13; task 4.4 | Live smoke; N-004; DAVID milestone; d15ebd2 pushed to main. | None for the first live deployment. | Build and verify overflow. |
| overflow | done | Overflow | core | runtime 7.9, 10, 13; training 6.6 | Live smoke, N-005, 5b3d1fc published. | None. | Complete swap tool and poll handoff. |
| swap | blocked | Serving trained model and model-swap | core | runtime 6.4, 7.11, 13; training 9.5 | bbd0aa6; 25 targeted tests pass; e24794c compares 27 stock serving rows. Fresh source check at 06:25:50 Eastern still finds all three paths absent. | [needs: selected/, calibration.json, long_context.json on intent-monitor-training] | Read-only watcher69631 continues; validate and swap when delivered. |
| done | blocked | Done agent-run | core | runtime 10, 12, 13 | bfdebab; short deletion misses at 0.47628301784589894; latest live burst delivers twenty results once. | [needs: selected model and calibration passing the short deletion] | After handoff, verify the same fixed scenario on live. |
| false | blocked | Demo-no-false-correction | core | runtime 10, 12 | bfdebab; legitimate SQLite edit receives a false correction at 0.5071212456353408. | [needs: selected model and calibration passing legitimate actions] | Run the complete legitimate-prefix check after the handoff swap. |
| desktop | blocked | Owner desktop live run | core | runtime 10; task 4.7 | The agent-run driver exercises the live class; desktop delivery is owned by David and Noah. | [needs: owner live run] | Owners run the real desktop demo. |
| close | blocked | Reconciliation and final recap | core | task 4.8, 8 | Preliminary blocked-state audit reconciled existing binding evidence and stale rows. | [needs: selected serving evidence and live model checks PASS] | Perform final claim-and-count reconciliation last, after the required live checks pass. |
| session-store | done | Session store | setup | runtime 6.5, 13 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| event-intake | done | Event intake and skip rules | setup | runtime 7.1, 13; training 6.1 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| model-loading | done | Selected model and calibration loading | setup | runtime 6.4, 7.11, 13; training 9.5 | VALIDATION-LOG.md; b271b05 | None for service-core scope. | Confirm the shared-format interface. |
| question-runner | done | Unrounded question runner | setup | runtime 6.4, 13; training 6.3, 9.5 | VALIDATION-LOG.md; b271b05 | None for service-core scope. | Confirm the shared-format interface. |
| firing-rules | done | Calibrated firing rules | setup | runtime 7.4, 13 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| finding-lifecycle | done | Findings and diagnostics trigger | setup | runtime 7.5-7.6, 13 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| action-selection | done | Action selection on fixed probabilities | setup | runtime 7.7, 13; training 6.5 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| pane-readings | done | Pane field formulas | setup | runtime 6.2, 7.8, 13 | Local fixtures at 69206d7. | None for fixed fixture behavior. | Resume the parent core or formats row. |
| requirement-filter | done | Requirement filter binding | setup | runtime 7.2, 13; training 6.7 | 6e81f7a; results/overflow-local.xml acceptance and replacement tests; deployed requirement rows in results/rendering-mod-shape/. Tested source unchanged. | None for the binding. | Verify selected-model calibration when delivered. |
| state-binding | done | State and row text binding | setup | runtime 6.3, 7.3, 13; training 4.2, 6.3-6.4 | 6e81f7a local binding tests; f60dd99 deployed parity compares eight corrected Mod states; row filler tests pass. Tested source unchanged. | None. | Preserve the shared renderer contract during the model swap. |
| correction-binding | done | Finding and correction text binding | setup | runtime 6.3, 7.7, 13; training 6.4-6.5 | 6e81f7a local shared-correction and delivery test; bfdebab live correction receipts. Tested source unchanged. | None for the binding; false correction remains a separate failed model gate. | Verify model quality after handoff. |
## Next Slices

1. Wait for selected/, calibration.json and long_context.json through the existing read-only watcher.
2. Validate actual handoff schema and source, swap dev, and verify calibration and a burst.
3. Swap live after the dev checks pass, warm, validate and publish the model/L milestone.
4. Pass the corrected live deletion and legitimate-action checks, then perform final reconciliation.
5. NN-003 remains deferred until demo checks pass under owner MSG-007.
