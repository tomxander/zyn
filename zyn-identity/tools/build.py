"""Rebuild Zyn's vector identity. All mark coordinates are in grid units."""
import json, math, html, zipfile
from pathlib import Path
from outline import outline

ROOT = Path(__file__).resolve().parents[1]
INK, PAPER = '#121211', '#FBFAF7'  # the review screen's zone 0 ink and record sheet
BLUE = {'light':'#1F5FCC','dark':'#5C9DFF'}  # the review screen's accent (AA on paper)

def route(points):
    return [['M' if i == 0 else 'L', *p] for i,p in enumerate(points)]

LOGOS = {
 'zyn': dict(commands=route([(0,0),(3,0),(0,3),(3,3)]), gap=3+(math.sqrt(18)-1)/2, dot=(3,3),
  rationale=['A Z follows one traceable route from input to output.', 'The diagonal pause makes review part of the route.']),
 'sift': dict(commands=route([(0,1),(3,1),(1,3),(0,3),(0,2),(3,2),(2,3),(2,1)]), gap=5.5+math.sqrt(8), dot=(1,0),
  rationale=['An open lattice sorts the source into usable requirements.', 'A retained dot sits above the mesh; an opening lets material through.']),
 'anvil': dict(commands=route([(0,3),(3,3),(3,2),(0,2),(1,1),(1,0),(2,0),(2,2)]), gap=10+math.sqrt(2), dot=(0,1),
  rationale=['A short striker meets a broad, grounded working surface.', 'The pause is at impact; the single dot is the spark of a checked test.']),
 'scribe': dict(commands=route([(3,0),(0,0),(0,1),(2,1),(2,2),(0,2),(0,3),(3,3)]), gap=11, dot=(3,3),
  rationale=['A written line returns, advances and keeps its place.', 'The square terminal is a cursor, ready for the next approved line.']),
 'source': dict(commands=route([(0,0),(3,0),(3,3),(0,3),(0,1),(2,1),(2,2)]), gap=4, dot=(2,2),
  rationale=['Supply enters from outside and winds inward to one accountable point.', 'The opening on the way in is where every input is checked.']),
 'assay': dict(commands=route([(0,0),(3,0),(3,2),(2,3),(1,3),(0,2),(0,1),(2,1)]), gap=4.6, dot=(2,2),
  rationale=['A hallmark: the stamp an assay office strikes once metal is tested against its standard.', 'The bar inside is the standard; the dot below it is the measured result.']),
}

# Compensate square-cap projections so the *visible* clearance, rather than
# merely the centreline omission, is exactly one grid unit. Every opening sits
# on a free span, clear of junctions. These are paint cuts, not route vertices.
for key in LOGOS:
    LOGOS[key]['cut']=[LOGOS[key]['gap']*6-.75,7.5]
# Anvil's opening arrives at the platen, so its cut also covers that stroke edge.
LOGOS['anvil']['cut']=[LOGOS['anvil']['gap']*6-1.5,7.5]
for mark in LOGOS.values():mark['visible_gap']=6

ICONS = {}
def icon(key, label, group, pts=None, commands=None, dot=None, gap=None, meaning=''):
    ICONS[key] = dict(label=label,group=group,commands=commands or route(pts),dot=dot,gap=gap,meaning=meaning)

for key in ['sift','anvil','scribe','source','assay']:
    ICONS[key] = {**LOGOS[key], 'label':key.title(),'group':'Navigation','meaning':'Tool identity, preserved at navigation size.'}
