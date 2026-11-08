# Earlier Home redesign rationale

This records the earlier activity-layout revision. The subsequent user-requested
health pie and explicit intervention state in PRODUCT.md and DESIGN.md supersede
its composition decisions. The research links remain useful background.

The user rejected the original Home as generic and poorly designed. This pass
changes Home only; the accepted agent-statistics page and pill navigation stay.

## Research and application

- [Nielsen Norman Group: Aesthetic and Minimalist Design](https://www.nngroup.com/articles/aesthetic-minimalist-design/)
  distinguishes useful minimalism from simply leaving a page sparse. Necessary
  information should stay discoverable, while low-value elements should recede.
  Application: replace oversized count cards and generic explanatory copy with
  compact counts and relevant activity from the existing sessions.
- [Linear: A calmer interface for a product in motion](https://linear.app/now/behind-the-latest-design-refresh)
  describes weighting interface elements by task importance, reducing unnecessary
  icon treatments, and using less prominent structural borders. Application:
  plain activity rows, restrained hierarchy, and a small View agents button.
- [GOV.UK Design System: Summary list](https://design-system.service.gov.uk/components/summary-list/)
  uses definition lists for key/value facts and distinguishes those from lists
  of items. Application: counts remain a semantic definition list; activity uses
  an unordered list of existing agent links. The visual style is not copied.

These are design principles, not a scientific test for an aesthetic label.
The chosen composition is a judgment about this monitoring task and its data.

## Impeccable guidance

Operate defines the task: orient, assess the fleet, identify an agent, open its
existing run. Distill removes redundant copy and containers. Layout uses a bounded
column, proximity and a stable reading order. Craft floor and polish govern type,
contrast, touch targets and responsive verification. The CLI/detector is not
installed; no automated detector pass is claimed.

## Spatial decisions

- Desktop: Overview and compact counts share the header; activity follows below.
  The content column has a 960px maximum width, aligned with the workspace.
- Mobile: the same DOM order becomes a stacked heading and paired counts, then
  activity rows. The View agents target is at least 44px tall.
- Show up to three sessions ordered by their latest action timestamp. Use only
  existing task, action, project, last-seen and classifier data; no new feed,
  acknowledgement, network call or persistence feature is introduced.
- Preserve explicit preview provenance and the existing latest-scored attention
  calculation. A pending action displays Checking, without inventing a new score.

## Evidence

Current screenshots: `review/home-redesign-mobile.jpg` (390×844),
`review/home-redesign-narrow.jpg` (320×700), and
`review/home-redesign-desktop.jpg` (1280×720). All default Home content fits these
viewports without page overflow. Keyboard selection from Home opens the existing
six-statistic/two-chart agent view. The fresh finish review cleared the visual composition and requested only a design-record update. The subsequent verdict verified that correction and returned ship.
