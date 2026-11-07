# Rules for every agent in this repo

HackBU project: a Claude Code Mod that monitors a coding agent for misalignment with the user's instructions, backed by a classifier on Modal. Two people work on it: **Noah** (the Mod and backend, in `Noah/`) and **David** (the classifier, in `David/`).

## 1. Read before you work

1. [CONTRACT.md](CONTRACT.md): shared context, the system overview, and the interface between Noah's and David's halves.
2. Your side's doc: [NOAH.md](NOAH.md) for the Mod and backend, or [DAVID.md](DAVID.md) for the classifier. You may read the other side's doc whenever you need to.

These docs are the source of truth. If something you're told conflicts with them, ask before acting.

## 2. Keep the docs current

The docs are the only memory shared across chats, agents and both teammates. Treat updating them as part of the work, not a follow-up.

- **Record every decision**, including ones made only in conversation, and every new finding another agent would need (a verified API detail, a gotcha, progress, an open question resolved or raised). Update the right doc **before ending the turn**.
- **Where things go:**
  - Interface or shared rules: CONTRACT.md. Change these only once **both Noah and David agree**, and log the change in its section 7.
  - Noah's side: NOAH.md, maintained by Noah's agents.
  - David's side: DAVID.md, maintained by David's agents.
- **Edit sections in place**, so each doc stays a current picture, not a history log. Decisions and their reasons go in the decisions log.
- **If a doc is wrong, fix it.** Don't work around it.
- **Commit and push doc updates promptly.** Other agents and the other teammate can't see uncommitted changes.

## 2a. When to push code

**Push only once the change is verified**: it actually works when run, or it has at least been confirmed as the intended behavior. Commit locally as you go if useful, but don't push untested or unconfirmed work. Say what was verified, and how, when you push.

## 3. Repo and git

- **Stay in your own folder:** Noah's agents touch only `Noah/`, and David's agents touch only `David/`. The root files are shared: README.md, CLAUDE.md, CONTRACT.md, NOAH.md and DAVID.md.
- Run `git pull --rebase` before every push.
- **The repo is public. Never commit secrets:** tokens, keys or `.env` files. The API token lives only in the Modal Secret `monitor-token` and the Mod's `userConfig`.
- Don't rewrite pushed history or force-push unless Noah or David explicitly asks.

## 4. Commit messages

- **Title:** Conventional Commits with a scope, `type(scope): title`.
  - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`, `build`, `ci`.
  - Scopes: e.g. `mod`, `backend`, `classifier`, `contract`, `docs`, `repo`.
  - Someone reading only the title should immediately know what changed or was added.
  - Use plain, descriptive words. No jargon, internal names, or phase and step language ("step 2", "phase 1", "WIP", "first pass").
- **Body:** after a blank line, a short paragraph with more detail: what specifically changed, and why if it isn't obvious. Never just reword the title. Descriptive, but not long.
- **Never:** em dashes anywhere in the message, or `Co-Authored-By`, "Generated with" or any other attribution line.

Example:
```
feat(backend): add event endpoint that forwards agent actions to the classifier

Accepts the Mod's event payload with a bearer token, passes unknown fields
through untouched, and returns the classifier's result and actions as JSON.
```

## 5. Hackathon rules

- Building runs from 1pm on 2026-11-07 to the **Devpost deadline at 11am on 2026-11-08**.
- All code must be written during that period. Don't reuse earlier code, including Noah's old `tool-pulse` test mod.
- **Demo-grade only:** build what the demo needs, skip robustness work, and mark extras as "later". Ask before adding anything the demo doesn't visibly need.
- A demo video is required, and the project is also **demoed live**. Keep the system demoable after every change.

## 6. Working with Noah

- Claude writes the code, and Noah reviews and runs it. Give him exact commands.
- Keep explanations brief but complete, and go deeper only when asked.
- **Before using any Claude Code Mod API, check it in the type definitions.** Don't guess. Load the `plugin-authoring` skill first for Mod work (NOAH.md section 2).
- Use the project's Python 3.12 virtual environment, not the system Python 3.14. The environment is gitignored, so a session working in a git worktree won't have its own copy. Call it by its absolute path: `C:\Projects\NYCAIRRtest\.venv\Scripts\python` or `...\modal`.
