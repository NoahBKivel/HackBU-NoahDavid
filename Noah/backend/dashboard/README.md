# VISION live dashboard

Local, read-only live view of VISION agent monitoring. The shell uses
Cursor/Codex-inspired project groups and compact agent rows, with the latest
supplied-image styling: dark rounded panels, larger quiet headings and restrained
neutral gray selection. The agent view keeps six run statistics near the top. The existing risk/drift graph
designs, summary calculations, chart windows and event disclosures are preserved.

The default desktop view fits on one screen, including both charts and the
three recent checks. Desktop chart height adapts to the viewport; expanded
details and additional rows can still scroll. Verified at 1024x650,
1280x600, 1280x720 and 1440x900.

Home starts with VISION above a left-aligned Agent overview title. The unboxed
health donut sits beside the active total and healthy/attention counts, without a
health heading or legend divider. An info icon explains Needs attention.
The Agents panel has no heading icon; its compact See all link opens the directory.
Home rows have two lines: task plus right-aligned folder/project, then semantic
health icon/status plus right-aligned update age. Whole rows open existing stats.

Agents groups all sessions by project, with folder headings and indented stacks
of rounded cards inspired by Codex. Every card retains task, inline Risk: percentage,
health icon/status and update age. The project is named once at the group level.
Narrow card titles wrap as needed; Home project names truncate first on narrow
screens while preserving full accessible text. Interface text is locally served
IBM Plex Sans; tasks are 18px medium. Status has a green check, red rounded warning
triangle or neutral info icon, without pills. No purple accents remain; drift is
muted amber with unchanged geometry/calculations. Mobile navigation stays a pill.

IBM Plex Sans is bundled in fonts/IBMPlexSans.ttf with its SIL Open Font License in
fonts/OFL-IBMPlexSans.txt, from the [official Google Fonts repository](https://github.com/google/fonts/tree/main/ofl/ibmplexsans). It is served locally and
included in static output, with no remote font request at runtime.

The breadcrumb/Home/Preview top bar is removed from Home, Agents and agent detail
on desktop and mobile. Sample-data provenance remains in the sidebar footer on
desktop and a quiet content footer on mobile. The images guide surrounding UI,
not graph geometry, lines, markers, calculation rules or financial features.

Health follows an explicit `requires_user_intervention` boolean: true means the
classifier requested a stop for human input, false means no such request, and
missing means unreported. Ordinary flags are separate. Pending/absent results
retain the newest valid snapshot by event sequence. Unreported agents use a
neutral pie segment. Samples illustrate two healthy and one intervention-needed
session; live liveness detection and integration remain pending.

Noah approved clearing the persistent classifier state on the next genuine new
user instruction. The implementation proposal for David is NN-003 in
Noah/NOTES-FOR-DAVID-AGENT.md; the shared contract has not yet changed. FastAPI's
existing extra-field support was verified locally for normal and late results.

Run the health-state checks with:

    node --test Noah/backend/dashboard/model.test.mjs

At mobile widths, a wide pill-shaped floating island places Back on the left, Home in the center
and Agents on the right. It has 16px edge gaps, respects the bottom safe area and reserves scroll clearance.
Back follows app history; direct-entry detail pages fall back to Agents.
Desktop exposes Home and Agents in the sidebar and has no bottom bar.

The default app polls the deployed backend once a second through the local server.
It reads the same events/results delivered to the Mod; no classifier calls or
warmups are triggered by viewing. Modal Dict vision-dashboard-sessions persists
up to 2,000 display points per session across backend shutdown/redeployment.
Modal Dict entries expire after seven days without reads/writes; this is demo
persistence, not permanent archival storage. Live data is labeled in the footer.

The server reads apiUrl/apiToken from the Mod's existing Claude settings, with
VISION_API_URL/VISION_API_TOKEN environment overrides and the gitignored backend
secrets.local.json token as fallback. Tokens stay on the server and are excluded
from the static build. GET /api/dashboard/sessions proxies only the authenticated
read endpoint. No browser token entry or additional setup is required locally.

Open /?preview=1 only for the explicitly labeled synthetic design samples. Live
mode never falls back to fake data. Connection errors retain the last received
state and show a connection warning; the initial load has an honest empty state.
Cursor updates replace changed sessions, including old pending points updated by
late_results. A backend restart resets the cursor and reloads the full saved view.

Recording begins with this deployment. Earlier Mod-only history is unavailable;
already-running sessions may initially lack project/title metadata. Missing
requires_user_intervention remains Unreported until David emits the field.
Corrections are treated as delivered when requested, as agreed for the demo.
No acknowledgement or extra control protocol is added. Existing classifier errors
and its final-event late-result gap remain visible rather than being fabricated.

## Run locally

From C:\Projects\NYCAIRRtest:

    node Noah/backend/dashboard/serve.mjs

Open <http://localhost:4173>. No package installation is needed. The server
binds only to this computer. Open See all from Home, then choose a session.
Desktop also supports choosing a session directly from the sidebar.

An alternative port can be selected with --port 4174. Source changes
rebuild automatically; refresh the browser to see them.

## Static output

    node Noah/backend/dashboard/build.mjs

The output is Noah/backend/dashboard/dist/ (gitignored). Imports and asset
paths are relative. Live mode additionally needs the authenticated read proxy;
GitHub Pages hosting and its production proxy/auth configuration are not published.

## Design guidance

The supplied Impeccable skill informed hierarchy and state (Operate), sidebar
and information density (layout/distill), and final visual and interaction
checks (polish/audit). Its command runtime was unavailable; project context and
guidance were read directly. PRODUCT.md records scope; DESIGN.md and
.impeccable/design.json record the reviewed design system. The graph renderer
was left unchanged during the desktop shell redesign.

An earlier Home revision used NN/g's useful-minimalism guidance,
Linear's information hierarchy principles, and Impeccable's distill/layout
references. It replaces the oversized metric cards and generic introductory
copy with existing agent activity. Research links and rationale are recorded
in .impeccable/home-research.md. The accepted statistics page and mobile pill
were preserved. The current revision adds the user-requested health pie and
explicit intervention status while following the desktop sidebar's visual style.


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

Validation: nine backend tests (parallel sessions, persistence/restart, cursor and
late-result updates, auth, storage-failure isolation), nine Node data/health tests,
syntax/build, deployed 401/200 checks and real incoming Mod events. Viewing never
calls /health or sends an event. Run backend tests with .venv/Scripts/python -m
unittest Noah.backend.test_dashboard, Node tests with node --test
Noah/backend/dashboard/model.test.mjs Noah/backend/dashboard/live-data.test.mjs.

## GitHub Pages

See [PAGES-SETUP.md](PAGES-SETUP.md). The workflow publishes the static build from
main. Localhost keeps its server-side proxy; hosted browsers directly read Modal
with a separate read-only key entered at runtime. No key is bundled in Pages.
The read-key Secret/CORS backend deployment was explicitly approved and is live.
Pages is published at https://noahbkivel.github.io/HackBU-NoahDavid/ . Local
operation is unchanged. Open the ignored local dashboard-access.local.json file
to copy DASHBOARD_TOKEN for first use on your phone. The read key was verified
to return saved sessions and to reject event submission.
