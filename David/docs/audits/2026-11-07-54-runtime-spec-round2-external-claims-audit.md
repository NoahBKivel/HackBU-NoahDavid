I found one claim that is wrong and four that are right but imprecise. The wrong one is the name `kev.api.prepare` in 6.4: no function by that name exists. Everything else on the checklist holds against the code and docs.

**Sources.** I confirmed the Kev clone's HEAD is `fc4a17e194bca35a48c57211392ec49ea54a94ac`, and I read its code without running it. I also read the three HackBU files, report 31, and Modal's Dicts and concurrent-inputs guides.

## Findings

**F1. `kev.api.prepare` does not exist (spec is wrong; medium consequence).**
- **Spec, 6.4:** "Probabilities are read unrounded through `Server.probs(rec)` with `rec, meta = kev.api.to_record(kev.api.prepare(request))`".
- **Source:**
  - `kev/api.py` (L1–165) has no `prepare`, and `kev/__init__.py` is empty (0 bytes), so nothing re-exports it.
  - `prepare` is defined in `kev/serve.py` L223–225: `return req.model_copy(update={"state": with_date_facts(req.state)}) if DATE_FACTS else req`.
  - `Server.answer` calls it as the bare name `prepare(req)` inside `serve.py` (L202).
- **Consequence:** code written from the spec raises `AttributeError` on its first event. The fix is `kev.serve.prepare(request)`, or simply `kev.api.to_record(request)`. Both are the same here, because `prepare` changes nothing unless `KEV_DATE_FACTS=1`, and the deployed image doesn't set it.

**F2. `Server.probs(rec)` returns a tuple, not just the probabilities (right but imprecise; low consequence).**
- **Spec, 6.4:** "Probabilities are read unrounded through `Server.probs(rec)`".
- **Source:**
  - `serve.py` L147–148: `probs` returns `self.submit(rec).result()`.
  - L133: the future holds "(probabilities, stats)".
  - L189–191: the value is `([q.tolist() for q in p], {"tokens": …, "latency_ms": …, …})`, with one unrounded fp32 list per question.
  - Option order comes from `api.py` L98 and L110. For a yes/no question it is `[no, yes]`, so `p[1]` is yes. For a choice it is criteria order, and for a score it is level order.
- **Consequence:** the builder has to write `ps, stats = server.probs(rec)` and index `p[1]`/`p[0]` for yes/no. Pairing the raw return value with `meta` goes wrong. The spec should state both.

**F3. `backend_sent_at` doesn't measure the backend's actual wait (right but imprecise; medium-low consequence).**
- **Spec, 7.10:** "a result is late when `time.time() − backend_sent_at ≥ 8.0`". **Spec, 1:** "delivered once … (lateness measured from `backend_sent_at`)".
- **Source:**
  - Noah `app.py` L321: `call = await classifier().classify.spawn.aio(event)`. L326: `raw = await call.get.aio(timeout=CLASSIFY_WAIT_S)`. The 8 s clock starts only after `spawn` returns.
  - The backend is itself a separate Modal app (`alignment-monitor`, L34 and L364–372). So `backend_sent_at` and `time.time()` in `classify` come from two different hosts' clocks.
  - Report 31 C3 puts Dict I/O at about 100 ms. In the current code that Dict work happens after the lateness decision and before the return (`app.py` L144–157).
- **Why the measurement is off:** the backend actually gives up at (`backend_sent_at` + spawn latency + 8 s). It receives the result only after `classify`'s remaining Dict work plus the return transport. Any clock offset between the two hosts adds to the error.
- **Consequence:** two narrow windows open near the 8 s boundary.
  - **Duplicates.** A result marked late can still reach a backend that is waiting. It is then delivered twice, now and again in `late_results`. CONTRACT L158 says the Mod applies each result by `event_id`, so a correction could be injected twice. This breaks "each delivered once" and could make `burst-backlog` flaky.
  - **Losses.** If the Dict work plus return transport takes longer than the spawn latency, a result marked on time can arrive after the backend has stopped listening, and it is lost.
- **Fix:** make the lateness check the last step before returning, and use a margin (for example 7.5 s). Then also drop any late result the backend already returned. One backend container (`max_containers=1`, L367) could keep that list in memory. Or state the boundary behaviour as accepted.

**F4. Section 9 understates the Modal and Dict overhead (right but imprecise; low consequence).**
- **Spec, 9:** "Modal and Dict add about 0.05–0.15 s".
- **Source:** report 31 C3 (L47). A skipped event, which only reads the Dict, takes about 100 ms of `classify_ms`. The client round trip minus `classify_ms` adds 56 ms at the median (239 − 183) and 144 ms at p95 (343 − 199).
- **Consequence:**
  - Report 31 supports roughly 0.15–0.25 s, so the stated range sits at or below the Dict share alone.
  - The new design writes at least two Dict entries per event (6.5). Report 31 measured reads only.
  - The client in C3 was outside Modal, so its round-trip overhead may run higher than the backend's.
  - No latency budget changes: everything stays far below 8 s.

**F5. "So Kev's server batches them" in 7.2 is true but weaker than it sounds (right but imprecise; low consequence).**
- **Source:**
  - The model thread starts a batch with the first record queued and then takes only what is already waiting (`serve.py` L153–160, with a 0.05 s blocking get and then `get_nowait`). So a loop of `submit` calls can split across two batches.
  - States between 1,024 and 4,096 tokens get an eager state pass one at a time (`model.py` L475, L484; `cuda_graphs.py` L46, L52, L268–271). Only their question rows share graphed passes.
