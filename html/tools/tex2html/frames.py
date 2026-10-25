"""The deck's .tex -> a list of pages, each the HTML of one PDF page (no line breaks yet)."""
import re
from latex import *

C = Conv()
T = '\t'

def paragraphs(h):
    """inline HTML with \\x00markers\\x00 and \\n\\n paragraph breaks -> list of ('p'|'skip'|..., html)"""
    out = []
    for part in re.split(r'(\x00[a-z]+(?::[^\x00]*)?\x00|\n\n)', h):
        if part is None:
            continue
        if part.startswith('\x00'):
            out.append(('mark', part.strip('\x00')))
        elif part == '\n\n':
            out.append(('par', ''))
        elif part.strip():
            out.append(('p', part.strip()))
    return out

def visible(h):
    return re.sub(r'<[^>]*>|\x00[^\x00]*\x00', '', h).strip()

def balanced(h):
    """every tag opened in h closed in it: \\hfill was not inside a group"""
    return len(re.findall(r'<(?!/|br)[a-z]', h)) == len(re.findall(r'</', h))

def hfills(h):
    """\\hfill in a paragraph of its own: an empty line; between two pieces of a paragraph: the line
    spread from margin to margin. Any other \\hfill is left to the caller"""
    if '\x00hfill\x00' not in h:
        return h
    paras = re.split(r'(\n\n)', h)
    if len(paras) == 1 and not re.search(r'\S\s*\x00hfill\x00\s*\S', h.replace('\x00hfill\x00', '\x00hfill\x00', 1)):
        return h
    out = []
    for q in paras:
        segs = [x.strip() for x in q.split('\x00hfill\x00')]
        if q == '\n\n' or len(segs) == 1:
            out.append(q)
        elif not any(segs) and len(paras) > 1:
            out.append('\x00disp:<div class="emptyline"></div>\x00')
        elif len([x for x in segs if visible(x)]) > 1 and visible(segs[0]) and all(balanced(x) for x in segs):
            marks = re.findall(r'\x00[^\x00]*\x00', q)   # what else the paragraph holds follows it
            segs = [re.sub(r'\x00[^\x00]*\x00', '', x).strip() for x in segs]
            out.append('\x00disp:<p class="spread">' + ''.join(f'<span>{x}</span>' for x in segs if x) + '</p>\x00'
                       + ''.join(m for m in marks if m != '\x00hfill\x00'))
        else:
            out.append(q)
    return ''.join(out)

def container(s, ind, mode='body'):
    """the block content of s -> list of HTML lines; mode: body | li | block | quote | center"""
    s = re.sub(r'\n[ \t]*\n', r'\\par ', s)
    items, i, buf = [], 0, ''
    flags = set()

    def flush_text(t):
        h0 = C.inline(t)
        h0 = hfills(h0)
        if '\x00hfill\x00' in h0:
            flags.add('hfill')
            h0 = h0.replace('\x00hfill\x00', '')
        for kind, h in paragraphs(h0):
            if kind == 'mark':
                if h in ('medskip', 'smallskip', 'bigskip', 'vfill'):
                    items.append(('raw', f'<div class="{h}"></div>'))
                elif h in ('centering',):
                    flags.add('center')
                elif h == 'hfill':
                    flags.add('hfill')
                elif h.startswith('img:') or h.startswith('disp:'):
                    items.append(('raw', h[h.index(':') + 1:]))
                elif h.startswith('vspace:'):
                    items.append(('raw', f'<div class="vspace" style="--v: {h[7:]}"></div>'))
                elif h.startswith('counter:'):
                    flags.add(h)
            elif kind == 'p':
                h2 = h.replace('\x00hfill\x00', '')
                items.append(('p', h2))

    while True:
        m = next_env(s, i)
        if not m:
            flush_text(s[i:])
            break
        # only top-level environments: skip ones inside a brace group
        flush_text(s[i:m.start()])
        env = m.group(1)
        a, b = find_end(s, m.end(), env)
        inner = s[m.end():a]
        i = b
        items.append(('raw', env_html(env, inner, ind)))

    # side by side: consecutive minipages are one line of boxes
    grouped = []
    for kind, h in items:
        if kind == 'raw' and h.lstrip().startswith('<div class="minipage"'):
            if grouped and grouped[-1][0] == 'minipages':
                grouped[-1][1].append(h)
            else:
                grouped.append(('minipages', [h]))
        else:
            grouped.append((kind, h))
    items = [('raw', '\n'.join([f'{ind}<div class="minipages">'] + [T + l for x in h for l in x.split('\n')]
                                + [f'{ind}</div>'])) if kind == 'minipages' else (kind, h) for kind, h in grouped]
    lines = []
    first = True
    for kind, h in items:
        if kind == 'p':
            hf = h.replace('\x00hfill\x00', '')
            if 'hfill' in flags and mode != 'li':
                lines.append(f'{ind}<p class="center">{hf}</p>')
                flags.discard('hfill')
            elif mode == 'li' and first:
                lines.append(f'{ind}{hf}')
            else:
                lines.append(f'{ind}<p>{hf}</p>')
        else:
            lines.append(h if '\n' in h or h.startswith(ind) else ind + h)
        first = False
    return lines, flags

