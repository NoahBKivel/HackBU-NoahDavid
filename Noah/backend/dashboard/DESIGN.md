---
name: VISION companion dashboard
description: A quiet agent overview, directory and monitoring instrument.
colors:
  bg: "#101010"
  sidebar: "#151515"
  panel: "#1c1c1b"
  text: "#f0f0ed"
  muted: "#b0b0aa"
  faint: "#92928d"
  border: "#2d2d2a"
  line: "#2a2a28"
  hover: "#272725"
  selected: "#30302d"
  success: "#81bd85"
  warning: "#dcb26a"
  error: "#ed9898"
  focus: "#c5c5bd"
  accent: "#bdbdb5"
  accent-soft: "#e7e7e1"
  health-healthy: "#7eac8b"
  health-attention: "#cf8d82"
  health-unknown: "#606060"
  chart-risk: "#378ADD"
  chart-drift: "#BFA574"
  chart-flag: "#E24B4A"
  chart-warning: "#EF9F27"
  chart-correction: "#1D9E75"
  chart-pending: "#B4B2A9"
  chart-axis: "#888780"
  chart-grid: "#88878040"
typography:
  agent-task:
    fontFamily: "IBM Plex Sans, Segoe UI Variable, Segoe UI, sans-serif"
    fontSize: "18px"
    fontWeight: 500
    lineHeight: "1.3"
    letterSpacing: "-.015em"
  agents-panel-title:
    fontFamily: "IBM Plex Sans, Segoe UI Variable, Segoe UI, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: "1.5"
    letterSpacing: "-.035em"
  directory-heading:
    fontFamily: "IBM Plex Sans, Segoe UI Variable, Segoe UI, sans-serif"
    fontSize: "34px"
    fontWeight: 600
    lineHeight: "1.5"
    letterSpacing: "-.035em"
  directory-risk:
    fontFamily: "IBM Plex Sans, Segoe UI Variable, Segoe UI, sans-serif"
    fontSize: "26px"
    fontWeight: 600
    lineHeight: "1.5"
    letterSpacing: "-.035em"
  home-heading:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "28px"
    fontWeight: 500
    lineHeight: "1.25"
    letterSpacing: "-.03em"
  panel-title:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "18px"
    fontWeight: 450
    lineHeight: "1.5"
    letterSpacing: "-.02em"
  page-heading:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "28px"
    fontWeight: 500
    lineHeight: "1.5"
    letterSpacing: "-.03em"
  headline:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "26px"
    fontWeight: 500
    lineHeight: "1.35"
    letterSpacing: "-.03em"
  metric:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "25px"
    fontWeight: 550
    lineHeight: "1.25"
    letterSpacing: "-.025em"
  metric-current:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "28px"
    fontWeight: 550
    lineHeight: "1.25"
    letterSpacing: "-.025em"
  title:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "16px"
    fontWeight: 450
    lineHeight: "1.5"
    letterSpacing: "-.02em"
  body:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "1.5"
    letterSpacing: "normal"
  label:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: "1.5"
    letterSpacing: "normal"
  meta:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: "1.5"
    letterSpacing: "normal"
  control:
    fontFamily: "Segoe UI Variable, Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "10px"
    fontWeight: 400
    lineHeight: "1.5"
    letterSpacing: "normal"
rounded:
  control: "4px"
  session: "6px"
  taskbar-item: "999px"
  taskbar-island: "999px"
  popup: "8px"
  chart: "20px"
  home-panel: "22px"
  page-link: "10px"
  status-row: "12px"
spacing:
  space-1: "4px"
  space-2: "8px"
  space-3: "12px"
  space-4: "16px"
  space-5: "24px"
  space-6: "32px"
