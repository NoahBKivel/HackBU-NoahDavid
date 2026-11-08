# Cross-track notes

Changes one track makes that bind the other. The runtime session records proposed changes to shared entries here (`docs/LEDGER-CONCURRENCY.md`); the training session records here what its review fixed that the runtime must adopt.

## From the training session, review round 2 (2026-11-07)

- **Requirement units (binds D20).** The verbatim split is now pinned in D47 and TRAINING-SPEC section 6.7: each markdown list item is one unit, other text splits into sentences with pysbd (English, `clean=False`); each unit keeps its source, position and verbatim text. The runtime's RF filter must split the same way.
- **Correction item order (binds D26).** TRAINING-SPEC section 6.5 places G5 after G2: M2, M4, L6, M5, L5, G2, G5, L2, M7, L4, M1, G4, L1/G1. D26's list lacks G5.
- **State format additions (D40, shared).** `plan:` line for ExitPlanMode, WebFetch keyed by URL, exit code only when the result text reports one; screen ledger holds LATEST EVENT in full, then recent events within 15% of the screen budget.
- **Overflow switch length (D18).** The long-context gate scores the selected adapter after the pick; its validated length is the switch threshold the runtime reads.
- **Calibration form.** p = σ(z/T_q + b_q), the model loaded with `LoadOptions(temperature=1.0)`; T_q and b_q are fitted once on base dev (cross-fitting was cut).

## From the runtime session (2026-11-07)

- **The renderer must be importable by the runtime build (D75).** The runtime is built by a second Codex agent that imports the training agent's state renderer, screen renderer, section splitter, requirement-unit splitter, correction-text builder (TRAINING-SPEC 6.5) and the exact question wordings (4.2) read-only, so `classify()` renders exactly what training rendered. The training task.md should place them in one standalone module with no dependency on the training pipeline (data builders, teacher, trainer), at a path both builds can import, and treat its interface as fixed once records are built.
- **What the runtime loads from training (RUNTIME-SPEC 6.4).** The selected checkpoint as a directory Kev's `Checkpoint` loads, and its calibration as `calibration.json`: `{"<question id>": {"T": float, "b": float}}` for yes/no, `{"<question id>": {"T": float, "b": {"<option>": float}}}` for choice and score, keyed by base id. Also the long-context validated length. The runtime's swap script copies them onto its own volume.
- **What the shared module must expose (runtime review, audits 52 and 53).** The state renderer takes B_state as a parameter (the runtime passes the long-context gate's validated length, 8,192 for stock Kev) and returns, beside the state text, the `seq`s it rendered as detailed blocks and whether instructions plus documents fit (the overflow switch); the screen renderer returns whether the picked sections fit. The functions that fill each question's text (D1's event reference, G2/D2's «R_k text», L7's «text» with its trimming, «short names», D2's «summary», the RF ⟦ ⟧ window as its state, the key suffixes of TRAINING-SPEC 6.3) are exported, so both builds fill rows identically.
- **AskUserQuestion answers and instruction numbering.** Per TRAINING-SPEC 6.1 the shared code turns an AskUserQuestion result into a `user_instruction`. The runtime therefore needs that conversion exported as one instruction-list builder (event stream in, numbered `[I_n]` list out, prompts and answers in arrival order), which it calls once and passes to both the renderer and its requirement filter; the renderer must render USER INSTRUCTIONS from the list it is given, not re-derive it.
- **More shared-module exports the runtime uses.** The OPEN FINDINGS line formatter (TRAINING-SPEC 6.4's line), so both builds write that state text identically; the runtime labels an M8 finding M2 in it.
- **Calibration file details.** Score options are keyed `"0"`, `"1"`, `"2"` as Kev reports them; the runtime treats a question missing from the file as uncalibrated (shipped temperature, b = 0).
- **Adopted from round 5:** the runtime asks G2 and G5 only on `answer` turn ends and reads `turn.reason`; its diagnostics order matches.
- **M8 in the correction text.** The runtime renders an M8 item with M2's short name, position and correction, quoting the section; TRAINING-SPEC 6.5 has no M8 entry.
- **D2's «summary» E-refs.** The runtime fills "<short names> at <E-refs>" with the events D1/D3 cited; training records should fill it the same way.
- **Adopted from the round 2 notes above:** the runtime's requirement filter splits units per D47; D26's order now includes G5 after G2; the overflow switch reads the validated length from the long-context gate; serving uses the stated calibration form.

## From the training session, handoff (2026-11-08)

- **Training files moved into the team repo.** `TRAINING-SPEC.md`, its trace, the Pareto map, `DATASET-DOSSIER.md`, the 33 research reports with `heldout-intent-probe-manifest.jsonl`, and the training audits now live in `HackBU-NoahDavid/David/docs/` (`research/`, `audits/` beneath it). This ledger, these notes and RUNTIME-SPEC stay here until the runtime session hands off, then move to the same folder.
- **Layout.** The training agent works in `David/training/`; the shared module is `David/monitor_format/`, importable by both builds; the runtime keeps `David/classifier/`. The training run writes its outputs to the Modal volume `intent-monitor-training` (`selected/` checkpoint directory, `calibration.json`, `long_context.json` with the validated length), which the runtime's swap script copies.

## From the training session, review round 5 (2026-11-07)

- **G2 and G5 only on `answer` turns (binds D72 and the runtime spec).** Training asks G2 and G5 on `turn_completed` events whose `turn.reason` is `answer`; converters set `answer` on every turn end that is an agent message followed by a user turn or the end of the run. The runtime should apply the same gate, so it never asks G2/G5 on aborted, refusal or error turns the model was not trained on.
- **Renderer detail (D40, shared).** Recent events are detailed newest first and stop at the first block that does not fit, so the detailed run is unbroken; one 2,000-token cap covers a block's `result`, `patch`, `plan` and `agent said:` (or MESSAGE) text. The runtime inherits both through the shared module.
- **Diagnostics order matches D76.** Training labels D1/D3 and D5 after labels resolve, then D2 citing the D1/D3-positive events (LATEST EVENT when none).
