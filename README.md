# AI Agent Alignment Monitor (HackBU)

A Claude Code Mod that watches what a coding agent does and checks it against what the user actually asked for. When the agent drifts from its goals or optimizes a proxy, for example by deleting slow tests to make CI faster when the user said to keep coverage, a classifier on Modal flags it. The Mod then tells the user in chat and sends the agent a correction.

## Repository layout

| Folder | Owner | Contents |
|---|---|---|
| `Noah/` | Noah | Claude Code Mod (`mod/`), FastAPI backend on Modal (`backend/`) |
| `David/` | David | Alignment classifier (kev-based) on Modal |

Each person pushes only to their own folder.

## Docs

| Doc | Covers | Maintained by |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | Rules every agent follows: reading and updating the docs, git, commit messages, hackathon rules | Both |
| [CONTRACT.md](CONTRACT.md) | Shared context, system overview, the interface between the two halves | Both (changes need agreement) |
| [NOAH.md](NOAH.md) | Mod and backend architecture and build guide | Noah's side |
| [DAVID.md](DAVID.md) | Classifier architecture and build guide | David's side |
