# Deployed rendering driver

Run after other dev GPU verification is quiet:

```powershell
$env:PYTHONUTF8='1'
& 'David/classifier/.venv/Scripts/python.exe' David/classifier/scripts/verify_rendering.py --target dev
```

The script compiled and its CLI help loaded. No GPU check was run by the renderer worker, so no gate PASS is claimed.

The driver sends corrected Noah samples and a handwritten session through classify.spawn and get(timeout=8). It waits for any pending original to finish only to inspect its completed shape; that inspection is not counted as backend delivery. Before each call it snapshots the deployed session header and independently applies correction arrival marking to the reference finding fields. Expected state uses the shared renderer and a tokenizer loaded at the base/revision logged by the deployed class, with token=False. No Kev code runs locally.

The handwritten stream covers one AskUserQuestion answer, a missing seq3 followed by a late seq3 instruction, and answer versus aborted turn ends. The expected G2 set comes from the actual accepted requirement units, rather than assuming RF accepts every instruction. The four samples use empty shell file_changes, null denied, and structured Edit patch hunks with the action path.

Evidence goes to results/rendering: calls.json, headers.json, reference-states.json, model.log and parity.json. The script saves completed-call receipts incrementally, then fetches app logs and compares actual request-state digests. A one-byte changed reference text must be rejected by the same comparison function. This negative control checks the comparator against a fixed deployed digest; it does not redeploy a product-source mutation. If the owner requires a product mutation literally, run that separate-worktree variant and preserve the expected failure in addition to this receipt.

The default length is the current stock serving contract. Pass --length if the deployed validated length changes. All samples use fresh session IDs. The intentional missing event incurs the real eight-second wait and may produce a late result. The script is a correctness check, not a latency characterization.
