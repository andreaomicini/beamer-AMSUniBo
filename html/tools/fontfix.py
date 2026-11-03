#!/usr/bin/env python3
"""Give the private-use glyphs of dvisvgm's fonts their real characters too.

dvisvgm cannot map some glyph names to Unicode (old-style figures 'two.osf', small caps …) and gives
them U+E000 + their code in the font: the page looks right, but copied, searched or read aloud,
"2022" is four private-use characters. For each such glyph whose base character (code − 0xE000) is
printable and not already taken in that font, the cmap gets the base character as well, pointing to
the same glyph; the text can then use the real character.

Run with Homebrew's fonttools interpreter (it has brotli, for WOFF2):
  /opt/homebrew/opt/fonttools/libexec/bin/python3 -I fontfix.py < in.json > out.json
in: {"family": "data:...;base64,<woff2>"}; out: {"family": {"data": "...", "cps": [private code points]}}
"""
import base64, io, json, sys
from fontTools.ttLib import TTFont

out = {}
for fam, data in json.load(sys.stdin).items():
    raw = base64.b64decode(data.split(',', 1)[1])
    f = TTFont(io.BytesIO(raw))
    cps = []
    for t in f['cmap'].tables:
        if not t.isUnicode():
            continue
        cmap = t.cmap
        for cp, g in list(cmap.items()):
            base = cp - 0xE000
            if 0xE000 <= cp <= 0xE0FF and 0x20 < base < 0x7F or 0xE000 <= cp <= 0xE0FF and 0xA0 <= base <= 0xFF:
                if base not in cmap:
                    cmap[base] = g
                    cps.append(cp)
    # a drawn glyph of zero width (\\not's slash) is skipped by WebKit when alone in its <text>: one unit of width, harmless since every <text> has its own x
    if 'glyf' in f:
        for g, (w, lsb) in list(f['hmtx'].metrics.items()):
            if w == 0 and f['glyf'][g].numberOfContours:
                f['hmtx'][g] = (1, lsb)
    b = io.BytesIO(); f.flavor = 'woff2'; f.save(b)
    out[fam] = {'data': data.split(',', 1)[0] + ',' + base64.b64encode(b.getvalue()).decode(),
                'cps': sorted(set(cps))}
json.dump(out, sys.stdout)
