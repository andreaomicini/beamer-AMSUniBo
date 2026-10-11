"""nudge.py <engine> [pages]: one pass of per-frame corrections, written to nudges.json"""
import json, sys, os
from measure import compare, run
K = 1024 / 362.835
from deck import DIR
from align import PDF
NJ = DIR / 'nudges.json'
nud = json.load(open(NJ)) if NJ.exists() else {}
eng = sys.argv[1]
pages = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 and sys.argv[2] else list(range(2, len(PDF) + 1))
mode = sys.argv[3] if len(sys.argv) > 3 else 'both'   # gaps | shift | both
data = run(eng, pages)
for n in pages:
    nd = data[n]
    rows, _, _ = compare(n, nd)
    lines = []
    for k, dx, dy, t, cite, y in rows:
        if cite or nd[k]['path'].startswith('h2'):
            continue
        if lines and abs(lines[-1][0] - y) < 1:
            continue
        lines.append((y, dy, k))
    if not lines:
        continue
    e = nud.setdefault(str(n), {'shift': 0.0, 'm': {}})
    if mode in ('gaps', 'both'):
        for (ya, dya, ka), (yb, dyb, kb) in zip(lines, lines[1:]):
            step = dyb - dya
            r = nd[kb]
            if abs(step) > 0.4 and r['eidx'] >= 0 and not r['brk']:
                cur = r['emargin'] / K
                e['m'][str(r['eidx'])] = round(cur - step, 2)
    if mode in ('shift', 'both'):
        dy0 = sorted(l[1] for l in lines)[len(lines) // 2]   # median offset
        if abs(dy0) > 0.3:
            e['shift'] = round(e['shift'] - dy0, 2)
json.dump(nud, open(NJ, 'w'), indent=0, sort_keys=True)
print('nudged', len(pages), 'pages')
