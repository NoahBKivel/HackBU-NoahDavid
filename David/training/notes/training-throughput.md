# Training throughput at 8K

The best safe measured configuration is native SDPA with checkpointing ON and a46,080-token physical pass cap. It achieves7,327.478906records/hour,4,962.862525useful tokens/second and8,627.663932padded tokens/second on the fixed46-record sample. The20,000tokens/second target was not reached.

## Matched native measurements

Both measurements use the same prepared records, current production planner, logicalB16, pinned model/environment and two timed cycles after warming every group.

| Setting | Records/hour | Useful tokens/s | Padded tokens/s | Peak allocated memory | Conditional12,200 compute |
|---|---:|---:|---:|---:|---:|
| ON/P115200 | 5751.676593 | 3895.579992 | 8944.065496 |109909343232bytes|2.121120651h|
| ON/P46080 | 7327.478906 | 4962.862525 | 8627.663932 |55918221312bytes|1.664965557h|

Useful throughput rises27.397269percent while padded throughput falls because less padding is executed. The smaller-cap passes contain5+11,6+10 and4+10records for the three optimizer groups. The largest realized physical pass is36,323padded tokens. All corresponding group losses fall between cycles:0.35818635→0.33053979,0.40279061→0.37315708,0.26012941→0.24111303.

Checkpointing OFF exhausted memory at tested caps115200,86400,57600,34560and23040. Retain ON. Before choosing a production cap, establish that every frozen record fits it and rerun only the necessary representative throughput measurement.

These are92record executions over six optimizer updates, not92distinct examples. The46input parents contain six native replay records and no actualSCR/M8screen; their designated screen followed the ordinary task format. The stated epoch times are conditional compute projections, excluding cold compilation, launch, checkpoint saves, scoring and evaluation. They are not the final representative run forecast. The original4.192566h instrument result included un-warmed shapes and a different greedy pass partition; it is superseded.

## Executed kernels and rejected attention change

The actual first-step CUDA profile confirms FLA chunk/causal-convolution kernels and SDPA's sm80CUTLASS memory-efficient attention on B200. Its16records contain33,254useful versus85,841padded tokens. Attention forward accounts for0.713GPU-seconds and backward1.470GPU-seconds; copy/cast operators account for1.676GPU-seconds. Profiler elapsed time includes instrumentation overhead and is not the throughput measurement.

A specialized SDPA path unpads independent state/branch sequences and uses lower-right causal bias for branch continuation. Explicit-mask fp32 outputs and all input gradients agree below1e-6; mixed-precision checks pass. Actual Flashforward/backward kernels execute, but full-model loss parity FAILS: maximum relative difference0.00560573224 exceeds measured same-seed noise0.00248658872. First loss0.36159279943 differs from reference0.36363121867. The path is NOT adopted. No more attention trials are planned.

Two actual integration defects were fixed before this final comparison: scatter buffers must match SDPA's output dtype, and causal-bias dispatch needs explicit autocast Q/K/V normalization because it validates before standard SDPA's autocast dispatcher. These fixes do not enable the experimental path in production.

Pinned source references: [PyTorch2.8causal bias](https://raw.githubusercontent.com/pytorch/pytorch/v2.8.0/torch/nn/attention/bias.py), [Transformers5.17SDPA](https://raw.githubusercontent.com/huggingface/transformers/v5.17.0/src/transformers/integrations/sdpa_attention.py).

## Durable artifacts

- Native reference: results/profiling/native-result.json; volume/training/profiling/20261108T093349576067Z/result.json.
- Smaller-cap result: results/profiling/padding-result.json; volume/training/profiling/20261108T094911845046Z/result.json.
- Rejected attention result: results/profiling/bounded-result.json; volume/training/profiling/20261108T094318976954Z/result.json.
- Actual operator profile: results/profiling/profile.json; volume/training/profiling/20261108T090827141405Z/profile.json.
- Last comparison call:fc-01M6X8ZJV9QAWHW895EKX9QCBW; appap-IxzzuN6ApGUtqZnPtA3dNU; imageim-ylWl4KFzmbLaebbsaWkfLf.

Code commits:0a28dec,f608a7b,d8ad58c,60c72c8,64afdb7,957f057. Only new profiler/experimental modules, their launcher and tests changed; no production model, renderer, environment or trainer behavior was modified. Three focused pure tests and all named-file credential scans passed; no dependency installation occurred.

The sole final122-record sampler/admission belongs toaccelerate_train. It must use30native,90source-weighted tasks and a complete two-screen pair, with pair/sibling closure and one immutable payload/hash shared by both training paths. Its blocker is broad prepared source coverage, not this GPU experiment. No sampler code or payload was created by the throughput worker.