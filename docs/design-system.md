# Zyn design system

Every screen in Zyn uses this design system. A new tool (Scribe, Source, or anything else), a new tab or a new card is built from these parts and goes through the process at the end. If something does not fit, change the system first (a token, a component, this page), then use it.

The visual world is the **exposure record**: review as a darkroom printer's record. Each item is a ruled record sheet; what needs a person is hatched over the exact words it concerns; where code and the AI reviewer disagree the hatches cross. Chosen by Tom on 2026-11-13 from a bolder re-roll (the direction contract is in [.impeccable/surfaces/web-src-app-tsx.md](../.impeccable/surfaces/web-src-app-tsx.md); product truth is in [PRODUCT.md](../PRODUCT.md)).

The review screen is a React app in [web/](../web/) served by the Python API in [harness/api/](../harness/api/). Run it with `python -m harness serve` (or `.\review.ps1`).

| What | Where |
| --- | --- |
| Tokens (the only place for colours, fonts, durations) | [web/src/styles/tokens.css](../web/src/styles/tokens.css) |
| Component styles, token values only | [web/src/styles/app.css](../web/src/styles/app.css) |
| Components | [web/src/components/](../web/src/components/) (`ui.tsx`, `Decision.tsx`, `Drawer.tsx`, `Loader.tsx`) |
| Motion presets | [web/src/components/motion.ts](../web/src/components/motion.ts) |
| Keyboard review | [web/src/lib/keys.ts](../web/src/lib/keys.ts) |
| Logos and icons (source of truth) | [zyn-identity/](../zyn-identity/): edit `tools/build.py`, run it, copy `icons/zyn-sprite.svg` to `web/src/assets/` |
| Screens | [web/src/screens/](../web/src/screens/) |
| View models and rules (checks, reasons, blocks) | [harness/api/views.py](../harness/api/views.py), [server.py](../harness/api/server.py) |

[tests/test_design_system.py](../tests/test_design_system.py) checks the hard rules (section 9). If it fails, the change is not done.

---

## 1. Principles

1. **The person decides; the screen makes that easy and honest.** The item and its evidence come first. Model output is labelled as advice and never looks like a decision.
2. **Code checks are shown as checks, not as confidence.** A check passed or failed, with a legend. No scores dressed up as certainty.
3. **Near-monochrome.** Ink and paper on an eleven-step grey ramp. One accent (blue) marks the primary action's key cell, focus and the current tab. Status colour appears only as a small square mark, never as a fill, banner or tinted block.
4. **Line work carries meaning.** Single hatch: needs a person. Cross-hatch: broken or in conflict. Dotted outline: open or advice. Solid: decided or passed (status marks fill in their small status colour; check boxes fill in ink). Status is always written in words as well.
5. **The record is ruled.** Square corners, ink rules, boxes that share edges. No floating rounded cards, no pills, no stat tiles.
6. **Calm motion.** Things move to show what changed or where to look, never for show. Short, damped, no bounce. Everything respects the reduced-motion setting.
7. **Plain words.** Sentence case in copy; legends set in tracked capitals by style, not by typing. Name the action. No em dashes.

## 2. Libraries

| Library | Used for |
| --- | --- |
| React 18, Vite, TypeScript | The app |
| TanStack Query | Loading run data, optimistic decisions, polling stage progress |
| Radix UI (`radix-ui`) | Accessible tabs, select, switch, checkbox, tooltip, collapsible, dialog |
| Motion (`motion/react`) | Header and empty-state entrances, list reflow when filtering, status mark swap, tab and run highlights |
| NumberFlow (`@number-flow/react`) | Counts that roll when they change |
| Sonner | Toasts, drawn as ruled slips: decision with Undo, stage finished, errors |
| Vaul | Side drawers for edit forms and new runs |
| cmdk | Ctrl+K palette: runs, actions, theme, keyboard legend |
| Zyn identity set ([zyn-identity/](../zyn-identity/)) | Every icon and mark: 44 glyphs on a 4 by 4 grid, one route each, served from a sprite by [icons.tsx](../web/src/components/icons.tsx). No stock icon library. Kit wordmarks are D-DIN Condensed Bold capitals (open licence, the kit's stand-in for the screen's condensed DIN) and its blue is the screen's accent, #1F5FCC light and #5C9DFF dark |
| AutoAnimate | Check legends rearranging after an edit |

