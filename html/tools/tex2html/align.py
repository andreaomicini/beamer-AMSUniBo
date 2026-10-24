"""Copy TeX's line breaks from the PDF into the HTML: align characters, insert <br> where the PDF wraps."""
import re, unicodedata, difflib, html as H
import pymupdf

from deck import path, STYLE

PDF = pymupdf.open(path('pdf'))
BLOCK = {'p', 'div', 'ul', 'ol', 'li', 'dl', 'dt', 'dd', 'h2', 'h3', 'section', 'br', 'img', 'table', 'tr', 'td', 'th'}

def norm(c):
    c = unicodedata.normalize('NFKC', c)
    return c

def pdf_chars(pn, ytop=STYLE['title'], ybot=STYLE['foot'], skip_cite=True):
    out = []
    raw = PDF[pn - 1].get_text('rawdict')
    for b in raw['blocks']:
        for l in b.get('lines', []):
            for sp in l['spans']:
                cite = skip_cite and sp['size'] < 6.2 and sp['color'] == STYLE['cite']
                for ch in sp['chars']:
                    x, y = ch['origin']
                    if y < ytop or y > ybot or cite:
                        continue
                    for c in norm(ch['c']):
                        if c.isspace():
                            continue
                        out.append(dict(c=c, x=x, y=y, x1=ch['bbox'][2], size=sp['size'], color=sp['color'], font=sp['font']))
    return out

def html_chars(h):
    """visible non-space characters of an HTML fragment: (char, start, end, flow); and visible spaces"""
    chars, spaces = [], set()
    i, flow, skip = 0, 0, []
    while i < len(h):
        c = h[i]
        if c == '<':
            j = h.index('>', i)
            tag = h[i + 1:j]
            name = re.match(r'/?([a-z0-9]+)', tag).group(1)
            closing = tag.startswith('/')
            if name in BLOCK or re.search(r'class="bib-', tag):
                flow += 1
            if skip:
                if name == skip[-1][0]:
                    if closing:
                        skip[-1][1] -= 1
                        if skip[-1][1] == 0:
                            skip.pop()
                    elif not tag.endswith('/'):
                        skip[-1][1] += 1
            elif not closing and re.search(r'class="[^"]*\b(ccite)\b', tag):
                skip.append([name, 1])
            lab = re.search(r'data-label="([^"]*)"', tag)
            if lab and not skip:
                # the label is in the PDF's text: keep it in the stream, in a flow of its own
                for cc in lab.group(1):
                    if not cc.isspace():
                        chars.append((cc, j + 1, j + 1, flow))
                flow += 1
            i = j + 1
            continue
        if c == '&':
            j = h.index(';', i)
            ch = H.unescape(h[i:j + 1])
            end = j + 1
        else:
            ch, end = c, i + 1
        if not skip:
            if ch.isspace():
                if ch == ' ' or ch == '\n' or ch == '\t':
                    spaces.add(i)
            else:
                for cc in norm(ch):
                    chars.append((cc, i, end, flow))
        i = end
    return chars, spaces

def newline(a, b):
    return b['y'] > a['y'] + 2.5 and b['x'] < a['x1'] - 1

def add_breaks(h, pn, report=True, **kw):
    """h: the HTML of one page; returns h with <br> where the PDF breaks lines"""
    hc, spaces = html_chars(h)
    pc = pdf_chars(pn, **kw)
    a = ''.join(x[0] for x in hc)
    b = ''.join(x['c'] for x in pc)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    match = {}
    problems = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            for k in range(i2 - i1):
                match[i1 + k] = j1 + k
        else:
            problems.append((op, a[max(0, i1 - 12):i2 + 12], a[i1:i2], b[j1:j2]))
    inserts = []
    for i in range(len(hc) - 1):
        if i not in match or i + 1 not in match:
            continue
        if hc[i][3] != hc[i + 1][3]:
            continue
        p, q = pc[match[i]], pc[match[i + 1]]
        if not newline(p, q):
            continue
        gap = [k for k in range(hc[i][2], hc[i + 1][1]) if k in spaces]
        if gap:
            inserts.append((gap[0], gap[0] + 1, '<br>'))
        else:
            between = b[match[i] + 1:match[i + 1]]
            inserts.append((hc[i][2], hc[i][2], '-<br>' if '-' in between else '<br>'))
    for s, e, t in sorted(inserts, reverse=True):
        h = h[:s] + t + h[e:]
    return h, problems, len(inserts)
