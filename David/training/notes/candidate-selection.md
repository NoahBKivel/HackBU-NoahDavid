# Candidate scoring and calibration

The `intent_training.select` package reads prepared records and uses Kev's
`materialize` function for option order, hard labels and soft targets. Scoring
loads checkpoints at temperature one, uses `forward_batch` with shared prefixes,
and admits physical batches under the caller's padded pass-token cap. CUDA
scoring binds the existing required FLA kernels and requests SDPA. No local model
load or GPU measurement was performed for implementation verification.

Each scored question row carries `record_id`, `group_id`, `question_id`,
`options`, `label`, `target`, `logits`, `temperature`, `is_intent` and
`is_base_dev`. Boolean option keys are `false` and `true`; score option keys
are string indices. Choice option keys retain the record's canonical order.
The evaluation module consumes the same raw-logit rows for serving parity.

Selection averages AUROC equally across base questions, using macro one-versus-rest
for choice and score questions. Training twins are excluded. Candidate rows must
match exactly in identities, groups, labels and dev membership. The paired
bootstrap samples dev groups with replacement. Cached rank and tie information
allows multiplicity-weighted AUROC to equal literal duplication of sampled rows.
Every candidate receives the same 1,000 accepted resamples. Degenerate draws
without both classes are rejected jointly and counted. The one-standard-error
kept set is ranked by intent AUROC, followed by stock as the fallback.

Calibration uses only rows marked `is_base_dev`; top-up rows are excluded. Tuned
calibration computes prior offsets from post-cap training targets and base dev
targets with half a pseudocount per class, then fits temperature constrained to
at least one. Stock fits temperature and offsets jointly. Output is keyed by
base question ID in the runtime's `{T, b}` format. The offset is applied after
temperature. SciPy and NumPy were already available in the reused environment.

With `src`, `vendor/kev` and `David` importable, the executable interface is:

```text
python -m intent_training.select score --checkpoint <checkpoint> --records <dev.jsonl> --out <scores.jsonl> --max-state <limit> --pass-tokens-max <cap> --base-dev --intent-ids <ids.json>
python -m intent_training.select pick --candidate stock=<stock.jsonl> --candidate tuned=<tuned.jsonl> --stock stock --out <selection.json>
python -m intent_training.select calibrate --dev-scores <winner.jsonl> --train-records <frozen.jsonl> --out <calibration.json>
python -m intent_training.select calibrate --dev-scores <stock.jsonl> --stock --out <stock-calibration.json>
```

Score base dev and top-ups separately so only base dev carries the fitting flag.
Combine their score rows for candidate discrimination. Intent IDs are explicit
record IDs from the grouped intent slice. Production candidate scoring, the
selected model's calibration fit and serving parity require actual dev records
and model checkpoints; unit fixtures do not close those gates.
