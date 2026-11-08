# Training Build Sidequests

Rules:
- Map the goal-directed chain before opening a row; record necessity, exit condition, budget and fallback.
- While a row is open, every recap carries both anchors (this row and the interrupted task row). On close, stop anchoring it and return.
- Budget exhausted: take the fallback and close, or escalate through the owner alert.

## Sidequest Table

| ID | Status | Sidequest | Goal-directed chain | Exit evidence | Budget / fallback | Return |
|---|---|---|---|---|---|---|
| SQ01 | closed | Restore Docker registry and Harbor DNS access. | DNS repair -> available agent and HVTB sources -> setup and records -> calibrated08:00 model. | At 00:41:31 EST, elevated host and container DNS plus HTTPS passed, and the authenticated Harbor request succeeded. See notes/dns-repair.md and results/dns-host.json. | Closed in under2 minutes without network changes. | T01, TASKLIST.md:L15 |
