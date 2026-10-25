"""build.py: the deck's page, from its .tex, .bbl and PDF and the inputs in $TEX2HTML_DECK.
Keeps the page's ASSETS block, if there is one: refill it with assets.py."""
import re, json, pathlib
from frames import pages, C, T
from bib import entries
from align import add_breaks, PDF
from deck import CFG, DIR, path, STYLE
from depth import depths

HERE = pathlib.Path(__file__).parent
OUT = path('page')
NUD = json.load(open(DIR / 'nudges.json')) if (DIR / 'nudges.json').exists() else {}

def pt(v):
    return f'calc({v:g} * var(--pt))'

def body_style(n, centred):
    """the frame's shift, in pt, as padding: [c] moves 0.6 of a top padding and 0.4 of a bottom one"""
    s = NUD.get(str(n), {}).get('shift', 0.0)
    if abs(s) < 0.05:
        return ''
    if not centred:
        return f'padding-top: {pt(round(s, 2))}' if s > 0 else f'margin-top: {pt(round(s, 2))}'
    return f'padding-top: {pt(round(s / 0.6, 2))}' if s > 0 else f'padding-bottom: {pt(round(-s / 0.4, 2))}'

TAG = re.compile(r'<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>')
def margins(n, h):
    """the gaps TeX's glue made: margin-top on the k-th element of the body"""
    m = NUD.get(str(n), {}).get('m', {})
    if not m:
        return h
    out, k, last = [], 0, 0
    for t in TAG.finditer(h):
        if str(k) in m:
            st = re.search(r' style="([^"]*)"', t.group(2))
            if st:   # one style attribute: a second one would be ignored
                a = t.start(2) + st.start(1)
                out.append(h[last:a] + f'margin-top: {pt(m[str(k)])}; ')
                last = a
            else:
                out.append(h[last:t.end() - 1] + f' style="margin-top: {pt(m[str(k)])}">')
                last = t.end()
        k += 1
    out.append(h[last:])
    return ''.join(out)

def columns(n, h):
    """each column of the page moved as a whole, by a translate"""
    cs = NUD.get(str(n), {}).get('cols', {})
    if not cs:
        return h
    parts = re.split(r'<div class="column(?=[" ])', h)
    for c, v in cs.items():
        k = int(c) + 1
        if k < len(parts):
            parts[k] = re.sub(r'style="', f'style="translate: 0 {pt(v)}; ', parts[k], count=1)
    return '<div class="column'.join(parts)

def secname(h):
    return re.sub(r'<[^>]+>', '', h)

def titlepage():
    """the title page is the deck's own, written once in titlepage.html"""
    return (DIR / 'titlepage.html').read_text().strip()

def section_open(n, cls, sec, extra='', centred=True, sub=''):
    bst = body_style(n, centred)
    sub = f' data-subsection="{secname(sub)}"' if sub else ''
    return f'<section class="{cls}" data-section="{sec}"{sub}{extra}>', (f' style="{bst}"' if bst else '')

# the contents frames are [c]: their corrections move them as a centred frame's. Pages made before
# experiment 6 corrected them as [t] and keep doing so, unless deck.json says "toc_centred": true
TOCC = CFG.get('toc_centred', False)

def toc(n, p, title=True):
    cls = 'frame toc' + ('' if title else ' outline')
    head, bst = section_open(n, cls, secname(p['section']), centred=TOCC, sub=p.get('subsection', ''))
    out = [head]
    if title:
        out.append(f'{T}<h2 class="frametitle">{CFG["toc_title"]}</h2>')
    out.append(f'{T}<div class="body"{bst}>')
    out.append(f'{T}{T}<ol class="toc">')
    for k, s in enumerate(p['secs'], 1):
        sh = ' class="shaded"' if title and k != p['current'] else ''
        out.append(f'{T}{T}{T}<li{sh}>{s}</li>')
    out += [f'{T}{T}</ol>', f'{T}</div>', '</section>']
    return '\n'.join(out)