components:
  home-agents-link:
    backgroundColor: "{colors.line}"
    textColor: "#d4d4ce"
    rounded: "{rounded.taskbar-item}"
    padding: "7px 10px"
  home-agents-link-hover:
    backgroundColor: "#353531"
    textColor: "{colors.text}"
  health-pie:
    width: "180px"
  health-legend:
    textColor: "#cecec7"
  home-panel:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.home-panel}"
    padding: "20px 24px"
  event-panel:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.chart}"
    padding: "16px 20px"
  home-status-row:
    rounded: "{rounded.status-row}"
    padding: "18px 10px"
  page-link:
    textColor: "{colors.muted}"
    rounded: "{rounded.page-link}"
    padding: "9px 12px"
  page-link-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.accent-soft}"
  taskbar-item:
    textColor: "{colors.muted}"
    rounded: "{rounded.taskbar-item}"
  session-row:
    textColor: "#b5b5b5"
    rounded: "{rounded.session}"
    padding: "8px 10px"
  session-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.text}"
    rounded: "{rounded.session}"
  window-button:
    textColor: "{colors.muted}"
    rounded: "{rounded.control}"
    padding: "4px 6px"
    typography: "{typography.control}"
  chart-card:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.chart}"
    padding: "18px 20px 12px"
  event-row:
    typography: "{typography.label}"
    padding: "9px 0"
---
# Design System: VISION companion dashboard

## Overview

**Creative North Star: "The quiet desktop instrument"**

VISION pairs familiar project/session navigation with the dark separated panels, generous corners, clear text hierarchy and neutral gray accents drawn from four user-supplied dashboard images. These images inspire the surrounding UI and typography; they are not approved pixel-matching comps, and their graph details or product features are not requirements. Native interface fonts remain portable.

This code-led local synthetic preview starts with Agent overview, an open health summary and an Agents panel. Agents and agent detail share the panel vocabulary. Every page omits the top breadcrumb/Home/Preview strip. Sample-data provenance lives in a quiet footer. Graph rendering, calculations, health semantics and mobile pill geometry remain intact.

**Key Characteristics:**
- Project-grouped compact session navigation.
- Rounded dark panels and clear type hierarchy.
- Violet navigation distinct from monitoring colors.
- Existing graph semantics and progressive disclosure.

The supplied-image style pass passed a fresh manual finish review with no material fixes. Current `.impeccable/review/reference-*.jpg` evidence covers desktop Home (1280x720), desktop Agents/detail (1280x600), compact detail (1024x650), and mobile Home/Agents (390x844). Mobile detail is provider-encoded at 375x812 for CSS 390x844; narrow Home is 305x667 for CSS 320x700. No image editing or resizing was performed. This known scrolling-capture scale is an evidence limitation, not CSS geometry.

`reference-qa.json` records zero top headers across pages, no horizontal overflow, working Last 10 filtering, correction disclosure and navigation, and an empty console. Detail lists end at 550.5px within 600px and 600.5px within 650px. Mobile Home provenance ends at 747.25px before the pill at 762px; narrow detail ends at 603.8px before the pill at 618px. Syntax/build checks passed. Graph-renderer hash and model semantics are unchanged. The Impeccable CLI/detector is unavailable; no detector pass is claimed. This is synthetic local evidence with no API/GPU calls. NN-003 and live integration remain pending.

## Colors

### Primary

Risk Blue and Drift Violet retain their graph meanings; the risk area remains a translucent fill. The supplied images do not authorize graph redesign.

### Secondary

Neutral gray selection and bright selected-page text identify navigation. Focus Gray marks keyboard focus. Health Green, Health Rose and Health Unknown retain the explicit health-state meanings. Soft Green, Amber and Rose remain monitoring text states; saturated chart warning, flag and correction colors remain separate.

### Neutral

Near-black workspace, deeper navigation and warmer raised panels create depth. Bright text, muted labels and faint metadata establish reading order. Fine borders and dividers contain panels and rows; hover stays neutral.

**The Semantic Color Rule.** Use neutral gray for navigation and focus; preserve separate health, risk and drift colors for their data meanings.

## Typography

The agent-list refinement uses locally served IBM Plex Sans for task titles, its panel/directory headings and risk figures. Native interface type remains for metadata, sidebar, health summary and instruments; charts retain `Segoe UI, sans-serif`. The user explicitly requested a stronger type treatment beyond the single basic font.

- **Home Heading:** Agent overview uses 28px desktop and 25px mobile, weight 500.
- **Page Heading:** Agents uses 28px desktop and 22px mobile, weight 500.
- **Headline:** agent detail uses 26px desktop, 20px short desktop and 18px mobile.
- **Panel Title:** Home panels use 18px desktop and 17px mobile, weight 450.
- **Title:** chart headings use 16px desktop and 14px mobile, weight 450; event headings use 15px.
- **Body / Label / Meta:** general copy is 14px; compact labels and metadata remain 12px and 11px. Agent-status titles use 15px with 13px state and 12px metadata.
- **Metric / Metric Current:** existing statistic roles keep tabular values and current-risk emphasis.

