"""blocks.py <engine> [-a]: every block's box, HTML against the box the PDF draws, in pt.
Prints blocks whose top or bottom is off by more than 0.6pt (-a: all), with what the block ends
with: a bottom off by about 2.4pt is a last line without descenders (see depth.py)."""
import sys
from playwright.sync_api import sync_playwright
from align import PDF
from deck import path
from depth import blocks, near

K = 1024 / 362.835
TITLE = [(0.212, 0.408, 0.38), (0.733, 0.18, 0.161), (0.698, 0.843, 0.824)]   # block, alert, example
JS = """(()=>{const f=document.querySelector('.frame.current');return [...f.querySelectorAll('.block')].map(k=>{
  const r=k.getBoundingClientRect();let e=k.querySelector(':scope>.block-body'),d=[];
  while(e.lastElementChild&&!['P','SPAN','EM','A','BR','I','B','CODE'].includes(e.lastElementChild.tagName)){
    e=e.lastElementChild;d.push(e.tagName.toLowerCase()+(e.className?'.'+e.className.split(' ')[0]:''))}
  return [r.top,r.bottom,!!k.querySelector(':scope>.block-title'),d.join('>')||'p']})})()"""

def titles(n):
    return sorted(dr['rect'].y0 for dr in PDF[n - 1].get_drawings()
                  if dr.get('fill') and dr['rect'].x0 > 1 and dr['rect'].width > 60 and near(dr['fill'], TITLE)
                  and 13 < dr['rect'].y0 and dr['rect'].y1 < 262)

eng = sys.argv[1]
rows = []
with sync_playwright() as p:
    b = getattr(p, eng).launch()
    pg = b.new_page(viewport={'width': 1024, 'height': 768})
    pg.goto(path('page').as_uri() + '#1'); pg.wait_for_timeout(500)
    for n in range(1, len(PDF) + 1):
        pg.evaluate(f'location.hash="#{n}"'); pg.wait_for_timeout(40)
        hb = pg.evaluate(JS)
        if not hb:
            continue
        bodies, tops, ti = blocks(n), titles(n), 0
        if len(bodies) != len(hb):
            rows.append((n, -1, None, None, f'{len(hb)} blocks, {len(bodies)} in the PDF'))
            continue
        for k, (t, bt, titled, desc) in enumerate(hb):
            top = tops[ti] if titled and ti < len(tops) else bodies[k][1]
            ti += titled
            rows.append((n, k, t / K - top, bt / K - bodies[k][3], desc))
    b.close()
bad = rows if '-a' in sys.argv else [r for r in rows if r[2] is None or abs(r[2]) > 0.6 or abs(r[3]) > 0.6]
print(f'{eng}: {len(rows)} blocks, {len(bad)} listed (page, block, top, bottom, ends with)')
for n, k, dt, db, d in bad:
    print(f'  {n:3} {k:2}', '' if dt is None else f'{dt:+6.2f} {db:+6.2f}', d)
