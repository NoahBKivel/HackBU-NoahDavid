# Shared renderer checkpoint

The shared implementation is in `David/monitor_format/`. Its public exports are
listed in `__init__.py`. All product functions are pure. The caller supplies the
already-loaded tokenizer through the keyword-only `tokenizer` argument on
budgeted renderers and row fillers. The functions escape special-token strings
exactly like pinned Kev's `model.user_tokens` before tokenization.

## Validation

The complete renderer suite passed 23 tests at 00:41 EST on 2026-11-08.
It includes actual pinned-base BPE checks, full golden sessions, token budgets,
oldest-event collapse, recent-detail suffixes, document overflow, exact field
caps, schema failures, requirement-unit preservation, diagnostics and corrections.
The golden fixtures include corrected Noah sample events and every tool kind.

Changing one heading byte from `O` to `0` made the actual-tokenizer golden test
fail. Restoring it made the full suite pass. Evidence and the exact tested file
hashes are in `results/renderer/parity.json`, with red and green command output
beside it. The root orchestrator must attach its code commit hash to the gate log.
No commit has been made by the renderer worker.

The tests load the pinned `data/tokenizer/tokenizer.json` using the Rust
`tokenizers.Tokenizer` directly. This avoids the partially installed local torch
package, which temporarily makes importing transformers fail at
`torch._strobelight`. It uses the actual pinned BPE tokenizer, not a character
approximation. After torch installation completes, comparing AutoTokenizer token
ids with this loader on the fixture text is a useful integration check.

## Caller contracts

- Instructions are dictionaries with `id` such as `I1` and verbatim `text`.
- Documents are dictionaries with `path` and verbatim `text`, or a path-to-text map.
- `render_state` takes event sequence `k`, filters events through that sequence,
  and returns text, detailed event sequence numbers and the overflow fit flag.
- Sections have `id`, `path`, `heading` and verbatim `text`. Call
  `screen_section_cap` with the actual instructions and events, then
  `split_sections(..., tokenizer=tokenizer, cap=cap)` before rendering screens.
- Requirement units have `source`, one-based `position` and verbatim `text`.
  `rf_window` takes a zero-based index into that list.
- Findings have `id`, `question`, `event_seqs`, `correction_seq` and optional
  `status`, which defaults to `open`. The correction body never enters the state.
- Correction items have `question`, `event_seqs`, `requirement`, `probability`,
  `answer` and `evidence`. Optional `not_done` and `broken` lists explain G2.
  `severity` can request the serious stop sentence. M8 uses M2's correction.
- `fill_question` returns a fresh question row without its label. Supported
  fillers are `requirement_text`, `correction`, `fired_questions`, `event_seq`,
  `summary` and `section_id`. Supply the tokenizer and `row_budget` to enforce
  the available question-branch allowance. It defaults to 640 tokens.
- `validate_event` expects the specified fields even when empty. Nonempty
  `file_changes` are allowed only for Edit and Write. Patches are structured
  hunk lists or null. Turn-completed events require an end reason.

## Resume command

From the repository root:

```powershell
David/training/.venv/Scripts/python.exe -m pytest David/monitor_format/tests -q
```

There is no running renderer process. The worker is ready for a restart.

Active task anchor: TASKLIST.md:L16
