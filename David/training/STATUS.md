# Training Build Status

Last updated: 2026-11-08 03:49 EST.

## Active work

The goal is active. Owner MSG056 fixes the freeze at06:00EST and completion of the entire build and evaluation at09:00EST. N remains12,200:9000task,3000replay,200screen. MSG057 permits judgment calls within cost caps that preserve planned classifier quality and the demo. No smaller split or reduced evaluation is authorized. Root owns status. Next measured report03:56EST.

Labelling is the critical path. MSG055 requires a continuous queue, batch claims, in-memory prompts, votes-only output, byte-identical8K/10Kstate reuse, and all free Codex slots labelling. OpenAI uses standard concurrent calls only for paired intent/judgment; Batch disabled. All API work is exempt from the local workload cap. Local compute remains capped at8, with freeRAM>3.5GiB before starting. Last root measurement5.386GiB at03:41:58; later worker measurements exceed5GiB. Docker stays stopped. No OSprocess management.

## Units

| Unit | Status | Tests/Evidence | Notes |
|---|---|---|---|
| Renderer | complete | Existing renderer-parity gate, codef0239e5. | Frozen; existing b_state8191 parameter. |
| FourGPU trainer | active | T28torchrunDDP andT29Accelerate implementations run independently. | First passing same-fixed-batch per-step loss comparison is used. Neither has passed yet. Globalbatch16, paired groups and normalization preserved. |
| Existing trainer gates | active | Identity426backbone+4headPASS; resumeFAIL with no-resume fallback. | No repeat of passed checks. FourGPU correctness still required. |
| Timing | active | Existing oneB2008KON5833.7041records/hour has only6replay. | Corrected nativeCPU output has12replay/42task but screen missing; prep fixes explicit screen routing before representative4GPU timing. |
| Unsloth | complete | Worker retrieved existing H10010K trial:802.45reference versus841.64RMSNormrecords/hour, loss/timing gatePASS. | Historical harness only; no B2008K gain claimed or adopted. |
| Preparation | active | Existing local C750main; complete aggregate context was absent at recovery. | Reconcile two existing remote writers, deliver atomic complete shards, prepare full source/native pool. No third duplicate writer. |
| Codex labels | active | Teacher has2260 RF auxiliary windows over40parents ready:1747singleSol/513paired. | Dispatch count and sustained completion rate not yet measured. Continuous queue change in progress. RFwindows are not2260 complete main records. |
| OpenAI labels | active | Root inspected ledger:26.695418USD,89settled rows. Prior97809exit0 yielded142Solrecords/40paidcalls. | Existing claims reconciled; new paid work only paired intent/judgment. No Batch. |
| Construction consumers | active | Root counted goalflip270,goalsplice282,constraint400,priority300,screen200. | Omission/correction/pressure/composite files remain0at03:48 count; generation responses are not completed records. |
| Source consumers | active | Worker reports25Ambig converted; UserBench/IFmulti parser seams being fixed. | Incremental existing/new responses feed preparation. |
| Anthropic generation | active | One executor session11743,20APIrequests concurrently; first20IFmulti completions reported. | Max provider-allowed concurrency within reserve/caps; clinicalAgentIF stays held. |
| Label assembly | active | Assembly reports182main/2136askedrows resolved;169singleSol/13paired. Only40contexts currently admitted. | RF/G2/ordered diagnostics/twins/sibling admission and final gates unfinished. |
| Quota redistribution/setup | active | T30 assigns omitted Docker runs to same-objective eligible sources. | Setup closes on documented redistribution; no Docker launch. |
| Selection/calibration | active | Codeb88a541; five modules and CLI;11focused tests passed. | Final scoring needs dev and trained candidates; no held-out access. |
| Evaluation/serving | active | Modules and CLI implemented; focused tests being written. | Real serving parity/demo and full evaluation still unrun. |
| Train/run/handoff | blocked | No frozen train, continuation, selected model or calibration yet. | Needs full gated12200 at06:00 and passing4GPU trainer. |

## Gates and clock

| Gate | Status | Current measured result |
|---|---|---|
| setup | pending | Docker omission redistribution authorized; exact mapping/closeout due. |
| renderer-parity | PASS | Existing gate retained. |
| identity-parity | PASS | Existing real checkpoint426+4 tensors retained. |
| resume-parity | FAIL | Explicit no-resume fallback; a crash reruns. |
| kernel-check | PASS | Existing oneB200FLA/SDPA evidence retained;4GPU path needs actual configuration confirmation. |
| distributed parity | pending | Two implementations in parallel; compare same fixed batches/global normalization. |
| records/data gates | pending | Required checks remain at freeze; no data gate inferred from votes. |
| run/selection/calibration/serve/demo/lift | pending | No actual trained artifact. |

The freeze is06:00EST. The final deadline is09:00EST. latest_training_start and agent_run_cutoff await measured4B200actual8Kmixture throughput; no unmeasured4x speed claim. Docker runs are omitted, so their cutoff is no longer actionable. Previous oneGPU/synthetic forecasts are historical. No change to positive floors,1:10cap or held-out exclusion.

## Spend

Root read ledgers at03:48EST: OpenAI26.695418USD, separate200USDcap. Anthropic cost_usd-field sum48.31712833USD; generator reports53.21290393exposure basis still being reconciled. Treat exposure conservatively until explained; never add reservations as actual paid cost. Generation reserve76USD; Anthropic totalcap200USD. Modal actual billing not yet collected. FourB200 pricing/throughput forecast is pending actual implementation measurement, not assumed cost-neutral.

## Saved jobs and next actions

1. Teacher/API implement the continuous queue without duplicating completed/owned votes; root verifies actual sustained rates at the required interval.
2. Preparation recovers existing remote outputs, fixes explicit screen routing and streams complete8K inputs. Construction/source consumers fill actual planned shortfalls.
3. DDP and Accelerate compare required fixed-batch losses; the first passing implementation measures real-mix8Kthroughput and supplies the run forecast.
4. Assemble all passes, preserve provenance, run required data gates, freeze12200at06:00 and launch the selected fourB200 path.
5. Finish dev/intent and downstream scoring/calibration/serving/evaluation implementation while labels proceed; held-out scoring occurs only after selection.

Saved remote IDs and historical qualifications remain in recaps/recap-009.md. ExistingAPI97809 is confirmed terminal. Current context and owner changes are in recaps/recap-dawn-002.md. No completion claim is made.

Active task anchor: TASKLIST.md:L18
Parallel active task anchor: TASKLIST.md:L22