I found no outright false claims, but three findings change what a builder must do. The pinned Kev code doesn't support the calibration path as written (F1, F2), and the "No lost results" guarantee depends on a Modal behaviour the current timing rule can't see (F3). Four smaller findings follow. Everything else I checked holds.

Sources checked: Kev cloned into `C:\Users\david\AppData\Local\Temp\claude\e4a7ca8b20dbf3e0\268d08f3-9886-4040-b110-005af90899a7\scratchpad\kev-verify\repo` at `fc4a17e1…` (code read, nothing run); the three HackBU files; `verify_deploy.py`; reports 31 and 1; Modal docs (Dicts, concurrent inputs, scale, Volumes, `modal.concurrent`, job queue); and modal-client source `py/modal/app.py` for the `App.cls` signature, because the docs page rendered empty.

## Findings

**F1. The loading options are incomplete (right but imprecise; high consequence for a builder).**
- **Spec, 6.4:** "The model is loaded with `LoadOptions(temperature=1.0)`."
- **Source:** `kev/checkpoint.py` L121–128 sets the defaults: `dtype=None` means fp32 (L89), and `cuda_graphs=None` and `fused=None` mean both are off (L113–119). Only `kev.serve.main()` switches on bf16, CUDA graphs and fused kernels (`serve.py` L343–347). Constructing `Server` directly does not.
- **Current code:** `app.py` L98 passes `LoadOptions(dtype=torch.bfloat16, cuda_graphs=True, fused=True)`. Report 31 L13 measured the section 9 latencies on that configuration.
- **What the code does with temperature:** `checkpoint.py` L241 sets `m.head.temperature = meta.temperature if opts.temperature is None else opts.temperature`, and `model.py` L218/L223 divide the logits by it. So `temperature=1.0` does give raw logits, and that part is right.
- **Consequence:** a builder who writes the call literally gets an fp32 model with no graphs and no fused kernels. That means roughly twice the memory and latencies that no longer match section 9.
- **Fix:** write `LoadOptions(dtype=torch.bfloat16, cuda_graphs=True, fused=True, temperature=1.0)`.
- **Related:** with T = 1 loaded, `model.head.temperature` reads 1.0. The stock fallback ("T = the checkpoint's shipped temperature") has to read `ck.meta.temperature` (`checkpoint.py` L61, L173). The current load log (`app.py` L106) prints `model.head.temperature`, which would then show 1.0.

**F2. Kev never exposes logits, and `Server.answer` rounds probabilities (unsupported / imprecise; high consequence).**
- **Spec, 1 and 7.4, and the section 10 check:** "p = σ(z/T_q + b_q)…", "Each raw output is calibrated…", and section 10's "the p `classify()` acts on equals σ(z/T_q + b_q)".
- **What Kev returns:**
  - Only softmax probabilities: `model.py` L413 and L505, computed in fp32 because the head runs in fp32 (L324, L360).
  - `Server.probs` / `submit` return them unrounded as `q.tolist()` (`serve.py` L147–148, L189).
  - `Server.answer`, which the deployed code and report 31's Part D both use, rounds everything to 4 decimals (`api.py` L143–146), and gives a yes/no (noul) question only `p(true)` (`api.py` L153).
- **How to get z:** it has to be rebuilt, as z = log p_yes − log p_no for a yes/no question, or as log p (up to a constant) for a choice. That is exact from `Server.probs`. It is not exact from `Server.answer`.
- **This happens on real outputs.** Report 31 L73 shows still-pursuing items as low as p = 0.01 at T = 2.406. That is a raw z of about −11.1, so the raw p_yes is about 1.6e-5. `Server.answer` rounds it to 0.0, and log(0) gives −inf or a math error.
- **Consequence:** the section 10 calibration test can't pass exactly, and saturated rows produce infinities or NaN. A NaN risk fails the backend's `ge=0, le=1` check (Noah `app.py` L70), so the backend returns its fallback result.
- **Fix:** the spec should name `Server.submit`/`probs` together with `kev.api.to_record` as the path, not `answer`.