Left out on purpose: GSAP, anime.js, react-spring, Lenis, AOS, Barba, Lottie, three.js, Theatre.js (one animation library keeps timing consistent; scroll effects and page transitions fight a review tool).

Fonts are local: Bahnschrift (DIN lineage, the German engineering standard face) and Cascadia Mono ship with Windows, so the screen needs no network to look right. Bahnschrift is declared through `@font-face { src: local() }` in tokens.css; without that, browsers ignore its condensed width.

## 3. Hierarchy

Every run view, top to bottom:

| Level | What | Component |
| --- | --- | --- |
| 0 | Prototype slip, read-only note without a reviewer | Shell |
| 1 | Title in condensed capitals over the ruled provenance row (tool, source, converter, sha256, ...) | `PageHeader` |
| 2 | Running stages for this run | `JobsStrip` (`JobPanel`) |
| 3 | Segmented ruled tab bar; the current segment is solid ink with an accent square | `Tabs` |
| 4 | Stage actions for the tab | `Button` in a `.toolbar` |
| 5 | Counts as one ruled record row, with the eleven-step decided wedge | `Stats` |
| 6 | Filters as ruled legend strips with an ink label cell. A tool picker (`data-marks`) shows each tool's mark in place of the square, the chosen tool in solid ink | `FilterGroup`, `Switch` |
| 7 | Section heading when a tab has more than one group | `Section` |
| 8 | The sheet stack | `Cards`, `Card` (section 7) |

Inside the current sheet, top to bottom: `CardHead` (ID in mono, legends, status mark), `ItemText`, `Quote` (the tracing overlay), `Checks` (legend row), messages (`Msg`: cross-hatch before hatch before dotted), `DecisionBar`, edit at the right of the decision row.

Sidebar: the Z mark and ZYN wordmark with the prototype tag, run rows with their tool's mark (`markFor` in ui.tsx; a run with no tool of its own carries the Z mark), Reviewer, Runs as a ruled index (the open run in solid ink), Start new run, then the hatch legend (what each mark means), the model line and theme switch. On a desktop the column is pinned: only the run list scrolls, and it keeps the open run in view. On phones the run list folds behind a Show button so the record is in the first screen.

## 4. Theme

Light (a daylit light table) is the default; `[data-theme="dark"]` (the darkroom) inverts the roles on the same ramp. The reviewer picks System, Light or Dark in the sidebar; `index.html` sets the theme before first paint. Toasts follow the same choice.

## 5. Tokens

All in [tokens.css](../web/src/styles/tokens.css). Every token is used and listed; an unused or undocumented token fails the test.

### The zone ramp

Eleven greys, zone 0 (ink) to zone 10 (paper). The only greys anywhere.

| `--zyn-z0` | `--zyn-z1` | `--zyn-z2` | `--zyn-z3` | `--zyn-z4` | `--zyn-z5` | `--zyn-z6` | `--zyn-z7` | `--zyn-z8` | `--zyn-z9` | `--zyn-z10` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ink | primary hover | | secondary text | legends | muted mark | scrollbar | | soft rules | sheet beneath | paper |

### Roles

