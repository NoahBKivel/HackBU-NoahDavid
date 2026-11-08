# Intent-Fidelity Monitor Training Build: Standing Rules

Immutable once the build starts, except by owner instruction. Read in full every session (task.md Section 0 names this read). This file carries the timeless laws that bind every session in every phase. The build's machinery lives in `task.md`; the design lives in `David/docs/TRAINING-SPEC.md`. Where task.md touches a law's subject, it refers here.

## 1. The commit law

1. Conventional commits with a scope: `type(scope): title`. Types: feat, fix, docs, refactor, test, chore, perf, build. Scopes: `training`, `monitor-format`, `docs`. A reader of the title alone knows what changed.
2. A body after a blank line: a short paragraph saying what specifically changed and why, never a reworded title.
3. No internal-process language: no "step", "phase", "gate N", task-row IDs, spec-section references or "WIP". Describe the change.
4. No history language (v1/v2, "revised", "updated"). No em dashes anywhere in a message. No `Co-Authored-By`, "Generated with" or any attribution line; a commit that lands with one is amended once, immediately.
5. Two commits per slice. The code commit carries code, tests and config only, after the relevant tests ran on exactly that tree (`git status` confirms no unstaged edits in the tested paths). The doc closeout is a separate, adjacent commit (STATUS, BUILD-LOG, TASKLIST, recap, VALIDATION-LOG, CONSTRAINTS). There is no test re-run for the closeout.
6. Stage by name. Leave untracked caches and build artifacts alone.
7. `git pull --rebase` before every push. Push a code commit only once its gate or test has passed; push doc closeouts promptly. Never force-push or rewrite pushed history.
8. Run the secrets scan (TRAINING-SPEC 12.2 patterns) over staged text files before every commit.

## 2. The repo-boundary law

The repository is public. Committed: `David/monitor_format/` (code and tests), and in `David/training/` the code, tests, `task.md`, this file, STATUS, TASKLIST, SIDEQUESTS, TASK-CLAIMS, MESSAGES, BUILD-LOG, VALIDATION-LOG, CONSTRAINTS, `recaps/`, `prompts/`, `notes/`, `reports/`, `scripts/`. Never committed: `.env` or any key, `data/` (downloads, records, frozen splits), `results/`, `vendor/`, `.venv/`, model weights. Agents in this build touch only `David/`; of the shared root files, only `DAVID.md` is edited, and only for the milestones task.md names. `David/classifier/` and `David/docs/` are never edited.

## 3. The writing law

Binds everything the build writes: docs, comments, error messages, commit bodies, reports. No em dashes. Complete sentences; no terse fragment cadence. No self-narration. No stock cadences, empty intensifiers or hedging stacks. Every number is real: measured, fetched or counted, never typed from memory, and it carries the label of what it measures. Reports state results plainly with their n and interval, including results that miss their bar.

## 4. The artifact-hygiene law

No project-guidance metadata in product artifacts. Task-row IDs, spec-section references, step names, status pointers and agent guidance never appear in code identifiers, field names, file names or values. The filesystem drives the work; code, schemas, tests and records stay self-contained. A domain term that coincides with project vocabulary is fine; the test is whether the name refers to a project document.

## 5. The resource-access law

Pre-authorized, never permission-asking:
- **Keys:** `C:\Users\david\Documents\GitHub\classifier-for-metagaming\.env` (`ANTHROPIC_API_KEY`, `HF_TOKEN`, `OPENAI_API_KEY`). Load into the environment of the commands that need them; never print, log, copy or commit them; never generate or alter credentials.
- **Anthropic API and `claude -p`:** Haiku 5.5 and Sonnet 5.5, up to $200 in total for this build, every job logged in `results/spend.jsonl`.
- **OpenAI labelling API:** GPT 6.1 Sol and Terra, with a separate $200 total cap, real usage and cost logged per call, and shared ownership preventing duplicate votes. Use standard concurrent requests with cached fixed instructions. Report a roughly 50-record pilot's measured full-train cost projection before scaling.
- **Modal** (workspace `davidkny22`, CLI logged in): the app `intent-monitor-training` and the volume `intent-monitor-training`, H100 for training and scoring. The app `intent-monitor` and the volume `intent-monitor-model` belong to the runtime build and are never modified.
- **Hugging Face, Harbor (`davidkny22`), Docker Desktop, GitHub** (git credentials present).
- **Codex subagents:** up to 100 concurrent.
- **Local resources:** at most eight concurrent local Python, Docker or shell workload workers, with no new local workload until available RAM exceeds 4 GB. API-bound labelling subagents are exempt from that worker cap. Move heavy conversion to Modal. Docker remains stopped; do not restart it or manage other local processes.
- **The owner alert** (`scripts/alert.ps1`): for the cases task.md lists, never for routine progress.
Every output that matters ends up on the Modal volume or in `David/`, never only in a container.

## 6. The environment law

Dependency installation is authorized: install, record in BUILD-LOG, continue. Reuse `David/training/.venv`; a second environment needs a recorded conflict. Smoke scale first: dev and diagnostic runs use small inputs; full-scale runs happen only where a gate requires them. Diagnose stalls, never wait on them: a wedged download, build or job is time-boxed, killed and root-caused. Downloads are untrusted: each in its own folder, read with `python -I`, never executed.

## 7. The organization law

One concern per module and directory; split a file before it grows past a few hundred lines. Test code never lives in product files; unit tests sit in test modules beside their code or in `tests/`. Internals move freely behind the stable public interfaces (`monitor_format/__init__.py`, the source and construction registries). The shared module never imports from `David/training/`.

## 8. The reading law

Full-file reads only where a document mandates one (the Section-0 reads, the first-session spec read, an anchored section). Elsewhere, read the needed range. Any read of 300 lines or more goes in ordered chunks of about 200 lines. Grep locates; it is scoped (a path, a tight pattern, a bounded count) and never stands in for a mandated read. A data file or table is searched for the matching records, never read whole.

## 9. The instance law

Code and tests assert properties, never instances. Commit hashes, dates, absolute paths of one machine, library versions and measured numbers are resolved at run time from version control, the environment or an evidence record, never written into code as constants. The one legitimate pin is a contract artifact kept as data: the pinned Kev commit, the model revisions and the environment pins of TRAINING-SPEC 9.1, and the golden renderer fixtures.