**F3. "No lost results" can't hold under the timing rule the spec keeps (unsupported; medium-high consequence).**
- **Spec, 1:** "No lost results. A result that finishes after the backend's 8 s wait is delivered once…"
- **Spec, 7.10:** "Lateness keeps its current rule: a result finishing ≥ 8.0 s after the method started is stored…" with `max_containers=1` and `max_inputs=4`.
- **Source:**
  - `app.py` L120 starts the clock inside the method.
  - The backend's 8 s starts after `spawn` returns (Noah `app.py` L321–328).
  - Modal says extra inputs "may need to queue up" while containers start (concurrent-inputs guide). The scale guide implies inputs wait when no capacity is free. With `max_containers=1`, a 5th concurrent input therefore waits outside the method.
- **Consequence:** a result can finish under 8 s by `classify`'s clock but after 8 s by the backend's. It is then neither returned nor stored. That happens to anything that queued during a burst, and to cold starts (which section 12 already lists).
- **The spec contradicts itself:** section 1 claims the guarantee and section 10's `burst-backlog` test expects it, but section 12 leaves `backend_sent_at` open. Bursts need the same fix as cold starts.

**F4. The contract check can't use `verify_deploy.py` as it stands (right but imprecise; low-medium).**
- **Spec, 10:** "validates against Noah's `Result` model (`David/classifier/verify_deploy.py`)".
- **Source:** the `Result` copy in `verify_deploy.py` L27–48 is verbatim. But `check()` (L57–58) also asserts `actions == []` and that `drift` and `drift_rate` are None.
- **Consequence:** every result from the new design fails `check()` until those asserts are changed.

**F5. "Kev's prefix cache makes the repeat state free to reuse" (7.5, 9) is true only when the cached state hasn't been evicted (right but imprecise; low-medium).**
- **Source:**
  - The cache key is the exact state token tuple (`serve.py` L55). The same state string is a hit, and its prefill is skipped (report 31 C2: 8K miss/hit at q = 1 is 470/71 ms).
  - The cache is shared LRU across all requests: 4 states and 65,536 tokens (`serve.py` L27–29, L80–87). At 32K only two states fit.
  - A batch keeps only its last distinct new states (`serve.py` L52–61).
- **Consequence:** with `max_inputs=4`, other sessions' events, RF windows or overflow screen states can evict the state between the first and second request. The diagnostics request then pays full prefill, about 2 s at 32K.
- **What stays true either way:** the "~70 ms per row" figure. Report 31 L43 says it holds on long states whether or not the state is cached.

**F6. "Submitted together" in 7.2 and 7.9 (right; imprecise on how).**
- **Source:** the model thread takes everything queued, up to 64 requests, as one batch (`serve.py` L34, L150–160).
- **But:** `Server.answer` blocks (L147–148, L200–203). Batching only happens through `submit()` futures or concurrent threads.
- **No speed-up above 4K:** states over 4,096 tokens aren't admitted to the CUDA graphs (`cuda_graphs.py` L52, L268–271) and run one at a time inside the batch (`model.py` L475–477). So the 8K screen states get no parallel gain. That is consistent with section 9's "expected beyond 8 s".

**F7. The Modal Dict session record and 7.10's threading (right; imprecise).**
- **Size:** the Dict can hold the record as described. Modal's per-object limit is 100 MiB, but its docs recommend objects under 5 MiB. The record holds full documents (the Mod sends up to 5 MB per event, CONTRACT L76) and an event list that keeps growing, and the spec rewrites the whole record after every event. In report 31 C3, Dict I/O was already about 100 ms on tiny records.
- **Expiry:** each entry expires after 7 days without a read or write. That is irrelevant for the demo but unstated.
- **Threads:** Modal runs a sync method's concurrent inputs "on separate threads", so the in-memory records and the ordering gate need locking. `Server` itself is thread-safe (a queue plus futures).