BEGIN = re.compile(r'\\begin\{([a-z]+)\}')
def next_env(s, i):
    """the next \\begin{env} at i or after it that is text, not inside math"""
    while True:
        m = BEGIN.search(s, i)
        if not m:
            return None
        k, inside = i, None
        while k < m.start():
            if s.startswith('\\\\', k) or s.startswith('\\$', k):
                k += 2
            elif s.startswith('\\[', k):
                e = s.find('\\]', k)
                if e > m.start():
                    inside = e + 2
                    break
                k = e + 2
            elif s[k] == '$':
                e = s.find('$', k + 1)
                if e > m.start():
                    inside = e + 1
                    break
                k = e + 1
            else:
                k += 1
        if inside is None:
            return m
        i = inside

def env_html(env, inner, ind):
    if env in ('itemize', 'enumerate'):
        m = re.match(r'\s*\\setcounter\{enumi\}\{(\d+)\}', inner)
        if m:
            inner = inner[m.end():]
        # a size declared before the first item sizes the whole list
        sz = re.match(r'\s*\\(tiny|scriptsize|footnotesize|small)(?![A-Za-z])', inner)
        if sz:
            inner = inner[sz.end():]
        h = itemize(inner, ind, 'ol' if env == 'enumerate' else 'ul')
        if m and int(m.group(1)):
            h = h.replace('<ol>', f'<ol style="counter-reset: enum {int(m.group(1))}">', 1)
        if sz:
            h = re.sub(r'<(ul|ol)', lambda q: f'<{q.group(1)} class="{sz.group(1)}"', h, count=1)
        return h
    if env == 'description':
        return description(inner, ind)
    if env == 'minipage':
        w, j = read_group(inner, skip_ws(inner, 0))
        frac = float(w.replace('\\textwidth', '').replace('\\linewidth', '') or 1)
        body, flags = container(inner[j:], ind + T, 'body')
        return '\n'.join([f'{ind}<div class="minipage" style="width: calc({frac:g} * 342.295 * var(--pt))">'] + body
                         + [f'{ind}</div>'])
    if env in BLOCK_ENVS:
        title, j = read_group(inner, skip_ws(inner, 0))
        sz = re.match(r'\s*\\(tiny|scriptsize|footnotesize|small)(?![A-Za-z])', inner[j:])
        if sz:   # a size declared first sizes the whole body
            j += sz.end()
        body, flags = container(inner[j:], ind + T * 2, 'block')
        cls = 'block' + BLOCK_ENVS[env] + ('' if title.strip() else ' notitle')
        bcls = 'block-body' + (' center' if 'center' in flags else '') + (' ' + sz.group(1) if sz else '')
        out = [f'{ind}<div class="{cls}">']
        if title.strip():
            th = C.inline(title).strip()
            md = re.fullmatch(r'\x00disp:(.*)\x00', th, re.S)   # a display for a title: centred
            out.append(f'{ind}{T}<h3 class="block-title{" display" if md else ""}">{md.group(1) if md else th}</h3>')
        out += [f'{ind}{T}<div class="{bcls}">'] + body + [f'{ind}{T}</div>', f'{ind}</div>']
        return '\n'.join(out)
    if env == 'indquotation':
        body, flags = container(inner, ind + T, 'quote')
        return '\n'.join([f'{ind}<div class="quote">'] + body + [f'{ind}</div>'])
    if env == 'center':
        body, flags = container(inner, ind + T, 'center')
        return '\n'.join([f'{ind}<div class="center">'] + body + [f'{ind}</div>'])
    if env == 'picturecolumns':
        img, j = read_group(inner, skip_ws(inner, 0))
        name = img.split('/')[-1]
        body, flags = container(inner[j:], ind + T * 2, 'body')
        return '\n'.join([f'{ind}<div class="picturecolumns">',
                          f'{ind}{T}<img class="figure fig-{name}" data-asset="{name}" alt="ALT-{name}">',
                          f'{ind}{T}<div class="pc-text">'] + body + [f'{ind}{T}</div>', f'{ind}</div>'])
    if env == 'figure':
        _, j = read_opt(inner, 0)
        label = 'Figure'
        m = re.search(r'\\renewcommand\{\\figurename\}\{([^}]*)\}', inner)
        if m:
            label = m.group(1)
        inner = re.sub(r'\\(re)?newcommand\{\\\w+\}\{[^}]*\}', '', inner[j:])
        cap = ''
        m = re.search(r'\\caption\{', inner)
        if m:
            g, k = read_group(inner, m.end() - 1)
            cap = f'{ind}{T}<p class="caption"><span class="caption-label">{label}:</span> {C.inline(g).strip()}</p>'
            inner = inner[:m.start()] + inner[k:]
        body, flags = container(inner, ind + T, 'center')
        return '\n'.join([f'{ind}<div class="figure">'] + body + ([cap] if cap else []) + [f'{ind}</div>'])
    if env == 'columns':
        opt, j = read_opt(inner, 0)
        cols = []
        k = j
        while True:
            m = re.compile(r'\\begin\{column\}').search(inner, k)
            if not m:
                break
            a, b = find_end(inner, m.end(), 'column')
            w, q = read_group(inner, skip_ws(inner, m.end()))
            frac = float(w.replace('\\textwidth', '').replace('\\linewidth', '') or 1)
            body, flags = container(inner[q:a], ind + T * 2, 'body')
            c2 = ' center' if 'center' in flags else ''
            if cols:   # beamer's \hfill after the column before, and one more for each \hfill in the source
                fills = 1 + len(re.findall(r'\\hfill', inner[k:m.start()]))
                cols += [f'{ind}{T}<div class="fill"></div>'] * fills
            cols.append('\n'.join([f'{ind}{T}<div class="column{c2}" style="--w: {frac:g}">'] + body + [f'{ind}{T}</div>']))
            k = b
        al = ' top' if opt and 't' in opt else ''
        return '\n'.join([f'{ind}<div class="columns{al}">'] + cols + [f'{ind}</div>'])
    if env == 'multicols':
        n, j = read_group(inner, skip_ws(inner, 0))
        body, flags = container(inner[j:], ind + T, 'body')
        return '\n'.join([f'{ind}<div class="multicols" style="--cols: {n}">'] + body + [f'{ind}</div>'])
    raise ValueError('env ' + env)

