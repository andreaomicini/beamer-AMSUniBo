#!/usr/bin/env python3
"""Fix what PGF's SVG driver cannot draw in a dvisvgm page of a Beamer deck.

Beamer's block shadow is a black rectangle (beamerbaseboxes: 0bp,-7bp to boxwidth+8bp,boxheight-1bp)
made transparent by a fading; PGF's SVG drivers have no fadings, so it comes out solid black and
hides the block title drawn before it. Here each such rectangle becomes what the fading draws: a
soft shadow below and to the right of the box, drawn before the block so that the box covers it.

Also: a <use> of a <symbol> with a viewBox needs that box's size, or SVG makes it 100% of the
page (dvisvgm puts a repeated picture in a symbol and uses it without a size); and a bitmap linked
by path (graphicx's dvisvgm driver links PNG and JPG) is embedded, so the page stands alone.

Usage: svgfix.py <in.svg> <out.svg> [<dir the DVI was converted in>]   (run with python3 -I)
"""
import re, sys

import base64, os
src, dst = sys.argv[1], sys.argv[2]
base = sys.argv[3] if len(sys.argv) > 3 else '.'
s = open(src, encoding='utf-8').read()
n = 0

def shadow(m):
    global n
    n += 1
    W, H = float(m.group(1)), float(m.group(2))
    bw = W - 8          # \bmb@boxwidth
    # a blurred rectangle a little larger than the box, offset down and right; drawn before the block
    # (see hoist below), so title and body cover it and only its fringe shows
    return (f"<defs><filter id='bsf{n}' filterUnits='userSpaceOnUse' x='-20' y='-20' width='{bw + 48:.3f}' "
            f"height='{H + 40:.3f}'><feGaussianBlur stdDeviation='2.2'/></filter></defs>"
            f"<g><rect x='-1' y='-7' width='{bw + 8:.3f}' height='{H + 1:.3f}' rx='4' "
            f"fill='#000' fill-opacity='.5' filter='url(#bsf{n})'/></g>")

# the colour groups added to the DVI carry a stroke for paths; glyphs must not be outlined by it
s = s.replace('<style type=\'text/css\'>\n<![CDATA[', '<style type=\'text/css\'>\n<![CDATA[\ntext{stroke:none}', 1)
# word spaces marked by spaces.py: a space at the end of the text just before each mark
def space(m):
    return m.group(1) + ' ' + m.group(2)
s = re.sub(r"((?:</tspan>)?)(</text>)\s*<!--s-->", lambda m: ' ' + m.group(1) + m.group(2) if not m.group(1) else m.group(0).replace('</tspan></text>', ' </tspan></text>').replace('<!--s-->', ''), s)
s = s.replace('<!--s-->', '')
# the marks split dvisvgm's text into one element per word: consecutive <text> of the same class on
# the same baseline are joined again, each later one as a <tspan> at its own x
def join(m):
    items = re.findall(r"<text class='([^']+)' x='([^']+)' y='([^']+)'>((?:(?!</?text\b).)*)</text>", m.group(0), re.S)
    out, cur = [], None
    for cls, x, y, body in items:
        if cur and cur[0] == cls and cur[2] == y:
            cur[3].append(f"<tspan x='{x}'>{body}</tspan>" if not body.startswith('<tspan') else
                          re.sub(r"^<tspan", f"<tspan x='{x}'", body, count=1) if " x='" not in body.split('>', 1)[0] else body)
        else:
            if cur: out.append(cur)
            cur = [cls, x, y, [body]]
    if cur: out.append(cur)
    return '\n'.join(f"<text class='{a}' x='{b}' y='{c}'>{''.join(d)}</text>" for a, b, c, d in out)
s = re.sub(r"(?:<text class='[^']+' x='[^']+' y='[^']+'>(?:(?!</?text\b).)*</text>\s*){2,}", join, s, flags=re.S)
s = re.sub(r"<g fill='#000'>\s*<path d='M0-7\.02625H([\d.]+)V([\d.]+)H0Z' stroke='none'/>\s*</g>", shadow, s)
# Beamer draws title, then shadow, then body: the shadow moves before the block's first picture (the
# first one at the same x since the previous block), inside the body picture's transform
SH = re.compile(r"<defs><filter id='bsf\d+'.*?</defs><g><rect [^>]*/></g>")
GR = re.compile(r"<g stroke-miterlimit='10' transform='(translate\(([-\d.]+),[-\d.]+\)scale\([-\d.]+,[-\d.]+\))'>")
floor = 0
while True:
    m = next((k for k in SH.finditer(s) if k.start() > floor), None)
    if not m:
        break
    body = [g for g in GR.finditer(s, 0, m.start())][-1]
    first = next((g for g in GR.finditer(s, floor, body.end()) if g.group(2) == body.group(2)), body)
    ins = f"<g transform='{body.group(1)}'>{m.group(0)}</g>"
    s = s[:m.start()] + s[m.end():]
    s = s[:first.start()] + ins + s[first.start():]
    floor = m.end() + len(ins) - len(m.group(0))
sizes = dict((m.group(1), (m.group(2), m.group(3))) for m in
             re.finditer(r"<symbol id='([^']+)' viewBox='0 0 ([\d.]+) ([\d.]+)'", s))
def sized(m):
    tag, ref = m.group(0), m.group(1)
    if ref in sizes and ' width=' not in tag:
        w, h = sizes[ref]
        return tag.replace('<use ', f"<use width='{w}' height='{h}' ", 1)
    return tag
s = re.sub(r"<use [^>]*xlink:href='#([^']+)'[^>]*/>", sized, s)
def embed(m):
    path = os.path.join(base, m.group(1))
    if not os.path.exists(path):              # named bare, found by TeX's search path: look for it
        for root, _, files in os.walk(base):
            if os.path.basename(m.group(1)) in files:
                path = os.path.join(root, os.path.basename(m.group(1))); break
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'svg': 'image/svg+xml'}.get(ext)
    if not mime or not os.path.exists(path):
        return m.group(0)
    if mime == 'image/svg+xml':               # as text, not base64: gzip can then compress it
        t = open(path, encoding='utf-8').read()
        t = re.sub(r'^<\?xml[^>]*>\s*', '', t).replace('%', '%25').replace('#', '%23').replace("'", '%27').replace('\n', ' ')
        return "xlink:href='data:image/svg+xml;utf8,%s'" % t
    return "xlink:href='data:%s;base64,%s'" % (mime, base64.b64encode(open(path, 'rb').read()).decode())
s = re.sub(r"xlink:href='(?!data:|#|https?:)([^']+\.(?:png|jpe?g|svg))'", embed, s)
# a \\videolink poster: its MP4 found among the sources, named by absolute path for assemble.py
def video(m):
    for root, _, files in os.walk(base):
        if os.path.basename(m.group(1)) in files:
            return f"data-video='{os.path.abspath(os.path.join(root, os.path.basename(m.group(1))))}'"
    return m.group(0)
s = re.sub(r"data-video='([^'/][^']*)'", video, s)
open(dst, 'w', encoding='utf-8').write(s)
print(f'{n} block shadow(s) redrawn')
