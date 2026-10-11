"""TeX ends a block at its last line's real depth; CSS always keeps the font's descent.
depths(n): for each block on PDF page n, top to bottom, how much shallower than a 'g' its last
line is, in pt, from the glyph outlines of the faces the PDF used."""
import subprocess, functools
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from align import PDF

BODY = [(0.867, 0.929, 0.922), (0.965, 0.851, 0.847), (0.882, 0.937, 0.929)]   # the three block bodies
FACE = {'MerriwthrSans-Light': 'MerriweatherSans-Light', 'MerriwthrSans-LightItali': 'MerriweatherSans-LightItalic',
        'MerriwthrSans-Regular': 'MerriweatherSans-Regular', 'MerriwthrSans-Bold': 'MerriweatherSans-Bold',
        'MerriwthrSans-BoldItalic': 'MerriweatherSans-BoldItalic', 'Inconsolatazi4-Regular': 'Inconsolatazi4-Regular'}

@functools.lru_cache(None)
def font(face):
    t = TTFont(subprocess.run(['kpsewhich', face + '.otf'], capture_output=True, text=True).stdout.strip())
    return t.getGlyphSet(), t.getBestCmap(), t['head'].unitsPerEm

@functools.lru_cache(None)
def ymin(face, c):
    gs, cmap, upm = font(face)
    if ord(c) not in cmap:
        return 0.0
    bp = BoundsPen(gs)
    gs[cmap[ord(c)]].draw(bp)
    return (bp.bounds[1] if bp.bounds else 0) / upm

def near(c, cs):
    return any(all(abs(a - b) < 0.01 for a, b in zip(c, x)) for x in cs)

def blocks(n):
    """the block bodies of page n, top to bottom: an untitled block is drawn as two fills"""
    rs = sorted((dr['rect'] for dr in PDF[n - 1].get_drawings()
                 if dr.get('fill') and dr['rect'].x0 > 1 and dr['rect'].width > 60 and near(dr['fill'], BODY)
                 and dr['rect'].y0 > 13 and dr['rect'].y1 < 262),   # not the head or foot lines
                key=lambda r: r.y0)
    out = []
    for r in rs:
        if out and r.x0 == out[-1][0] and r.y0 < out[-1][3]:
            out[-1] = (out[-1][0], out[-1][1], max(out[-1][2], r.x1), max(out[-1][3], r.y1))
        else:
            out.append((r.x0, r.y0, r.x1, r.y1))
    return out

def depths(n):
    lines = []
    for b in PDF[n - 1].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            for sp in l['spans']:
                face = FACE.get(sp['font'].split('+')[-1])
                for ch in sp['chars']:
                    if ch['c'].strip() and face:
                        lines.append((ch['origin'][1], ch['origin'][0], face, sp['size'], ch['c']))
    out = []
    for x0, y0, x1, y1 in blocks(n):
        inside = [c for c in lines if y0 < c[0] < y1 and x0 < c[1] < x1]
        if not inside:
            out.append(0.0)
            continue
        base = max(c[0] for c in inside)
        last = [c for c in inside if abs(c[0] - base) < 0.5]
        size = max(c[3] for c in last)
        deep = max(max(0.0, -ymin(face, c)) * s for _, _, face, s, c in last)
        g = -ymin(last[0][2], 'g') * size
        out.append(round(deep - g, 2))
    return out