def itemize(inner, ind, tag='ul'):
    parts = split_top(inner, 'item')
    assert not parts[0].strip(), parts[0]
    out = [f'{ind}<{tag}>']
    for p in parts[1:]:
        lab, j = read_opt(p, 0)
        attr = ''
        if lab is not None:
            small = '\\footnotesize' in lab
            text = re.sub(r'<[^>]+>', '', C.inline(lab)).strip()
            cl = ['lbl-small'] if small else []
            if 'class="btc"' in C.inline(lab):
                cl.append('lbl-btc')
            attr = f' data-label="{text}"' + (f' class="{" ".join(cl)}"' if cl else '')
        body, flags = container(p[j:], ind + T * 2, 'li')
        tall = re.search(r'class="cases" style="--rows: (\d+)"', body[0])
        if tall:   # cases in the item's first line: the line is taller, its baseline lower
            attr += f' style="--tall: {tall.group(1)}"'
        if len(body) == 1 and not re.match(r'<(p|div|ul|img)[ >]', body[0].strip()):
            out.append(f'{ind}{T}<li{attr}>{body[0].strip()}</li>')
        else:
            first = body[0].strip()
            rest = body[1:]
            if re.match(r'<(p|div|ul|img)[ >]', first):
                out.append(f'{ind}{T}<li{attr}>')
                rest = body
            else:
                out.append(f'{ind}{T}<li{attr}>{first}')
            out += rest + [f'{ind}{T}</li>']
    out.append(f'{ind}</{tag}>')
    return '\n'.join(out)

