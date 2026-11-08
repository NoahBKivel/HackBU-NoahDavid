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
| T01 | done | Verify access and launch bounded agent runs. | none | 7.1, 7.3, 8.6, 8.7, 9.1, 11, 12.2 | Access proofs and3actual isolated task results exist; old legacy jobs exited0. | None. | SetupPASS; owner-omitted Docker quotas redistributed in T30. |
| T02 | done | Freeze shared renderer and exact question interface. | none | 4.2, 6.1, 6.3, 6.4, 6.5, 6.6, 6.7, 12.1 | Codef0239e5; renderer-parity PASS in VALIDATION-LOG;23 tests and mutation evidence; DAVID milestone. | none | Import the frozen shared interface for converter rendering. |
| T03 | in-progress | Patch trainer saves, resume and grouped batching. | none | 9.1, 9.2, 10, 12.1 | Trainer saves/interpolation/grouping/full-Ppacking implemented;14nonTorch tests;identityPASS;resumeFAILfallback. | Production closeout and remaining gates. | Resumed under MSG052; no resume claim; crash reruns. |
| T04 | in-progress | Implement interpolation and run GPU smoke measurements. | none; integrates T03 | 9.1, 9.2, 9.3, 10, 12.1 | SafeB200ON/P46080 nativefixture7327.48R/h; OFFOOM; identityPASS; Accelerateapproxnoisegateaccepted. | Representative122realmix timing and production integration. | Fix sampler naturaloverflow classification and source slice coverage; no optional optimization. |
| T05 | in-progress | Convert construction bases and visible-label sources. | T02 | 6.1, 6.2, 7.1, 7.2, 7.3, 10, 12.2 | Raw source outputs exist; bounded acquisition closed. | 8Kadmission, quotas andlabels. | Resumed under MSG052; reuse existing conversions, no blanket redownload. |
| T06 | in-progress | Build constructions and reserved agent generation. | T05 | 7.4, 7.5, 7.6, 8.6, 8.7 | Rawconstraint400/priority300/screen200/goalsplice216;goalflip148normal responses. | Consumers;composite/pressure0;8Klabels. | Resumed under MSG052; consume existing responses afterresume;never retryrefusals. |
| T07 | in-progress | Convert remaining sources and original native replay; long training excluded. | T05 | 7.1, 7.2, 7.3, 7.7, 12.2 | 2500Kev+500tasksource native rows;long400excluded. | Full8Kadmission/exactnative structured-state rendering. | Resumed under MSG052; native-fixedCPUalreadyspawned, do notduplicate. |
| T08 | in-progress | Collect votes and resolve required diagnostics. | T06, T07 | 4.1, 4.2, 6.3, 7.4, 7.8, 8.1, 8.2, 8.3, 8.4, 8.5, 10, 12.2 | Canonical6744main;1206all-required;1197actualencoderadmitted. | Full10000 labels/admission,4199matchingcontexts, RF/orderedpasses/floors. | Remotecontextjoin and continuousmain/aux Codex; no paidOpenAI. |
| T09 | pending | Cap, group and freeze train split to volume. | T08 | 6.4, 7.8, 7.9, 10, 12.2 | Frozen0; owner permits gated freeze after06:00. | Full10000 provenance and required data gates/fallbacks. | Freeze immediately when fullscope gated, write count/hash and privatevolume copy. |
| T10 | pending | Train one continuation with persistent saves. | T04, T09 | 9.1, 9.2, 9.3, 10, 12.1 | No production training run. | Fullgatedfrozen10000hash/count;verifiedproductionconfiguration. | Launch fastest verified B200 path immediately after gates;09:00completiontarget unchanged. |
| T11 | pending | Prepare dev, intent slice and held-out conversions; no long pilot. | T10 | 7.9, 8.1, 8.2, 8.3, 9.4, 10, 12.3 | No dev/intent/heldoutJSONL;longpilotremoved. | Implementation,grouping andlabels. | Resumed under MSG052; code can proceed independentlyafterresume. |
| T12 | pending | Score candidate saves and fit stock calibration. | T11 | 9.3, 9.4, 9.5, 11, 12.4 | select/has0productfiles. | Scoringcode,dev andcandidates. | Resumed under MSG052; implement afterresume, finalscoringwaitsartifacts. |
| T13 | pending | Select and calibrate winner, upload handoff. | T12 | 9.3, 9.4, 9.5, 12.1 | none | Loadable selected directory and transforms. | Apply paired selection rule. |
| T14 | pending | Verify serving parity and demo, record milestone. | T13 | 6.4, 9.5, 12.1, 12.3 | none | Measured parity and demo probabilities. | Test winner and apply pick-order fallback. |
| T15 | pending | Run held-out lift and reported evaluations once. | T14 | 7.9, 12.3, 12.4, 13 | evaluate/has0productfiles;RESULTSunfinished. | Evaluationcode,selected+stock. | Resumed under MSG052; codeindependent, heldoutscoringonceonly. |
| T16 | pending | Reconcile claims, write final recap and alert owner. | T15 | 12.1, 12.2, 12.3, 12.4, 14 | none | All handoff and reporting obligations. | Verify artifacts before completion. |

