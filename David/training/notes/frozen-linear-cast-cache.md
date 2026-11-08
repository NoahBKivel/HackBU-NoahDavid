# Frozen linear cast reuse on B200

Retain native SDPA with checkpointing ON and the measured physical cap. Caching frozen linear weights produced only 0.543748 percent more useful tokens per second on the same immutable 46-record payload. This change is not adopted, and the 20,000 useful tokens per second target remains unmet.

| Measured arm | Useful tokens/s | Records/hour | Peak allocated bytes |
|---|---:|---:|---:|
| Native reference | 5087.099373684 | 7510.909916923 | 55918221312 |
| Frozen linear cache | 5114.760397422 | 7551.750372798 | 62793005568 |

Both rate arms warm every optimizer group, restore the same trainable snapshot and seed, execute two fixed parity updates, then time two complete cycles. Logical batch is 16, physical cap is 46,080 padded tokens, and pair/sibling grouping, model weights, dropout, loss, normalization, clipping, optimizer and scheduler remain the native paths. The candidate retains the original fp32 frozen weights and caches their existing bf16 autocast representation for 248 frozen Linear modules. The cache occupies 7,138,181,120 bytes and serves 21,824 calls. Trainable parameters, embeddings, norms, residual streams and attention remain unchanged. Production never imports the candidate module.

The maximum relative two-update loss difference is 0.000505560061; measured same-seed repeat noise is 0.000107319093. The instrument reports PASS because it follows the prior max(noise, 0.001) numerical floor. The difference exceeds measured repeat noise, and the negligible rate gain supplies no reason to accept that uncertainty or the added memory. The operational verdict is rejection.

## Source findings

The graph-retention hypothesis is ruled out. Both `kevpatch/profile_training.py:training_step` and `kevpatch/batched_measure.py:_step` backpropagate each physical pass immediately after globally normalizing its loss. Logged losses are detached. Gradients accumulate until one clip and optimizer update. Checkpointing-OFF OOM evidence already used this per-pass backward behavior.

`kevpatch/measure.py:training_model` loads the frozen backbone in fp32. The actual profiler records 1.675630 GPU-seconds in `aten::copy_` and 5,173 bf16 copy kernels. Reusing frozen matrix casts barely changes warmed throughput, so those aggregate copy costs do not support a claim that frozen matrix recasting dominates. Other activation and residual casts remain. Native `kev.train.batch_loss` calls `ce.item()` once per record and checks a CUDA finite scalar; the measurement harness also converts pass losses to Python floats. These are concrete synchronization sites, but this experiment does not establish that removing them materially accelerates training.

The profiler's 15,180 Command Buffer Full events and 7.135426 CPU-seconds are instrumented-profile facts, not unprofiled launch-overhead measurements. No CPU bottleneck claim follows from them alone.

## Evidence

- Payload SHA256: `011d0842ac022f663447094c6b5505d5211ce3cd3fda2466dc57e3af97e56501`.
- Private volume: `/training/cast-cache/20261108T102210460074Z/result.json`.
- Local immutable result: `results/cast-cache/result.json`.
- Modal call: `fc-01M6XAVZXZHBRX5AY96PHYXGK6`.
- App: `ap-HfTnAu1HLUbepBoC7iojjx`; image: `im-Oz52jizMJo9FkBhXPvB39L`.
- Code commit: `c25022a`.
- Three instrument modules passed AST parsing and named-file credential scans before launch. The staged scan found zero credentials. The actual B200 experiment completed every arm and remained below the 90 percent allocation limit. No local Torch import or dependency installation occurred.

The existing fixed sample is a geometry and compute experiment, not the final 122-record representative mixture. Its sampler and the eventual full-run forecast remain owned by the training coordinator. No further optimization trials are planned from this branch.