def description(inner, ind):
    parts = split_top(inner, 'item')
    assert not parts[0].strip(), parts[0]
    out = [f'{ind}<dl>']
    for p in parts[1:]:
        lab, j = read_opt(p, 0)
        body, flags = container(p[j:], ind + T * 2, 'li')
        dt = f'<dt>{C.inline(lab or "").strip()}</dt>'
        if len(body) == 1:
            out.append(f'{ind}{T}<div class="ditem">{dt}<dd>{body[0].strip()}</dd></div>')
        else:
            out += [f'{ind}{T}<div class="ditem">{dt}<dd>{body[0].strip()}'] + body[1:] + [f'{ind}{T}</dd></div>']
    out.append(f'{ind}</dl>')
    return '\n'.join(out)

# ---------------------------------------------------------------- the document
def includegraphics_hook():
    orig = C.command
    def command(name, s, i):
        if name == '\\includegraphics':
            o, i = read_opt(s, i)
            g, i = read_arg(s, i)
            n = re.sub(r'\.(png|jpe?g|pdf|svg)$', '', g.split('/')[-1])
            # a width in \linewidth: a share of the box it sits in (a column's, in columns); only PDF
            # pictures take it, the others are sized by their box
            st = ''
            fw = re.search(r'width\s*=\s*([0-9.]*)\s*\\(?:line|text)width', o or '')
            if fw and (ROOT / g).with_suffix('.pdf').exists() and not g.endswith(('.png', '.jpg')):
                st = f' style="width: {float(fw.group(1) or 1) * 100:g}%"'
            return f'\x00img:<img class="figure fig-{n}" data-asset="{n}" alt="ALT-{n}"{st}>\x00', i
        # \resizebox{<f>\textwidth}{!}{\<macro>}: a TikZ picture drawn by a deck macro, named in
        # deck.json's "tikzmacros" (macro -> asset); the width is the fraction of the text width
        if name == '\\resizebox':
            w, i = read_arg(s, i)
            _, i = read_arg(s, i)
            g, i = read_arg(s, i)
            mm = re.fullmatch(r'\s*\\(\w+)\s*', g)
            n = CFG.get('tikzmacros', {}).get(mm.group(1)) if mm else None
            fw = re.fullmatch(r'\s*([0-9.]*)\s*\\(?:text|line)width\s*', w)
            if n and fw:
                f = float(fw.group(1) or 1)
                return (f'\x00img:<img class="figure fig-{n}" data-asset="{n}" alt="ALT-{n}" '
                        f'style="width: calc({round(342.295 * f, 3)} * var(--pt))">\x00'), i
        if name == '\\lstinputlisting':
            from listing import listing
            o, i = read_opt(s, i)
            g, i = read_arg(s, i)
            return '\x00img:' + listing(ROOT / g, o, C.inline) + '\x00', i
        return orig(name, s, i)
    C.command = command
