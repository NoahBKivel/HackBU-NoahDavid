# Evaluation execution handoff

## Accomplished

Code 3e1290321248237e9cbbb913dd74cff4c6ddfc77 contains the evaluation package and three test files. Twenty-eight distinct
software checks passed across focused runs. Known cases verify paired accuracy direction,
complete conversation resampling, fixed endpoint membership and null lift failure. Serving
seam tests use the pinned Kev request conversion, shared renderer and real calibration
transform with mocked model probabilities. The complete held-out execution test emitted
1,200 synthetic score rows and proved that the durable admission ledger prevents a second
model invocation. These are software checks, not reported model evaluation results.

The CLI exposes score-heldout, score-serving, parity, demo and report. The usage and schema
are in notes/evaluation-serving.md. A staged scan of the 11 code/test files found no
credentials. No dependency was installed and no GPU or held-out dataset was read.

## Remaining work

Root must supply the prepared development and registered held-out manifests, the selected
and stock checkpoints, and their base-dev calibrations. The real serving comparison,
demo, retention and lift have not run. The existing golden Mod fixture has an offending
slow-test deletion at event 3, but its raw reasoning must first be moved to side data.
No selected model or completed handoff is claimed.

## Campaign continuity and clock

The primary campaign snapshot is recap-dawn-003.md. Owner direction sets full N=12,200,
freeze at 06:00 EST and completion including evaluation at 09:00 EST. Four-GPU timing and
the current training clock remain root's measurement work; no multiplier is assumed.
Root owns STATUS and TASKLIST updates and continues labelling, source preparation and
trainer work independently. The evaluation claim is released with its file manifest.

## Immediate next actions

Integrate the documented score artifacts with the prepared records, then execute actual
candidate selection and calibration after training. Drive serving parity and the demo
through the real loaded files, taking only the specified pick-order fallbacks. Score the
held-out endpoints once and serialize every measured evaluation with its denominator and
interval. Recovery after compaction still executes task.md Section 0 before other work.

Parallel active task anchor: TASKLIST.md:L22
Active task anchor: TASKLIST.md:L18
