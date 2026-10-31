#!/usr/bin/env python3
"""Append to a DVI (text form, dv2dt) one page that sets every character the deck uses, font by font.

dvisvgm embeds in each page's SVG a subset of each font with that page's characters only, and the
same font comes back hundreds of times, once per overlay step. Converted on its own, this extra page
yields one subset per font holding every character of the deck, which can stand in for all of them:
dvisvgm maps a glyph to the same code point on every page.

Usage: allglyphs.py <in.dt> <out.dt>   (run with python3 -I); prints the number of the added page.
"""
import re, sys

src, dst = sys.argv[1], sys.argv[2]
lines = open(src, encoding='latin-1').read().split('\n')
used, font, pages, last_bop = {}, None, 0, None
STR = re.compile(r"^\((.*)\)$")
for l in lines:
    if l.startswith('bop'):
        pages += 1; last_bop = l; font = None
    m = re.match(r'^(?:fn(\d+)|f[1-4] (\d+))$', l)
    if m:
        font = int(m.group(1) or m.group(2)); continue
    if font is None:
        continue
    m = STR.match(l)
    if m:
        t, k, chars = m.group(1), 0, []
        while k < len(t):
            if t[k] == '\\' and k + 1 < len(t):
                chars.append(t[k + 1]); k += 2
            else:
                chars.append(t[k]); k += 1
        used.setdefault(font, set()).update(ord(c) for c in chars)
        continue
    m = re.match(r'^[sp][1-4] (\d+)$', l)          # set1/put1 … a character by its code
    if m:
        used.setdefault(font, set()).add(int(m.group(1)))

page = [re.sub(r'^bop( -?\d+)', f'bop {pages + 1}', last_bop)]
for f, codes in sorted(used.items()):
    page.append(f'fn{f}' if f < 64 else f'f1 {f}' if f < 256 else f'f2 {f}')   # fnt1 holds one byte
    for c in sorted(codes):
        page.append(f's1 {c}' if c < 128 else f's1 {c}')
    page.append('d3 -800000')                      # a new line per font; overlaps would not matter
page.append('eop')
k = max(i for i, l in enumerate(lines) if l.startswith('eop'))
lines[k + 1:k + 1] = page
# the postamble counts the pages
lines = [re.sub(r'^(post( -?\d+){7}) \d+$', lambda m: f'{m.group(1)} {pages + 1}', l) for l in lines]
open(dst, 'w', encoding='latin-1').write('\n'.join(lines))
print(pages + 1)
