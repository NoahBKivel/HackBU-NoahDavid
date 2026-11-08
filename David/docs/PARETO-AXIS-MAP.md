# Pareto axis map: training track

The resources the training-track design buys and spends, the limits it never trades, and how they couple. Decision references are to `DESIGN-DECISIONS.md`.

## Axes the design pushes

| Axis | Measured by | Moved by |
|---|---|---|
| Intent discrimination (M1, L4, G1, M7) | intent-selection slice in dev; held-out probe (200 items) once | D27 intent hardening (polarity twins, goal-flip pairs), D28 intent sources, D30 full-set labels |
| Gaming and claim detection (M4, L6, M5, G5) | dev per-question AUROC; TRACE once | D28 natural-first hack sources, D27 privileged teacher labels on reasoning-heavy sources |
| Trajectory questions (L1, L2, L5, G4, L7) | dev per-question AUROC; accuracy on unedited real runs | D28 constructions, D30 exact labels |
| Shortcut resistance | the gap between constructed-dev and unedited-real accuracy; the note-pair gap; reasoning-stripped held-out copies | D27 pairs, the benign rewrites, D27 note pairs, D37 grouped splits |
| Calibration | per-question ECE on real-rate dev | D27 per-question temperature with prior correction, the balance cap |
| Long-context validity | the D18 gate (Kev's 3-point rule plus worst position) at 8K, 16K and 32K | ~10% long records, D22 sizing |
| Retention of general skill | decision-v7 dev regression | D28 replay (~25%), LoRA r16 at 2e-5 |

## Currencies spent freely

| Currency | Budget | Spent on |
|---|---|---|
| Teacher calls (Sol and Terra, fast) | ~18,000–20,000 | full-set labels, D5 severity, privileged labelling |
| Claude generations (Haiku and Sonnet) | ~3,000–3,500 plus ~300 headless runs, inside ~$200 of API credit | agent-side text, guess/ask continuations, benign rewrites, progress notes, agent runs |
| Record slots | 12,200 | per-objective plans scaled ~0.82; pairs and constructions inside the total |
| Modal training dollars | ~$10–13 per run (estimate) | one H100 run plus the smoke run |
| Build agent wall-clock | evening to ~07:00 | converters, constructions, labelling, training |

## Hard walls (never traded)

- 07:00 EST fallback trigger and the 11:00 EST deadline (D13).
- Public data only; licence and no-train notices honoured; the held-out suite is never trained on or used for selection (D37).
- One recipe, one run (D5); true resume makes a crash a delay, not a second run.
- Training renders are the runtime's formats exactly (D23, D38, D40).
- The monitor never sees raw reasoning; it sees notes in ~1% of thinking blocks (D27).

## Coupling ledger

| Pair | Coupling |
|---|---|
| Full-set labels × teacher throughput | ~3× more items than target-only labels; feasible only with batched, parallel subagents (D30). |
| Balance cap × rare questions | Trimming negatives costs no calls; rare questions still need positives from constructions. |
| Note-rate realism × reasoning signal | Signal moves into privileged teacher labels; the 3–5% note slice is practice only. |
| Long records × throughput | ~10% of records at 16–32K dominate token count; `--shared_prefix 1` and length-sorted passes contain it. |
| Steps (600–800) × calibration | Fewer steps hold calibration; per-question temperature repairs the rest. |
| Replay share × rare-question updates | Replay protects general skill and fights yes-bias, at the cost of task-row updates. |
| Selection × lift honesty | Picking on the intent slice and dev keeps the held-out lift unbiased; the slice is closer to training than the probe is. |
