# Supplied-image style pass

This pass applies Noah's four supplied images to site typography and surrounding
UI. They are inspiration, not approved comps or instructions to add financial
data, filters, avatars, settings, reports or new navigation.

- Images 1 and 2 inform the dark workspace, warmer raised panel surfaces,
  generous rounded corners, quiet metadata and restrained violet accents.
- Image 3 informs page-title hierarchy, consistent navigation and separated
  content regions. It does not request a light theme or its product features.
- Image 4 informs simple typography and spacing inside a panel; its financial
  labels, bars and metrics are not copied.
- Existing risk/drift renderer code, line/marker designs, calculations and the
  health-pie geometry/colors remain. Their surroundings receive the new skin.

The top breadcrumb/Home/Preview bar is removed from every page on desktop and
mobile, including its route-rendering code and obsolete CSS. Sample-data truth
remains in a quiet footer. Home says Agent overview. The later refinement unboxes the upper health
summary and places the active total with its breakdown; the Agents panel follows
below and retains View agents in its heading.

Native interface fonts remain portable; the changes come from size, weight,
tracking and hierarchy rather than claiming an exact font match to the images.
Panels use 20–22px corners. Selection and focus use violet while monitoring data
keeps its semantic colors. The existing pill keeps its geometry and controls.

Current QA captures use the `review/reference-*.jpg` prefix. Mobile naturally
scrolls at narrow sizes; content must clear the floating pill. On this capture
provider, scrolling pages encode at client-width scale: 390×844 CSS detail is
375×812 raster, and 320×700 CSS Home is 305×667 raster. No image resizing was
performed. Non-scrolling captures match their CSS viewport sizes.
