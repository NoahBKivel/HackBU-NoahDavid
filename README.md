# AI Agent Alignment Monitor (HackBU)

A Claude Code Mod that watches what a coding agent does and checks it against what the user actually asked for. When the agent drifts from its goals or optimizes a proxy, for example by deleting slow tests to make CI faster when the user said to keep coverage, a classifier on Modal flags it. The Mod then tells the user in chat and sends the agent a correction.

## Repository layout

| Folder | Owner | Contents |
|---|---|---|
| `Noah/` | Noah | Claude Code Mod (`mod/`), FastAPI backend on Modal (`backend/`), [architecture and contract](Noah/ARCHITECTURE.md) |
| `David/` | David | Alignment classifier (kev-based) on Modal |

Each person pushes only to their own folder.
