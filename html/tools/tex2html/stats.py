"""stats.py <engine> [pages] [-v]: worst baseline and left-edge error per page, in pt"""
import sys
from measure import compare, run
from align import PDF
eng = sys.argv[1]
pages = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 and sys.argv[2] not in ('', '-v') else list(range(1, len(PDF) + 1))
data = run(eng, pages)
worst = []
for n in pages:
    rows, nh, nm = compare(n, data[n])
    rows = [r for r in rows if not r[4]]
    my = max((abs(r[2]) for r in rows), default=0)
    mx = max((abs(r[1]) for r in rows), default=0)
    worst.append((n, my, mx))
    if '-v' in sys.argv and (my > 1 or mx > 1):
        for k, dx, dy, t, cite, y in rows:
            if abs(dx) > 1 or abs(dy) > 1:
                print(f'  {n:3} y{y:7.2f} dx {dx:+6.2f} dy {dy:+6.2f} {t}')
print('pages with |dy| > 1pt:', [(n, round(a, 1)) for n, a, b in worst if a > 1])
print('pages with |dx| > 1pt:', [(n, round(b, 1)) for n, a, b in worst if b > 1])
print('max dy %.2f, max dx %.2f' % (max(w[1] for w in worst), max(w[2] for w in worst)))
