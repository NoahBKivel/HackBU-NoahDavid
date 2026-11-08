# Single-B200 throughput handoff

## Accomplished

The actual8K training step was profiled on oneB200. Required FLA chunk and Triton convolution kernels execute. Attention uses SDPA's sm80CUTLASS memory-efficient path. The first16records contain33,254useful versus85,841padded tokens, exposing padding and attention/cast overhead.

Matched native measurements over92record executions/six updates, after warming all groups, show a safe runtime-parameter improvement. ON/P115200 gives5751.676593records/hour,3895.579992useful and8944.065496padded tokens/second. ON/P46080 gives7327.478906records/hour,4962.862525useful and8627.663932padded tokens/second, a27.397269percent useful-throughput gain. Peak allocated memory falls from109909343232to55918221312bytes. The smaller-cap passes contain5+11,6+10and4+10records, preserving each logical optimizer group. All corresponding cycle losses fall.

CheckpointingOFF exhausted memory at tested caps115200,86400,57600,34560and23040. KeepON. The20,000tokens/second target remains unmet.

## Rejected branch

A padding-free causalSDPA experiment reached actual Flash forward/backward kernels. Explicit-mask fp32 output/input-gradient checks agree below1e-6; mixed-precision checks pass. Actualmodel loss parityFAILS: maximumrelative difference0.00560573224 exceeds measuredsame-seed noise0.00248658872. The specialized path is NOT adopted and no further attention trials are planned. Production model/renderer/trainer/environment files were not changed.

Two real autocast interface errors were corrected during this bounded experiment: destination buffers must use SDPA output dtype, and causal-bias dispatch must normalize Q/K/V to autocast dtype before validating them. These corrections do not enable the experiment in production.

## Evidence and code

Detailed methodology and durable paths:notes/training-throughput.md. Native reference isresults/profiling/native-result.json and/training/profiling/20261108T093349576067Z/result.json. Best packing result isresults/profiling/padding-result.json and/training/profiling/20261108T094911845046Z/result.json. Rejected attention isresults/profiling/bounded-result.json and/training/profiling/20261108T094318976954Z/result.json. Actual operator profile isresults/profiling/profile.json.

Code commits are0a28dec,f608a7b,d8ad58c,60c72c8,64afdb7and957f057. Three focused pure tests passed; named-file credential scans were clean. No dependency installation occurred. Runtime hardware gates and failures remain inVALIDATION-LOG. The original4.192566h instrument figure included cold/un-warmed shapes and a different greedy partition; it is superseded.

Last native callfc-01M6X8ZJV9QAWHW895EKX9QCBW has committed its final result. No additional GPU launch is planned by this worker. Sampler ownership was transferred exclusively toaccelerate_train; this worker created no sampler code or payload.

## Clock and remaining proof

Owner decisions remain fullN12200, freeze06:00EST, complete training/selection/calibration/handoff/full evaluation09:00EST. Compute-only projection at the best packing point is1.664965557hours, compared with2.121120651hours atP115200. These figures exclude cold compilation/startup/saves/downstream work and are conditional on the imperfect46-input mixture: six replay records and no actualSCR/M8screen. Do not use them as the final representative clock forecast.

The sole final122 fixture must contain30native,90source-weighted tasks and a complete two-screen pair, with pair/sibling closure. Its blocker is prepared source coverage, not this GPU work. Preparation confirmed onlyC700plus41timingtask records at transfer. Accelerate owns the sole sampler/admission and will share one immutableJSONL/hash between both training paths. Do not create another48/122 sampler or rerun the rejected attention branch.

Before production choosesP46080, establish that the largest actual frozen record fits it and measure the required representative payload once. The accepted distributed backup remains independent. T31 staysin-progress because the20ktarget and representativeforecast are not closed; root owns the next choice and all campaign status. No model, calibration or handoff is claimed here.

Active task anchor: TASKLIST.md:L50