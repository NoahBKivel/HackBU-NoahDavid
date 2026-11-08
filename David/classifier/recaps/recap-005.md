# Service-core recap

## Accomplished

The service-core checks passed. The local suite has 25 passing tests, including full eight-second waits. Six baseline checks passed through the dev class with backend-style calls. A loaded calibration fixture with T=3.0 and b=0.7 also produced zero measured calibration error. The wrong warmup return was rejected after deploying with recreate, then the original service was restored.

## State of each step

Setup and service core are complete. Interface confirmation is active. Shared-format binding, live deployment, overflow, trained-model swap and the done bar remain pending.

## Key intelligence

Verifier commit b271b05012eb9b2e73be20bc6c4c11ddb487a152 fetches logs after calls because the CLI does not stream by default. It explicitly requires parameters for the calibration-file check. Rolling deployment can route to old containers while replacements start. An unchanged deploy does not reload volume files, so calibration cleanup used an explicit recreate rollover. All temporary dev calibration files were removed and stock fallback was warmed. Evidence is in results/core-dev, results/calibration-fixture and results/warmup-teeth.

## Dev and live

Dev serves stock Kev using product code 69206d7. The verifier repair is b271b05. Live remains the original stock placeholder. No live deploy has occurred. Main publication remains blocked by auto-review's branch authorization requirement; no new owner approval has arrived.

## Immediate next steps

Poll the training log and module milestone, read the frozen exports and the training task's interface list, then write the interface mapping. Bind shared formats only after that check. Keep polling the model handoff when its dependent row starts.

Active task anchor: TASKLIST.md:L17