includegraphics_hook()

# ---------------------------------------------------------------- automatic page breaks
def _pdf():
    from align import PDF
    return PDF

def pdf_title(pn):
    """the frame title of PDF page pn, without spaces"""
    from deck import STYLE
    t = ''.join(ch['c'] for b in _pdf()[pn - 1].get_text('rawdict')['blocks'] for l in b.get('lines', [])
                for sp in l['spans'] for ch in sp['chars'] if STYLE['head'] < ch['origin'][1] < STYLE['title'])
    return re.sub(r'\s+', '', t)

def pdf_body(pn):
    """the alphanumeric text of PDF page pn's body"""
    import unicodedata
    from deck import STYLE
    t = ''.join(ch['c'] for b in _pdf()[pn - 1].get_text('rawdict')['blocks'] for l in b.get('lines', [])
                for sp in l['spans'] for ch in sp['chars'] if STYLE['title'] < ch['origin'][1] < STYLE['foot'])
    return re.sub(r'[^0-9A-Za-z]', '', unicodedata.normalize('NFKC', t))

def plain(h):
    import html as H, unicodedata
    h = re.sub(r'data-label="([^"]*)"', lambda m: '>' + m.group(1) + '<', h)
    return re.sub(r'[^0-9A-Za-z]', '', unicodedata.normalize('NFKC', H.unescape(re.sub(r'<[^>]*>', '', h))))

def broken_pages(pn):
    """how many PDF pages, from pn on, an allowframebreaks frame fills: its titles end I, II, III ..."""
    t0 = pdf_title(pn)
    if not t0.endswith('I'):
        return 1
    base, k = t0[:-1], 1
    while pn + k <= len(_pdf()) and pdf_title(pn + k) == base + ROMAN[k + 1]:
        k += 1
    return k

def distribute(items, pn, k):
    """top-level items -> the PDF page (pn .. pn+k-1) each one starts on: TeX broke the frame between them"""
    bodies = [pdf_body(q) for q in range(pn, pn + k)]
    where, cur = [], 0
    for h in items:
        t = plain(h)
        page = None
        for w in (t[:40], t[:16], t[-16:], t[:8]):
            if len(w) >= 4:
                hits = [q for q in range(cur, k) if w in bodies[q]]
                if hits:
                    page = hits[0]
                    break
        if page is not None:
            cur = page
        where.append(page)
    # an item without text (a picture) goes to a page no text item took, else to the page before it
    for a, h in enumerate(items):
        if where[a] is None:
            prev = next((where[b] for b in range(a - 1, -1, -1) if where[b] is not None), 0)
            nxt = next((where[b] for b in range(a + 1, len(items)) if where[b] is not None), k)
            free = [q for q in range(prev + 1, nxt) if q not in where]
            where[a] = free[0] if free else prev
    return where