| T17 | done | Implement candidate scoring, selection and calibration modules. | none (implementation); scoring requires T11,T10 | 9.3, 9.4, 9.5, 12.1, 12.4 | Codeb88a541;11focusedtestsPASS;7filesecrets0; executableCLI. | None for implementation slice; real scoring remainsT12/T13. | Execute on actual dev/candidates when available. |
| T18 | done | Implement evaluation and serving handoff verification. | none (implementation); execution requires T13 | 7.9, 12.1, 12.3, 12.4, 13 | Code3e12903/docs1e429b2;28distincttestsPASS; scansclean. | None for implementation; hardware/evaluation execution remainsT14/T15. | Execute real serving/demo/lift after artifacts exist. |
| T19 | in-progress | Codex Sol labelling stream on verified complete 8K packets. | T02; per-packet schema validation complete before admission | 8.1, 8.2, 8.3, 8.4 | Existing exact8K packets and shared vote ownership. | Full required train Sol votes and diagnostics. | Scale complete inputs without duplicate ownership. |
| T20 | in-progress | Codex Terra labelling stream on policy-paired 8K packets. | T02; per-packet schema validation complete before admission | 8.1, 8.2, 8.3, 8.4 | Existing paired policy. | Required Terra votes on paired slices. | Launch parallel with corresponding Sol vote. |
| T21 | in-progress | OpenAI standard labelling stream. | T02; shared claims and budget guard | 8.1, 8.2, 8.3, 8.4 | Existing client and97809 ownership. | Reconciled existing calls and remaining priority votes. | Recover and resume within200USD cap. |
| T22 | superseded | OpenAI Batch labelling disabled by owner. | none | MSG055 | Zero submissions. | None. | Use standard API only on paired intent/judgment records under T21. |
| T23 | in-progress | Recover existing 8K preparation and stream complete packets. | T02 | 6.3, 6.4, 7.1, 7.2, 7.3, 12.2 | Existing remote jobs documented in recap009. | Reconciled duplicate writers and complete source/native admission. | Recover outputs without duplicate compute. |
| T24 | in-progress | Consume completed construction generation. | T02; completed response artifacts | 7.4, 8.6 | Existing completed generation reported in recap009. | Materialized validated records. | Consume existing responses without retries of refusals. |

| T25 | in-progress | Execute prepared independent public generation within reserve. | T02; validated request queues | 7.5, 7.6, 8.6, 8.7 | Existing request and response artifacts. | Remaining successful responses and consumer delivery. | Run eligible cached-deduplicated queue within spend caps. |