Health legend labels use 13px, counts 14px and desktop percentages 11px; percentages hide on mobile. Long navigation and event summaries truncate; disclosed event text wraps within 72ch.

**The Instrument Type Rule.** Use compact interface type and tabular numerals for statistics, timestamps and ages; do not introduce a hero display hierarchy.

## Layout

The desktop shell pairs a 248px rail with a flexible workspace, centered to a 1600px maximum and padded 32px. There is no top header or breadcrumb strip. At 701-1100px the rail is 216px and horizontal workspace padding is 24px. The recurring spacing primitives are in the frontmatter.

Home is bounded to 1200px. The title precedes an unboxed health summary: a 180px pie and a flexible summary up to 440px wide with a 48px gap. There is no visible health heading or legend divider. The active-agent total sits immediately above the two breakdown rows. Mobile uses a 140px pie and 24px gap; below 360px these become 112px and 16px. The active count remains above the legend on mobile. The rounded Agents panel follows 24px below the health summary. Desktop rows become compact at widths of 1000px and above, keeping all three sample sessions visible on short desktops.

Six statistics stay above the two charts. Current risk takes 1.35 shares and the other five one share each. Charts use two equal columns and a 20px gap; event panels use two equal columns and a 28px gap. Charts/events stack below 1000px, and statistics become three columns. Default event lists show three rows; expanded content may scroll naturally.

At desktop widths of at least 1000px, plot height remains `clamp(140px, calc(100dvh - 520px), 280px)`. At heights of 700px or less it remains `clamp(170px, calc(100dvh - 430px), 230px)`, with tighter surrounding gaps. Mobile chart controls may wrap in their heading; the graph renderer is unchanged.

Mobile hides the sidebar and uses 24px 20px main padding with 96px plus bottom safe-area clearance; below 360px horizontal padding is 16px. The floating Back/Home/Agents pill retains its accepted geometry. Sample data appears 16px below content on mobile and in the sidebar footer on desktop. Three supplied sessions illustrate the two-to-one health split; do not invent content to fill it.

## Elevation & Depth

**The Flat Surface Rule.** Use tonal separation and fine borders for depth; the implemented interface has no box shadows.

The Agents panel, charts, directory and event lists share warm raised fills and fine borders. The upper health summary has no background, border or card padding. The sidebar has a right divider. Information disclosures remain bordered overlays at z-index 3 without shadows. Hover changes tone rather than position.

## Shapes

The Home Agents panel has 22px corners (20px mobile); chart, directory and event panels use 20px. Page navigation uses 10px corners, status-row hover uses 12px, and compact session rows retain six-pixel corners. See all is a small pill; mobile navigation retains fully rounded corners. Inline stroked SVG provides icons. Pie geometry and circular legend dots remain unchanged.

## Components

### Navigation and provenance

Desktop Home/Agents links use neutral gray selected fill and bright text; selected session links use the same fill with bright text. Page links are at least 40px high with 9px 12px padding. Compact project-grouped session rows retain their 36px minimum. Each row opens its existing instrument.

Mobile uses a centered fixed pill, at most 440px wide, inset 16px from the sides and above the bottom safe area, with a one-pixel border, six-pixel internal padding and 999px corners. Back, Home and Agents retain equal targets with 52px minimum height, 20px icons and 10px labels. Agents stays selected in detail. Back follows app history with direct-entry parent fallback. No top breadcrumb, Home or Preview strip is present on any page. Sample-data provenance is in the appropriate footer.

### Health and agents panels

The upper health summary is open. The Agents panel uses the shared surface with 20px 24px padding (20px mobile), and its heading is plain Agents text without an icon. The health summary has no visible heading. See all is a quiet neutral pill in the Agents heading: 36px minimum height (44px mobile), 7px 10px padding and 11px text. Hover brightens its local neutral fill.

The accessible health SVG names healthy, attention and unreported counts. The definition-list legend supplies labels and counts, plus desktop percentages. Unreported state adds a neutral wedge and legend row; an empty fleet shows a neutral circle. Current synthetic samples show two healthy and one intervention-needed session, with a 67%/33% split.