icon('audit-log','Audit log','Navigation',[(0,1),(3,1),(3,0),(0,0),(0,3),(3,3),(3,2),(0,2)],meaning='A ruled ledger: every entry kept in order.')
icon('rule-profiles','Rule profiles','Navigation',[(0,3),(0,2),(1,2),(1,1),(2,1),(2,0),(3,0)],meaning='Stepped thresholds, from permissive to strict.')
icon('settings','Settings','Navigation',[(0,1),(1,1),(1,0),(2,0),(2,2),(1,2),(1,1),(3,1)],meaning='A single adjustable slider; no gear.')
icon('new-run','New run','Actions',[(1,0),(1,3),(1,1),(0,1),(3,1)],meaning='An addition sign, traced through its junction.')
icon('run-again','Run again','Actions',commands=[['M',1,0],['L',0,1],['L',1,2],['L',0,1],['L',2,1],['A',1,1,3,2],['A',1,1,2,3],['L',1,3]],meaning='Returning arrow: compute a fresh answer.')
icon('replay','Replay · reused','Actions',[(0,0),(2,1),(0,2),(0,0),(3,0),(3,3),(1,3)],meaning='Playback triangle with a return enclosure: reuse an existing answer.')
icon('approve','Approve','Actions',[(0,1),(1,2),(3,0)],meaning='An affirmative check.')
icon('reject','Reject','Actions',[(0,0),(3,0),(3,3),(0,3),(0,0),(3,3)],meaning='A ruled-out result, enclosed and struck through.')
icon('send-back','Send back','Actions',[(1,0),(0,1),(1,2),(0,1),(3,1),(3,3)],meaning='Leftward return arrow with an open tail.')
icon('export','Export','Actions',[(0,2),(0,3),(3,3),(3,2),(2,2),(2,0),(1,1),(2,0),(3,1)],meaning='A route leaving its tray.')
icon('evidence-report','Evidence report','Actions',[(3,0),(0,0),(0,3),(3,3),(3,1),(2,2),(1,1)],meaning='A document perimeter ending in a check.')
icon('compare','Compare','Actions',[(1,0),(2,0),(2,1),(3,1),(3,3),(1,3),(1,2),(1,1),(2,1),(2,2),(1,2),(0,2),(0,0),(1,0)],meaning='Two overlapping squares: what two results share and where they differ.')
icon('filter','Filter','Actions',[(0,0),(3,0),(2,1),(2,3),(1,3),(1,1),(0,0)],meaning='A funnel reduces a wide input.')
icon('search','Search','Actions',commands=[['M',3,3],['L',2,2],['L',1,2],['A',1,1,0,1],['A',1,1,1,0],['A',1,1,2,1],['L',2,2]],meaning='A quarter-arc lens and a diagonal handle.')
icon('code-check','Code check','Who said it',[(1,0),(0,1),(1,2),(2,0),(3,1),(2,2)],meaning='Angle brackets and a slash identify deterministic code.')
icon('ai-reviewer','AI reviewer','Who said it',[(0,1),(1,0),(2,0),(3,1),(2,2),(1,2),(0,1)],dot=(2,1),meaning='An open eye with its pupil forward identifies an independent reading.')
icon('person','Person','Who said it',commands=[['M',0,3],['L',0,2],['A',1,1,1,1],['A',1,1,2,2],['L',2,3]],dot=(1,0),meaning='A head and shoulder arch identify a human decision.')
icon('passed','Passed','Status',[(0,1),(1,2),(3,0)],meaning='Check. Shares the affirmative action vocabulary.')
icon('failed','Failed','Status',[(0,0),(3,0),(3,3),(0,3),(0,0),(3,3)],meaning='Struck-through square. Shares the rejection action vocabulary.')
icon('needs-review','Needs review','Status',commands=[['M',0,1],['A',1,1,1,0],['A',1,1,2,1],['A',1,1,1,2]],dot=(1,3),meaning='A question mark: a judgement is still required.')
icon('warning','Warning','Status',[(1,0),(2,0),(1,2),(0,0),(1,0)],dot=(1,3),meaning='An exclamation: a tapering wedge over its point. Sits with the question mark and the i.')
icon('info','Info','Status',[(1,1),(1,3),(0,3),(2,3)],dot=(1,0),meaning='A lowercase information stem with its point.')
icon('blocked','Blocked','Status',[(1,0),(2,0),(3,1),(3,2),(2,3),(1,3),(0,2),(0,1),(1,0)],meaning='A stop-sign octagon: progression is prevented.')
icon('running','Running','Status',commands=[['M',3,1],['L',3,2],['A',1,1,2,3],['L',1,3],['A',1,1,0,2],['L',0,1],['A',1,1,1,0],['L',2,0]],meaning='An incomplete rounded perimeter; recognisable even without motion.')
icon('empty','Empty','Status',[(0,1),(0,3),(3,3),(3,1)],meaning='An open tray with nothing inside.')
# Added 2026-11-13 for the review screen: the meanings the app still borrowed from a generic set.
icon('edit','Edit','Actions',[(1,3),(0,3),(0,2),(2,0),(3,1),(1,3),(0,2)],meaning='A pencil body and its ferrule line: change the wording, as a new version.')
icon('propose','Propose','Who said it',[(1,0),(2,1),(1,2),(0,1),(1,0)],dot=(2,2),meaning='A spark with its point set apart: a model proposal, advice until a person decides.')
icon('apply','Apply suggestion','Actions',[(0,3),(2,1),(3,1),(3,0),(2,0),(2,1)],meaning='A wand ending in a square head: take the suggested wording in one step.')
icon('approve-all','Approve all','Actions',[(3,0),(1,2),(0,1),(0,3),(3,3)],meaning='A check resting in its tray: approve every item a stated rule cleared.')
icon('next','Next','Actions',[(2,0),(3,1),(2,2),(3,1),(0,1)],meaning='Rightward arrow, the mirror of Send back: move on to the next step.')
icon('theme-system','System theme','Navigation',[(1,3),(1,2),(0,2),(0,0),(3,0),(3,2),(2,2),(2,3)],meaning='A screen on two legs: follow the computer.')
icon('theme-light','Light theme','Navigation',commands=[['M',3,2],['L',0,2],['A',1,1,1,1],['A',1,1,2,2]],dot=(1,0),meaning='A sun above the horizon, with its point: the daylit light table.')
icon('theme-dark','Dark theme','Navigation',commands=[['M',3,1],['L',0,1],['A',1,0,1,2],['A',1,0,2,1]],meaning='The same sun set below the horizon: the darkroom.')
icon('key','Key','Navigation',[(2,2),(1,2),(1,1),(0,0),(3,0),(3,3),(0,3),(0,0)],meaning='A keycap and its bevel: a keyboard shortcut.')
icon('chevron-right','Open','Navigation',[(1,0),(2,1),(2,2),(1,3)],meaning='A flat-nosed chevron, symmetric on the grid: open in place.')
icon('chevron-down','Expand','Navigation',[(0,1),(1,2),(2,2),(3,1)],meaning='The same chevron turned down: a list of choices.')
icon('save','Save','Actions',[(0,2),(0,3),(3,3),(3,2),(2,2),(1,1),(2,2),(3,1),(2,2),(2,0)],meaning='A route arriving in its tray, the mirror of Export.')
icon('score','Score','Actions',[(0,1),(0,3),(1,3),(1,2),(1,3),(2,3),(2,2),(2,3),(3,3),(3,1)],meaning='A measuring scale: findings counted against an answer key.')
icon('open-file','Choose file','Actions',[(3,1),(2,1),(2,0),(0,0),(0,3),(3,3),(3,1),(2,0)],meaning='A sheet with its corner turned: pick a document to bring in.')

