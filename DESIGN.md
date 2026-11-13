---
name: Zyn
description: Review screen for AI-produced engineering items, drawn as a darkroom exposure record.
colors:
  z0: "#121211"
  z1: "#222220"
  z2: "#363633"
  z3: "#4C4C48"
  z4: "#63635E"
  z5: "#7C7C76"
  z6: "#97968F"
  z7: "#B4B3AC"
  z8: "#D1D0C9"
  z9: "#E6E4DE"
  z10: "#F7F6F2"
  light-table: "#ECEAE4"
  record-sheet: "#FBFAF7"
  filtration-blue: "#1F5FCC"
  on-accent: "#FFFFFF"
  ok: "#157A4B"
  warn: "#A0520A"
  info: "#1868BA"
  bad: "#B3261E"
typography:
  display:
    fontFamily: "Zyn DIN, DIN Condensed, Arial Narrow, sans-serif"
    fontSize: "34px"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "0.01em"
    fontVariation: "\"wdth\" 75"
  headline:
    fontFamily: "Zyn DIN, DIN Condensed, Arial Narrow, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "0.02em"
    fontVariation: "\"wdth\" 75"
  title:
    fontFamily: "Bahnschrift, DIN Alternate, Segoe UI, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.5
  body:
    fontFamily: "Bahnschrift, DIN Alternate, Segoe UI, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
  body-sm:
    fontFamily: "Bahnschrift, DIN Alternate, Segoe UI, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Zyn DIN, DIN Condensed, Arial Narrow, sans-serif"
    fontSize: "11px"
    fontWeight: 500
    letterSpacing: "0.09em"
    fontVariation: "\"wdth\" 75"
  label-lg:
    fontFamily: "Zyn DIN, DIN Condensed, Arial Narrow, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    letterSpacing: "0.09em"
    fontVariation: "\"wdth\" 75"
  mono-id:
    fontFamily: "Cascadia Mono, Consolas, ui-monospace, monospace"
    fontSize: "13.5px"
    fontWeight: 700
    fontFeature: "\"tnum\""
  mono-figure:
    fontFamily: "Cascadia Mono, Consolas, ui-monospace, monospace"
    fontSize: "22px"
    fontWeight: 400
    lineHeight: 1.2
    fontFeature: "\"tnum\""
rounded:
  square: "0px"
spacing:
  s1: "2px"
  s2: "4px"
  s3: "6px"
  s4: "8px"
  s5: "12px"
  s6: "16px"
  s7: "24px"
  s8: "32px"
  s9: "48px"
components:
  button-primary:
    backgroundColor: "{colors.z0}"
    textColor: "{colors.record-sheet}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.square}"
    padding: "0 0 0 12px"
    height: "34px"
  button-primary-hover:
    backgroundColor: "{colors.z1}"
  button-primary-key-cell:
    backgroundColor: "{colors.filtration-blue}"
    textColor: "{colors.on-accent}"
    width: "30px"
  button-plain:
    backgroundColor: "{colors.record-sheet}"
    textColor: "{colors.z0}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.square}"
    padding: "0 12px"
    height: "34px"
  button-plain-hover:
    backgroundColor: "{colors.z9}"
  button-ghost:
    textColor: "{colors.z0}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.square}"
    padding: "0 12px"
    height: "34px"
  button-sm:
    typography: "{typography.label}"
    padding: "0 8px"
    height: "28px"
  input:
    backgroundColor: "{colors.record-sheet}"
    textColor: "{colors.z0}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.square}"
    padding: "6px 12px"
    height: "34px"
  tab:
    backgroundColor: "{colors.record-sheet}"
    textColor: "{colors.z3}"
    typography: "{typography.label-lg}"
    padding: "6px 16px"
    height: "34px"
  tab-active:
    backgroundColor: "{colors.z0}"
    textColor: "{colors.record-sheet}"
  card:
    backgroundColor: "{colors.record-sheet}"
    textColor: "{colors.z0}"
    rounded: "{rounded.square}"
    padding: "8px 16px"
  card-current:
    backgroundColor: "{colors.record-sheet}"
    padding: "24px 32px"
  card-under:
    backgroundColor: "{colors.z9}"
  filter-label:
    backgroundColor: "{colors.z0}"
    textColor: "{colors.record-sheet}"
    typography: "{typography.label}"
    padding: "0 8px"
  filter:
    textColor: "{colors.z0}"
    typography: "{typography.label-lg}"
    padding: "0 8px"
    height: "28px"
  table-header:
    backgroundColor: "{colors.z0}"
    textColor: "{colors.record-sheet}"
    typography: "{typography.label}"
    padding: "6px 12px"
  tooltip:
    backgroundColor: "{colors.z0}"
    textColor: "{colors.record-sheet}"
    typography: "{typography.label-lg}"
    padding: "6px 12px"