Health uses only the newest explicit boolean `requires_user_intervention` among nonpending points by event sequence: true is attention, false healthy, missing/null unreported. Ordinary flags, risk thresholds and correction text do not determine it. NN-003 proposes clearing persistent state on the next genuine new user instruction; Noah approved that lifecycle, while David's agreement and live implementation remain pending. A snapshot does not prove correction delivery or that an agent stopped.

The Agents panel lists up to three sessions, attention-first then latest activity. Whole-row links now lead with 18px/500 IBM Plex Sans task names, 13px project tags and recency, plain colored health text with square markers and an unboxed 32px arrow. Repeated leading session icons are removed from these rows. Desktop rows have a 70px minimum with 8px vertical padding; health aligns right across task/metadata rows. Mobile rows use an 80px minimum and two horizontal lines: title plus dimmed project, then status icon and label. Project text truncates before the title on narrow screens; timestamps and trailing arrows are hidden. No title is ellipsized. Existing session routing and health-state rules stay unchanged.

### Charts, events and directory

Chart panels use the chart radius and padding roles. Headings receive the new type treatment; window buttons retain neutral hover, pressed and active states with `aria-pressed`. The risk/drift graph code, lines, markers, labels and calculations remain unchanged. Window state stays per session and per chart.

Event lists are contained panels with 16px 20px padding (16px mobile). Native disclosure rows retain chevron rotation, timestamp, summary, risk and wrapping detail. Show more/less preserves open details and keyboard focus. The directory is a contained panel with eight-pixel padding; its aligned rows rearrange into labeled fields on mobile.

### Shared states

Links, buttons and summaries use a two-pixel Focus Gray outline with a three-pixel offset. Session/window transitions remain 150ms ease; reduced-motion preference disables transitions. Information disclosures retain their native behavior and bordered explanatory overlay.

## Do's and Don'ts

### Do:

- **Do** apply Operate guidance to selection, state and the task-to-instrument relationship.
- **Do** apply layout and distill guidance to clear panel hierarchy, compact session navigation and progressive disclosure.
- **Do** apply polish and audit guidance to keyboard focus, controls, disclosures, console output and content clearance above the mobile pill.
- **Do** retain visible sample-data provenance and existing chart/health semantics.

### Don't:

- **Don't** restore the top breadcrumb/Home/Preview bar on any page or viewport.
- **Don't** copy financial content, features or graph details from the inspiration images.
- **Don't** place mobile navigation on desktop or alter its accepted geometry during a skin change.
- **Don't** claim a CLI/detector pass or live classifier integration from this local preview.

The reference-inspired skin passed its recorded manual finish review. The subsequent open-health refinement was checked manually in the browser. No implementation limitation is promoted into a new visual rule.

## Open-health refinement verification

The Needs attention explanation is now a positioned tooltip attached to an authored SVG info button, visible on hover and focus (including tap). Its accessible description uses aria-describedby and role=tooltip. The summary is its positioning context, so it does not clip against the Agents panel. At 320px, the tooltip spans x=9 to x=289 within the viewport. No standalone explanation paragraph remains.

Evidence: .impeccable/review/open-health-desktop.jpg (1280x600) and open-health-mobile.jpg (390x844). Desktop content ends at 559px. Mobile footer ends at 717.75px before the island at 762px; narrow content can scroll above the island. Sample counts are three active, two healthy and one needing attention. The new docs session opens its existing instrument with eight-percent current risk, zero flags and zero corrections. No detector pass is claimed.

## Scoped agent typography amplification

Noah requested bolder inspiration from the supplied images for Home's Agents contents and the Agents page, especially type. Applied Impeccable bolder/polish guidance from the supplied ZIP. IBM Plex Sans is self-hosted in fonts/IBM Plex Sans.ttf, with fonts/OFL-IBM Plex Sans.txt from https://github.com/google/fonts/tree/main/ofl/manrope. Font loading was verified in the browser; no external font request occurs at runtime. The static build copies font/license assets and the preview serves the font as font/ttf.