| Token | Use |
| --- | --- |
| `--zyn-bg` | the light table (page ground) |
| `--zyn-sheet` | a record sheet: cards, sidebar, inputs, drawers |
| `--zyn-sheet-under` | the sheet beneath the current one, its edge showing |
| `--zyn-tracing` / `--zyn-tracing-lines` | the tracing-paper overlay for source quotes and previews, with faint 1px ruling; line height and rule spacing are one whole-pixel step (`.quote`, `.pre` in app.css) |
| `--zyn-ink`, `--zyn-ink-2`, `--zyn-ink-3` | text, secondary text, legends |
| `--zyn-rule`, `--zyn-rule-soft` | ink rules around boxes; soft rules inside them |
| `--zyn-overlay` | dimming behind drawers and the palette |
| `--zyn-hover` | hover and highlight on rows, buttons, tabs, menu items: one ramp step, never a hatch |
| `--zyn-on-ink` | text on a solid-ink area (the open run, the Tool cell, the chosen tab or tool) |
| `--zyn-on-ink-2` | secondary text on solid ink; flips with the theme, so never a fixed ramp step |
| `--zyn-ink-hover` | a solid-ink control (the primary button) under the pointer: lighter in light mode, darker in dark |
| `--zyn-mark-tint` | the faint tint behind the exact words a finding quotes |
| `--zyn-accent`, `--zyn-on-accent`, `--zyn-ring` | the one accent: primary key cell, current tab square, switch on, focus ring |
| `--zyn-ok`, `--zyn-warn`, `--zyn-info`, `--zyn-bad`, `--zyn-muted` | status mark colours, used only on small square marks |

### Line work

| Token | Use |
| --- | --- |
| `--zyn-hatch-ink` | the ink of every hatch |
| `--zyn-hatch` | single hatch: needs a person (warning marks, undecided cells of the wedge); never a hover |
| `--zyn-hatch-dense` | a denser hatch for small marks (failed check boxes, the prototype mark, the legend) and the 3 px band under quoted words; never drawn over text |
| `--zyn-crosshatch` | two hatches at 90 degrees: broken, or code and AI in conflict |
| `--zyn-line`, `--zyn-line-strong`, `--zyn-line-heavy` | 1px inner rules, 1.5px box rules, 2px for the current sheet, drawers and focus |
| `--zyn-shadow-lift` | the current sheet lifting off the stack |
| `--zyn-shadow-float` | drawers, palette, menus, toasts |

### Type

| Token | Value | Use |
| --- | --- | --- |
| `--zyn-font-display` | "Zyn DIN": Bahnschrift declared through `local()` so its width axis works | titles and every legend (tracked capitals) |
| `--zyn-condensed` | "wdth" 75 | the condensed width of the display face, with `font-stretch: 75%` |
| `--zyn-font-body` | Bahnschrift | reading text |
| `--zyn-font-mono` | Cascadia Mono | IDs, figures, key letters, code |
| `--zyn-text-xs` | 11px | legends, counts |
| `--zyn-text-sm` | 12px | buttons, tabs, marks |
| `--zyn-text-md` | 13.5px | captions, quotes, messages |
| `--zyn-text-base` | 16px | item text (18px on the current sheet) |
| `--zyn-text-lg` | 22px | section and drawer titles, stat figures |
| `--zyn-text-xl` | 34px | the run title |
| `--zyn-weight-body`, `--zyn-weight-label`, `--zyn-weight-strong` | 400, 500, 700 | running text, legends, titles and IDs |
| `--zyn-leading`, `--zyn-leading-tight` | 1.55, 1.05 | running text, condensed titles |
| `--zyn-track` | .09em | tracking on legends |
| `--zyn-measure` | 78ch | maximum width of item text and quotes |

### Space, size, layout

A 4px rhythm: `--zyn-s1` 2, `--zyn-s2` 4, `--zyn-s3` 6, `--zyn-s4` 8, `--zyn-s5` 12, `--zyn-s6` 16, `--zyn-s7` 24, `--zyn-s8` 32, `--zyn-s9` 48 (px). Controls: `--zyn-control` 34px, `--zyn-control-sm` 28px. Layout: `--zyn-page-width` 1080px, `--zyn-sidebar-width` 288px, `--zyn-drawer-width` 540px. Stacking: `--zyn-z-sticky`, `--zyn-z-overlay`, `--zyn-z-toast`. Corners are square everywhere; there is no radius token.

