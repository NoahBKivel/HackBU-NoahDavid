# Round 2 reviewer prompts, training spec (verbatim)

Copied by script from the Agent calls in session 48a356b8 at 2026-11-07 21:5x EST. Each prompt is exactly what its reviewer received.

## Round 2 spec review (Opus)

Model: `opus` · agent type: `general-purpose`

````text
You are a senior ML engineer who has fine-tuned decision/classifier models and built
labelled-data pipelines for agent monitoring. You are reviewing a training specification
an autonomous agent will execute without ever seeing any other design document. This is
review ROUND 2; round 1's findings were processed and the spec amended in place.

READ FIRST, IN FULL, IN THIS ORDER (every line, chunked to EOF; no skimming, sampling or
grepping in place of reading; keep a coverage ledger of files and line ranges read):
1. C:\Users\david\.claude\skills\reading-context\SKILL.md  (follow it for every read after)
2. C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md  (model names, papers and releases
   dated after your training cutoff are real; never flag something as hallucinated because
   you don't recognize it)
3. C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md
4. C:\Users\david\.claude\skills\design-ethos\SKILL.md and
   C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md
5. C:\Users\david\.claude\skills\initializing-projects\SKILL.md (steps 4 and 6) and
   C:\Users\david\.claude\skills\task-file-builder\SKILL.md (together: what belongs in a
   spec versus a task.md: session recovery, run order, choreography, cut-off scheduling,
   status docs and completion checklists are task.md material)
6. C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md
7. THE TARGET: C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md
8. THE DECISION LEDGER: C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md
   and the trace C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC-TRACE.md
9. THE ROUND-1 DISPOSITION REGISTER: C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-4-training-spec-round1-dispositions.md
   (the round-1 reports it refers to are in the same folder: -2- Opus review, -3- external
   claims, -5- Fable review; read a report's finding when you need its full text).

Do not invoke skills; read files directly. Do not edit any file. Run shell commands only in
the foreground, start no background processes, and make sure every process you start has
exited before the next one.

YOUR GOAL is to find real issues that are actually there, not to find issues. Zero
findings is a complete, acceptable result. Scope (what is built, how big, which sources)
was decided by the owner and is off limits; you may note a genuine infeasibility with
evidence, but never recommend cuts. Proportionality is in scope: a mechanism no reader or
builder needs is a finding, and "delete this" is a valid fix.

PART 0: DISPOSITION VERIFICATION (do this first). For every entry in the register:
- a FIX: confirm it landed in the spec text (quote the landed text with its section) and
  that the amendment created no new defect;
- a DEFENSE: confirm the defense still holds (do not flag the absence of a fix it defended);
- a decision David made: confirm the spec carries it as decided.
Report each register entry as LANDED / NOT LANDED / LANDED WITH NEW DEFECT / DEFENSE HOLDS /
DEFENSE FAILS, with the receipt. Report amendment-created defects as their own count.

Then review in four parts:
1. LOGIC AND CONTRACT AUDIT: every guarantee, formula, label rule, renderer rule and gate
   (sections 1, 6, 7, 8, 9, 12), re-derived; flag overreach, irreproducible formulas,
   unsupported claims, gates that cannot fail or fail through noise.
2. COST AUDIT: section 11 and the run-time claims in 9.1.
3. COMPLETENESS AGAINST THE LEDGER: for every ledger decision bearing on training data,
   labels, the run, selection, calibration or evaluation, check the spec carries it fully
   enough for an agent who never reads the ledger. An omission quotes the ledger entry
   verbatim and names the spec section where it belongs.
4. SPEC/TASK BOUNDARY: flag task.md material left in the spec; never report something
   missing that belongs in the task file.

EVERY FINDING CARRIES A RECEIPT or is dropped: id; part; kind (error / omission /
unsupported claim / overreach / task material / unneeded mechanism / amendment-created);
the exact spec text quoted with its section (for an omission: the ledger text quoted with
its entry id, plus where it belongs); the evidence; the consequence; whether it needs a
design choice or has one correct answer. No style findings.

Close with: counts (register entries verified, findings by kind, amendment-created
defects, blocking findings); the three most likely failure points; and a verdict on
implementation-readiness naming every blocking question individually.
Return the full report as your final message, including your coverage ledger.
````

## Round 2 spec review (Fable)

Model: `fable` · agent type: `general-purpose`

````text
You are a senior ML engineer who has fine-tuned decision/classifier models and built
labelled-data pipelines for agent monitoring. You are reviewing a training specification
an autonomous agent will execute without ever seeing any other design document. This is
review ROUND 2; round 1's findings were processed and the spec amended in place.

READ FIRST, IN FULL, IN THIS ORDER (every line, chunked to EOF; no skimming, sampling or
grepping in place of reading; keep a coverage ledger of files and line ranges read):
1. C:\Users\david\.claude\skills\reading-context\SKILL.md  (follow it for every read after)
2. C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md  (model names, papers and releases
   dated after your training cutoff are real; never flag something as hallucinated because
   you don't recognize it)
3. C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md
4. C:\Users\david\.claude\skills\design-ethos\SKILL.md and
   C:\Users\david\.claude\skills\design-ethos\references\gold-standard-spec-template.md
5. C:\Users\david\.claude\skills\initializing-projects\SKILL.md (steps 4 and 6) and
   C:\Users\david\.claude\skills\task-file-builder\SKILL.md (together: what belongs in a
   spec versus a task.md: session recovery, run order, choreography, cut-off scheduling,
   status docs and completion checklists are task.md material)
6. C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md
7. THE TARGET: C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md
8. THE DECISION LEDGER: C:\Users\david\Documents\GitHub\classifier-for-metagaming\DESIGN-DECISIONS.md
   and the trace C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC-TRACE.md
9. THE ROUND-1 DISPOSITION REGISTER: C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-4-training-spec-round1-dispositions.md
   (the round-1 reports it refers to are in the same folder: -2- Opus review, -3- external
   claims, -5- Fable review; read a report's finding when you need its full text).

Do not invoke skills; read files directly. Do not edit any file. Run shell commands only in
the foreground, start no background processes, and make sure every process you start has
exited before the next one.

YOUR GOAL is to find real issues that are actually there, not to find issues. Zero
findings is a complete, acceptable result. Scope (what is built, how big, which sources)
was decided by the owner and is off limits; you may note a genuine infeasibility with
evidence, but never recommend cuts. Proportionality is in scope: a mechanism no reader or
builder needs is a finding, and "delete this" is a valid fix.

PART 0: DISPOSITION VERIFICATION (do this first). For every entry in the register:
- a FIX: confirm it landed in the spec text (quote the landed text with its section) and
  that the amendment created no new defect;
- a DEFENSE: confirm the defense still holds (do not flag the absence of a fix it defended);
- a decision David made: confirm the spec carries it as decided.
Report each register entry as LANDED / NOT LANDED / LANDED WITH NEW DEFECT / DEFENSE HOLDS /
DEFENSE FAILS, with the receipt. Report amendment-created defects as their own count.

Then review in four parts:
1. LOGIC AND CONTRACT AUDIT: every guarantee, formula, label rule, renderer rule and gate
   (sections 1, 6, 7, 8, 9, 12), re-derived; flag overreach, irreproducible formulas,
   unsupported claims, gates that cannot fail or fail through noise.
2. COST AUDIT: section 11 and the run-time claims in 9.1.
3. COMPLETENESS AGAINST THE LEDGER: for every ledger decision bearing on training data,
   labels, the run, selection, calibration or evaluation, check the spec carries it fully
   enough for an agent who never reads the ledger. An omission quotes the ledger entry
   verbatim and names the spec section where it belongs.
4. SPEC/TASK BOUNDARY: flag task.md material left in the spec; never report something
   missing that belongs in the task file.

EVERY FINDING CARRIES A RECEIPT or is dropped: id; part; kind (error / omission /
unsupported claim / overreach / task material / unneeded mechanism / amendment-created);
the exact spec text quoted with its section (for an omission: the ledger text quoted with
its entry id, plus where it belongs); the evidence; the consequence; whether it needs a
design choice or has one correct answer. No style findings.

Close with: counts (register entries verified, findings by kind, amendment-created
defects, blocking findings); the three most likely failure points; and a verdict on
implementation-readiness naming every blocking question individually.
Return the full report as your final message, including your coverage ledger.
````

## Round 2 external claims (Opus)

Model: `opus` · agent type: `general-purpose`

````text
You are verifying factual claims in a training specification against their primary
sources. You are not reviewing the design. This is ROUND 2: the spec was amended after
round 1. Your goal is to find claims that are actually wrong, not to find issues; zero
findings is acceptable. Do not invoke skills; read files directly. Do not edit any project
file. Run shell commands only in the foreground, start no background processes, and make
sure every process you start has exited before the next one.

READ FIRST, IN FULL: C:\Users\david\.claude\skills\reading-context\SKILL.md (follow it),
C:\Users\david\.claude\skills\out-of-cutoff\SKILL.md,
C:\Users\david\.claude\skills\receipts-before-claims\SKILL.md, then the target
C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\TRAINING-SPEC.md, then
the round-1 external-claims report
C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-3-training-spec-external-claims-audit.md
and the disposition register
C:\Users\david\Documents\GitHub\classifier-for-metagaming\docs\audits\2026-11-07-4-training-spec-round1-dispositions.md.

SOURCES:
- Kev source at commit fc4a17e194bca35a48c57211392ec49ea54a94ac, already cloned at
  C:\Users\david\AppData\Local\Temp\claude\e4a7ca8b20dbf3e0\48a356b8-0453-4fa7-b972-ac20964e049d\scratchpad\kev-verify\kev
  (verify the checkout is that commit). Read code; never run anything from it.
- Reports: docs/research/2026-11-07-1-kev-repo-pipeline-research.md,
  -9-kev-replay-and-data-tooling-research.md, -31-stock-kev-modal-measurements-and-intent-probe-research.md,
  -33-claude-code-thinking-summaries-research.md (under C:\Users\david\Documents\GitHub\classifier-for-metagaming\).
- Dataset facts: docs/DATASET-DOSSIER.md (read the entries you need in full).
- C:\Users\david\Documents\GitHub\HackBU-NoahDavid\CONTRACT.md (Mod event fields).

PART 0: for each round-1 external-claims finding (C-F1 to C-F13) and each register fix that
touched a code or dataset claim, confirm the amended spec text is now correct against the
source (LANDED / NOT LANDED / LANDED WITH NEW ERROR, with the receipt).

THEN CHECK every claim the amendments added or changed about: the kev.train command and
flags (including --p_none, --p_none_distract, --p_distract, --head_lr, --anchor_w defaults,
dropping --suite/--replay, passing replay records through --data with their original source
names and whether the trainer's source validation accepts them), Kev's admission limits
(max_state, max_packed) and the state-budget formula, LoadOptions(temperature=...), the
weight-interpolation claims (lora_scale behaviour, merged LoRA product, head), SDPA as the
trainer's attention path, the build_long_states.py limits, TodoWrite's fields, the Mod's
result_text and correction attachment (CONTRACT.md), and the per-source label-basis
changes (Terminal Wrench, Goodfire, eungyeuk) against the dossier.

EVERY FINDING: the exact spec text quoted with its section; the primary source quoted
(file path and line numbers for code; section for the dossier, report or contract);
wrong / unsupported / right but imprecise; the consequence for a builder. List verified
claims one line each at the end. Return the full report as your final message, including
a coverage ledger.
````
