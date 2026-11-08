# Handoff wait and coordination recap

## Accomplished

The corrected Mod-shaped probe and durable capture tooling are published through 1aa1c03. The latest live burst delivered twenty original results once with fourteen pending calls. Both short-scenario model gates remain failed. Owner alert has been fired for the missing selected handoff and current model failures.

## State of each step

Setup, core, shared formats and overflow are complete. Selected-model deployment waits for selected/, calibration.json and long_context.json. Tooling and full-question serving verification are ready. Done and no-false-correction fail on the current stock model. The desktop app run needs David and Noah.

## Key intelligence

NN-003 arrived from Noah proposing a persistent requires_user_intervention field, with reset on a genuine new user instruction and event-ordered snapshots. It is explicitly awaiting David's agreement and is outside the authoritative runtime spec. No implementation was made. An async question asks whether to defer until demo checks pass or authorize the extension now. This optional pending scope decision does not stop required work.

The latest required poll found no handoff paths. Polling remains read-only, after an isolated pull. A temporary local watch process will poll every ten minutes and update STATUS; it performs no model copy or deployment and exits when the paths arrive.

## Dev and live

Both serve stock product 6e81f7a, live deployment tree 89247d5. No model deployment changed. Main publication is explicitly authorized; incoming Noah commits were merged without stashing or reverting foreign edits.

## Immediate next steps

Keep polling for the handoff. On arrival, validate the actual artifact and metadata, swap dev, warm, run verify_selection.py with the actual calibration and receipt, and run a burst. Only then switch live, warm, validate, alert and publish model/L notes. Repeat verify_done.py on the corrected samples and preserve its complete receipts. Apply no NN-003 extension until the owner answers the scope question.

Active task anchor: TASKLIST.md:L25