### Motion and state

| Token | Value | Use |
| --- | --- | --- |
| `--zyn-fast` | 120ms | colour changes, press |
| `--zyn-base` | 180ms | the current sheet lifting, switch thumb |
| `--zyn-slow` | 260ms | theme change, the wedge filling, the sheet developing in |
| `--zyn-loop` | 1600ms | one cycle of the loader, shimmer and dots |
| `--zyn-instant` | 0.01ms | what durations become under reduced motion |
| `--zyn-ease` | cubic-bezier(.2, 0, 0, 1) | every CSS transition; no bounce |
| `--zyn-press` | 0.98 | buttons while pressed |
| `--zyn-disabled` | 0.42 opacity | disabled controls, with a not-allowed cursor |

## 6. Motion

Motion presets live in [motion.ts](../web/src/components/motion.ts); screens never set their own timings (the test checks).

| Preset | Moves | Where |
| --- | --- | --- |
| `enter` | fade and rise 6px | page header, empty states, job panels |
| `fade` | opacity only, quick, no exit wait | switching tabs, switching runs, the palette |
| `item(i)` | fade and rise 8px, staggered for the first ten of each batch of 40 | sheets entering a list |
| `swap` | fade and scale from 0.92 | the status mark when a decision lands |
| `T_LAYOUT` | soft spring, no overshoot | sheets reflowing when filters change (lists of 60 or fewer), tab and run highlights |
| `AUTO` | AutoAnimate, 180ms ease-out | check legends rearranging |

The signature moment: press a, the sheet takes a solid mark, the wedge steps one zone darker, and the next sheet lifts and develops in (a short opacity fade). Exiting sheets keep their place while they fade (their list is `position: relative`), so nothing jumps.

**Thinking and loading:** `Pixels` (a 3 by 3 grid of zone squares lighting in one of four patterns), `Shimmer` (a slow light across the label; the one place a gradient touches text, because it is the loading signal Tom asked for), `Loading`, `JobPanel` (live trace of what a stage has done, read from the audit log), `Dots` (inside a busy button), `Skeleton` (a plain hover-tone sweep across a sheet; hatch is reserved for things that need a person). Under reduced motion only the pixels keep their opacity pulse.

## 7. Components

| Component | Use for |
| --- | --- |
| `PageHeader` | Top of every run view: title, then the provenance row. The tool name is that row's first cell, never a label above the title |
| `Section` | A group inside a tab, under a heavy rule |
| `Tabs` | Run view tabs as a segmented ruled bar |
| `Stats` | The counts row; adds the decided wedge when the counts are decision states; an item marked `aside` (such as "tests with findings") is shown but left out of "decided N of M". `Num` for a single rolling number |
| `FilterGroup` | A ruled legend strip of toggles with counts and an ink label cell |
| `Switch`, `Checkbox`, `Select`, `Field` | Square form controls (Radix) |
| `Cards` | The sheet stack: sheets lie edge to edge, the current one lifts and opens, the rest collapse to their head line. Above 60 sheets layout animation is off |
| `Card`, `CardHead` | Every item sheet; `CardHead` is its first line |
| `ItemText`, `Quote` | The item, and its source on the tracing overlay |
| `Badge`, `StatusBadge` | The status mark: filled approved, dotted open, half edited, struck closed |
| `Chip`, `Checks`, `Tag` | A legend; pass/fail checks as ink or hatched boxes; a meta legend between rules |
| `Msg` | A ruled note whose mark says the kind (cross-hatch, hatch, dotted, solid) |
| `Diff`, `Highlight` | Word diff (struck out, underlined in); quoted evidence hatched in place |
| `Disclosure` | A section that opens in place |
| `Button`, `Tip` | Ruled square buttons; the primary is solid ink with its key letter in the accent cell. Tooltips |
| `DecisionBar` | The decision row: primary, opposite, reason picker when the AI objected |
| `Drawer` | Edit forms and new runs, a sheet sliding in from the right |
| `Table` | Data tables with an ink header row |
| `Empty` | Nothing to show yet, and the one next step |
| `Pixels`, `Shimmer`, `Loading`, `JobPanel`, `Dots`, `Skeleton` | Loading and thinking (section 6) |
| `useProgressive` | Long lists render 40 at a time with a "Show more" button |

