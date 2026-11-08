# Runtime ordering and deployment recap

## Accomplished

The default eight-second wait was measured for one and two missing events. The full restored suite passed 25 tests in 16.82 seconds. Code commit e7fa685 contains the new measurements. Evidence is results/core-current.xml. The existing reduced-time checks also cover ordering, slow predecessors, exceptions and stale arrivals.

## State of each step

Setup is complete. The service core is deployed on dev and its GPU checks are running. Shared-format integration and subsequent work remain pending.

## Key intelligence

The dev model volume lists no files, establishing the absent selected.json condition. Existing publication approval remains unresolved and does not prevent authorized dev deployment. No new owner message has authorized a main push.

## Dev and live

Dev runs the product code of 69206d7. The only subsequent code change is the ordering test in e7fa685. Live remains the existing stock placeholder, unchanged by this build.

## Immediate next steps

Collect the live warmup and serving-check results. Run the warmup mutation check on dev, restore it, and finish the service-core gate before confirming the shared module interface.

Active task anchor: TASKLIST.md:L6
