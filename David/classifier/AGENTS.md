# Intent-Fidelity Monitor Runtime Build: Standing Rules

Immutable once the build starts, except by owner instruction. Read in full every session (task.md Section 0 names this read). This file carries the timeless laws that bind every session in every phase. The build's machinery lives in `task.md`; the design lives in `David/docs/RUNTIME-SPEC.md`. Where task.md touches a law's subject, it refers here.

## 1. The commit law

1. Conventional commits with a scope: `type(scope): title`. Types: feat, fix, docs, refactor, test, chore, perf, build. Scopes: `classifier`, `docs`. A reader of the title alone knows what changed.
2. A body after a blank line: a short paragraph saying what specifically changed and why, never a reworded title.
3. No internal-process language: no "step", "phase", "gate N", task-row IDs, spec-section references or "WIP". Describe the change.
4. No history language (v1/v2, "revised", "updated"). No em dashes anywhere in a message. No `Co-Authored-By`, "Generated with" or any attribution line; a commit that lands with one is amended once, immediately.
5. Two commits per slice. The code commit carries code, tests and config only, after the relevant tests ran on exactly that tree (`git status` confirms no unstaged edits in the tested paths). The doc closeout is a separate, adjacent commit (STATUS, BUILD-LOG, TASKLIST, recap, VALIDATION-LOG, CONSTRAINTS). There is no test re-run for the closeout.
6. Stage by name. Leave untracked caches and build artifacts alone, and leave every file outside `David/classifier/` untouched by your staging (the training build commits in the same repository).
7. `git pull --rebase` before every push. Push a code commit only once its gate or test has passed; push doc closeouts promptly. Never force-push or rewrite pushed history.
8. Run the secrets scan (token-shaped patterns: `sk-ant-`, `sk-svcacct-`, `sk-proj-`, `ghp_`, `github_pat_`, `AKIA`, `hf_`, private-key blocks, `CLAUDE_CODE_OAUTH_TOKEN=` with a value) over staged text files before every commit.

## 2. The repo-boundary law

The repository is public. Committed: in `David/classifier/` the code, tests, `task.md`, this file, STATUS, TASKLIST, SIDEQUESTS, TASK-CLAIMS, MESSAGES, BUILD-LOG, VALIDATION-LOG, CONSTRAINTS, `recaps/`, `prompts/`, `notes/`, `scripts/`. Never committed: `.env` or any key, `.venv/`, `results/`, `vendor/`, model weights. Agents in this build touch only `David/classifier/`, plus two shared files: `DAVID.md`, for the milestones task.md names, and `David/NOTES-FROM-DAVID-AGENT.md`, for the notes to Noah task.md names. `David/monitor_format/`, `David/training/` and `David/docs/` are never edited; `Noah/` and the other root files are never edited.

## 3. The writing law

Binds everything the build writes: docs, comments, error messages, commit bodies, notes to Noah, notice and correction texts. No em dashes. Complete sentences; no terse fragment cadence. No self-narration. No stock cadences, empty intensifiers or hedging stacks. Every number is real: measured, fetched or counted, never typed from memory, and it carries the label of what it measures.

## 4. The artifact-hygiene law

No project-guidance metadata in product artifacts. Task-row IDs, spec-section references, step names, status pointers and agent guidance never appear in code identifiers, field names, file names or values. The filesystem drives the work; code, tests and results stay self-contained. A domain term that coincides with project vocabulary is fine; the test is whether the name refers to a project document.

## 5. The resource-access law

Pre-authorized, never permission-asking:
- **Modal** (workspace `davidkny22`, CLI logged in, auto-refill on). The dev app `intent-monitor-dev`, its session Dict `intent-monitor-dev-sessions` and its model volume `intent-monitor-model-dev` are yours to deploy, test and change freely. The live app `intent-monitor`, its Dict `intent-monitor-sessions` and its volume `intent-monitor-model` serve Noah's backend: redeploy them only when task.md says a phase passed its checks. The weights cache volume `intent-monitor-hf` is shared by both apps. The training build's app and volume `intent-monitor-training` are read-only to you: copy the handoff files out of it, never write to it.
- **GitHub** (git credentials present) for this repository.
- **The owner alert** (`scripts/alert.ps1`): for the cases task.md lists, never for routine progress.
- **Not used:** the `.env` file at `C:\Users\david\Documents\GitHub\classifier-for-metagaming\.env` and the Anthropic credit belong to the training build. This build makes no Claude or Anthropic API calls and never reads that file.
Every output that matters ends up in `David/classifier/`, on a Modal volume, or in the logs; never only in a container.

## 6. The environment law

Dependency installation is authorized: install, record in BUILD-LOG, continue. Create and reuse one environment, `David/classifier/.venv`; a second environment needs a recorded conflict. The team repo's `C:\Projects\...` path in `CLAUDE.md` is Noah's machine and does not exist here. Smoke scale first: diagnostic runs use small inputs. Diagnose stalls, never wait on them: a wedged deploy or call is time-boxed, killed and root-caused.

## 7. The organization law

One concern per module and directory; split a file before it grows past a few hundred lines. Test code never lives in product files; unit tests sit in `tests/`. Internals move freely behind the Modal class's two methods, `classify` and `warmup`, which never change shape. The runtime never formats a state, a requirement unit, a question text or a correction itself: it calls `David/monitor_format/`.

## 8. The reading law

Full-file reads only where a document mandates one (the Section-0 reads). Elsewhere, read the needed range. Any read of 300 lines or more goes in ordered chunks of about 200 lines. Grep locates; it is scoped (a path, a tight pattern, a bounded count) and never stands in for a mandated read.

## 9. The instance law

Code and tests assert properties, never instances. Commit hashes, dates, absolute paths of one machine, library versions and measured numbers are resolved at run time from version control, the environment or an evidence record, never written into code as constants. The legitimate pins are contract artifacts kept as data: the Kev commit and the model revision of spec 6.4, the app, Dict and volume names, and the test fixtures.