## 8. Patterns

**The sheet stack.** Item lists use `Cards`. The current sheet (the first, until you move) is open, lifted, with the sheet beneath showing at its edge; others show only their head line and first line of text. Click a sheet or press j/k to make it current.

**Keyboard review.** j and k move between sheets, a approves, r rejects, e opens edit; a decision by key moves on to the next sheet unless a reason must be chosen first. Ctrl K opens the palette, Ctrl Enter saves an open drawer. Sheets carry `data-card`; the buttons the keys press carry `data-key="a"`, `"r"` or `"e"`, and the primary shows its key in the accent cell. Any new sheet must keep those attributes.

**Decisions feel instant, and can be undone.** A decision changes the mark at once and rolls back if the server refuses. A toast names what changed and offers Undo, which records a "reopened" event: the item goes back to awaiting a decision and both events stay in the audit log. A live region reads each decision out.

**Disabled, not hidden.** Without a reviewer name, decision buttons stay visible and disabled with a tooltip, and the page shows the read-only note. A disabled button with a reason uses `aria-disabled`, so it can be focused and its reason read.

**Tones.** Five, each with one meaning, drawn as a mark: `ok` (passed, approved: solid), `warn` (needs a person: dotted or hatched), `info` (edited, advice: half or dotted), `bad` (broken, conflict: cross-hatch), `muted` (closed with no action: struck).

**Messages.** `Msg` tones: bad (code check failed or unusable as is), warn (needs a person), info (advice), ok (accepted or done). Say who said it in the `who` legend: "code check", "AI reviewer (model, on v2)". An AI accept is a check legend, not a message.

**Model output.** Always attributed and always advice. Model numbers are labelled for what they are ("model self-rating 0.95").

**Bulk actions.** Only behind a stated rule, in a `Disclosure` that lists the items, with an "I have read these" checkbox.

**Long work.** Model stages run as background jobs (`useStartStage`) shown in the `JobPanel`; quick code-only actions run directly with `busy` on the button.

**Rules live in Python.** Reasons, blocks and checks are computed in `harness/api/views.py` and enforced again in `server.py`. Screens only show them.

**Person menu and project switcher.** In team mode, the sidebar shows the person menu with the signed-in person's name, email, role chip on the active project (sentence case, muted tone), the project switcher for switching active projects, access tokens, admin team settings, and sign out. Switching projects drops any open run from the previous project.

**Disabled with reason for roles and four-eyes.** When a person does not have the required role on a project or is blocked by the four-eyes rule (cannot decide on their own changes or findings on runs they started), actions and decision buttons remain visible and disabled with an explanatory tooltip (`aria-disabled="true"`). The reason is computed by the server and displayed inline as a warning note on the card.

**Access tokens and team settings.** Slide-in drawers (`Drawer`) for managing access tokens (creation with secret shown once, copy with clipboard fallback, confirmation on revoke, separate active and revoked lists) and viewing read-only team settings (masked secrets, project roles, service accounts).

**Copy.** Sentence case in the source; legends become capitals by style. Counts in labels. No em dashes, no "please", no exclamation marks.

## 9. Hard rules (enforced by the test)

1. Only `tokens.css` holds colours, font names and durations. `app.css` uses `var(--zyn-...)` only and never `transition: all`.
2. Screen and component code has no colour values, no inline font or colour styles, and no animation timings outside `motion.ts`.
3. Every token is defined, used (by a rule, a component or another token), and listed on this page. Every component is listed on this page.
4. Every tone has a CSS class; unknown tones are rejected.
5. No em dashes in the code or this page.
6. The legacy Streamlit screen (appendix) follows the same rules for its own files.

