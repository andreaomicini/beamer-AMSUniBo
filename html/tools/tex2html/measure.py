"""measure.py <engine> [pages]: every text run's baseline and left edge, HTML against PDF, in TeX points.
Prints, per page, the runs off by more than 0.6pt: dy > 0 means the HTML sits lower than the PDF."""
import sys, json, difflib, statistics, unicodedata, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from browser import Browser
from align import PDF, SAME

K = 1024 / 362.835
from deck import path, STYLE
URL = path('page').as_uri()
JS = r'''() => {
  const f = document.querySelector('.frame.current');
  const out = [];
  const walk = document.createTreeWalker(f, NodeFilter.SHOW_TEXT);
  const nodes = [];
  let n;
  while ((n = walk.nextNode())) nodes.push(n);
  // labels are generated content: their text is in the PDF, so give it to the alignment
  const labelOf = new Map();
  f.querySelectorAll('li[data-label]').forEach(li => {
    const w = document.createTreeWalker(li, NodeFilter.SHOW_TEXT);
    let t0;
    while ((t0 = w.nextNode()) && !/\S/.test(t0.data));
    if (t0 && li.dataset.label) labelOf.set(t0, li.dataset.label);
  });
  const marks = [];
  for (n of nodes) {
    const p = n.parentElement;
    if (p.closest('.headline, .footline')) continue;
    const t = n.data;
    const i = t.search(/\S/);
    if (i < 0) continue;
    if (labelOf.has(n)) out.push({t: labelOf.get(n), x: 0, base: 0, cite: true, fs: '', path: 'label', brk: false, eidx: -1, emargin: 0, label: true});
    const m = document.createElement('span');
    m.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
    const r = document.createRange();
    r.setStart(n, i); r.setEnd(n, i + 1);
    const x = r.getBoundingClientRect().left;
    const chain = [];
    for (let e = p; e && !e.classList.contains('frame'); e = e.parentElement) {
      if (['SPAN', 'EM', 'A', 'B', 'I', 'CODE', 'SUB'].includes(e.tagName)) continue;
      let d = e.tagName.toLowerCase();
      if (e.className) d += '.' + e.className.split(' ')[0];
      if (e.tagName === 'LI' && e.dataset.label !== undefined) d += '[l]';
      chain.unshift(d);
    }
    // the outermost block element this run opens: where a gap before it can be corrected
    const body = f.querySelector('.body');
    let E = null;
    if (body && body.contains(n)) {
      for (let e = p; e && e !== body; e = e.parentElement) {
        // never a block's body: under a title bar a margin there opens a gap, or covers the bar;
        // an untitled block moves as a whole
        if (e.classList.contains('block-body')) {
          if (e.parentElement.querySelector(':scope > .block-title')) break;
          continue;
        }
        if (getComputedStyle(e).display.startsWith('inline')) continue;
        // never inside multicols: a margin there rebalances the columns
        if (e.parentElement.closest('.multicols')) continue;
        const w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
        let t0;
        while ((t0 = w.nextNode()) && !/\S/.test(t0.data));
        if (t0 === n) E = e; else break;
      }
    }
    const all = body ? [...body.querySelectorAll('*')] : [];
    const eidx = E ? all.indexOf(E) : -1;
    const emargin = E ? parseFloat(getComputedStyle(E).marginTop) : 0;
    let prevSib = n.previousSibling;
    const brk = prevSib && prevSib.nodeName === 'BR';
    const colEl = p.closest('.column');
    const col = colEl ? [...f.querySelectorAll('.column')].indexOf(colEl) : -1;
    out.push({t, x, base: 0, cite: !!p.closest('.ccite'), fs: getComputedStyle(p).fontSize, path: chain.join('>'), brk, eidx, emargin, col});
    marks.push([n, i, m]);
  }
  // all markers in, read, then all out: inserting splits text nodes
  for (const [n, i, m] of marks) { const r2 = document.createRange(); r2.setStart(n, i); r2.collapse(true); r2.insertNode(m); }
  const real = out.filter(o => !o.label);
  marks.forEach(([n, i, m], k) => { real[k].base = m.getBoundingClientRect().bottom; });
  for (const [n, i, m] of marks) { const p = m.parentNode; m.remove(); p.normalize(); }
  return out;
}'''

def pdf_chars(pn):
    out = []
    for b in PDF[pn - 1].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            for sp in l['spans']:
                for ch in sp['chars']:
                    x, y = ch['origin']
                    if y < STYLE['head'] or y > STYLE['foot']:
                        continue
                    for c in unicodedata.normalize('NFKC', ch['c']).translate(SAME):
                        if not c.isspace():
                            out.append((c, x, y))
    return out

def run(engine, pages):
    res = {}
    with Browser(engine) as b:
        b.goto(URL + '#1'); b.wait(500)
        for n in pages:
            b.eval(f'location.hash = "#{n}"'); b.wait(60)
            res[n] = b.eval(JS)
    return res

def compare(n, nodes, limit=0.6):
    hc, own, first = [], [], []
    for k, nd in enumerate(nodes):
        t = unicodedata.normalize('NFKC', nd['t']).translate(SAME)
        f = True
        for c in t:
            if c.isspace():
                continue
            hc.append(c); own.append(k); first.append(f); f = False
    pc = pdf_chars(n)
    sm = difflib.SequenceMatcher(None, ''.join(hc), ''.join(c[0] for c in pc), autojunk=False)
    per = {}
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != 'equal':
            continue
        for t in range(i2 - i1):
            k = own[i1 + t]
            per.setdefault(k, []).append((first[i1 + t], pc[j1 + t]))
    rows = []
    for k, ms in sorted(per.items()):
        nd = nodes[k]
        dy = statistics.median(nd['base'] / K - c[2] for _, c in ms)
        fx = [c for f, c in ms if f]
        dx = nd['x'] / K - fx[0][1] if fx else 0.0
        rows.append((k, dx, dy, nd['t'].strip()[:50], nd['cite'], fx[0][2] if fx else ms[0][1][2]))
    return rows, len(hc), len(per)

if __name__ == '__main__':
    eng = sys.argv[1]
    pages = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 and sys.argv[2] != '-v' else list(range(1, len(PDF) + 1))
    allv = '-v' in sys.argv
    data = run(eng, pages)
    for n in pages:
        rows, nh, nm = compare(n, data[n])
        bad = [r for r in rows if abs(r[1]) > 0.6 or abs(r[2]) > 0.6]
        print(f'page {n}: {len(rows)} runs, {len(bad)} off' + ('' if bad or allv else ''))
        for k, dx, dy, t, cite, y in (rows if allv else bad):
            print(f'   y{y:7.2f}  dx {dx:+6.2f}  dy {dy:+6.2f}  {"c " if cite else ""}{t}')