N_ICONS = len(ICONS)
_rows = sum(-(-sum(1 for v in ICONS.values() if v['group']==g)//7) for g in ['Navigation','Actions','Who said it','Status'])
ICON_SHEET_H = max(1540, 215 + _rows*150 + 4*68 + 140)

def path_d(commands):
    out=[]
    for c in commands:
        if c[0] in ('M','L'): out.append(f'{c[0]}{3+6*c[1]:g} {3+6*c[2]:g}')
        else: out.append(f'A{6*c[1]:g} {6*c[1]:g} 0 0 {c[2]} {3+6*c[3]:g} {3+6*c[4]:g}')
    return ' '.join(out)

def drawing(data, accent=False):
    cut=data.get('cut')
    dash = f' stroke-dasharray="{cut[0]:.8f} {cut[1]:g} 1000 1000"' if cut else ''
    p=f'<path d="{path_d(data["commands"])}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter" stroke-miterlimit="4"{dash}/>'
    if data.get('dot') is not None:
        x,y=data['dot']; fill='var(--zyn-accent, currentColor)' if accent else 'currentColor'
        p+=f'<rect class="zyn-dot" x="{2+6*x:g}" y="{2+6*y:g}" width="2" height="2" fill="{fill}"/>'
    return p

def text(value, x, y, size=12, family='mono', tracking=0, color='currentColor'):
    p,w=outline(value, family, size, tracking)
    return f'<g aria-label="{html.escape(value,quote=True)}" transform="translate({x:g} {y:g})" fill="{color}">{p}</g>'

def lockup(key):
    p,w=outline(key,'display',20,-0.65)
    return drawing(LOGOS[key],True)+f'<g transform="translate(30 18)" fill="currentColor">{p}</g>', 6*math.ceil((31+w)/6)

def svg(body, width=24, height=24, vb=None, theme=None, title=None, desc=None):
    vb=vb or f'0 0 {width:g} {height:g}'
    style=f' style="color:{INK if theme=="light" else PAPER};--zyn-accent:{BLUE[theme]}"' if theme else ''
    meta=(f'<title>{html.escape(title)}</title>' if title else '')+(f'<desc>{html.escape(desc)}</desc>' if desc else '')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}" height="{height:g}" viewBox="{vb}"{style} role="img">{meta}{body}</svg>'

def write(path, body):
    target=ROOT/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(body,encoding='utf-8')

def place(body,x,y,size):
    return f'<g transform="translate({x:g} {y:g}) scale({size/24:g})">{body}</g>'

def rect(x,y,w,h,fill): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'
def line(x1,y1,x2,y2,color='#C8CBCB',weight=1): return f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="{color}" stroke-width="{weight}"/>'

def sheet(body,w,h,theme,title,number):
    bg=INK if theme=='dark' else PAPER
    muted='#B7BABB' if theme=='dark' else '#606466'
    header=text('ZYN / IDENTITY SYSTEM',56,45,12)+text(number,w-150,45,12)
    footer=line(56,h-55,w-56,h-55,'#454749' if theme=='dark' else '#D9DBDC')+text('Zyn prototype',56,h-26,11,color=muted)+text('4 × 4 / ONE ROUTE / ONE REVIEW GAP',w-430,h-26,11,color=muted)
    return svg(rect(0,0,w,h,bg)+header+body+footer,w,h,theme=theme,title=title)

def grid(x,y,size,color='#B3B7B9'):
    s=''
    for row in range(4):
        for col in range(4): s+=f'<circle cx="{x+(3+6*col)*size/24:g}" cy="{y+(3+6*row)*size/24:g}" r="2" fill="{color}"/>'
    return s

def construction():
    b=text('A path. A pause. A decision.',56,129,52,'display',-1.8)
    b+=text('ENGINEERING WORK, WITH REVIEW BUILT INTO THE ROUTE.',58,165,13)
    b+=grid(72,235,432)+place(drawing(LOGOS['zyn'],True),72,235,432)
    b+=text('4 × 4 DOT GRID',80,715,15)+text('u = 6 px / 24 px canvas',80,744,12)
    b+=line(126,227,234,227)+line(126,218,126,236)+line(234,218,234,236)+text('1u',166,210,12)
    rules=[('01','One route','All route vertices sit on the sixteen grid points.'),('02','One deliberate gap','Exactly 1u of visible clearance. Review lives here.'),('03','One uniform stroke','1.5 px at 24 px. Square caps. Mitred joins.'),('04','At most one solid dot','2 × 2 px. Its centre is a grid point. Only it takes blue.'),('05','Two surfaces, one identity','Ink on paper. Paper on ink. No effects or extra fills.')]
    for i,(n,t,d) in enumerate(rules):
        y=254+i*96
        b+=text(n,592,y,12)+text(t,643,y,24,'display',-.5)+text(d,643,y+29,12)
    b+=line(56,807,1544,807)
    b+=text('THE FAMILY',56,850,12)
    for i,(k,v) in enumerate(LOGOS.items()):
        x=80+i*(1440//len(LOGOS))
        b+=grid(x,876,96)+place(drawing(v,True),x,876,96)+text(k,x+120,933,27,'display',-.7)
    b+=text('CONSTRUCTION NOTES',56,1040,12)
    notes=['The route is continuous; the single omitted interval interrupts its ink. No independent branches are added.',
           'Gap = 6 px of visible clearance along the route. Cut lengths compensate for square caps.',
           'Route vertices stay on-grid. Paint cuts may fall between points, including the approved diagonal cut in Z.',
           'Anvil’s cut also covers the platen edge it arrives at. Revisited junctions are permitted; there are no pen lifts.',
           'Wordmarks are separate typography: D-DIN Condensed Bold capitals, tracking 0.06em. Labels: IBM Plex Mono.']
    for i,n in enumerate(notes): b+=text(n,56,1073+i*25,11.4)
    write('sheets/01-construction.svg',sheet(b,1600,1280,'light','Zyn construction','01 / 05'))

def logo_sheets(theme):
    b=text('One family. Six working paths.',56,125,48,'display',-1.5)+text('MARKS + WORDMARKS / FULL COLOUR AND MONOCHROME',58,160,12)
    for i,(k,v) in enumerate(LOGOS.items()):
        y=210+i*300
        if i: b+=line(56,y-22,1544,y-22,'#454749' if theme=='dark' else '#D9DBDC')
        b+=place(drawing(v,True),65,y+30,144)
        lock,w=lockup(k)
        b+=place(lock,262,y+52,88)
        b+=text(v['rationale'][0],263,y+172,13)+text(v['rationale'][1],263,y+198,13)
        b+=text('NATIVE SIZE',1090,y+14,10)
        for n,(sz,x) in enumerate([(64,1090),(32,1230),(16,1335)]):
            b+=place(drawing(v,True),x,y+45,sz)+text(f'{sz} px',x,y+132,10)
        b+=text('MONO / 16 px',1090,y+181,10)
        mono=drawing(v,False)
        b+=place(mono,1090,y+208,16)
        b+=place(lock.replace('var(--zyn-accent, currentColor)','currentColor'),1130,y+208,16)
    write(f'sheets/02-logos-{theme}.svg',sheet(b,1600,210+len(LOGOS)*300+90,theme,f'Zyn logos, {theme}','02 / 05'))

def icon_sheet(theme):
    b=text('Tools for checked work.',56,125,48,'display',-1.5)+text(f'{N_ICONS} GLYPHS / 24 PX CANVAS / 1.5 PX STROKE / MONOCHROME FIRST',58,164,12)
    y=215
    for group in ['Navigation','Actions','Who said it','Status']:
        entries=[(k,v) for k,v in ICONS.items() if v['group']==group]
        b+=text(group.upper(),56,y,13)+line(250,y-4,1544,y-4,'#454749' if theme=='dark' else '#D9DBDC')
        y+=24
        for i,(k,v) in enumerate(entries):
            col=i%7; row=i//7;x=56+col*214; yy=y+row*150
            b+=place(drawing(v,False),x+9,yy+20,48)
            b+=place(drawing(v,False),x+94,yy+39,24)+place(drawing(v,False),x+140,yy+47,16)
            b+=text(v['label'],x+8,yy+98,11.6)
        y+=math.ceil(len(entries)/7)*150+44
    b+=text('48 px overview / 24 px native / 16 px reduction. All judgements retain their meaning without colour.',56,y+7,12)
    write(f'sheets/03-icons-{theme}.svg',sheet(b,1600,ICON_SHEET_H,theme,f'Zyn full icon set, {theme}','03 / 05'))

def proof_sheet(theme):
    b=text('Small enough to work.',56,125,48,'display',-1.5)+text('MONOCHROME / ACTUAL 16 PX GLYPHS / NO COLOUR DEPENDENCE',58,164,12)
    b+=text('TOOL SILHOUETTES',56,231,12)
    for i,k in enumerate(LOGOS):
        x=56+i*(1470//len(LOGOS))
        b+=place(drawing(LOGOS[k],False),x,265,16)+text(k,x+35,278,13)
    y=365
    for group in ['Navigation','Actions','Who said it','Status']:
        b+=text(group.upper(),56,y,12)
        entries=[(k,v) for k,v in ICONS.items() if v['group']==group]
        for i,(k,v) in enumerate(entries):
            x=56+(i%5)*294;yy=y+36+(i//5)*65
            b+=place(drawing(v,False),x,yy,16)+text(v['label'],x+32,yy+13,12)
        y+=math.ceil(len(entries)/5)*65+72
    b+=text('16 px uses a proportional 1 px stroke; no pixel-only detail or colour has been added.',56,1274,12)
    write(f'sheets/04-small-size-{theme}.svg',sheet(b,1600,1380,theme,'Zyn sixteen pixel proof','04 / 05'))

def overview():
    # A compact, shareable presentation of the whole system, with both surfaces.
    b=text('zyn',56,150,100,'display',-3.2)+text('Traceable work.',575,119,42,'display',-1.3)+text('Checked twice. Decided by a person.',577,158,20,'display',-.4)
    b+=line(56,208,1544,208)
    for i,(k,v) in enumerate(LOGOS.items()):
        x=64+i*(1490//len(LOGOS))
        b+=place(drawing(v,True),x,265,144)+text(k,x+4,462,34,'display',-1)
    b+=text('DETERMINISTIC CODE CHECKS  +  INDEPENDENT AI REVIEW  →  HUMAN DECISION',57,542,14)
    b+=rect(0,605,1600,438,INK)
    b+=f'<g style="color:{PAPER};--zyn-accent:{BLUE["dark"]}">'
    for i,k in enumerate(LOGOS):
        x=64+i*(1490//len(LOGOS))
        lk,w=lockup(k); b+=place(lk,x,684,58)
        b+=place(drawing(LOGOS[k],False),x+5,818,16)+text('16 px / mono',x+39,832,11)
    b+='</g>'
    b+=text('THE IN-APP VOCABULARY',56,1105,12)
    for i,(k,v) in enumerate(ICONS.items()):
        col=i%15;row=i//15;x=57+col*99;yy=1146+row*114  # 15 across fits all 43 in three rows
        b+=place(drawing(v,False),x+7,yy,24)+text(v['label'],x+7,yy+57,9)
    b+=text('4 × 4 grid. One route. One review gap. One optional signal dot.',56,1535,14)
    write('sheets/00-overview.svg',sheet(b,1600,1640,'light','Zyn identity system overview','00 / 05'))
    # Compact cover for sharing the mark family without reducing the icon sheet.
    write('sheets/00-family-preview.svg',svg(rect(0,0,1600,1043,PAPER)+text('ZYN / IDENTITY SYSTEM',56,45,12)+b,1600,1043,theme='light',title='Zyn mark family, light and dark'))

def exports():
    for key,data in LOGOS.items():
        mark=drawing(data,True);lk,w=lockup(key)
        write(f'logos/themeable/{key}-mark.svg',svg(mark,24,24,title=f'{key} mark'))
        write(f'logos/themeable/{key}-wordmark.svg',svg(lk,w,24,title=f'{key} wordmark'))
        for theme in ['light','dark']:
            for size in [512,64,32,16]:
                write(f'logos/{theme}/{size}/{key}-mark.svg',svg(mark,size,size,'0 0 24 24',theme,f'{key} mark'))
                write(f'logos/{theme}/{size}/{key}-wordmark.svg',svg(lk,w*size/24,size,f'0 0 {w:g} 24',theme,f'{key} wordmark'))
    for key,data in ICONS.items():
        for size in [24,16]:
            write(f'icons/{size}/{key}.svg',svg(drawing(data,key in LOGOS),size,size,'0 0 24 24',title=data['label']))
    defs=''.join(f'<symbol id="zyn-{key}" viewBox="0 0 24 24">{drawing(v,key in LOGOS)}</symbol>' for key,v in ICONS.items())
    write('icons/zyn-sprite.svg',f'<svg xmlns="http://www.w3.org/2000/svg"><defs>{defs}</defs></svg>')

def documentation():
    lines=['# Zyn identity system','', 'Engineering documents → checked outputs. Code checks and an independent AI reviewer evaluate; a person approves or rejects.','',
    'Open `index.html` for the local review page. No server, installation or network connection is needed.','',
    '## Files','', '- `sheets/`: construction, logos, all ' + str(N_ICONS) + ' labelled icons, and actual-size 16 px proofs in SVG and PNG.', '- `logos/themeable/`: master mark and outlined wordmark SVGs.', '- `logos/light/` and `logos/dark/`: mark and wordmark SVG + PNG at 512, 64, 32 and 16 px.', '- `icons/24/` and `icons/16/`: individual SVGs. `icons/zyn-sprite.svg` is the symbol sprite.', '- `raster/icons/{light,dark}/{24,16}/`: background-flattened PNGs.', '- `source/geometry.json`: all paths, grid vertices, dot positions, semantic labels and rationales.', '- `tools/`: reproducible vector generator, raster renderer and construction validator.', '',
    '## Construction','', 'The 24 × 24 viewBox has sixteen grid points: x,y ∈ {3,9,15,21}. Grid unit u=6; active field 18 × 18. Every route vertex is on this grid. Straight segments and true quarter arcs only. There is one path element and one initial M per glyph. Some junctions are retraced, keeping one route without pen lifts.', '',
    'The six logo routes each have one visible gap, exactly 6 viewBox units measured along the route. One dash interruption cuts the ink; there is no background-coloured patch or second path. A square cap projects 0.75 px beyond a cut centre, so isolated gaps omit 7.5 px of centreline to leave exactly 6 px clear. All route vertices remain on-grid. Paint cuts may fall between points, including the diagonal cut in Z approved by the user. Anvil’s cut also covers the platen edge it arrives at. Sift places its opening on a free span, clear of crossing strands.', '',
    '“One continuous stroke” means one underlying continuous route with one interruption in its ink. A literally unbroken ink stroke and a gap are incompatible.', '',
    'The accent dot is a 2 × 2 px solid square, centred on a grid point. This square treatment unifies the family with Scribe’s cursor. Zyn, Anvil, Scribe and Source use a terminal or witness point; Sift retains it above its lattice; Assay holds it inside its hallmark as the measured result. There is at most one per glyph. All other mark geometry is unfilled.', '',
    'Icons retain the 24 px construction and 1.5 px stroke. At 16 px they scale proportionally to 1 px. Only the five tool glyphs preserve the logo gap and accent dot; other icons use no accent. Needs review uses a question mark and a separate punctuation dot; Warning uses an exclamation built the same way, so the two read as one punctuation pair with Info. Approve/Passed and Reject/Failed intentionally share the same affirmative/negative shape.', '',
    '## Theme and type','', 'Ink #121211; paper #FBFAF7. Signal Blue #1F5FCC in light mode; #5C9DFF in dark mode, the same accent as the review screen (4.5:1 on paper). Blue appears only on the square dot. Themeable SVGs inherit currentColor and default to monochrome; set --zyn-accent to opt into the signal colour. Themed presentation exports set those defaults at the SVG root. PNGs flatten onto their respective paper/ink surfaces.', '',
    'Wordmarks are D-DIN Condensed Bold capitals with 0.06em tracking, matching the review screen; the mark sits left with a 6 px gap at native 24 px. The transparent lockup height equals its mark tile height. Thus a 64 px wordmark export has a 64 px mark tile, and its width follows the word length. Labels, version tags and the exact descriptor “Zyn prototype” use IBM Plex Mono Regular.', '',
    'Wordmark glyphs and sheet typography are portable vector outlines, so the SVGs do not need fonts installed. The no-fill rule applies to the symbols, not typeset letters, sheet backgrounds or construction guides. The open-source fonts and their SIL OFL licences are included under fonts/: D-DIN Condensed Bold (display) and IBM Plex Mono (labels). Space Grotesk is kept for the record but no longer used.', '',
    '## Mark rationale','']
    for k,v in LOGOS.items():lines += [f'### {k}', '', *v['rationale'], '']
    lines += ['## Integration','', 'Inline an SVG or use the sprite with `<svg><use href="icons/zyn-sprite.svg#zyn-sift"/></svg>`. External `<img>` elements cannot inherit host currentColor; use the themed exports in that case. Give icon-only controls a label. Show the judgement actor name beside its glyph; do not rely on the shape alone. Status labels remain visible and never rely on colour.', '',
    'Run `python tools/build.py`, then `node tools/render.cjs`. FontTools is needed for the build; Sharp and Playwright are needed for rendering and browser review. The build script uses the two included fonts. Generated assets have no runtime dependencies.','']
    write('README.md','\n'.join(lines))
    write('source/geometry.json',json.dumps(dict(grid=dict(canvas=24,points=[3,9,15,21],unit=6,stroke=1.5,dot=2,gap=6,gap_measure='visible clearance; square-cap compensation'),logos=LOGOS,icons=ICONS),indent=2,ensure_ascii=False))

def gallery():
    # All gallery content is local, and all controls operate on the SVGs in view.
    data=json.dumps(dict(logos=LOGOS,icons=ICONS))
    head='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Zyn — checked work, drawn as a system</title>
<style>
@font-face{font-family:Space;src:url(fonts/D-DINCondensed-Bold.ttf)}@font-face{font-family:Plex;src:url(fonts/IBMPlexMono-Regular.ttf)}
:root{--paper:#FBFAF7;--ink:#121211;--muted:#626769;--rule:#D5D8D9;--zyn-accent:#1F5FCC;color-scheme:light}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:Space,sans-serif}body.dark{--paper:#121211;--ink:#FBFAF7;--muted:#B7BABB;--rule:#4B4E50;--zyn-accent:#5C9DFF;color-scheme:dark}body.mono{--zyn-accent:currentColor}a{color:inherit;text-underline-offset:5px}button,input{font:inherit}button,a.control{border:1px solid var(--rule);background:none;color:inherit;border-radius:0;padding:11px 15px;cursor:pointer;font:12px Plex,monospace}button[aria-pressed=true]{border-color:var(--ink);background:var(--ink);color:var(--paper)}button:focus-visible,a:focus-visible,input:focus-visible{outline:2px solid var(--ink);outline-offset:4px}header{padding:22px 40px;border-bottom:1px solid var(--rule);display:flex;align-items:center;gap:20px;justify-content:space-between}header p{font:11px Plex,monospace;margin:0}nav{display:flex;gap:20px;font:11px Plex,monospace}main{max-width:1600px;margin:auto;padding:0 56px}section{padding:52px 0 64px;border-bottom:1px solid var(--rule)}.eyebrow,.mono,.number{font:12px Plex,monospace}.hero{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:end;padding-top:72px}.hero h1{font-weight:500;font-size:clamp(52px,7vw,104px);line-height:1;letter-spacing:-.045em;margin:20px 0 28px}.hero p{max-width:550px;font-size:21px;line-height:1.55}.hero-art{display:flex;justify-content:center;align-items:center;min-height:340px;border:1px solid var(--rule)}.hero-art svg{width:270px;height:270px}.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:30px}.controls p{font:11px Plex,monospace;margin-left:auto}.family{display:grid;grid-template-columns:repeat(6,1fr);border-left:1px solid var(--rule);border-top:1px solid var(--rule);margin-top:32px}.tool{border-bottom:1px solid var(--rule);border-right:1px solid var(--rule);padding:32px 24px}.tool .large svg{width:96px;height:96px}.tool h3{font-size:30px;letter-spacing:-.035em;font-weight:500;margin:27px 0 17px}.tool p{font-size:14px;line-height:1.6;min-height:90px;color:var(--muted)}.tool .sizes{display:flex;gap:22px;align-items:center;height:64px;margin:20px 0 30px}.tool a{font:11px Plex,monospace}h2{font-size:40px;letter-spacing:-.035em;font-weight:500;margin:15px 0 20px}.intro{color:var(--muted);max-width:760px;font-size:17px;line-height:1.6}.construction{display:grid;grid-template-columns:1fr 1.3fr;gap:70px;align-items:center;margin-top:32px}.grid-proof{border:1px solid var(--rule);padding:30px;display:flex;justify-content:center}.grid-proof svg{width:min(100%,350px);height:auto}.rules{display:grid;grid-template-columns:70px 1fr;gap:19px 10px}.rules dt{font:13px Plex,monospace}.rules dd{margin:0;font-size:16px;line-height:1.6}.note{font:11px/1.8 Plex,monospace;color:var(--muted);margin-top:28px}.icon-controls{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin:28px 0}input{background:transparent;color:inherit;border:1px solid var(--rule);border-radius:0;padding:12px 15px;min-width:260px}.icon-group{margin-top:38px}.icon-group h3{font:12px Plex,monospace;text-transform:uppercase;letter-spacing:.05em;padding-bottom:15px;border-bottom:1px solid var(--rule)}.icon-grid{display:grid;grid-template-columns:repeat(7,1fr)}.glyph{padding:26px 12px;min-height:130px;display:flex;flex-direction:column;gap:22px;border-bottom:1px solid var(--rule)}.glyph .glyph-picture{height:48px;display:flex;gap:22px;align-items:center}.glyph label{font:11px Plex,monospace}.glyph a{text-decoration:none}.glyph .download{font:10px Plex,monospace;color:var(--muted)}.glyph[hidden]{display:none}.hidden{display:none}.sheets{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:32px}.sheet{display:block;border:1px solid var(--rule);text-decoration:none}.sheet img{display:block;width:100%;aspect-ratio:1.2;object-fit:contain;background:#FBFAF7;border-bottom:1px solid var(--rule)}.sheet span{display:block;padding:18px;font:12px Plex,monospace}.downloads{display:flex;gap:15px;flex-wrap:wrap;margin-top:25px}footer{padding:28px 40px;display:flex;justify-content:space-between;font:11px Plex,monospace}.canvas-grid{opacity:0}.showgrid .canvas-grid{opacity:1}.sprite{position:absolute;width:0;height:0;overflow:hidden}@media(hover:hover){button:hover,a.control:hover{border-color:var(--ink)}.glyph a:hover{text-decoration:underline}.sheet:hover{border-color:var(--ink)}}@media(max-width:1000px){main{padding:0 24px}.family{grid-template-columns:repeat(3,1fr)}.hero{grid-template-columns:1fr}.hero-art{min-height:260px}.icon-grid{grid-template-columns:repeat(4,1fr)}.construction{gap:28px}.sheets{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){header{padding:18px 24px;align-items:start}nav{gap:12px;flex-wrap:wrap;justify-content:end}.family{grid-template-columns:repeat(2,1fr)}.tool{padding:24px 15px}.tool p{min-height:120px}.construction{grid-template-columns:1fr}.icon-grid{grid-template-columns:repeat(2,1fr)}.sheets{grid-template-columns:1fr}.hero h1{font-size:56px}.hero p{font-size:18px}footer{padding:24px;gap:20px}.controls p{margin-left:0}h2{font-size:34px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{header,.controls,.icon-controls,.downloads{display:none}main{padding:0 20px}.family{grid-template-columns:repeat(6,1fr)}section{break-inside:avoid}.hero{padding-top:20px}body{--paper:#FBFAF7;--ink:#121211}a{text-decoration:none}}
</style><body><header><p>Zyn prototype / identity 01</p><nav><a href="#family">Marks</a><a href="#construction">Construction</a><a href="#icons">Icons</a><a href="#files">Files</a></nav></header><main>
<section><div class="hero"><div><span class="eyebrow">ZYN / LOGO &amp; ICON SYSTEM</span><h1>Traceable work.<br>Visible review.</h1><p>Engineering documents become checked outputs. Code checks and an independent reviewer assess the work. A person makes the decision.</p></div><div class="hero-art" id="hero-art"></div></div><div class="controls"><button id="theme" aria-pressed="false">Dark mode</button><button id="mono" aria-pressed="false">Monochrome</button><button id="grid" aria-pressed="false">Show grid</button><p>16 points. One route. One review gap.</p></div></section>
<section id="family"><span class="eyebrow">01 / THE SIX MARKS</span><h2>Related by construction.</h2><p class="intro">A shared weight, open interval and square signal point. Each tool keeps a distinct silhouette, including at 16 px with colour removed.</p><div class="family" id="family-items"></div></section>
<section id="construction"><span class="eyebrow">02 / CONSTRUCTION</span><h2>The pause belongs to the path.</h2><div class="construction"><div class="grid-proof" id="construction-art"></div><dl class="rules"><dt>GRID</dt><dd>4 × 4 equally spaced points.<br>x, y = 3, 9, 15, 21 on a 24 px canvas.</dd><dt>STROKE</dt><dd>1.5 px, square caps, mitred joins.<br>One underlying route; only straight lines or quarter arcs.</dd><dt>GAP</dt><dd>One grid unit of visible clearance along the route.<br>Cut lengths compensate for square caps.</dd><dt>DOT</dt><dd>At most one 2 × 2 px solid square, centred on a grid point. It alone may take Signal Blue.</dd><dt>TYPE</dt><dd>D-DIN Condensed Bold, capitals, 0.06em tracking.<br>IBM Plex Mono for labels, tags and “Zyn prototype”.</dd></dl></div><p class="note">A route with a review gap is continuous in construction and interrupted in ink. Gap dimensions refer to visible clearance along the route. Cuts compensate for the 0.75 px square-cap projection. Route vertices stay on-grid; paint cuts can sit between points, including the approved diagonal cut in Z.</p></section>
<section id="icons"><span class="eyebrow">03 / IN-APP ICONS</span><h2>Judgements have an author.</h2><p class="intro">Code check uses angle brackets. The AI reviewer uses an open eye. A person uses a head and shoulders. Keep their names beside the icons in the app.</p><div class="icon-controls"><input id="search" type="search" aria-label="Find an icon" placeholder="Find an icon…"><button id="size" aria-pressed="false">Inspect at 16 px</button><span class="mono" id="count" aria-live="polite">__N_ICONS__ icons</span></div><div id="icon-groups"></div><p class="note">Approve / Passed and Reject / Failed share their respective shapes. Running is recognisable without animation. Status remains labelled and works without colour.</p></section>
<section id="files"><span class="eyebrow">04 / DELIVERY</span><h2>Ready to inspect. Ready to use.</h2><p class="intro">Portable SVGs use currentColor for ink. Wordmarks are outlined. The archive includes themed marks and wordmarks at 512, 64, 32 and 16 px, plus all __N_ICONS__ icons at 24 and 16 px.</p><div class="downloads"><a class="control" href="zyn-identity.zip" download>Download complete system ↗</a><a class="control" href="README.md">Construction &amp; integration notes ↗</a><a class="control" href="source/geometry.json">Geometry source ↗</a></div><div class="sheets" id="sheet-links"></div></section>
</main><footer><span>Zyn prototype</span><span>Checked twice. Decided by a person.</span></footer>
<script>'''
    js='''
const DATA=__DATA__;
function shape(d,accent=false){let p=d.commands.map(c=>c[0]==='A'?`A${c[1]*6} ${c[1]*6} 0 0 ${c[2]} ${3+c[3]*6} ${3+c[4]*6}`:`${c[0]}${3+c[1]*6} ${3+c[2]*6}`).join(' ');return `<path d="${p}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter" stroke-miterlimit="4" ${d.cut?`stroke-dasharray="${d.cut[0]} ${d.cut[1]} 1000 1000"`:''}/>`+(d.dot?`<rect x="${2+d.dot[0]*6}" y="${2+d.dot[1]*6}" width="2" height="2" fill="${accent?'var(--zyn-accent,currentColor)':'currentColor'}"/>`:'')}
function grid(){let o='';for(let y=0;y<4;y++)for(let x=0;x<4;x++)o+=`<circle cx="${3+x*6}" cy="${3+y*6}" r=".22" fill="var(--muted)"/>`;return o}
function art(d,size=24,accent=false,forced=false){return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true"><g class="${forced?'':'canvas-grid'}">${grid()}</g>${shape(d,accent)}</svg>`}
document.querySelector('#hero-art').innerHTML=art(DATA.logos.zyn,270,true);
document.querySelector('#construction-art').innerHTML=art(DATA.logos.zyn,350,true,true);
document.querySelector('#family-items').innerHTML=Object.entries(DATA.logos).map(([key,d])=>`<article class="tool"><div class="large">${art(d,96,true)}</div><h3>${key}</h3><p>${d.rationale.join('<br>')}</p><div class="sizes">${art(d,32,true)}${art(d,16,true)}</div><a href="logos/themeable/${key}-wordmark.svg" download>Wordmark SVG ↗</a></article>`).join('');
for(const group of ['Navigation','Actions','Who said it','Status']){let entries=Object.entries(DATA.icons).filter(([k,d])=>d.group===group);document.querySelector('#icon-groups').insertAdjacentHTML('beforeend',`<div class="icon-group"><h3>${group}</h3><div class="icon-grid">${entries.map(([k,d])=>`<article class="glyph" data-name="${d.label.toLowerCase()} ${group.toLowerCase()}"><div class="glyph-picture" data-key="${k}">${art(d,24,k in DATA.logos)}${art(d,16,false)}</div><label>${d.label}</label><a class="download" href="icons/24/${k}.svg" download title="${d.meaning}">SVG ↗</a></article>`).join('')}</div></div>`)}
let sheets=[['00-overview','System overview'],['01-construction','Construction rules'],['02-logos-light','Six logos · light'],['02-logos-dark','Six logos · dark'],['03-icons-light','All __N_ICONS__ icons · light'],['03-icons-dark','All __N_ICONS__ icons · dark'],['03-icons-both','All icons · both surfaces'],['04-small-size-light','16 px proof · light'],['04-small-size-dark','16 px proof · dark']];
document.querySelector('#sheet-links').innerHTML=sheets.map(([file,label])=>`<a class="sheet" href="sheets/${file}.svg"><img src="sheets/${file}.svg" loading="lazy" alt="${label}"><span>${label} ↗</span></a>`).join('');
for(const [id,cls] of [['theme','dark'],['mono','mono'],['grid','showgrid']])document.getElementById(id).onclick=e=>{let on=document.body.classList.toggle(cls);e.currentTarget.setAttribute('aria-pressed',String(on));};
document.querySelector('#search').oninput=e=>{let n=0,q=e.target.value.toLowerCase();document.querySelectorAll('.glyph').forEach(el=>{el.hidden=!el.dataset.name.includes(q);if(!el.hidden)n++});document.querySelectorAll('.icon-group').forEach(el=>el.hidden=![...el.querySelectorAll('.glyph')].some(g=>!g.hidden));document.querySelector('#count').textContent=`${n} icon${n===1?'':'s'}`};
document.querySelector('#size').onclick=e=>{let small=e.currentTarget.getAttribute('aria-pressed')!=='true';e.currentTarget.setAttribute('aria-pressed',String(small));document.querySelectorAll('.glyph-picture').forEach(el=>{let k=el.dataset.key;el.innerHTML=art(DATA.icons[k],small?16:24,k in DATA.logos)+(small?'':art(DATA.icons[k],16,false))});document.querySelectorAll('.download').forEach(el=>el.href=el.href.replace(small?'/24/':'/16/',small?'/16/':'/24/'))};
</script></body></html>'''.replace('__DATA__',data)
    write('index.html',(head+js).replace('__N_ICONS__',str(N_ICONS)))

if __name__=='__main__':
    exports();construction();overview()
    for t in ['light','dark']:logo_sheets(t);icon_sheet(t);proof_sheet(t)
    light=(ROOT/'sheets/03-icons-light.svg').read_text(encoding='utf-8')
    dark=(ROOT/'sheets/03-icons-dark.svg').read_text(encoding='utf-8').replace('<svg ', '<svg x="1600" ',1)
    write('sheets/03-icons-both.svg',svg(light+dark,3200,ICON_SHEET_H,title=f'All {N_ICONS} Zyn icons, light and dark on one sheet'))
    documentation();gallery()
    print(json.dumps({'logos':len(LOGOS),'icons':len(ICONS),'svg_files':len(list(ROOT.rglob('*.svg')))}))