Home's Agents title is 22px/600 IBM Plex Sans. Directory heading is 34px desktop and 30px mobile; task names are 20px/600, risk values 26px/600, and metadata 13px native UI type. Labels and recency are subordinate rather than making all text equally bold. Project tags use #282826 with #c4c3bd type. Healthy badges use #26362b/#acd6b7; attention uses #3b2c29/#f0b3a7; unreported uses #303033/#c0bec6. Badges are 13px/600 with 7px 10px padding and semantic dots.

Directory keeps current risk separate from its Health column, which uses the same explicit intervention-state badges as Home. At widths below 1000px, directory entries reflow into stacked rows. Mobile places Current risk above its larger figure, preventing collisions with health labels. Row arrows are round navigation cues within the existing full-row link. No extra controls or product features were added.

Manual browser QA covered Home and directory at 1280x600, 1024x650, 768x900, 390x844 and 320x700 as applicable. Home ends at 577px on 1280x600; directory ends at 518.5px on 1024x650. Narrow pages have matching client/scroll widths and their footers scroll above the island. Keyboard directory selection opens the existing six statistics and two charts, whose font remains the native stack. Console warnings/errors were empty. Evidence: .impeccable/review/type-*.jpg. This scoped pass does not claim a new detector result.

## Current neutral and type refinement

The latest user request supersedes the earlier scoped typography pass: IBM Plex
Sans is now the interface font, including metadata and navigation. Home task names
are 18px/500, with plain health text and a 5px square marker rather than colored
pills. Home row arrows are unboxed. Health title and legend divider are removed.
All purple is removed, including selection, keyboard focus, sidebar/mobile active
states and hover. The drift trace changes only in color to #BFA574; geometry,
markers, calculations and classifier state semantics remain unchanged.

Manual verification: Home fits 1280x600 without scrolling. Mobile Home/directory
and detail navigation checked at 390px and 320px without horizontal overflow.
IBM Plex Sans loaded; legend border is 0px and status backgrounds transparent.
Six model tests pass and browser warnings/errors are empty. Native evidence:
review/neutral-home-desktop.jpg and review/neutral-home-mobile.jpg. No new detector
or independent review is claimed for this bounded refinement.

## Compact mobile Home rows

Agents has no leading heading icon; See all opens the directory. Below 701px,
Home entries have two lines and an 80px minimum: 18px title with dimmed inline
project, followed by a 16px green check or red exclamation in a rounded triangle
and status label. Unknown state uses a neutral info icon. Timestamp and trailing
arrow are hidden at this breakpoint. Full-row links and accessible text remain;
project names ellipsize before sample titles on narrow screens. Desktop retains
70px rows, project/timestamp metadata and right-aligned plain statuses.

Verified at 390x844 and 320x700: two-line rows measure about 82px, sample titles
remain fully visible, no horizontal overflow, and See all opens the directory.
Desktop Home fits 1280x600; heading icon count is zero. Build/syntax checks pass;
browser console is empty. Evidence: review/two-row-home-mobile.jpg and
review/two-row-home-desktop.jpg. No model or graph behavior changed.

## Centered Home and donut refinement

Home heading is centered and the overview adds 12px top padding. The health SVG
masks a 54-unit transparent center from its 90-unit radius, retaining existing
slice proportions and semantic colors. See all has no fixed minimum height:
13px text at 1.4 line height plus 4px vertical padding produces about 26px height.
Short desktop section gap is 16px, preserving 1280x600 one-screen fit. Verified
at 390x844 and 1280x600 with no horizontal overflow; console is empty. Evidence:
review/donut-home-mobile.jpg and review/donut-home-desktop.jpg.

## Current project-grouped card layout

The latest request supersedes centered Home and hidden mobile timestamps. Home
starts with a small VISION wordmark above a left-aligned Agent overview title.
Rows use a two-by-two grid: 18px medium task at upper left, dim folder/project at
upper right, semantic status icon/text at lower left, update age at lower right.
Project text truncates before the sample task titles at narrow widths. The Home
wordmark uses the available top space rather than another global header.

Agents now groups every session by project, with a 20px folder icon beside each
16px project heading. Indented stacks (30px desktop, 18px mobile) contain separate
12px-radius neutral cards. Each retains task, current risk, health and update age.
The project heading supplies context without repeating project tags inside cards.
Task is 18px medium, status is 13px, update age is 12px, and risk uses an 18px
figure with a 12px label. Narrow titles may wrap; Risk: stays inline immediately before its percentage at all widths.
Semantic status icons are used consistently in Home and directory at all sizes.