- **Consequence:** for RF windows of about 2K tokens, batching saves only the row passes. Section 9's "about 0.1 s per unit … several seconds" already assumes that, so nothing else changes.

## Verified correct (one line each)

- `LoadOptions(dtype=torch.bfloat16, cuda_graphs=True, fused=True, temperature=1.0)` is valid: all four fields exist on the frozen dataclass (`checkpoint.py` L121–128). It matches the deployed call (`app.py` L98) plus `temperature`. An explicit `fused=True` needs fla `0.5.2`, which equals `FLA_VERSION` (`fused_qwen35.py` L53) and is what the image pins (`app.py` L41).
- `temperature=1.0` makes the loaded head read 1.0 (`checkpoint.py` L241), and the head then returns raw logits (`model.py` L218, L223).
- `Checkpoint.meta.temperature` holds the shipped value from `head.pt` (`checkpoint.py` L16, L61, L173). Report 31 L11 measured 2.406 for this checkpoint.
- `Server.answer` rounds to 4 decimals and returns only p(yes) for a yes/no question (`api.py` L143–146, L153).
- The probabilities are unrounded fp32: the head and softmax run in fp32 on both the eager and the graphed path (`model.py` L324, L360, L413–414, L503–505; `serve.py` L189).
- z = log p_yes − log p_no recovers the raw logit difference exactly in fp32. The only break is when p_no underflows to 0, which needs a gap of about 100 or more in the raw logits.
- z_o = log p_o for choice and score questions differs from the raw logits by a constant shared across options, and softmax(z/T + b) ignores that constant.
- With T = the shipped temperature and b = 0, the calibrated p equals Kev's shipped p.
- `Server.submit` returns a `Future`, and one model thread batches up to 64 queued records (`serve.py` L34, L132–145, L150–170).
- States over 4,096 tokens are not admitted to the CUDA graphs, even when cached, and run one at a time through `probs_one` inside the batch (`cuda_graphs.py` L52, L268–271; `model.py` L472–477).
- 7.3: serving checks only the state against `SERVE_MAX_STATE` and each row (state plus branch) against `SERVE_MAX_BRANCH` (`model.py` L102, L112, L138). There is no packed-length check on the serving path: `max_packed` is enforced only in `predictors.py` L129 and `train.py` L329. `questions` has no maximum count (`api.py` L46).
- `Server` is built to be called from several threads. Its docstring says "Request threads encode their record and queue it" (`serve.py` L95–100), and it uses a `queue.Queue` plus futures (L114, L143–145). The prefix cache is touched only by the model thread.
- Modal Dict: the per-object limit is 100 MiB, objects under 5 MiB are recommended, and entries expire after 7 days of inactivity (Dicts guide). One entry per event, capped at 5 MB (CONTRACT L76), fits.
  - The header can go past the 5 MiB recommendation with large documents: it stores each document twice, as `documents` and as unit texts, and is rewritten after every event. It stays far below 100 MiB.
- "For synchronous Functions, Modal will execute concurrent inputs on separate threads", and the class-level decorator applies to all methods (concurrent-inputs guide). Kev's single model thread serializes the GPU work.
- The backend calls `classify.spawn.aio` and then `get.aio(timeout=8)` (Noah `app.py` L321–328, `CLASSIFY_WAIT_S = 8` at L32), and it doesn't yet send `backend_sent_at`.
- Section 9 figures against report 31:
  - 1,221 ms at 8K and 2,907 ms at 32K for 12 rows on a cache miss (L35, L39).
  - About 70 ms per row above 4,096 tokens (L43).
  - 10–25 D1 rows is 0.7–1.75 s.
  - 107 ms for one row on a 2K miss (L33), and 60 units comes to about 6 s.
  - An 8K state with 20 rows takes 1,789 ms, so several screen states plus the merged state exceed 8 s.
  - $2.27/h (C5).

One thing outside my brief: 6.5 keys each event as `<session_id>:e:<seq>`, but the backend allows `seq` to be absent (Noah `app.py` L48), and 7.10 lets such events through. Two events without a `seq` would share the key `…:e:None`, and the second would overwrite the first.

## Coverage ledger

| Source | Lines read | Every line covered |
|---|---|---|
| `reading-context`, `out-of-cutoff`, `receipts-before-claims` SKILL.md | 1–98, 1–103, 1–29 | yes |
| `RUNTIME-SPEC.md` | 1–345 | yes |
| Round-1 audit (`…-51-runtime-spec-external-claims-audit.md`) | 1–101 | yes |
| Report 31 | 1–98 | yes |
| `kev/serve.py` | 1–358 | yes |
| `kev/api.py` | 1–165 | yes |
| `kev/checkpoint.py` | 1–362 | yes |
| `kev/model.py` | 1–508 | yes |
| `kev/cuda_graphs.py` | 1–375 | yes (round 1 only searched it) |
| `kev/__init__.py` | 0 bytes | yes |
| `kev/fused_qwen35.py` | L53 only, via grep | no (located `FLA_VERSION` only) |
| `kev/predictors.py`, `kev/train.py`, `kev/suite.py` | grep hits for `max_packed` only | no (located only) |
| `David/classifier/app.py` | 1–161 | yes |
| `Noah/backend/app.py` | 1–394 | yes |
| `CONTRACT.md` | 1–261 | yes |

I fetched two Modal pages: `modal.com/docs/guide/dicts` and `modal.com/docs/guide/concurrent-inputs`. Not checked: `TRAINING-SPEC.md` and whether Modal keeps the clocks of two containers in sync (no Modal doc I fetched says either way).