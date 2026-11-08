# Shared binding implementation recap

## Accomplished

Commit 5baed456a0b3540364acc119ecea65e4f8871ccd connects the full runtime to the frozen shared formatter and removes the placeholder input builder. Requirement units are filtered through queued RF requests, accepted identities survive late instruction renumbering, and document replacement removes old units. Shared row fillers, short names, finding lines and correction text now own their formats. The development suite passed 32 tests. Results/shared-local.xml is the test artifact. This is not the deployed shared-renderer gate.

## State of each step

Setup, service core and interface confirmation are complete. Shared-format binding is implemented and awaits dev deployment and its real-path checks. Overflow, trained-model swap, live deployment and the done bar remain pending.

## Key intelligence

The owner changed task.md, AGENTS.md and TASK-CLAIMS.md during this work. The current task and standing laws were read in full. Claims now use the stable runtime slug, with the broad core claim released and formats claimed. The claims header, task and standing-law edits belong to the owner and must not be staged by this agent. Recaps now use slug filenames.

Model traces include the SHA256 of each actual request state. Startup logs include the checkpoint's base and revision so a host verifier can load the identical tokenizer without executing Kev locally. Installing transformers at the image's existing pin in classifier/.venv is running under process handle 6842. Verify its completion rather than assuming installation succeeded.

The shared module's current files matched the frozen f0239e5 tree. The row allowance accounts for the state token and follows L plus 640 minus the actual state length. Events without seq need a compatibility decision before calling a renderer that requires seq; the Mod itself always supplies seq. No synthetic events have been introduced.

## Dev and live

Before the pending deployment, dev serves stock fallback from product commit 69206d7. Live remains the original stock placeholder and has not been changed by this build. Commit 5baed45 is ready for dev deployment. Publication to main remains pending after automatic approval review rejected the prior push.

## Immediate next steps

Deploy 5baed45 to dev with recreate. Add the deployed shared-format driver: compare actual request-state digests to independently rendered states using the real pinned tokenizer, prove one-byte mismatch rejection, test AskUserQuestion numbering and late arrivals, answer/aborted turn rows, and the two-burst session. Read Noah's NN-002 section and four samples in their corrected Mod shape. The old verify_core.py assumes the single-question placeholder and is not the shared-format verifier. Resolve events without seq on the runtime path. Do not deploy live until the shared-format checks pass. No overflow implementation yet.

Active task anchor: TASKLIST.md:L18