## Verified correct (one line each)

- The temperature divides the pointer logits at inference; 1.0 means raw (`model.py` L211–223, `checkpoint.py` L105, L241).
- Stock fallback: "T = shipped temperature, b = 0" reproduces Kev's shipped probabilities exactly (`softmax(z/T)`).
- Hub id `jaredpalmer/kev-4b@6cfce5c2…` matches `app.py` L25–26; `Checkpoint` accepts either a directory or `hub@rev` (`checkpoint.py` L30–45).
- Over-length states are refused: more than 65,536 tokens including `<state>` raises `ContextOverflow`, turned into an in-process `HTTPException(422)` (`model.py` L18, L101–103, L130–142; `serve.py` L139–142), which reaches the backend's fallback (Noah `app.py` L329–331).
- Section 9: 8K miss q = 12 is 1,221 ms and 32K miss q = 12 is 2,907 ms (report 31 L35, L39). These are Kev model time and exclude Dict I/O.
- Section 9: about 70 ms per row on long states (report 31 L43; 8K hit (1,375−71)/19 ≈ 69 ms; 32K ≈ 73 ms).
- Section 9: $2.27/h (report 31 C5; estimated from list rates).
- The every-event set has 12 rows.
- The 16,000-character cap equals 4 × 2,000 × 2.
- `App.cls` accepts `max_containers` (modal-client `py/modal/app.py` L1135, L1149, L1190).
- `@modal.concurrent(max_inputs=…)` decorates a class (Modal reference).
- A Dict persists across containers and redeploys (Modal Dicts guide).
- Volumes: a new container mounts the latest committed state at start; a running one needs `reload()`. This supports 7.11's "redeploy after the swap".
- The backend calls `classify.spawn` and then `get(timeout=8)` (Noah `app.py` L321–328), and `CLASSIFY_WAIT_S = 8` (L32).
- The current lateness rule and `_test_sleep_s` behaviour match `app.py` L133–156.
- The read-only tool list matches Noah's `READ_TOOLS` (L132).
- Notice texts carry no source prefix (CONTRACT L240).
- `Result`/`Action` fields: `event_id` str is required, `flagged` bool, `risk` Optional[float] in [0, 1], `details` dict, `actions` list of Action (`type` required, `level`/`text` optional), `pending` defaults to False, and `extra="allow"`. So `drift`, `drift_rate` (including negative values) and `late_results` pass through, and the backend checks each late result separately (Noah `app.py` L38–108).
- L40S, `max_inputs=4` and the `intent-monitor-sessions` Dict match `app.py` L48, L86–88 and CONTRACT section 6.

## Coverage ledger

| Source | Lines read | Every line covered |
|---|---|---|
| `RUNTIME-SPEC.md` | 1–326 | yes |
| report 31 | 1–98 | yes |
| report 1 | 1–171 | yes |
| `David/classifier/app.py` | 1–161 | yes |
| `verify_deploy.py` | 1–102 | yes |
| `Noah/backend/app.py` | 1–394 | yes |
| `CONTRACT.md` | 1–261 | yes |
| `kev/serve.py` | 1–358 | yes |
| `kev/api.py` | 1–165 | yes |
| `kev/checkpoint.py` | 1–362 | yes |
| `kev/model.py` | 1–508 | yes |
| `kev/cuda_graphs.py` | located by grep only (L52, L268–271) | no, not a full read |

Modal docs fetched: the Dicts, concurrent-inputs, scale, Volumes and job-queue guides, plus the `modal.concurrent` reference. The `modal.App` reference page came back empty, so I checked `App.cls` against modal-client `py/modal/app.py` instead.

Not checked: the companion `TRAINING-SPEC.md`, NOAH.md and the NN-002 claim in section 11, and the 07:00 rule. None of these were in the sources I was given.