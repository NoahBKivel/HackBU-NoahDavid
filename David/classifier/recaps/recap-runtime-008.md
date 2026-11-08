# Model swap tooling recap

## Accomplished

The swap helper is committed at bbd0aa6. Its 25 targeted tests, compilation and CLI help passed before commit. The actual source format will be checked when delivered. Source is mounted read-only; destination copies go to fresh checkpoint directories and the runtime pointer switches last. Deployment is followed by explicit rollover so a volume-only change reloads.

## State of each step

Setup, core, shared formatting and overflow are complete. Model swap remains active because selected/, calibration.json and long_context.json have not arrived. The live done bar failed the short deletion. The live no-false-correction check passed for the current stock model.

## Key intelligence

The existing core verifier assumes the former single-question placeholder, so it must not be used to close selected-model calibration on the full question set. Prepare a full trace comparison against the copied calibration and expected source before the handoff arrives. Actual receipt and loaded model identity must agree. No training files or volume were modified.

## Dev and live

Both serve stock Kev with product 6e81f7a, live from tree 89247d5. No deployment occurred for the helper commit. N-005 is published.

## Immediate next steps

Prepare selected-model trace verification, poll every ten minutes, and inspect actual handoff files before any copy. Verify on dev and run a burst before the live swap. Warm live immediately and repeat the fixed done scenarios. Publish model and validated-length notes after a successful live switch.

Active task anchor: TASKLIST.md:L25