def subtoc(n, p):
    """\\AtBeginSubsection's frame: every section shaded, the current one's subsections listed, the
    current subsection shown"""
    head, bst = section_open(n, 'frame toc subtoc', secname(p['section']), centred=TOCC, sub=p['subsection'])
    out = [head, f'{T}<h2 class="frametitle">{CFG["subtoc_title"]}</h2>', f'{T}<div class="body"{bst}>',
           f'{T}{T}<ol class="toc">']
    for k, sct in enumerate(p['secs'], 1):
        if k == p['current'] and p['subs'][k - 1]:
            out.append(f'{T}{T}{T}<li class="parent"><span class="shade">{sct}</span>')
            out.append(f'{T}{T}{T}{T}<ul class="subtoc">')
            for q, sub in enumerate(p['subs'][k - 1], 1):
                sh = '' if q == p['currentsub'] else ' class="shaded"'
                out.append(f'{T}{T}{T}{T}{T}<li{sh}>{sub}</li>')
            out += [f'{T}{T}{T}{T}</ul>', f'{T}{T}{T}</li>']
        else:
            out.append(f'{T}{T}{T}<li class="shaded">{sct}</li>')
    out += [f'{T}{T}</ol>', f'{T}</div>', '</section>']
    return '\n'.join(out)

SIZEP = re.compile(r'<p>(\s*)<span class="(tiny|scriptsize|footnotesize|small|smaller|large|Large)">(.*)</span>(\s*)</p>')

def quirks(h):
    """TeX quirks that CSS has to be told about"""
    # a paragraph that is all one size: its baselineskip is that size's
    h = SIZEP.sub(lambda m: f'<p class="{m.group(2)}">{m.group(3).strip()}</p>' if '</span>' not in m.group(3) else m.group(0), h)
    # an item that is all one size, declared inside \item: its paragraph's baselineskip is that size's
    h = re.sub(r'<li([^>]*)><span class="(tiny|scriptsize|footnotesize|small|smaller|large|Large)">((?:(?!</?span)[^\n])*'
               r'(?:<span[^>]*>(?:(?!</?span)[^\n])*</span>(?:(?!</?span)[^\n])*)*)</span></li>',
               lambda m: f'<li{m.group(1)} class="{m.group(2)}">{m.group(3)}</li>' if 'class=' not in m.group(1) else m.group(0), h)
    # an item that wraps before its sub-list: the sub-list's font, and so its baselineskip,
    # is already in force when TeX breaks the item's lines
    lines = h.split('\n')
    for i, l in enumerate(lines[:-1]):
        m = re.match(r'(\s*)<li\b([^>]*)>(.*)$', l)
        if m and '<br>' in m.group(3) and re.match(r'<ul[ >]', lines[i + 1].strip()):
            attrs = m.group(2)
            if 'class="' in attrs:
                attrs = attrs.replace('class="', 'class="wrapsub ')
            else:
                attrs += ' class="wrapsub"'
            lines[i] = f'{m.group(1)}<li{attrs}>{m.group(3)}'
    return '\n'.join(lines)

def block_depths(n, h):
    """each block body ends where TeX's last line ends: shallower than a 'g', less padding"""
    ds = depths(n)
    parts = h.split('<div class="block-body')
    if len(parts) - 1 != len(ds):
        print(f'page {n}: {len(parts) - 1} blocks, {len(ds)} in the PDF: depths left alone')
        return h
    out = parts[0]
    for d, rest in zip(ds, parts[1:]):
        if abs(d) >= 0.05:
            q = rest.index('"')
            rest = rest[:q + 1] + f' style="padding-bottom: {pt(round(STYLE["bottom"] + d, 2))}"' + rest[q + 1:]
        out += '<div class="block-body' + rest
    return out

def frame(n, p):
    body = '\n'.join(p['body'])
    body, probs, k = add_breaks(body, n)
    body = quirks(body)
    body = margins(n, body)
    body = columns(n, body)
    body = block_depths(n, body)
    head, bst = section_open(n, 'frame' + (' top' if p['top'] else '') + (' shrink' if p.get('shrink') else ''),
                             secname(p['section']), ' data-noframenumbering' if p['nonum'] else '',
                             centred=not p['top'], sub=p['subsection'])
    cls = 'body' + (' center' if 'center' in p['flags'] else '')
    return '\n'.join([head, f'{T}<h2 class="frametitle">{p["title"]}</h2>', f'{T}<div class="{cls}"{bst}>', body,
                      f'{T}</div>', '</section>'])