def pages():
    src = strip_comments(open(path('tex')).read())
    doc = src[src.index('\\begin{document}') + 16:src.index('\\end{document}')]
    subtocs = '\\AtBeginSubsection' in src[:src.index('\\begin{document}')]
    # the sections, and their subsections, for the contents frames
    secs, subs = [], []
    for m in re.finditer(r'\\(sub)?section(\*?)\{', doc):
        g, _ = read_group(doc, m.end() - 1)
        C.reset()
        if m.group(2):
            continue
        if m.group(1):
            if subs:
                subs[-1].append(C.inline(g))
        else:
            secs.append(C.inline(g))
            subs.append([])
    out = []
    section = subsection = ''
    i = 0
    tok = re.compile(r'\\(sub)?section(\*?)\{|\\frame(\[[a-z,]*\])?\{\\(titlepage|tableofcontents)(\[[^]]*\])?\}|\\begin\{frame\}'
                     r'|\\setbeamertemplate\{page number in head/foot\}\{\}')
    nonumber = False
    secno = subno = 0
    while True:
        m = tok.search(doc, i)
        if not m:
            break
        if m.group(0).startswith('\\setbeamertemplate'):
            nonumber = True
            i = m.end()
            continue
        if m.group(0).startswith('\\subsection'):
            g, i = read_group(doc, m.end() - 1)
            C.reset()
            subsection = C.inline(g)
            if not m.group(2):
                subno += 1
                if subtocs:
                    out.append(dict(kind='subtoc', section=section, subsection=subsection, current=secno,
                                    currentsub=subno, secs=secs, subs=subs))
            continue
        if m.group(0).startswith('\\section'):
            g, i = read_group(doc, m.end() - 1)
            C.reset()
            section = C.inline(g)
            subsection = ''
            subno = 0
            if not m.group(2):
                secno += 1
                out.append(dict(kind='toc', section=section, current=secno, secs=secs))
            continue
        if m.group(4) == 'titlepage':
            out.append(dict(kind='titlepage', section=section, subsection=subsection))
            i = m.end()
            continue
        if m.group(4) == 'tableofcontents':
            out.append(dict(kind='outline', section=section, subsection=subsection, secs=secs))
            i = m.end()
            continue
        # a frame
        a, b = find_end(doc, m.end(), 'frame')
        fr = doc[m.end():a]
        i = b
        # an overlay specification: <presentation:0>, <beamer:0> or <0> keeps the frame out of the PDF
        k0 = skip_ws(fr, 0)
        if fr[k0:k0 + 1] == '<':
            spec = fr[k0 + 1:fr.index('>', k0)]
            fr = fr[fr.index('>', k0) + 1:]
            if any(re.fullmatch(r'(?:(?:beamer|presentation):)?0', x.strip()) for x in spec.split('|')):
                continue
        opts, j = read_opt(fr, 0)
        j = skip_ws(fr, j)
        if fr.startswith('\\frametitle', j):
            j += len('\\frametitle')
        title, j = read_group(fr, skip_ws(fr, j))
        opts = (opts or '').split(',')
        nonum = 'noframenumbering' in opts or nonumber
        broken = 'allowframebreaks' in opts
        parts = split_top(fr[j:], 'framebreak') if broken else [fr[j:]]
        roman = 0
        for k, part in enumerate(parts):
            C.reset()
            part = re.sub(r'^\{\}', '', part.strip())
            if '\\bibliography{' in part:
                sz = re.match(r'\s*\\(tiny|scriptsize|footnotesize|small)(?![A-Za-z])', part)
                out.append(dict(kind='bib', section=section, subsection=subsection, title=C.inline(title),
                                nonum=nonum, top='t' in opts, size=sz.group(1) if sz else 'tiny'))
                continue
            t = C.inline(title)
            body, flags = container(part, T * 2, 'body')
            groups = [body]
            if broken:
                pn = len(out) + 1
                n = broken_pages(pn)
                if n > 1:
                    where = distribute(body, pn, n)
                    groups = [[h for h, w in zip(body, where) if w == q] for q in range(n)]
                    groups = [g for g in groups if g] or [body]
            for g in groups:
                roman += 1
                out.append(dict(kind='frame', section=section, subsection=subsection,
                                title=t + (' ' + ROMAN[roman] if broken else ''), body=g, flags=flags,
                                top='t' in opts, nonum=nonum, shrink='shrink' in opts))
    return out

if __name__ == '__main__':
    ps = pages()
    print(len(ps), 'pages;', 'unknown:', C.unknown)
    for n, p in enumerate(ps, 1):
        print(n, p['kind'], p.get('title', '')[:60])
