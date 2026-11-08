# Selected-model verification readiness recap

## Accomplished

The full-question verifier e24794c drove the actual dev class with backend spawn/get calls. It compared 27 serving rows against independent power-weight calibration, including risk, firing and drift, with maximum error 1.1102230246251565e-16. It requires the expected calibration and checkpoint/source when a swap receipt is supplied. Results live in results/selection-stock/.

The swap helper bbd0aa6 has 25 passing targeted tests. Both tooling slices are committed. Main publication through 48a2c51 succeeded after a normal merge of two incoming Noah commits. No concurrent owner or training edit was stashed or reverted.

## State of each step

Setup, core, shared formats and overflow are complete and deployed. Model swap remains active, waiting for selected/, calibration.json and long_context.json. The short live deletion failed while burst deletion and legitimate actions passed. The stock-model done bar remains failed. The desktop demo needs an owner live run.

## Key intelligence

Do not use the old core verifier to check the full question set. Use verify_selection.py with the actual copy receipt and copied calibration. A selected-model gate still requires the real selected checkpoint on dev and then live; the stock-path proof closes only readiness of the instrument. The trained-model source, long-context length and calibrated probabilities must be checked on the actual delivered artifact.

## Dev and live

Both serve stock Kev with product 6e81f7a. Live deployment tree is 89247d5. No product deployment changed during verification. The last handoff poll found the three required paths absent.

## Immediate next steps

Poll every ten minutes. On delivery, validate actual source formats, swap dev, warm, run verify_selection.py and a burst. Swap live only after those pass, warm immediately, send a valid test event, alert the owner and publish the model/L milestone and Noah note. Repeat the fixed live done scenarios. Reconcile final claims only after the live run passes.

Active task anchor: TASKLIST.md:L25
