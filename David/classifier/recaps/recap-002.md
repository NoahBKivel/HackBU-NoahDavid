# Runtime recap

## Accomplished

The startup scaffold was committed in adjacent code and documentation commits, 5c17914 and 68ebf0b, and both were pushed. Modal workspace davidkny22 lists apps. Python 3.13 has modal, pytest, pydantic and pysbd installed. DNS resolution succeeded after clearing the transient cache. An isolated checkout in results/sync-probe passed git pull --rebase without changing the training build's unstaged files.

The core modules implement ordering, storage, event intake, calibration, firing, findings, action selection, Pane readings and the per-event lifecycle. The fixed-probability suite passed 20 tests, then ten planted defects were rejected. The restored suite passed 20 tests again. These core changes remain uncommitted. Results/mutations/summary.json records the deliberate defects and their failing test outputs.

## State of each step

Setup awaits confirmation of the pinned vendor checkout. The service core is active. The new serving-wrapper tests and app import are queued. Shared-format integration, live deployment, overflow, model swap and the done bar have not started. The existing single-question input builder stays in app.py and delegates its lifecycle to single_question.py until the shared formats are bound. No second formatter was built.

## Key intelligence

The original full Kev clone stalled and was stopped by its verified process tree. The pinned revision was fetched successfully, but checkout encountered a stale index lock and untracked files from the interrupted checkout. A forced checkout restricted to this disposable vendor clone is pending. Do not treat its HEAD as pinned until rev-parse confirms it.

Automatic approval review initially rejected a push to main. Reading task.md line 199 and AGENTS.md lines 30-32 established the explicit publication authorization. Retrying the same push with that evidence succeeded. No permission answer is pending.

The first pytest command was too broad because the shell working directory is the repository root. It was canceled and earns no validation credit. Always use the explicit classifier configuration and test path: python -m pytest -c David/classifier/pytest.ini David/classifier/tests -q. The later scoped run passed. No pytest process remained in the targeted process query.

The pinned Kev api.py and serve.py were read through the GitHub connector before coding. Server.probs returns unrounded lists in request metadata order. Server.submit queues a Future. Modal's official concurrency guide confirms synchronous inputs use separate threads, and the Dict guide confirms writes require explicit assignment. These facts support the per-session gate and write-through header.

## Dev and live

No dev deployment has been made by this build. Live remains the pre-existing stock placeholder. Its deployed commit has not been established. The new app defaults to dev and uses the separate dev Dict and model volume. Before deploying, propagate INTENT_MONITOR_TARGET into the image environment as well as local resource selection so a future live import cannot default to dev.

## Immediate next steps

1. Collect outputs from the pending vendor checkout, new wrapper tests and app import. Fix the image target propagation before deployment.
2. Read the pinned checkpoint temperature/load implementation and the Mod event-building ranges located by rg. Save the reusable source note.
3. Complete the local restored-tree tests, commit the coherent core slice, then write its adjacent documentation closeout with the exact commit hash and mutation evidence. Log setup PASS only after the pinned clone is verified.
4. Deploy to intent-monitor-dev and run the required serving checks through scripts/backend_driver.py. Only after those checks pass, proceed to the shared-module interface row.

Active task anchor: TASKLIST.md:L6
Sidequest anchor: SIDEQUESTS.md:L5
