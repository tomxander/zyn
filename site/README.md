# Zyn website

The public page for Zyn. A static React site: `npm run build` writes `dist/`, which any static host can serve.

```bash
npm --prefix site install
npm --prefix site run dev      # http://localhost:5180
npm --prefix site run build    # writes site/dist
```

## Where the design comes from

The layout follows a studied reference (restless.ai): a coloured hero field, a headline whose second line is an indented ink bar with a block after it, square corners, 6 px pixel squares on tags and buttons, a live diagram in the hero, small ink tags naming each section, coloured panels with line art holding a dark product sheet, a band dividing the hero from the page, and a large wordmark in the footer.

Everything inside that layout is Zyn's own:

| Reference pattern | Zyn version |
| --- | --- |
| Yellow, cyan, green, pink fields | Zyn's light table and zone-ramp sheets, with Zyn blue as the one colour |
| Pixel-glitch display face | Space Grotesk and IBM Plex Mono from `zyn-identity/fonts` |
| API calls flowing through lanes | Requirement, test and CAN records flowing through the code-check gate, taking Zyn's verdict marks (solid, hatch, cross-hatch) |
| Checkerboard band | The same two-row checker, growing out from the centre |
| Fisheye, arc and wave line art | Zyn's own patterns (fisheye, waves, arcs, fan, lattice, mesh, bow, tunnel) on a canvas, with ink traffic |
| Logo bars | The Zyn Z mark and wordmark, with the accent dot |

Every claim and number is in [src/content.ts](src/content.ts) and comes from the repository README and benchmark wiki. Change it there first.

## Motion: how it works

The motion follows a measured study of the reference site (its scripts and styles, read as data). The rules:

- **One runtime** ([src/components/runtime.ts](src/components/runtime.ts)): one IntersectionObserver and one frame loop. Every animation counts *visible* time only: scroll away and it freezes, come back and it resumes where it stopped. CSS loops inside a `[data-run-surface]` pause the same way.
- **No scroll effects.** No smooth-scroll library, no fade-in-on-scroll, a nav that scrolls away. Headings are static; the motion lives in the panels.
- **Three curves.** HOUSE `cubic-bezier(.6,.6,0,1)` for anything that moves or resizes, QUART `(.165,.84,.44,1)` for small fades and 8 to 12 px rises, SHARP `(.9,0,.1,1)` for 60 to 90 ms colour and state snaps.
- **Constant-speed ink traffic,** linear and pre-warmed so nothing starts empty: hero rows 92/102/112 px/s, rule blocks and slider rules 200 px/s, hub wires and packets 900 px/s, panel traffic 360 to 1100 px/s.
- **Zyn's colours only:** ink, paper and the zone-ramp greys for every field, Zyn blue for highlights (`--hi-on-ink`: #5C9DFF on ink in light, #1F5FCC on ink in dark).

| Piece | Where | What it does |
| --- | --- | --- |
| Hero flow | `sections/HeroFlow.tsx` | Records ride through the frame; ~every 11 s one goes wrong ahead of the check point (30% across), the flow slows to 0.45x, a popup steps through the real check name, the quoted source and the decision, sparks fly, the fix stays |
| Side wires | same | The rows continue to both page edges |
| Rule blocks | `sections/Hero.tsx` | Ink blocks run along the headline rules, rest 0.1 to 0.7 s, run again |
| Checker bands | `components/bands.tsx` | Grow out from the centre with jitter in 0.72 s |
| Panel line art | `components/PatternField.tsx` | Canvas line art; bold strokes and travelling gaps in the outer border band only; under 1 s morph on tab change |
| The problem | `sections/Problem.tsx` | Card scales in 0.5 s after first seen, rows stage in, counts run 1.2 s |
| How it works | `sections/How.tsx` | Layers auto-advance every 8 s (visible time); card swaps with a staged reveal and a `- \ \| /` spinner |
| The proof | `sections/Proof.tsx` | Tabs auto-advance every 5 s with a 2 px progress line; ledger slides with direction, rows stagger, bars draw |
| The tools | `sections/Tools.tsx` | Wires draw out at 900 px/s, packets shuttle, tiles invert when hit, pixel bursts at impact |
| For teams | `sections/Teams.tsx` | Desk and team modes auto-switch every 6 s until someone picks one; both values share one cell so nothing resizes; the walls diagram's packets run at constant speed and pause off screen |
| Daily work, roadmap | `sections/Why.tsx`, `sections/Roadmap.tsx` | Still: tables and lists, no motion |
| Contribute | `sections/Start.tsx` | Scripted terminal loop (an illustration, no real commands): rows decode behind a scramble front, shimmer, hard-blink cursor; beside it the invitation and the form |
| Footer | `components/Wordmark.tsx`, `bands.tsx` | Slider rules; a lens over the wordmark shows its outline alternate and, on exit, ricochets forever |

## Libraries

| Library | Used for |
| --- | --- |
| Motion | Card entrances, tab layouts, swaps, the hero popup, the footer link marker |
| Radix UI | The command picker menu |
| cmdk | Ctrl K palette: sections, docs pages, theme |
| Sonner | "Command copied" slips |
| Vaul | The phone menu drawer |
| marked | Reading the wiki into the docs pages |

Canvas work (line art, bands, bursts, ripples) is hand-written. GSAP and Lenis were tried and removed: the reference uses no scroll library, and one shared frame loop keeps every timing on visible time.

## Docs pages

Every page of the repository wiki (`docs/wiki/*.md`) is a page here, at `/<name>`, rendered at build time ([src/docs/](src/docs/)). Wiki links become site links; links to files in the private repository show as plain paths. `scripts/pages.mjs` writes a folder with an `index.html` per page so direct visits work on a static host.

## Accessibility

Light and dark themes (system by default, switch in the nav or the palette). Reduced motion stops every loop and timeline; panels show their finished state and the hero a still frame. Keyboard: every control is a real button or link with a visible focus ring; Ctrl K opens the palette.

## Coming soon, and the contribute form

Zyn is not released, so the page links to nothing outside itself: no GitHub, no downloads, no install commands, and outside addresses in the docs show as plain text. The Contribute section invites people to help; its form posts to `/api/zyn-contribute`, a function in the thomasalex.in repository that stores each note as a private JSON file in the Vercel Blob store `zyn-contributors`. Locally the form shows its error state, because that function only runs on Vercel.

## Publishing to thomasalex.in/zyn

`npm run build:thomasalex`, then copy `dist/` over `zyn/` in the thomasalex.in repository (delete its old `zyn/assets/` first: names are hashed) and push. No page links to GitHub.

The host (thomasalex.in) drops trailing slashes, so a refresh turns `/zyn/` into `/zyn`. The router treats `/zyn` as the home page and home links point there (`HOME` in `src/docs/docs.ts`); docs pages keep `/zyn/<slug>`.
