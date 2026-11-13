---
version: 1
slug: "web-src-app-tsx"
primary_target: "web/src/App.tsx"
related_targets: ["web/src"]
---

# Zyn review screen

Scope: the whole React review screen (web/src), every run view (Sift, Sift Review, Anvil, Sift Delta, smoke/eval) and the app frame. Visitor mode: Operate.

Audience and task: one engineer in a bright room deciding hundreds of AI-produced items per session (approve, reject, edit) with the evidence in view. Constraints: near-monochrome (accent only for the primary action's key cell, focus and the current tab/item), daylight-first with a full dark theme, offline (no runtime font or asset fetches), not a generic SaaS dashboard, not spreadsheet-cramped.

## Direction contract

THESIS: Review as a darkroom exposure record. Each item is a ruled record sheet; what needs a person is hatched over the exact words it concerns, and where code and the AI reviewer disagree the hatches cross. It refuses the category default of floating rounded cards, coloured pills and stat tiles.

OWN-WORLD: A warm light-grey ground stepped on an eleven-zone grey ramp; ink-black rules at one and a half pixels; square corners everywhere; tall condensed DIN capitals (Bahnschrift Condensed) for titles and tracked legends; Bahnschrift for reading text; tabular mono for IDs and figures; line hatching as the only warning language (single hatch: needs a person, cross-hatch: conflict or broken, dotted outline: held back or open); one blue accent in the primary button's key cell, the focus ring and the current tab.

STORY: The reviewer sees where they are in the run (a zone wedge of decided against total), reads the current sheet top to bottom (ID, text, source on a tracing overlay, checks as a legend, AI verdict), decides with one key, and the next sheet lifts. Nothing is ever erased: undo is a new record.

FIRST VIEWPORT: Left rail: ZYN wordmark, reviewer field, runs as a ruled record table. Main: the run title in large condensed capitals with a ruled provenance row beneath (file, converter, sha256, taxonomy); a segmented ruled tab bar; a record row of counts with the eleven-step wedge; then the stack of item sheets, the current one expanded and lifted with a sheet edge behind it, the rest collapsed to their head line. Approve sits bottom-left of the current sheet as a solid ink bar with its key letter in the blue cell.

FORM: Exposure record (darkroom printer's record with tracing overlays and zone ramp), bolder re-roll round 2, dealt first and chosen by the user. Seed key e2b85cf7.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Memorable moment

Pressing a, the sheet takes a solid ink mark, the zone wedge steps one cell darker, and the next sheet lifts into place.

## Unresolved

Whether to collapse non-current sheets by default on very short runs (under ten items); currently they collapse everywhere.
