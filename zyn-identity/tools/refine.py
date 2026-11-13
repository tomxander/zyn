"""One-time update to construction copy and preview renderer."""
from pathlib import Path
p=Path(__file__).with_name('build.py')
s=p.read_text(encoding='utf-8')
changes={
 'The five logo routes have one omitted interval, exactly 6 viewBox units measured along the centreline. This is represented with one dash interruption; it is not a background-coloured patch or a second path. Square caps extend 0.75 px at each cut at native size, leaving 4.5 px of clear ink-to-ink space across an isolated straight gap. This measurement convention is explicit; the centreline interval is 1u. The Z diagonal cut ends are between grid points, as approved by the user. Its underlying vertices remain on-grid.':
 'The five logo routes each have one visible gap, exactly 6 viewBox units measured along the route. One dash interruption cuts the ink; there is no background-coloured patch or second path. A square cap projects 0.75 px beyond a cut centre, so isolated gaps omit 7.5 px of centreline to leave exactly 6 px clear. Anvil compensates for the existing platen edge; Source compensates for the arrival dot edge. All route vertices remain on-grid. Paint cuts may fall between points, including the diagonal cut in Z approved by the user. Sift places its opening on a free span, clear of crossing strands.',
 'Needs review uses a question-mark dot with one terminal interval omitted.':'Needs review uses a question mark and a separate punctuation dot.',
 "gap_measure='centreline'":"gap_measure='visible clearance; square-cap and arrival compensation'",
 'One grid unit along the route’s centreline.<br>The Z’s diagonal cut ends may sit between points.':'One grid unit of visible clearance along the route.<br>Cut lengths compensate for square caps and arrival edges.',
 'Gap dimensions refer to the omitted centreline interval; square caps extend 0.75 px from each cut at 24 px. The requested diagonal exception is recorded in the construction sheet.':'Gap dimensions refer to visible clearance along the route. Cuts compensate for the 0.75 px square-cap projection and any arrival edge. Route vertices stay on-grid; paint cuts can sit between points, including the approved diagonal cut in Z.',
 "${d.gap!=null?`stroke-dasharray=\"${d.gap*6} 6 1000 1000\"`:''}":"${d.cut?`stroke-dasharray=\"${d.cut[0]} ${d.cut[1]} 1000 1000\"`:''}"
}
for old,new in changes.items():
    assert s.count(old)==1,(old,s.count(old))
    s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
