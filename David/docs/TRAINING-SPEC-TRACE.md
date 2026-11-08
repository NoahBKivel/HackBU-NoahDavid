# Trace: decision ledger → training specification

An internal check that every training-relevant decision in `DESIGN-DECISIONS.md` is carried by `docs/TRAINING-SPEC.md`, so the executor, who reads only the spec, misses nothing.

| Ledger entry | Spec section(s) |
|---|---|
| D1 product target | 1, 4.2 |
| D2 black-box observation (thinking notes only when shown) | 6.1, 7.5, 8.1 |
| D3 Kev-4B, pinned revision | 1, 9.1 |
| D4 native noul / choice / score | 4.2, 6.3 |
| D5 one recipe | 9.1 |
| D6 public data, existing labels first | 2, 7.3, 8.4 |
| D11, D26 correction template and composition | 6.5 |
| D13 08:00 best-model rule, demo | 9.4, 12.3 (demo check), 14 |
| D18 long context in the recipe, overflow records | 6.6, 7.4, 7.7, 12.3 (long-context validity) |
| D19 question set, D38 exact wordings | 4.2 |
| D19.P screen form, section unit, M8 placement | 4.2 (SCR, M8), 6.6, 7.4 |
| D20 requirement filter (RF) | 4.2 |
| D21 classified event types | 6.1, 7.2 |
| D22 run ledger and sizing | 6.4 |
| D23 layout (training uses full prefill) | 6.4 |
| D27 recipe, intent hardening, rendering, rewrites, balance, batching, steps, pick rule, calibration | 7.5, 7.6, 7.8, 9.1–9.5 |
| D28 composition, sources, exclusions, agent runs, scope total | 7.1, 7.3, 7.9, 8.7, 11 |
| D30 construction vs teacher, votes, vote form, instructions, label clash, mismatch, priority band, throughput, generator | 7.4, 8.1–8.6 |
| D32, D32.P intent battery and probe | 7.9 (held out), 12.4 |
| D33 host, flags, Unsloth gate, saves, true resume | 9.1, 9.2, 12.1 |
| D36 track boundary | 1 (scope), 6 |
| D37 splits, dev floor, held-out, lift | 7.9, 12.4 |
| D40 data-touching formats | 6.4, 6.5 |
| D41 forced mechanics | 7.1, 7.5, 9.1, 9.5, 10 |
| D42 guarantees and approximation bounds | 1, 12 |
| D43 architecture, side record, negative cuts | 5, 6.2, 6.3, 7.2 |
| D44 gates | 12 |
| D45 build values | 6.6, 7.2, 7.3, 7.4, 8.3, 9.4, 12.1 |
| D47 round-2 mechanics | 4.1, 4.2, 6.4, 6.7, 7.3, 7.7, 7.8, 7.9, 12.3 |

Not carried (runtime track or execution): D7, D8, D9, D10, D12, D14, D15, D16, D17, D24, D25, D29, D34, D35 belong to the runtime specification; D39 (one Codex agent, prompts it writes, stage choreography) belongs to the task file.
