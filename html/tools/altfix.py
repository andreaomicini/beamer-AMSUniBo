#!/usr/bin/env python3
"""altfix.py <deck.alt> <svg dir> <pages> -- every image a text alternative: role="img" and aria-label on the
group the wrapper put around it. Its alt= key first, else the caption of its figure; an image with neither is
named in a WARNING (its text is then written in the deck's source as alt=). What Beamer's background
templates draw is decoration: aria-hidden."""
import re, sys, html, os
alt_file, d, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
lang = sys.argv[4] if len(sys.argv) > 4 else 'en'
def clean(t):
    t = re.sub(r'\\(%|&|_|#|\$|\{|\})', r'\1', t)
    t = re.sub(r'\\[a-zA-Z@]+\*?\s?', '', t).replace('{', '').replace('}', '').replace('~', ' ')
    t = t.replace('---', '—').replace('--', '–').replace('``', '“').replace("''", '”')
    return re.sub(r'\s+', ' ', t).strip()
imgs, caps = {}, {}
for line in open(alt_file, encoding='utf-8', errors='replace') if os.path.exists(alt_file) else []:
    m = re.match(r'I (\d+) (\d+|D) (.*?) \| ?(.*)$', line.rstrip('\n'))
    if m: imgs[m.group(1)] = (m.group(2), m.group(3), clean(m.group(4))); continue
    m = re.match(r'C (\d+) \| ?(.*)$', line.rstrip('\n'))
    if m and m.group(1) != '0': caps.setdefault(m.group(1), clean(m.group(2)))
missing = []
for p in range(1, n + 1):
    f = os.path.join(d, 'p%d.svg' % p)
    if not os.path.exists(f): continue
    s = open(f, encoding='utf-8').read()
    def put(m):
        fig, name, a = imgs.get(m.group(1), ('0', '?', ''))
        if fig == 'D':
            return "<g class='dvialt' aria-hidden='true'>"
        a = a or caps.get(fig, '')
        if not a:
            missing.append((p, name)); return m.group(0)
        return "<g class='dvialt' role='img' lang='%s' aria-label=\"%s\">" % (lang, html.escape(a, quote=True))
    t = re.sub(r"<g class='dvialt' data-alt='(\d+)'>", put, s)
    # the page is a group of text and pictures, not one picture: its children reach the accessibility tree
    t = re.sub(r'<svg\b(?![^>]*\brole=)', '<svg role="group"', t, count=1)
    if t != s: open(f, 'w', encoding='utf-8').write(t)
for p, name in sorted(set(missing)):
    print('WARNING: no alt and no caption: page %d, %s' % (p, name))
