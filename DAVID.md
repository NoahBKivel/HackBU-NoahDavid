# David's side: the classifier

This is the architecture and build guide for `David/`: the alignment classifier on Modal.
- Shared context, the system overview and the interface with Noah's backend are in [CONTRACT.md](CONTRACT.md). **Read it first.**
- Noah's side is in [NOAH.md](NOAH.md).

> **Every agent: keep this file current.** Maintained by David's agents. Whenever you learn or change something another agent would need, update the right section **in the same change**. Interface changes go in CONTRACT.md, and only with both sides agreeing. Edit sections in place. If something turns out to be wrong, fix it. Don't work around it.
>
> **Seeded by Noah's agent on 2026-11-07** from the planning discussions with David. Everything marked *(to confirm)* is David's call. **David's agent: correct and expand this file.**

---

## 1. Job

**Runtime deployment milestone, 2026-11-08 04:52:37 -0500:** The designed classifier is live and warmed on stock Kev, deployed from `3b40ef1` with product code `5baed45`. A fresh backend-style stream validated the results.

**Deployed now:** app `intent-monitor`, class `Classifier` (`classify` + `warmup`), serves the designed classifier on stock Kev-4B. Reads are unscored; classified events return calibrated risk and drift, with notices and corrections for qualifying findings. The trained-model swap has not run. Oversized documents now use the verified screen-and-merge path, with `details.overflow` on those results. Product commit: `6e81f7a`.

Expose `classify(event: dict) -> dict` as a Modal function (CONTRACT.md section 4):
- It takes the event exactly as the Mod sent it. Pick the fields you need from CONTRACT.md section 5 and ignore the rest.
- It returns `{event_id, monitor, flagged, risk, details, actions[]}`.
- **This side decides everything:** whether something is a violation, the thresholds, whether to notify the user or correct the agent, the wording, and the action order. Noah's side never applies thresholds.

---

## 2. Model: kev

**Training handoff milestone, 2026-11-08:** The shared module
`David/monitor_format/` is available at commit `f0239e5`. It exports
`build_instructions`, `render_state`, `render_screen`, `split_sections`,
`split_units`, `rf_window`, question-row fillers, finding and correction
formatting, schema validation, and the exact question and short-name tables.
Budgeted functions take the caller's loaded tokenizer as a keyword argument.
The interface is frozen after 23 tests passed on the pinned base tokenizer,
including golden event bytes and a deliberate mutation that failed before
restoration. See `David/training/notes/renderer.md` for caller field contracts.
Training checkpoints and calibration files are not available yet.

- **What it is:** kev, github.com/jaredpalmer/kev, Apache-2.0. Jared Palmer's open-source clone of TypeSafe AI's closed "Jev" System One decision model. It's a LoRA adapter plus a pointer head on a frozen Qwen3.5 base. It returns probabilities, never generated text.
- **API:** `POST /v1/systemone` with `{state, model, questions}`. Each question has a type:
  - `noul`: a yes/no question. Returns `{type: "noul", noul: p_yes}`, with no confidence field.
  - `choice`: up to 255 options, **supplied with each request**. Returns `{choice, confidence, probabilities}`.
  - `score`: ordered levels. Returns `{score, legend, probabilities, confidence}`.
- **Limits:**
  - The pointer head scores **only answer options**. It can't point into the input. To find *which* requirement was violated, use a `choice` question whose options are the requirements (plus "none").
  - Questions can't see each other, so their answers can disagree.
  - The 0.8B, 4B and 9B models are validated up to about **8K tokens of input**, so the context sent to kev has to be selected and trimmed.
  - Kev-4B uses about 14 GB of GPU memory and fits a 24 GB A10G or L4.
- **Hosting:**
  - The README has a Modal deploy guide.
  - Store the weights on a Modal **Volume**.
  - Set `min_containers=1` during the demo to avoid cold starts.
- **Fine-tuning:**
  - Data is JSONL, one request per line, plus a label per question.
  - Start from the released checkpoint (`--init_from`) at a learning rate around 2e-5.
  - The repo includes a `kev-finetune` skill that runs on Modal.
- **Fallback:** if fine-tuning doesn't work, run kev **without fine-tuning**. The architecture and contract stay the same.

---

## 3. Planned design *(to confirm)*

- **Question:** a goal-adherence noul, such as "Did the agent's action violate the user's instructions?", which gives `risk`. Possibly a `choice` over requirement IDs to say which requirement was violated.
- **History and context:**
  - A database on Modal, possibly SQLite with FTS5 full-text search, holding whatever history this side needs.
  - Possibly a recursive chain of kev calls that narrows all the context down to what's useful for the decision.
  - The internals can change freely as long as the `classify()` contract holds.
- **Concurrency:** SQLite on a Modal Volume breaks if several containers write at once. Limit `classify()` to one container, or route writes through a single function.
- **Requirement extraction (undecided):**
  - One prompt can hold several connected but distinct requirements, so treating one prompt as one requirement doesn't work.
  - Using `$.model.complete` (Haiku) to extract requirements is **disfavored**, because a model from the same family could share the agent's proxy bias.
  - A model-free option to consider: split the user's prompts by sentence or clause, verbatim, and use those as R-ids.
- **Correction text (`inject_agent`):**
  - A deterministic template: "A [monitor] monitor was asked [question], given [context evaluated] and [behavior evaluated], and output [result]."
  - Then: "Check whether [issue] occurred. If not, ignore this message. If it did, [desired behavior: stop / ask the user / etc.]."
  - It always names its source.
- **User notices (`notify_user`):**
  - `detected` or `intervened` around a correction.
  - `potential` alone, for a below-threshold detection with no intervention.

---

## 4. Open items

- The Modal app name, and confirming the `classify()` call and output shape (CONTRACT.md section 7).
- Which event fields are used, and which large items are needed. Tell Noah, so trimming doesn't drop something needed.
- Requirement extraction approach.
- Fine-tuned or not, and which kev size.

