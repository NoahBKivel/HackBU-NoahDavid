# Dashboard navigation and monitoring surface

Mode: Operate. Build path: code-led. Noah's four supplied dashboard images now
guide the visual direction: dark separated panels, rounded corners, larger quiet
headings, clear text hierarchy and neutral gray navigation. Existing
Cursor/Codex-style project/session navigation stays. The images are inspiration,
not approved pixel-matching comps; their financial content and graph designs do
not become product requirements. Copies are in reference/visual-inspiration/.

## First viewport contract

Home starts with VISION above a left-aligned Agent overview title.
There is no breadcrumb/Home/Preview top bar on Home, Agents or agent details.
The upper health summary is unboxed: pie on the left and the active-session count beside its healthy/attention
breakdown. The health heading and divider between legend rows are removed. An info icon beside Needs attention reveals its description on
hover or focus and remains usable by tapping. A rounded Agents panel follows
below with the dedicated See all control. Desktop uses compact rows with
two lines: task plus right-aligned folder/project, then semantic health
icon/status plus right-aligned update age.
Home Agents has no title icon; its directory link is See all. Health retains its
pie and neutral unreported state when needed. Stop requests lead the up-to-three-session
list, followed by recency. No generic welcome copy, fake filters or new metrics.
Agents opens
a directory grouped by folder/project headings with indented stacks of agent
cards. Each card retains task, inline Risk: percentage, health icon/status and update age.
Choosing a card opens that session's existing six statistics,
two charts with preserved geometry and calculations, flagged actions and recent checks. Disclosures stay inline.

Desktop keeps a full-height project-grouped session rail with Home and Agents
navigation. Mobile uses a wide pill-shaped fixed island with Back left, Home
center and Agents right; it is inset 16px from the sides and bottom, respects the bottom safe area and retains content clearance.
Back follows app navigation history, with a parent-page fallback on direct entry.
Sample-data provenance is a quiet sidebar footer on desktop and content footer
on mobile. No notifications or remote controls are added. Graph geometry,
line/marker designs and calculations stay unchanged; only the drift color changes to muted amber; surrounding chart panels,
headings, statistics and event lists share the reference-inspired typography and
surfaces. Mobile pill geometry and behavior stay. Sidebar and directory icons/labels identify intervention
requests. Current sample data shows two healthy and one intervention-needed agent.

Intervention uses the proposed explicit boolean `requires_user_intervention`,
not a risk cutoff or ordinary flag. It persists until a genuine new user
instruction; David's implementation and shared contract agreement remain pending.
The preview consumes explicit snapshots by event sequence; missing/pending results
do not clear an existing state. See NN-003 in Noah/NOTES-FOR-DAVID-AGENT.md.

The signature is the relationship between a session-list selection and its
instrument view: familiar thread navigation paired with VISION's existing blue
risk and muted amber drift traces. No decorative metaphor, extra navigation item or
fake action is introduced.

## Review scope

Current refinement removes the visible Agent health title and legend divider,
uses IBM Plex Sans throughout interface text, reduces Home task titles to 18px
medium, replaces health pills with plain status text and square markers, and
removes purple from navigation, hover, focus, selection and the drift trace.
Drift becomes muted amber; geometry, calculations and state semantics remain.
The supplied Impeccable ZIP's bolder/polish guidance informs this bounded pass.

Desktop: 1280x720 and a short laptop viewport. Default content must fit
without vertical or horizontal page overflow. Open details and Show more may
scroll naturally. Check both preview sessions, chart windows, native disclosures,
selection/focus and console output. Mobile: 390px and 320px widths; verify Home,
Agents and detail routes, bottom-bar placement, Back/Home/Agents actions and
scroll clearance above the bar. Classifier and live-data calls remain outside scope.

## Skill use

Use Impeccable's Operate guidance for hierarchy and state, layout/distill for the
navigation and information density, then polish/audit for interaction and visual
verification. The supplied ZIP has guidance but no installed command runtime;
context was read directly from the project. No downloaded launcher is run.


Latest card refinement verified at 390px/320px mobile and 1280x600 desktop;
Home and grouped Agents fit the short desktop with no horizontal overflow.
See review/grouped-*.jpg. No new features or classifier/data behavior changes.

Agents displays overall healthy and needs-attention totals above its project list.
View problems filters to sessionHealth === attention, using the explicit
intervention snapshot rather than ordinary flags or a risk threshold. Remove
filter restores the complete directory. Counts stay fleet-wide; empty project
groups disappear and a no-match message is available. The filter remains active
when opening a card and returning, and resets on full page reload. It changes
only this viewing UI, never the agent or classifier. Focus is retained on the
toggle and result changes use a polite live region.

The Agents page total is a small N agents total line directly above the project
list, below health counts/filter controls, rather than beside the page title.
It remains the overall total when the stopped-agent filter is active.

Agents health totals are stacked vertically: healthy first, needs attention
second. View problems sits immediately to the right of the attention row;
Remove filter occupies the same position while active.

## Live data integration

Default mode now polls real saved backend events/results through the localhost
server once a second; ?preview=1 is an explicit synthetic mode only. Footer
reports Live data or a connection warning. No visual layout, graph calculations,
classifier calls or warm-pool settings change. State survives cursor reset and
backend redeployment via Modal Dict; charts, list expansions, windows and filter
state are retained during updates. Missing health signals stay Unreported.
Earlier Mod-only history and metadata cannot be inferred. The existing classifier
session KeyError event_ids is documented in Noah/NOTES-FOR-DAVID-AGENT.md NN-004.
