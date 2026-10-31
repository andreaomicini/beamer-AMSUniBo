#!/usr/bin/env python3
"""Mark the word spaces of a DVI (text form, dv2dt), so that the SVG text gets real space characters.

TeX sets no space glyph: a word space is a move to the right, and dvisvgm places each word by its x
alone, so the text it writes reads "StaticGraph:Agent'sState…" when copied, searched or read aloud.
Here a move right larger than 0.12 of the current font's size (kerns are far smaller), and a move
down after text (a line break), get a raw special '<!--s-->' just after them; svgfix.py turns each
into a space at the end of the text before it, where it changes nothing visible.

Usage: spaces.py <in.dt> <out.dt>   (run with python3 -I); prints how many it marked.
"""
import re, sys

src, dst = sys.argv[1], sys.argv[2]
lines = open(src, encoding='latin-1').read().split('\n')
MARK = "special1 20 'dvisvgm:raw <!--s-->'"
size, font, reg, out, n, after_text = {}, None, {'w': 0, 'x': 0}, [], 0, False
for l in lines:
    out.append(l)
    t = l.split(' ')
    op = t[0]
    if re.match(r'^fd[1-4]$', op):
        size[int(t[1])] = int(t[3]); continue
    m = re.match(r'^(?:fn(\d+)|f[1-4])$', op)
    if m:
        font = int(m.group(1) or t[1]); continue
    if l.startswith('(') or re.match(r'^s[1-4]$', op):
        after_text = True; continue
    if op == 'bop':
        after_text = False; continue
    mv = re.match(r'^([wxr])([0-4])$', op)
    if mv:
        k, w = mv.group(1), mv.group(2)
        v = int(t[1]) if w != '0' else reg.get(k, 0)
        if k in 'wx' and w != '0':
            reg[k] = v
        if after_text and font in size and v > 0.12 * size[font]:
            out.append(MARK); n += 1; after_text = False
        continue
    if re.match(r'^[dyz][0-4]$', op) or op == 'down':
        if after_text:
            out.append(MARK); n += 1; after_text = False
        continue
    if op.startswith('special') and 'dvisvgm:raw' in l:   # a picture; colour changes and links are neutral
        after_text = False
open(dst, 'w', encoding='latin-1').write('\n'.join(out))
print(f'{n} word space(s) marked')
