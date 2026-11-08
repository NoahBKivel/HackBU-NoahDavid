# VISION companion dashboard

VISION monitors whether Claude Code agent actions follow the user's instructions.
This companion is a read-only view of separate Mod sessions, for checking each
agent's risk, drift, flags, corrections and recent actions.

The current deliverable is a local responsive live dashboard on localhost:4173.
It polls authenticated saved backend sessions through the local server; browsing
does not invoke classification or warmup. Synthetic samples are explicit opt-in
via ?preview=1 and never substituted for a failed live connection.

## Current brief

- Retain familiar project/session navigation while using Noah's four dashboard reference images for the surrounding typography, spacing, dark panels and neutral gray navigation, hover, focus and selection states.
- Remove the breadcrumb/Home/Preview top bar from every page and viewport. Keep sample-data provenance in a quiet footer.
- List active sessions as compact task rows grouped by project, not large cards.
- Preserve the existing graph designs and calculations.
- Keep current risk and the other five run statistics near the top.
- Keep the default desktop view on one screen at normal laptop viewport sizes.
- Preserve existing selection, chart windows and event disclosures.
- Do not add product features, notifications, authentication or remote controls.
- Home is the default page, with active-agent and needs-attention counts and a dedicated See all link.
- Home starts with VISION above a left-aligned Agent overview title. Its health pie is a donut with a transparent center (inner radius 54 of outer radius 90). See all uses text-proportional height (13px type, 1.4 line height, 4px vertical padding), including mobile. Short desktop section gap is 16px to retain one-screen fit.
- Home is titled Agent overview. Its unboxed upper health summary pairs the pie with the active-agent total and the healthy/attention breakdown, without a title or divider. A hover/focus/tap info icon explains Needs attention. There is no Agent health heading. The rounded Agents panel follows below; desktop rows are compact and mobile rows use a compact two-line identity/status layout.
- Preserve graph geometry, line/marker designs, calculations and data semantics; use muted amber for drift to remove purple. Restyle their surrounding panels, headings and event lists consistently with the references. Preserve mobile pill geometry and navigation behavior.
- Agents shows overall healthy and attention counts above the list. View problems filters to explicit intervention-needed sessions only; Remove filter restores every session. Counts remain fleet totals. Empty project groups are hidden; no matches shows No agents need attention. Filter state persists while navigating within the app and resets on page reload.
- The Agents page groups every session by project. Folder/project headings sit above indented stacks of rounded agent cards. Each card retains the task, inline Risk: percentage, health icon/status and update age, and opens its existing statistics view.
- Use locally served IBM Plex Sans throughout the interface. Home agent titles are 18px medium. Health uses plain text with green check/red rounded warning/neutral info icons without pill backgrounds. No purple UI or chart accents remain.
- Home Agents has no heading icon and links to the directory through See all. Mobile Home rows use two lines: title plus dimmed project, then a green check or red rounded intervention triangle beside status text. Folder/project is right-aligned on the first line; update age is right-aligned on the second line. Whole-row navigation remains.
- Mobile has a fixed, wide pill-shaped floating island: Back on the left, Home in the center, Agents on the right.
- Desktop uses Home and Agents sidebar links alongside the compact session list, without a bottom bar.
- Needs attention now means an explicit `requires_user_intervention: true` classifier snapshot, separate from ordinary flags. Explicit false means good health; missing signals are unreported, not healthy. The latest valid non-pending snapshot by event sequence wins.
- Noah approved clearing the classifier's persistent intervention state on the next genuine new user instruction. This is a proposal for David, not implemented live. See Noah/NOTES-FOR-DAVID-AGENT.md NN-003.
- Preview data illustrates two healthy and one intervention-needed session, producing a 67%/33% pie. The shared contract and classifier source remain unchanged pending David's agreement.
- The preview treats its supplied sessions as active. Live liveness detection remains pending.

All source stays in this repository. Event/result persistence and live polling
are deployed; GitHub Pages workflow and direct read-key client are prepared; read-key creation/backend deployment and enabling Pages remain pending.

The Agents page total is a small N agents total line directly above the project
list, below health counts/filter controls, rather than beside the page title.
It remains the overall total when the stopped-agent filter is active.

Agents health totals are stacked vertically: healthy first, needs attention
second. View problems sits immediately to the right of the attention row;
Remove filter occupies the same position while active.
