"""Construction checks independent of the SVG formatter."""
import json,math,re,xml.etree.ElementTree as ET
from PIL import Image
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NS={'s':'http://www.w3.org/2000/svg'}
data=json.loads((ROOT/'source/geometry.json').read_text(encoding='utf-8'))
errors=[]
def check(condition,message):
    if not condition: errors.append(message)

def validate(key,mark,is_logo):
    commands=mark['commands']
    check(sum(c[0]=='M' for c in commands)==1,f'{key}: one initial move')
    length=0;current=None
    for c in commands:
        end=c[-2:]
        check(all(isinstance(p,int) and 0<=p<=3 for p in end),f'{key}: vertex on grid: {end}')
        if c[0]=='L': length+=math.dist(current,end)
        if c[0]=='A':
            r=c[1]
            check(abs(end[0]-current[0])==r and abs(end[1]-current[1])==r,f'{key}: exact quarter arc')
            length+=math.pi*r/2
        current=end
    dot=mark.get('dot')
    if dot:check(all(isinstance(p,int) and 0<=p<=3 for p in dot),f'{key}: on-grid dot')
    if is_logo:check(mark.get('gap') is not None,f'{key}: one logo gap')
    if mark.get('gap') is not None:check(mark['gap']>=0 and mark['gap']+1<=length+1e-7,f'{key}: gap inside route')
    p=ROOT/('logos/themeable/'+key+'-mark.svg' if is_logo else 'icons/24/'+key+'.svg')
    doc=ET.parse(p).getroot();paths=doc.findall('s:path',NS);dots=doc.findall('s:rect',NS)
    check(len(paths)==1,f'{key}: one stroke path')
    check(len(dots)<=1,f'{key}: at most one solid dot')
    check(doc.attrib['viewBox']=='0 0 24 24',f'{key}: native viewBox')
    for el in paths:
        check(el.attrib.get('fill')=='none',f'{key}: unfilled stroke')
        for attr,value in [('stroke','currentColor'),('stroke-width','1.5'),('stroke-linecap','square'),('stroke-linejoin','miter')]:check(el.attrib.get(attr)==value,f'{key}: {attr}')
        check(el.attrib['d'].count('M')==1,f'{key}: no pen lifts')
        if mark.get('cut') is not None:
            dash=[float(n) for n in el.attrib['stroke-dasharray'].split()]
            check(dash[1]>=6 and dash[2]>=length*6,f'{key}: one compensated interruption')
            check(dash[0]+dash[1]<=length*6+1e-6,f'{key}: compensated cut inside route')
        else:check('stroke-dasharray' not in el.attrib,f'{key}: no accidental interruptions')
    for el in doc.iter():check(el.tag.split('}')[-1] not in ['image','filter','linearGradient','radialGradient'],f'{key}: vector-only geometry')

for key,m in data['logos'].items():validate(key,m,True)
for key,m in data['icons'].items():validate(key,m,False)
check(len(data['logos'])==6,'All six logos')
check(len(data['icons'])==44,'All 44 icons')
for theme in ['light','dark']:
    for size in [512,64,32,16]:
        for key in data['logos']:
            for variant in ['mark','wordmark']:
                for ext in ['svg','png']:check((ROOT/f'logos/{theme}/{size}/{key}-{variant}.{ext}').exists(),f'Missing {theme}/{size}/{key}-{variant}.{ext}')
    for size in [24,16]:
        for key in data['icons']:check((ROOT/f'raster/icons/{theme}/{size}/{key}.png').exists(),f'Missing icon {key}/{size}/{theme}')
for p in ROOT.glob('sheets/*.svg'):ET.parse(p)

# Independent optical check: sample the flattened 512 px output along the
# entire route. Crossings, cap projections and the dot all contribute ink.
# There must be one clear interval, physically 6 viewBox units long.
optical={}
for key,mark in data['logos'].items():
    image=Image.open(ROOT/f'logos/light/512/{key}-mark.png').convert('RGB')
    empty=[];distance=0;step=.005;current=None
    for c in mark['commands']:
        b=(3+6*c[-2],3+6*c[-1])
        if c[0]=='M':current=b;continue
        a=current
        if c[0]=='L':
            length=math.dist(a,b)
            at=lambda t,a=a,b=b:(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
        else:
            # Quarter arc: pick the centre whose sweep direction matches the SVG flag.
            r=6*c[1];sweep=1 if c[2] else -1
            for centre in [(a[0],b[1]),(b[0],a[1])]:
                a0=math.atan2(a[1]-centre[1],a[0]-centre[0]);a1=math.atan2(b[1]-centre[1],b[0]-centre[0])
                delta=(a1-a0+math.pi)%(2*math.pi)-math.pi
                if delta*sweep>0:break
            length=r*abs(delta)
            at=lambda t,centre=centre,a0=a0,delta=delta,r=r:(centre[0]+r*math.cos(a0+delta*t),centre[1]+r*math.sin(a0+delta*t))
        count=math.ceil(length/step)
        for i in range(count):
            t=i/count;x,y=at(t)
            px=max(0,min(511,int(x*512/24)));py=max(0,min(511,int(y*512/24)))
            rgb=image.getpixel((px,py))
            # All channels near paper means no ink or accent at this point.
            if min(rgb)>=244:empty.append(distance+length*t)
        distance+=length;current=b
    groups=[]
    for value in empty:
        if not groups or value-groups[-1][-1]>.02:groups.append([value])
        else:groups[-1].append(value)
    gaps=[round(g[-1]-g[0]+step,3) for g in groups if g[-1]-g[0]>.1]
    optical[key]=gaps
    check(len(gaps)==1 and abs(gaps[0]-6)<.12,f'{key}: one visible 6 px gap, raster measurement {gaps}')

report={'result':'PASS' if not errors else 'FAIL','logo_count':len(data['logos']),'icon_count':len(data['icons']),'grid':'16 points, 6 px pitch','stroke':'1.5 px / square / miter','gap_convention':'1u visible clearance; cut lengths compensate square caps','visible_gaps_measured_at_512':optical,'approved_exception':'Z diagonal cut ends between grid points; paint cuts are not route vertices','checks':'Route vertices; arc angles; dot count and location; one path; one M; currentColor; no fills on strokes; compensated cut interval; optical gap width; export completeness; valid XML.','errors':errors}
(ROOT/'source/validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
raise SystemExit(bool(errors))
