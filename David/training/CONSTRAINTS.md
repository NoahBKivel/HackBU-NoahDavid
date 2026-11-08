# Training Build Constraints

Append-only format: CONSTRAINT [NNN]: name / MODULE / OBSERVATION / IMPLICATION / DATE

Maintenance: append at the end; supersede an entry with a new one that names it, never edit or delete. Durable lessons only: nothing here changes when a gate next passes.

## Constraints
CONSTRAINT [001]: Host identity for effective configuration / setup / A sandbox-launched app server omitted the owner's user layer, while the same installed binary under host identity loaded effective subagent100. / Verify app startup settings with the application's host identity before changing configuration again. / 2026-11-08 00:46:08
CONSTRAINT [002]: Distinguish DNS from authentication and sandbox access / setup / Elevated host and container probes recovered Docker and actual Harbor API DNS, and authenticated Harbor returned valid JSON without changing network settings. / Verify both network paths before flushing caches or altering DNS servers. / 2026-11-08 00:46:08

CONSTRAINT [003]: Sandbox pytest temporary directory / evaluation tests / Default pytest temp discovery hit Windows access denial outside the workspace. A workspace --basetemp completed the test without changing product code. / Use an isolated workspace results directory for temporary test artifacts. / 2026-11-08 04:07:24 EST
