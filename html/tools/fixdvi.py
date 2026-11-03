#!/usr/bin/env python3
"""Make a Beamer DVI digestible by dvisvgm, working on its text form (dv2dt / dt2dv).

1. Colours inside PGF pictures. Beamer fills its boxes after a plain \\color (beamerbaseboxes:
   \\color{upper.bg}); in DVI that is a 'color push' special, which dvisvgm applies to glyphs only,
   so the path keeps the picture's text colour. Inside a picture each 'color push' therefore also
   opens a raw <g fill stroke> group, closed by its 'color pop'.
2. Unbalanced groups. PGF typesets each picture between 'dvisvgm:bbox lock' and its 'dvisvgm:bbox
   unlock' (\\pgfsys@typesetpicturebox): at the unlock, whatever was opened since the matching lock
   and is still open is closed there. Before that, In some frames PGF's driver leaves a <g> open inside a picture, and dvisvgm
   refuses the page ("missing closing tag(s): </g>"). Every group opened inside a picture belongs
   to it, so they are closed when the picture's own closing </g> arrives (the raw '</g>' that
   \\pgfsys@endpicture emits, followed by 'color pop'); anything still open is closed before eop.

Usage: fixdvi.py <in.dt> <out.dt>   (run with python3 -I); prints what it changed.
"""
import re, sys

src, dst = sys.argv[1], sys.argv[2]
lines = open(src, encoding='latin-1').read().split('\n')
SPEC = re.compile(r"^special(\d) (\d+) '(.*)'$")
PIC = 'stroke-miterlimit="10" transform="translate({?x},{?y})'

def content(l):
    m = SPEC.match(l)
    return m.group(3) if m else None

def make(c):
    n = len(c.encode('latin-1'))
    return f"special{1 if n < 256 else 4} {n} '{c}'"

def hexcolour(spec):
    p = spec.split()
    try:
        if p[0] == 'rgb':
            r, g, b = map(float, p[1:4])
        elif p[0] == 'gray':
            r = g = b = float(p[1])
        elif p[0] == 'cmyk':
            c, m, y, k = map(float, p[1:5])
            r, g, b = (1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k)
        else:
            return None
    except (ValueError, IndexError):
        return None
    return '#%02x%02x%02x' % tuple(round(255 * v) for v in (r, g, b))

