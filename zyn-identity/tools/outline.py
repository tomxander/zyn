import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'python-libs'))
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
ROOT = Path(__file__).resolve().parents[1]

def load(name, weight=None):
    font = TTFont(ROOT / 'fonts' / name)
    if weight and 'fvar' in font:
        font = instantiateVariableFont(font, {'wght': weight}, inplace=False)
    return font

# Display: D-DIN Condensed Bold (SIL OFL), the open-licence match for the review screen's
# condensed DIN capitals. Labels: IBM Plex Mono. Space Grotesk stays in fonts/ but is retired.
fonts = {'display': load('D-DINCondensed-Bold.ttf'), 'mono': load('IBMPlexMono-Regular.ttf')}
DISPLAY_TRACKING = 0.06  # em, positive: condensed capitals need air
cache = {}

def outline(value, family='mono', size=12, tracking=0):
    if family == 'display':
        # the display voice is always capitals with the same open tracking
        value, tracking = value.upper(), size * DISPLAY_TRACKING
    key = (value, family, size, tracking)
    if key in cache: return cache[key]
    f = fonts[family]
    gs = f.getGlyphSet()
    cm = f.getBestCmap()
    scale = size / f['head'].unitsPerEm
    pos = 0
    paths = []
    # GPOS pair adjustment is applied for the brand words below by the caller's
    # intentionally tight tracking. No font dependence remains in the output.
    for char in value:
        glyph = cm.get(ord(char), '.notdef')
        pen = SVGPathPen(gs)
        gs[glyph].draw(pen)
        d = pen.getCommands()
        if d: paths.append(f'<path d="{d}" transform="translate({pos:.5f} 0) scale({scale:.8f} {-scale:.8f})"/>')
        pos += f['hmtx'][glyph][0] * scale + tracking
    result = (''.join(paths), pos - tracking if value else 0)
    cache[key] = result
    return result

if __name__ == '__main__':
    print(json.dumps({'font_check': list(fonts)}))
