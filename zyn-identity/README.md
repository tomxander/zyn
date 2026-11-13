# Zyn identity system

Engineering documents → checked outputs. Code checks and an independent AI reviewer evaluate; a person approves or rejects.

Open `index.html` for the local review page. No server, installation or network connection is needed.

## Files

- `sheets/`: construction, logos, all 44 labelled icons, and actual-size 16 px proofs in SVG and PNG.
- `logos/themeable/`: master mark and outlined wordmark SVGs.
- `logos/light/` and `logos/dark/`: mark and wordmark SVG + PNG at 512, 64, 32 and 16 px.
- `icons/24/` and `icons/16/`: individual SVGs. `icons/zyn-sprite.svg` is the symbol sprite.
- `raster/icons/{light,dark}/{24,16}/`: background-flattened PNGs.
- `source/geometry.json`: all paths, grid vertices, dot positions, semantic labels and rationales.
- `tools/`: reproducible vector generator, raster renderer and construction validator.

## Construction

The 24 × 24 viewBox has sixteen grid points: x,y ∈ {3,9,15,21}. Grid unit u=6; active field 18 × 18. Every route vertex is on this grid. Straight segments and true quarter arcs only. There is one path element and one initial M per glyph. Some junctions are retraced, keeping one route without pen lifts.

The six logo routes each have one visible gap, exactly 6 viewBox units measured along the route. One dash interruption cuts the ink; there is no background-coloured patch or second path. A square cap projects 0.75 px beyond a cut centre, so isolated gaps omit 7.5 px of centreline to leave exactly 6 px clear. All route vertices remain on-grid. Paint cuts may fall between points, including the diagonal cut in Z approved by the user. Anvil’s cut also covers the platen edge it arrives at. Sift places its opening on a free span, clear of crossing strands.

“One continuous stroke” means one underlying continuous route with one interruption in its ink. A literally unbroken ink stroke and a gap are incompatible.

The accent dot is a 2 × 2 px solid square, centred on a grid point. This square treatment unifies the family with Scribe’s cursor. Zyn, Anvil, Scribe and Source use a terminal or witness point; Sift retains it above its lattice; Assay holds it inside its hallmark as the measured result. There is at most one per glyph. All other mark geometry is unfilled.

Icons retain the 24 px construction and 1.5 px stroke. At 16 px they scale proportionally to 1 px. Only the five tool glyphs preserve the logo gap and accent dot; other icons use no accent. Needs review uses a question mark and a separate punctuation dot; Warning uses an exclamation built the same way, so the two read as one punctuation pair with Info. Approve/Passed and Reject/Failed intentionally share the same affirmative/negative shape.

## Theme and type

Ink #121211; paper #FBFAF7. Signal Blue #1F5FCC in light mode; #5C9DFF in dark mode, the same accent as the review screen (4.5:1 on paper). Blue appears only on the square dot. Themeable SVGs inherit currentColor and default to monochrome; set --zyn-accent to opt into the signal colour. Themed presentation exports set those defaults at the SVG root. PNGs flatten onto their respective paper/ink surfaces.

Wordmarks are D-DIN Condensed Bold capitals with 0.06em tracking, matching the review screen; the mark sits left with a 6 px gap at native 24 px. The transparent lockup height equals its mark tile height. Thus a 64 px wordmark export has a 64 px mark tile, and its width follows the word length. Labels, version tags and the exact descriptor “Zyn prototype” use IBM Plex Mono Regular.

Wordmark glyphs and sheet typography are portable vector outlines, so the SVGs do not need fonts installed. The no-fill rule applies to the symbols, not typeset letters, sheet backgrounds or construction guides. The open-source fonts and their SIL OFL licences are included under fonts/: D-DIN Condensed Bold (display) and IBM Plex Mono (labels). Space Grotesk is kept for the record but no longer used.

## Mark rationale

### zyn

A Z follows one traceable route from input to output.
The diagonal pause makes review part of the route.

### sift

An open lattice sorts the source into usable requirements.
A retained dot sits above the mesh; an opening lets material through.

### anvil

A short striker meets a broad, grounded working surface.
The pause is at impact; the single dot is the spark of a checked test.

### scribe

A written line returns, advances and keeps its place.
The square terminal is a cursor, ready for the next approved line.

### source

Supply enters from outside and winds inward to one accountable point.
The opening on the way in is where every input is checked.

### assay

A hallmark: the stamp an assay office strikes once metal is tested against its standard.
The bar inside is the standard; the dot below it is the measured result.

## Integration

Inline an SVG or use the sprite with `<svg><use href="icons/zyn-sprite.svg#zyn-sift"/></svg>`. External `<img>` elements cannot inherit host currentColor; use the themed exports in that case. Give icon-only controls a label. Show the judgement actor name beside its glyph; do not rely on the shape alone. Status labels remain visible and never rely on colour.

Run `python tools/build.py`, then `node tools/render.cjs`. FontTools is needed for the build; Sharp and Playwright are needed for rendering and browser review. The build script uses the two included fonts. Generated assets have no runtime dependencies.