Short desktop Home uses a 164px donut to retain 1280x600 fit after the brand line.
Manual verification covered Home and Agents at 390px/320px and 1280x600: two
project groups contain all three sample agents, all risk values remain present,
card routing opens existing stats, no horizontal overflow, and no console errors.
Evidence: review/grouped-home-mobile.jpg, review/grouped-agents-mobile.jpg,
review/grouped-home-desktop.jpg and review/grouped-agents-desktop.jpg.

Latest risk-label refinement: directory cards now use Risk: inline before the
percentage on desktop and mobile. At 390px, cards measure about 81px high;
320px also has no horizontal overflow. Build/syntax checks pass and console
is empty. Evidence: review/inline-risk-mobile.jpg.

## Agents summary and stopped filter

A compact controls row below the Agents heading shows overall healthy and
attention counts with the existing semantic check/warning icons. Unreported
count appears only when needed. A neutral outlined Show stopped agents toggle
uses 13px type, 6px 10px padding, 8px radius and aria-pressed/aria-controls.
It becomes Remove filter when active. Controls wrap naturally on mobile.

Filtering uses existing explicit attention state, preserves fleet totals, hides
projects with no matches and has a No agents need attention empty state. It
preserves directory routing and filter state across in-app navigation; full
reload restores the default all-agents view. Keyboard focus remains on the
toggle after render and result changes have a polite live region.

Verified actual toggle: three cards/two projects become one attention card/one
project; Remove filter restores all three/two. Counts remain two healthy/one
attention. Opening a filtered card and returning preserves the filter. Mobile
390px/320px have no horizontal overflow; desktop 1280x600 fits with all cards.
Build/syntax and six health-state tests pass; console warnings/errors empty.
Evidence: review/attention-counts-desktop.jpg and review/attention-filter-mobile.jpg.

## Agent total placement

The Agents h1 is plain text. A 13px muted, tabular-numeric N agents total line
sits directly above the project list with 12px bottom spacing, below summary
and filter controls. It always reflects all sessions. Verified mobile 390px,
filter preservation and 1280x600 desktop fit. Build/syntax pass; console empty.
Evidence: review/agent-total-mobile.jpg.

## Stacked Agents health controls

Healthy and needs-attention counts now occupy two vertical rows (24px/32px,
4px gap). View problems sits in column two beside the attention row with a 16px
gap; Remove filter retains that position. Filtering semantics and list total are
unchanged. Verified filter/restoration, 390px/320px layout and 1280x600 fit;
syntax/build pass and console is empty. Evidence: review/stacked-counts-mobile.jpg.

## Live data integration

Default mode now polls real saved backend events/results through the localhost
server once a second; ?preview=1 is an explicit synthetic mode only. Footer
reports Live data or a connection warning. No visual layout, graph calculations,
classifier calls or warm-pool settings change. State survives cursor reset and
backend redeployment via Modal Dict; charts, list expansions, windows and filter
state are retained during updates. Missing health signals stay Unreported.
Earlier Mod-only history and metadata cannot be inferred. The existing classifier
session KeyError event_ids is documented in Noah/NOTES-FOR-DAVID-AGENT.md NN-004.

## Analytics semantic colors

The six top statistics match Mod display bands and HEADLINE_COLORS: green
#53C556, amber #E49C06, red #F17778, scoped to .metrics. Current risk percentage
and label share a tone; drift/max/average use riskColor(value, false). Nonzero
flags are red, nonzero corrections green, zeros neutral and missing values muted.
This changes no classifier threshold, calculation or chart trace. Verified against
the same live screenshot values (44/13/68/48 percent, 4 flags, 0 corrections).
Evidence: review/metric-colors-desktop.jpg.

Mobile Home health legend now uses 4px vertical row padding (formerly 12px),
with a 90px three-state legend at 390px. Desktop retains 12px padding. Verified
no horizontal overflow. Evidence: review/compact-health-mobile.jpg.

Successful live connections now hide the entire sidebar/mobile provenance footer
instead of displaying Live data. Connecting, access/connection errors and sample
mode labels still appear. Verified hidden elements and no rendered Live data
text at 390px. Evidence: review/no-live-footer-mobile.jpg.
