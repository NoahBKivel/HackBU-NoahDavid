# Intent-Fidelity Monitor: project brief

I'm David. We are building the classifier half of a HackBU hackathon project, and you are the agent doing the work. Start here, then read the sources listed at the end. The decision ledger, DESIGN-DECISIONS.md, outranks anything else I have written.

## What we are building

A Kev-4B System One classifier that judges, on every agent event and across the whole run, whether a Claude Code agent is doing what its user actually asked. It returns Jev-style decisions plus a correction the agent can act on. The question it answers is "is my agent doing what I wanted," so it is not a general AI-safety or content-moderation classifier. Its targets are requirement adherence, goal substitution, proxy optimization, reward hacking and metagaming (D1).

It is for anyone who gives a Claude Code agent a task. The user may authorize unconventional or risky work, and the monitor's job is to preserve that authorized purpose.

The monitor sees only what Claude Code exposes: prompts, tool calls and results, diffs, visible messages, and thinking text when Claude Code shows it. It cannot see weights, activations or hidden reasoning, so it reports observed deviation and makes no claim about hidden motive (D2).

## Deadline

The work period runs from 2026-11-07 13:00 EST to the Devpost deadline at 2026-11-08 11:00 EST, 22 hours in all. I will sleep about 4 hours and hold 2 hours for presubmission work, or 1 hour of that plus 1 hour of slack. All code is written inside the work period, and a demo video is required.

## Team split

Noah owns the Claude Code Mod (desktop app), the FastAPI backend on Modal and the Mod Pane UI. I own the classifier behind one Modal function, with my own database on Modal. Noah's team chose Claude Code desktop as the only host, so Codex is out for the hackathon (D12). The long-run aim is reuse across coding agents.

- The Mod sends every event. I choose which events are classified and which results the Mod acts on (D15).
- The boundary is the `Classifier` class in the Modal app `intent-monitor`, with `classify()` and `warmup()` (D35, D34.N).
- A result carries `event_id`, `monitor`, `flagged`, `risk`, `correction_message`, `schema_version`, an open `details{}` and an ordered `actions[]` of `notify_user` and `inject_agent`. It also carries `drift` and `drift_rate` (D10, D17).
- I set every threshold. The Mod and FastAPI apply none (D10).
- The backend waits 8 s for a result, then returns `pending`. The finished result rides on the session's next response as `late_results` (D29).
- The team repo is `https://github.com/NoahBKivel/HackBU-NoahDavid.git`, with `Noah/` and `David/` folders. I work in `David/` and run `git pull --rebase` before every commit. All docs are committed, and only transient artifacts are gitignored (D16).

Noah is doing his best to account for my side, and I want to account for his. The transcript of his session also records what I said about my side of the work.

## Goal and definition of done

Done at the deadline means a fine-tuned Kev-4B behind `classify()` catches the planted demo deviation live in Noah's Mod and sends a correction the agent acts on. It also means one held-out eval compares fine-tuned and stock Kev-4B on public intent and reward-hacking data. The pre-registered lift is that tuned beats stock on the intent probe and on TRACE, with a paired lower confidence bound above 0 (D13, D37).

If time allows, the demo adds a side-by-side run. One prompt, whose ordinary ambiguity reliably makes Claude reward-hack, goes to two Claude agents. The monitored agent is caught and the correction fixes it, and the unmonitored agent visibly fails to progress (D13).

The fallback trigger is 08:00 EST. If a trained, calibrated checkpoint with its stock-versus-tuned eval is not done by then, the live demo runs on the best model measured by then: a saved intermediate checkpoint, an interpolated checkpoint or stock Kev, chosen by D27's pick rule. The writeup reports whatever eval exists (D13).

## Hard constraints

- **Model.** Kev-4B, `jaredpalmer/kev-4b` at revision `6cfce5c`, with its native noul, choice and score outputs (D3, D4, D42). I kept it with reservations, and I reopen it only for a hard blocker in the fine-tuning or serving path (D3). Stock Kev scored near chance on 2 of 4 intent capabilities, so the recipe is built for a weak base (D3, D27).
- **Training.** No fresh pretraining. One integrated recipe, Hardened CE with intent hardening, in one run on a Modal H100, headless (D5, D27, D33). The plan is 12,200 training records (D28).
- **Data.** Public sources only, reusing existing labels, with selective teacher annotation. Commercial licensing is not a constraint, and eval-only restrictions are honored. The held-out suite is not trained on or used for selection (D6, D37). GPT 6.1 Sol and Terra on fast mode are the teachers, and Claude Haiku 5.5 and Sonnet 5.5 write the agent-side text (D30).
- **Budget.** About $30 of Modal credit for inference, with under 5 to 10 hours of active inference (D7). A training run costs about $10 to $13 beyond inference (D33). Agent runs and generations may spend up to about $200 of my Claude Code API credit, and the key comes through an environment secret that stays out of commits (D28).
- **Hardware.** Local deployment is not required, and remote inference is acceptable. The monitor must not impose unreasonable delays on the agent.
- **Monitoring.** Every captured event enters monitoring. No learned model gates which events get inspected, and checks are not made periodic to hide latency (D8).
- **Out of scope.** Codex, subagent monitoring, blocking interventions and activation probes (D12, ledger "Deliberately scoped out").

## How we work

I want to contribute to the consequential design, not approve a finished one. You gather the facts, present proposals with their trade-offs, and I decide. A recommendation does not become binding because you made it. No build begins until each load-bearing decision is partner-confirmed, partner-authored or a logged justified default. Do not reopen a settled decision without new material evidence. Do not underestimate how fast you and my other agents can work.

The training track is specced and built first, and the runtime track is designed while it runs (D36).

## Status and open items

D1 to D47 and D70 to D77 are on record. The training spec passed five review rounds and is implementation-ready; the runtime track is designed (D70 to D77).

## Sources of truth

- `DESIGN-DECISIONS.md`: the decision ledger, current state.
- `docs/TRAINING-SPEC.md`: the training-track specification, and `docs/PARETO-AXIS-MAP.md` for its axes.
- `docs/PROJECT-CONTEXT.md`: context from the old brief that no other document carries.
- `CONTRACT.md` in the team repo: the Noah and David interface.
- `docs/DATASET-DOSSIER.md` and `docs/research/`: the dataset plan's numbered sources and the research reports.
- `docs/research/2026-11-07-partner-noah-session-transcript.md` and `docs/research/2026-11-07-chatgpt-design-session-export.md`: the two design sessions. The coverage audit `docs/audits/2026-11-07-1-chatgpt-session-coverage-audit.md` lists what only the export's prompts hold.
- `docs/BRIEF.md`: the old brief. Where it differs from the ledger, the ledger wins.