## 10. Process for any new UI

1. **Brief.** One line: who uses this screen, and what decision or output it produces. Check it against [PRODUCT.md](../PRODUCT.md).
2. **Place it.** Which tool, which tab, where in the hierarchy (section 3). A new tool gets a `WORKFLOW_NAME` entry and a view in `harness/api/views.py`, a kind in `run_view`, a form in `NewRun.tsx`, and its own screen registered in `App.tsx`.
3. **Rules first, in Python.**
4. **Reuse first.** Build from sections 7 and 8. A meaning with no icon gets a new glyph in `zyn-identity/tools/build.py` (on-grid, one route, straight lines or true quarter arcs, 1.5 px square-capped stroke, no accent dot unless it is a tool mark), checked with `tools/validate.py`, then added to `icons.tsx`; never a stock icon. A new pattern goes into the components and this page first, in the world's vocabulary: ruled, square, hatched, near-monochrome.
5. **Every state.** Empty, loading, read-only, disabled with a reason, failed, done.
6. **Motion check.** Presets only; lists in `Cards`; counts in `NumberFlow`; nothing loops except loaders.
7. **Hierarchy and copy check.** One primary per sheet or tab, one status mark per sheet, item text the largest on the sheet.
8. **Test.** API test in [tests/test_api.py](../tests/test_api.py); `pytest -q`; in `web/`, `npx tsc -b` and `npx vite build`.
9. **Look at it.** Light and dark, desktop and phone width, motion settled before judging a capture. Test decisions against a copy of the audit database.
10. **Record.** If the system changed, update this page in the same commit.

## 11. History

- 2026-11-13: first React screen (ink-and-paper, rounded cards, Space Grotesk/Inter/Plex Mono), then an audit pass against ten UI skill sources (contrast, keyboard review, undo, calmer motion).
- 2026-11-13: replaced by the exposure-record world after Tom found the first look misaligned and its accents scattered. Kept from the audit: keyboard review, optimistic decisions with Undo, contrast floors, quick tab and run switches, layout animation off on long lists. Dropped: rounded cards, tinted badges and chips, stat tiles, the label above the page title.
- 2026-11-13: identity kit brought in line with the screen: wordmarks became ZYN, SIFT, ANVIL, SCRIBE, SOURCE in D-DIN Condensed Bold capitals (Space Grotesk retired), the kit blue became the screen's accent, and 14 new glyphs replaced the last stock icons.
- 2026-11-13: tool names completed. Test Check became Anvil Review (Anvil mark); benchmark runs became Assay, with its own hallmark mark. Every place a tool is named (sidebar, page header, Start new run picker, Ctrl+K) shows its mark.

---

## Appendix: legacy Streamlit screen

The original Streamlit screen ([harness/review/app.py](../harness/review/app.py), `.\review-classic.ps1`) stays available but is not redesigned. Its helpers: `ui.badge`, `ui.status_badge`, `ui.chip`, `ui.chips`, `ui.quiet`, `ui.diff_html`, `ui.page_header`, `ui.section`, `ui.card_head`, `ui.text`, `ui.text_html`, `ui.quote`, `ui.empty`, `ui.notice`, `ui.brand`, `ui.side_label`. Its own tokens (defined again in [harness/review/ui.py](../harness/review/ui.py)) share names with the old world: `--zyn-ok-bg`, `--zyn-warn-bg`, `--zyn-info-bg`, `--zyn-bad-bg`, `--zyn-muted-bg`, `--zyn-line`, `--zyn-shadow`, `--zyn-shadow-hover`, `--zyn-quiet`, `--zyn-r-xs`, `--zyn-r-sm`, `--zyn-r-md`, `--zyn-r-lg`, `--zyn-r-xl`, `--zyn-r-pill`. Do not add features there.