out, tags, colours = [], [], []   # tags: 'pic' | 'g' | a dict for a colour group; colours: dict | None
picdepth = []   # per open picture: len(colours) when its 'pic' group opened (its own colour push is the last one)
stats = {'colour': 0, 'closed': 0, 'unlock': 0}
locks = []
specials = [i for i, l in enumerate(lines) if SPEC.match(l)]
nxt = {a: b for a, b in zip(specials, specials[1:])}
page = 0
for i, l in enumerate(lines):
    if l.startswith('bop'):
        tags, colours, locks, picdepth, page = [], [], [], [], page + 1
    if l.startswith('eop') and tags:
        out.append(make('dvisvgm:raw ' + '</g>' * len(tags)))
        stats['closed'] += len(tags); tags = []
    c = content(l)
    if c is None:
        out.append(l); continue
    if c.startswith('color push '):
        hx = hexcolour(c[len('color push '):]) if 'pic' in tags else None
        out.append(l)
        if hx:
            grp = {'open': True}
            tags.append(grp); colours.append(grp)
            out.append(make(f'dvisvgm:raw <g fill="{hx}" stroke="{hx}">'))
            stats['colour'] += 1
        else:
            colours.append(None)
        continue
    if c == 'color pop':
        grp = colours.pop() if colours else None
        if grp and grp['open']:
            while tags:                       # close it, and anything opened inside it
                t = tags.pop()
                out.append(make('dvisvgm:raw </g>'))
                if t is grp:
                    break
                if isinstance(t, dict):
                    t['open'] = False
        out.append(l); continue
    if c == 'dvisvgm:bbox lock':
        locks.append(len(tags)); out.append(l); continue
    if c == 'dvisvgm:bbox unlock' and locks:
        d = locks.pop()
        if len(tags) > d:
            k = 0
            while len(tags) > d:
                t = tags.pop(); k += 1
                if isinstance(t, dict):
                    t['open'] = False
            out.append(make('dvisvgm:raw ' + '</g>' * k)); stats['unlock'] += k
        out.append(l); continue
    if not c.startswith('dvisvgm:raw '):
        out.append(l); continue
    raw = c[len('dvisvgm:raw '):]
    # the picture's own end is a raw '</g>' followed by the 'color pop' of the colour pushed just before it
    # opened; a '</g>' + 'color pop' inside the picture (\textcolor in a node: AMSCesena's \emph) is not, and
    # taking it for the end closed every group of the picture there (SMA-LS 08·09 S1a p. 6, 2026-11-04)
    is_endpic = (raw == '</g>' and i in nxt and content(lines[nxt[i]]) == 'color pop'
                 and (not picdepth or len(colours) <= picdepth[-1]))
    if is_endpic and tags and tags[-1] != 'pic' and 'pic' in tags:
        extra = 0
        while tags and tags[-1] != 'pic':
            t = tags.pop(); extra += 1
            if isinstance(t, dict):
                t['open'] = False
        raw = '</g>' * extra + raw
        stats['closed'] += extra
    # a colour group of ours still open when PGF closes one of its own groups is closed first: in
    # XML, PGF's </g> would otherwise close ours, and every count after it would be off by one
    parts, pos = [], 0
    for m in re.finditer(r'<g\b[^>]*>|</g>', raw):     # a self-closing <g .../> opens nothing
        t = m.group(0)
        if t == '</g>':
            while tags and isinstance(tags[-1], dict):
                parts.append(raw[pos:m.start()] + '</g>'); pos = m.start()
                tags.pop()['open'] = False
                stats['colour_closed'] = stats.get('colour_closed', 0) + 1
            if tags:
                if tags.pop() == 'pic' and picdepth:
                    picdepth.pop()
        elif not t.endswith('/>'):
            ispic = PIC in raw[m.start():m.start() + 120]
            tags.append('pic' if ispic else 'g')
            if ispic:
                picdepth.append(len(colours))
    parts.append(raw[pos:]); raw = ''.join(parts)
    out.append(make('dvisvgm:raw ' + raw))
# a last, plain pass on the result: per page, recount the groups from the raw specials alone; a </g>
# with nothing open is dropped, and what is still open at the end of the page is closed before eop
final, depth, dropped, added = [], 0, 0, 0
for l in out:
    if l.startswith('bop'):
        depth = 0
    if l.startswith('eop') and depth > 0:
        final.append(make('dvisvgm:raw ' + '</g>' * depth)); added += depth; depth = 0
    c = content(l)
    if c is not None and c.startswith('dvisvgm:raw '):
        raw, keep = c[len('dvisvgm:raw '):], []
        pos = 0
        for m in re.finditer(r'<g\b[^>]*>|</g>', raw):
            if m.group(0).endswith('/>'):
                continue
            if m.group(0) == '</g>':
                if depth == 0:
                    keep.append(raw[pos:m.start()]); pos = m.end(); dropped += 1; continue
                depth -= 1
            else:
                depth += 1
        keep.append(raw[pos:])
        l = make('dvisvgm:raw ' + ''.join(keep))
    final.append(l)
out = final
stats['dropped'], stats['added'] = dropped, added
open(dst, 'w', encoding='latin-1').write('\n'.join(out))
print(f"{stats['colour']} colour group(s) added inside pictures, {stats['closed']} open group(s) closed, "
      f"{stats['unlock']} closed at the end of their picture box, "
      f"last pass: {stats['dropped']} stray close(s) dropped, {stats['added']} close(s) added at page ends")