def bib_pages(n0, p):
    from align import pdf_chars, html_chars
    import difflib
    es = entries()
    out = []
    # page of each entry: its first character's page in the PDF
    pc = []
    last = len(PDF)   # the bibliography runs to the end of the deck
    for pn in range(n0, last + 1):
        for c in pdf_chars(pn, skip_cite=False):
            c['pn'] = pn
            pc.append(c)
    hc, own = [], []
    for k, (key, h) in enumerate(es):
        cs, _ = html_chars(h)
        hc += [x[0] for x in cs]
        own += [k] * len(cs)
    sm = difflib.SequenceMatcher(None, ''.join(hc), ''.join(c['c'] for c in pc), autojunk=False)
    page = {}
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            for t in range(i2 - i1):
                page.setdefault(own[i1 + t], pc[j1 + t]['pn'])
    from frames import ROMAN
    last = max(page.values())   # frames may follow the bibliography
    for pn in range(n0, last + 1):
        items = [h for k, (key, h) in enumerate(es) if page[k] == pn]
        body = '\n'.join(f'{T}{T}{h}' for h in items)
        body, probs, nb = add_breaks(body, pn, skip_cite=False)
        body = margins(pn, body)
        head, bst = section_open(pn, 'frame' + (' top' if p.get('top', True) else ''), secname(p['section']),
                                 ' data-noframenumbering' if p.get('nonum', True) else '', centred=False)
        out.append('\n'.join([head, f'{T}<h2 class="frametitle">{p["title"]} {ROMAN[pn - n0 + 1]}</h2>',
                              f'{T}<div class="body {p.get("size", "tiny")} refs"{bst}>', body, f'{T}</div>', '</section>']))
    return out

ps = pages()
parts = []
n = 0
for p in ps:
    n += 1
    sep = '<!-- ======================================================================= -->\n'
    if p['kind'] == 'titlepage':
        parts.append(sep + titlepage())
    elif p['kind'] == 'outline':
        parts.append(sep + toc(n, p, title=False))
    elif p['kind'] == 'toc':
        parts.append(sep + toc(n, p))
    elif p['kind'] == 'subtoc':
        parts.append(sep + subtoc(n, p))
    elif p['kind'] == 'frame':
        parts.append(frame(n, p))
    elif p['kind'] == 'bib':
        bp = bib_pages(n, p)
        parts.append(sep + bp[0])
        parts += bp[1:]
        n += len(bp) - 1
frames_html = '\n\n'.join(parts)
ALT = CFG.get('alt', {})
for k, v in ALT.items():
    frames_html = frames_html.replace(f'alt="ALT-{k}"', f'alt="{v}"')
assert 'ALT-' not in frames_html

theme = (HERE / STYLE['theme']).read_text()
deck_css = (DIR / 'deck.css').read_text()
script = (HERE / 'script.js').read_text()
comment = '\n'.join('  ' + l if l else '' for l in CFG['comment'])
sh = CFG['short']
STYLEATTR = f' data-style="{CFG["style"]}"' if CFG.get('style', 'AMSUniBo') != 'AMSUniBo' else ''
html = f'''<!doctype html>
<!--
{comment}
  Keys: → ← space, PgUp PgDn, Home End; f full screen. #n opens page n.
-->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{CFG['title']}</title>
<meta name="author" content="{CFG['author']}">
<meta name="description" content="{CFG['description']}">
<style>
{theme}</style>
</head>
<body>
<main class="deck"{STYLEATTR}
	data-width="{CFG['width']}"
	data-height="{CFG['height']}"
	data-shortauthor="{sh['author']}"
	data-shortinstitute="{sh['institute']}"
	data-shorttitle="{sh['title']}"
	data-shortdate="{sh['date']}"
	data-totalframes="{CFG['totalframes']}">

{frames_html}

</main>

<style>
{deck_css}</style>

<script>
{script}</script>

<!-- ASSETS -->
<!-- /ASSETS -->
</body>
</html>
'''
if OUT.exists():
    m = re.search(r'<!-- ASSETS -->.*?<!-- /ASSETS -->', OUT.read_text(), re.S)
    if m:
        html = html.replace('<!-- ASSETS -->\n<!-- /ASSETS -->', m.group(0))
OUT.write_text(html)
print(OUT, len(html) // 1024, 'KB', 'unknown TeX:', ' '.join(sorted(C.unknown)) or 'none')