---

# Design System: Zyn

This file records the built system for agents generating new screens. The full component catalogue, hierarchy, patterns, process and the rules the test enforces are in [docs/design-system.md](docs/design-system.md); the tokens themselves live only in [web/src/styles/tokens.css](web/src/styles/tokens.css). If this file and tokens.css disagree, tokens.css wins.

## Overview

**Creative North Star: "The Exposure Record"**

Review as a darkroom printer's record. Each item is a ruled record sheet lying on a warm light table. What needs a person is hatched over the exact words it concerns; where code and the AI reviewer disagree the hatches cross. The reviewer reads the current sheet top to bottom, decides with one key, and the next sheet lifts into place. Nothing is erased: undo is a new record.

The world is near-monochrome ink and paper on an eleven-zone grey ramp, with one blue (the record's filtration colour) reserved for the primary key cell, the focus ring, the current tab and a switch that is on. Line work carries meaning that colour elsewhere would carry: rules, hatching, dotted outlines and solid ink. Density is that of a working record, not a spreadsheet: sheets collapse to their head line except the current one, which opens wide.

Light (a daylit light table) is the default for a bright room; the dark theme (the darkroom) inverts the roles on the same structure. Everything runs offline: the faces are Bahnschrift and Cascadia Mono, both installed with Windows.

**Key Characteristics:**
- Square corners everywhere; ink rules at 1.5px around boxes, 1px soft rules inside them.
- Tall condensed DIN capitals for titles and every legend; Bahnschrift for reading; tabular mono for IDs and figures.
- Hatching as the only warning language; status colour only on small square marks.
- One lifted sheet at a time, with the sheet beneath showing at its edge.
- Damped, short motion with no bounce; reduced motion respected everywhere.

## Colors

Ink and paper on a warm grey ramp, with one blue and four status hues that only ever appear as marks.

### Primary
- **Filtration Blue** (light #1F5FCC, dark #5C9DFF): the key letter cell on the primary button, the 2px focus ring, the 7px square on the current tab, the thumb of a switch that is on. Nowhere else. Text on it is white in light and near-black (#07111F) in dark.

### Neutral
- **The Zone Ramp** (z0 #121211 to z10 #F7F6F2, eleven steps): every grey in the world. z0 is ink (text, rules, solid fills, the primary button, the open run, the current tab); z1 is the primary button on hover; z3 is secondary text; z4 is legends; z5 the muted mark; z6 the scrollbar; z8 soft inner rules; z9 hover and the sheet beneath; z10 paper.
- **Light Table** (#ECEAE4): the page ground behind the sheets.
- **Record Sheet** (#FBFAF7): every sheet, the sidebar, inputs, the ruled rows, drawers, the palette.
- **Tracing Paper** (rgba(251,250,247,.78) over faint 1px z8 ruling every 1.55em): the overlay for source quotes and previews.
- **Darkroom roles** (dark theme): ground #141413, sheet #1C1C1A, sheet beneath #232321, hover #2A2A27; ink becomes z10, secondary text z8, legends z7, rules z7, soft rules z2.

### Status marks
- **Ok** (light #157A4B, dark #3DD68C), **Warn** (#A0520A / #F5A04D), **Info** (#1868BA / #5CB1FF), **Bad** (#B3261E / #FF7A70), **Muted** (z5): the border or fill of an 11px status square, the border of a check box, the icon in a message mark. Never a fill, banner or tinted block.

### Named Rules
**The One Filtration Rule.** Blue marks only the primary key cell, focus, the current tab and a switch that is on. If a second blue thing appears on a screen, it is wrong.

**The Mark Not Fill Rule.** Status colour lives on a small square mark and is always paired with a written legend. A coloured background, banner or tinted chip is not part of this world.

## Typography

**Display Font:** Zyn DIN, which is Bahnschrift declared through `@font-face { src: local("Bahnschrift") }` so its width axis works, set at `"wdth" 75` with `font-stretch: 75%` (fallbacks DIN Condensed, Arial Narrow)
**Body Font:** Bahnschrift (fallbacks DIN Alternate, Segoe UI, system-ui)
**Label/Mono Font:** Cascadia Mono (fallbacks Consolas, ui-monospace) with tabular figures

**Character:** One DIN lineage at two widths: the condensed cut speaks for the record (titles, legends, buttons, tabs), the normal width carries the reading text. Mono is reserved for what must line up or be copied exactly.

### Hierarchy
- **Display** (700, 34px, 1.05, capitals): the run title only, max 32ch. 22px at phone width.
- **Headline** (700, 22px, capitals, .02em): section titles under a heavy rule, drawer titles, empty-state titles.
- **Title** (400, 18px, 1.5): the item text on the current sheet, max 78ch. The largest text on any sheet.
- **Body** (400, 16px, 1.55): item text on other sheets and running text; collapsed sheets show it at 13.5px on one line.
- **Body small** (400, 13.5px): quotes, messages, captions, provenance values, inputs.
- **Label** (500, 11px or 12px, .09em, capitals by style): every legend, button, tab, filter, table header, tag, status and check label.
- **Mono** (700 at 13.5px for item IDs; 400 at 22px for stat figures; 11px for key letters and counts): IDs, figures, key letters, code.

### Named Rules
**The Legend Voice Rule.** Every label is the condensed display face, uppercase by style and tracked .09em. Copy is written in sentence case in the source; capitals are never typed.

**The Item Is Largest Rule.** On a sheet, the item text outranks its ID, legends and messages. Nothing on the sheet is set larger.

## Layout

Two columns: a 288px sidebar (the record's index column, sticky, full height, ruled on the right at 1.5px) and a main column padded 24px top, 32px sides, 48px bottom, holding a page at most 1080px wide. Reading text and quotes stop at 78ch (quotes on the current sheet at 1.3 times that). Drawers are 540px or the full viewport, whichever is smaller.

Spacing runs on one 4px rhythm (2, 4, 6, 8, 12, 16, 24, 32, 48). Controls are 34px tall, small controls 28px.

Top to bottom, a run view is: title, ruled provenance row, running stages, the segmented tab bar, stage actions, the counts row with the wedge, filter strips, then the sheet stack. Boxes share edges: the provenance row, counts row, tab bar and filter strips are each one ruled box divided by soft 1px rules, and sheets in a stack overlap by one rule width so their borders coincide.

At 860px and below the sidebar stacks above the record with the run list folded behind a Show button, the title drops to 22px, the current sheet loses its sheet-beneath edge and side offset, counts sit two to a row, the provenance row becomes a two-column grid, filter strips go full width, and button labels wrap instead of widening the page.

### Named Rules
**The Shared Edge Rule.** Related cells sit inside one ruled box and share their rules. Separate floating boxes with gaps between them are not used for counts, provenance or tabs.

## Elevation & Depth

The record is flat and ruled. Depth exists only where a sheet physically sits on another: the current sheet, and overlays. The current sheet lifts with a 2px rule, the lift shadow and the sheet beneath showing at its lower right edge (offset 6px in, 7px out, z9 with a 1px ink rule). Drawers, the palette, select menus and toasts float with the float shadow. Everything else has no shadow. In dark the shadows deepen to black so they still read.

### Shadow Vocabulary
- **Lift** (`box-shadow: 0 10px 28px -12px rgba(18,18,17,.30), 0 2px 4px rgba(18,18,17,.06)`): the current sheet only.
- **Float** (`box-shadow: 0 18px 48px -16px rgba(18,18,17,.38), 0 2px 6px rgba(18,18,17,.08)`): drawers, palette, menus, toasts.

### Named Rules
**The One Lift Rule.** Only one sheet is lifted at a time, and it is the one the keys act on. Hover never lifts; it steps the background one zone (z9).

## Shapes

Square corners throughout: `border-radius: 0` is set explicitly on inputs, buttons, switches, checkboxes and the third-party toasts, and there is no radius token. Form is made with rules at three weights (1px soft inner rules, 1.5px box rules, 2px for the current sheet, drawers and focus) and with four line patterns that carry meaning: single hatch (135 degrees, 1px ink every 6px; 3.5px for small marks), cross-hatch (135 and 45 degrees), dotted outline, and solid ink. Status and check marks are squares (11px and 13px), never circles or pills.

### Named Rules
**The Square Corner Rule.** No radius anywhere, including library components restyled into the world.

**The Hatch Grammar Rule.** Single hatch: needs a person. Cross-hatch: broken, or code and AI in conflict. Dotted outline: open, or advice. Solid ink: decided or passed. The meaning is always also written in words. Hatching is never decoration and never a hover state.

## Components

Ruled, square and quiet; the primary is the only solid object on a sheet. Every component and its use is listed in [docs/design-system.md](docs/design-system.md) section 7; the notes below record how the main ones are drawn.

### Buttons
- **Shape:** square (0px), 1.5px ink rule, 34px tall (28px small), label voice at 12px.
- **Primary:** a solid ink bar with sheet-coloured text and its key letter in a 30px blue cell flush at the right, mono, uppercase. One per sheet or tab; on a sheet it sits bottom left of the decision row.
- **Hover / Focus:** plain buttons step to z9; the primary steps to z1. Pressed buttons scale to 0.98. Focus is a 2px blue outline offset 2px.
- **Plain:** sheet background, ink rule; when it carries a key, the letter sits in a small soft-ruled mono box after the label.
- **Ghost:** no rule or fill; hover underlines with a 4px offset.
- **Disabled:** 0.42 opacity with a not-allowed cursor; with a reason it stays focusable (`aria-disabled`) and shows the reason as a tooltip.

### Status marks and checks
- **Status mark:** an 11px square plus a legend. Filled: approved. Dotted: open. Half filled on the diagonal: edited. Struck through: closed. Cross-hatched: broken.
- **Checks:** a legend row of 13px boxes. Passed: ink box with a tick. Needs a person: hatched box. Failed: cross-hatched. Advice: dotted.

### Cards / Containers (the sheet stack)
- **Corner Style:** square.
- **Background:** record sheet on the light table; hover on a collapsed sheet is z9.
- **Shadow Strategy:** flat, except the current sheet (see Elevation & Depth).
- **Border:** 1.5px ink, overlapping the next sheet by one rule; 2px on the current sheet.
- **Internal Padding:** collapsed 8px by 16px showing only the head line and one line of text; current 24px by 32px, offset 3px left.
- **Order inside the current sheet:** head line (mono ID, title legend, meta tags between soft rules, status mark at the right), item text, the source on the tracing overlay (a 1px z4 rule, laid 0.25 degrees askew), checks, messages, decision row under a soft rule. Content develops in with a 260ms opacity fade.

### Inputs / Fields
- **Style:** record sheet, 1.5px ink rule, square, 34px minimum, 13.5px text, label legend above at 11px in z4.
- **Focus:** a 2px blue ring drawn as a box shadow, no outline.
- **Switch and checkbox:** square. A switch is a 34 by 18px ruled box whose square thumb slides 15px and turns blue when on; a checked box fills with ink.

### Navigation
- **Sidebar:** ZYN wordmark in the display face tracked .16em with a ruled prototype tag, the reviewer field, then runs as a ruled index of rows with soft rules between; the open run is solid ink with sheet-coloured text. The foot holds the hatch legend (what each mark means), the model line and the theme switch.
- **Tabs:** one ruled bar of segments divided by soft rules. The current segment is solid ink with a 7px blue square before its label; others are z3 text and step to z9 on hover. Counts in mono.
- **Filters:** a ruled legend strip that opens with a solid ink label cell; each toggle shows a 9px square, solid when on, dotted and z4 when off.

### Counts row and the wedge
One ruled row of counts with 11px legends over 22px mono figures. When the counts are decision states, a cell holds the eleven-step wedge: undecided cells are hatched; decided cells fill light to dark from z9 to z0, each ruled in ink, so a finished run ends in full ink.

### Messages
A ruled note with an 18px square mark at the left whose pattern says the kind (cross-hatch broken, hatch needs a person, dotted advice, solid ink accepted) and a legend naming who said it. A broken message takes the 1.5px rule.

### Overlays
Drawers slide in from the right with a 2px left rule and ruled head and foot. The palette is a 2px ruled box at 14vh with ink group headings. Tooltips are ink with sheet-coloured text. Toasts are ruled slips whose action button is ink.

### Loading
A 3 by 3 grid of 6px ink squares pulsing in sequence over a 1600ms loop, a label with a slow light passing across it, elapsed time in mono, and the trace of what the stage has done as a ruled list. Skeletons are ruled boxes with a hover-tone sweep. Under reduced motion only the pixel pulse remains.

### Motion
CSS uses 120ms (colour, press), 180ms (the lift, switch thumb), 260ms (theme, wedge, developing) and 1600ms (loader cycle), all on `cubic-bezier(.2, 0, 0, 1)`. Component motion comes only from the presets in `web/src/components/motion.ts`: rise 6px on enter, opacity-only fades for tab and run switches, staggered rises for the first ten sheets of each batch, a 0.92 scale swap for the status mark, and a damped spring (no overshoot) for reflow, switched off above 60 sheets.

## Do's and Don'ts

### Do:
- **Do** take every colour, font and duration from `tokens.css` by `var(--zyn-...)`; app.css and components hold no literal colour values.
- **Do** draw status as a square mark plus words, and warnings as hatching over the exact words concerned.
- **Do** keep one primary per sheet or tab, with its key letter in the blue cell, and keep `data-card` on sheets and `data-key` on the buttons the keys press.
- **Do** set legends in the condensed display face, uppercase by style, tracked .09em, from sentence-case source text.
- **Do** put related cells in one ruled box with shared soft rules.
- **Do** use hover as one ramp step (z9 light, #2A2A27 dark) and keep a disabled control visible with its reason.
- **Do** check light and dark, desktop and phone width, with motion settled, before calling a screen done.

### Don't:
- **Don't** use rounded corners, pills, floating rounded cards or stat tiles.
- **Don't** use colour as a fill, banner or tinted block for status; status colour stays on marks.
- **Don't** use the blue for anything beyond the key cell, focus, the current tab and a switch that is on.
- **Don't** use hatching as hover or decoration; it always means a person is needed or something is broken.
- **Don't** put a label above the page title; the tool name is the first cell of the provenance row.
- **Don't** set animation timings outside `motion.ts`, use `transition: all`, or loop anything except loaders.
- **Don't** write em dashes, "please" or exclamation marks in copy.