| T26 | in-progress | Consume generated instruction and ambiguity source responses. | T02; completed response artifacts | 6.1, 6.2, 7.3, 8.6, 12.2 | UserBench100 and Ambig25 existing responses. | Validated converted outputs and prepared8K packets. | Consume completed responses while generator fills remaining queues. |
| T27 | in-progress | Collect native-fixed timing and Unsloth result; production trainer entry. | none; uses T03 code | 9.1, 9.2, 12.1 | Existing remote calls and validated identity. | Native-fixed actual8Kmixture and ready invocation. | Collect existing calls; run only missing representative measurement. |

| T28 | superseded | Implement four-B200 torchrun distributed LoRA training. | none; existing pinned trainer | 9.1, 9.2, 12.1; MSG056 | Owner authorizes fourGPU data parallel. | Same fixed-batch per-step loss against oneGPU, real8Kthroughput. | Independent DDP implementation; first verified approach wins. |
| T29 | in-progress | Implement four-B200 Accelerate LoRA training. | none; existing pinned trainer | 9.1, 9.2, 12.1; MSG056 | Owner authorizes fourGPU data parallel. | Same fixed-batch per-step loss against oneGPU, real8Kthroughput. | Independent Accelerate implementation; first verified approach wins. |
| T30 | done | Redistribute omitted Docker agent-run quotas within objectives and close setup. | none | 7.1, 8.7; MSG056 | MappingSHA473cca48; exact totals preserved; setupPASS. | None for redistribution; converted gaps stayT05â€“T08. | Fulfill per-source targets and gates. |

| T31 | in-progress | Profile and fix single-B200 actual8Ktraining throughput. | none; existing native/shared renderer | 9.1, 9.2, 12.1; MSG058 | ActualFLA/SDPAprofile; nativeON/P46080 gives7327.48R/h,27.4percentgain; OFFcapsOOM; newattentionFAIL/fallback. | Target20000tokens/s unmet; representative122 forecast and largest-frozen-record cap bound. | Reuse safe packing result; accelerate_train owns sole122sampler; accepted distributed backup continues. |

| T32 | in-progress | Redistribute remaining genuinely blocked source quotas within objectives. | none; access and capacity artifacts | 7.1, 7.3, 10, 12.2 | impossible_swe access403 remains planned254. | Exact operational source targets summing12200 with sealed floors unchanged. | Remove genuinelyblocked quotas; never substitute for merelyunfinished preparation. |

| T33 | in-progress | Build grouped dev and intent data preparation and exclusion path. | none for implementation; execution consumes eligible labelled groups | 7.9, 9.4, 12.3 | Current dev/intent artifacts absent. | Executable grouped split and measured floor/top-up plan. | Build now; keep train labelling first and preserve12200 train. |
| T34 | in-progress | Convert held-out and retention datasets for once-only selected/stock evaluation. | none for conversion; scoring requires selected and stock | 7.9, 12.3, 12.4 | EvaluationCLI exists; input conversions incomplete. | Real dataset schemas, mapped records, exclusion/provenance manifests. | Prepare independent inputs now; never train/select/calibrate on heldout. |

| T35 | in-progress | Find and verify major compatible B200 optimizations from measured bottlenecks. | none; existing profile and native baseline | 9.1, 9.2, 12.1; MSG070 | Native safe7327records/hour, FlashcandidateparityFAIL. | Named-cause fixes with measured parity/speed and memory. | Independent bounded hunt; do notblockproduction path ordata freeze. |

| T36 | in-progress | Assess necessary and affordable Sonnet label coverage without paid inference. | none for assessment; actual eligible label slots required before execution | 8.2, 8.3, 8.6, 12.2; MSG076 | Exact ledger, provider billing permissions and ready label packets. | Measured access, token counts and remaining-work cost projection. | No paid calls until necessity, provenance and allocation are established. |

## Next Slices

1. T01, T02, T03 and T04 proceed independently in parallel, per the owner clarification.
2. T02 freezes the shared interface before record rendering.
3. T03 and T04 measure GPU correctness and throughput while source work proceeds.


