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
                if re.fullmatch(r'\s*(<br>\s*)+', h2):   # a \\ alone between two boxes ends their line, no more (C3b)
                    continue
                items.append(('p', h2))

    while True:
        m = next_env(s, i)
        if not m:
            flush_text(s[i:])
            break
        # only top-level environments: skip ones inside a brace group
        env = m.group(1)
        pre, size = s[i:m.start()], ''
        if env in ('verbatim', 'Verbatim', 'semiverbatim'):
            q = re.search(r'\\(tiny|scriptsize|footnotesize|small|normalsize)(?![A-Za-z])\s*$', pre)
            if q:
                pre, size = pre[:q.start()], q.group(1).replace('normalsize', '')
            q = re.search(r'\\fontsize\{([0-9.]+)\}\{([0-9.]+)\}\\selectfont\s*$', pre)   # S2's
            if q:
                pre, size = pre[:q.start()], f'fs:{q.group(1)}:{q.group(2)}'
        # \setbeamerfont{itemize/enumerate body|subbody}{size=\<size>} before a list: its items' sizes
        fonts = dict(re.findall(r'\\setbeamerfont\{itemize/enumerate (body|subbody)\}\{size=\\(\w+)\}%?', pre))
        pre = re.sub(r'\\setbeamerfont\{[^}]*\}\{[^}]*\}%?', '', pre)
        flush_text(pre)
        a, b = find_end(s, m.end(), env)
        inner = s[m.end():a]
        i = b
        h = verbatim_html(inner, ind, size) if env in ('verbatim', 'Verbatim', 'lstlisting') else env_html(env, inner, ind)
        if env == 'semiverbatim' and size and not size.startswith('fs:'):   # the size declared just before it (S5)
            h = h.replace('<pre class="verbatim semi">', f'<pre class="verbatim semi {size}">', 1)
        elif env == 'semiverbatim' and size:   # \fontsize{s}{b}\selectfont before it
            _, a, b = size.split(':')
            h = h.replace('<pre class="verbatim semi">', f'<pre class="verbatim semi" style="font-size: calc({a} * var(--pt)); '
                          f'line-height: calc({b} * var(--pt))">', 1)
        if fonts and env in ('itemize', 'enumerate'):
            cl = ' '.join(f'{"sub" if k == "subbody" else ""}body-{v}' for k, v in fonts.items())
            h = re.sub(r'<(ul|ol)( class="([^"]*)")?', lambda q: f'<{q.group(1)} class="{(q.group(3) + " ") if q.group(3) else ""}{cl}"', h, count=1)
        if env == 'thebibliography':   # each entry an item of its own, for allowframebreaks (C3a)
            items.extend(('raw', l) for l in h.split('\n') if l.strip())
        else:
            items.append(('raw', h))

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

BEGIN = re.compile(r'\\begin\{([a-z]+\*?|Verbatim)\}')
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

TIKZ = [0]   # tikzpictures met so far, in source order

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
    if env in CFG.get('lists', {}):   # a list environment of the deck's own: an itemize with a class (deck.json "lists")
        return re.sub(r'<ul', f'<ul class="{CFG["lists"][env]}"', itemize(inner, ind, 'ul'), count=1)
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
        cov = re.match(r'\s*\\COV ', inner[j:])   # an overlay not shown on this slide
        if cov:
            j += cov.end()
        body, flags = container(inner[j:], ind + T * 2, 'block')
        cls = 'block' + BLOCK_ENVS[env] + ('' if title.strip() else ' notitle') + (' covered' if cov else '')
        bcls = 'block-body' + (' center' if 'center' in flags else '') + (' ' + sz.group(1) if sz else '')
        out = [f'{ind}<div class="{cls}">']
        if title.strip():
            th = C.inline(title).strip()
            md = re.fullmatch(r'\x00disp:(.*)\x00', th, re.S)   # a display for a title: centred
            out.append(f'{ind}{T}<h3 class="block-title{" display" if md else ""}">{md.group(1) if md else th}</h3>')
        out += [f'{ind}{T}<div class="{bcls}">'] + body + [f'{ind}{T}</div>', f'{ind}</div>']
        return '\n'.join(out)
    if env == 'semiverbatim':   # beamer's: typewriter, spaces and lines kept, commands obeyed (overlays too)
        body = inner[1:] if inner.startswith('\n') else inner
        body = body.rstrip(' \t')
        body = body[:-1] if body.endswith('\n') else body
        body = re.sub(r'\\\((.*?)\\\)', r'$\1$', body)   # \(...\) is math (S5)
        body = body.replace(' ', ' ').replace('\n', '\\SVNL{}')
        h = C.inline(body).replace('\x00svnl\x00', '\n')
        return f'{ind}<pre class="verbatim semi">{h}</pre>'
    if env == 'fcbox':   # \fcolorbox around a minipage: a 0.4pt rule, the fill, \fboxsep 3pt; centred as a box
        a, j = read_group(inner, skip_ws(inner, 0))
        b, j = read_group(inner, skip_ws(inner, j))
        body, flags = container(inner[j:], ind + T, 'body')
        return '\n'.join([f'{ind}<div class="fcbox" style="border-color: var(--{a}); background: var(--{b})">'] + body + [f'{ind}</div>'])
    if env == 'sectionbox':   # S2's \sectionframe: the title colours' box, centred lines of the title's size
        h = C.inline(inner).strip()
        return f'{ind}<div class="sectionbox">{h}</div>'
    if env == 'apitable':   # S2's API tables, as the simpA manual has them: heads between double rules,
        # each operation's signatures in typewriter, its description below, a rule between operations
        o, j = read_opt(inner, skip_ws(inner, 0)) if inner.lstrip().startswith('[') else (None, 0)
        fs = re.search(r'\\fontsize\{([0-9.]+)\}\{([0-9.]+)\}', o or '')
        st = f' style="font-size: calc({fs.group(1)} * var(--pt)); line-height: calc({fs.group(2)} * var(--pt))"' if fs else ''
        out, k, body = [f'{ind}<div class="apitable"{st}>'], j, inner
        tok = re.compile(r'\\(apihead|apiop|hline)')
        while True:
            m = tok.search(body, k)
            if not m:
                break
            k = m.end()
            if m.group(1) == 'hline':
                out.append(f'{ind}{T}<div class="aprule"></div>')
                continue
            a, k = read_group(body, skip_ws(body, k))
            if m.group(1) == 'apihead':
                out += [f'{ind}{T}<div class="aprule2"></div>', f'{ind}{T}<p class="apihead">{C.inline(a).strip()}</p>',
                        f'{ind}{T}<div class="aprule2"></div>']
            else:
                b, k = read_group(body, skip_ws(body, k))
                code = '<br>'.join(C.inline(x).strip() for x in a.split('\\newline'))
                out += [f'{ind}{T}<p class="apicode"><code>{code}</code></p>', f'{ind}{T}<p class="apidesc">{C.inline(b).strip()}</p>']
        out += [f'{ind}{T}<div class="aprule"></div>', f'{ind}</div>']
        return '\n'.join(out)
    if env == 'thebibliography':   # beamer's, inside a frame, with the article icons (C3a)
        _, j = read_group(inner, skip_ws(inner, 0))
        out = []   # each entry an element of the body, so allowframebreaks can share them out
        for it in re.split(r'\\bibitem', inner[j:])[1:]:
            key, k = read_group(it, skip_ws(it, 0))
            parts = [C.inline(x).strip() for x in it[k:].split('\\newblock')]
            cls = ['ab-author', 'ab-title'] + ['ab-rest'] * (len(parts) - 2)
            out.append(f'{ind}{T}<p class="artitem" id="cite-{key}">' + ''.join(
                f'<span class="{c}">{x}</span>' for c, x in zip(cls, parts)) + '</p>')
        return '\n'.join(out)
    if env == 'lrbox':   # a box saved for a picture: drawn there, nothing here (S5)
        return ''
    if env == 'list':   # \begin{list}{<label>}{<params>}: an itemize of the deck's own fourth level (S5)
        _, j = read_group(inner, skip_ws(inner, 0))
        _, j = read_group(inner, skip_ws(inner, j))
        return re.sub(r'<ul', '<ul class="four"', itemize(inner[j:], ind, 'ul'), count=1)
    if env == 'definition':   # beamer's: a block titled Definition (<name>), its body upright
        cov = re.match(r'\s*\\COV ', inner)
        if cov:
            inner = inner[cov.end():]
        opt, j = read_opt(inner, skip_ws(inner, 0))
        title = 'Definition' + (f' ({opt})' if opt else '')
        return env_html('block', '{' + title + '}' + ('\\COV ' if cov else '') + inner[j:], ind)
    if env == 'quote':   # beamer's: both margins 2em, no indent, italic in the quote colour
        cov = re.match(r'\s*\\COV ', inner)
        if cov:
            inner = inner[cov.end():]
        body, flags = container(inner, ind + T, 'quote')
        return '\n'.join([f'{ind}<div class="quoteenv{" covered" if cov else ""}">'] + body + [f'{ind}</div>'])
    if env == 'quotation':   # LaTeX's: both margins 2em, each paragraph indented, italic in these decks
        body, flags = container(inner, ind + T, 'quote')
        return '\n'.join([f'{ind}<div class="quotation">'] + body + [f'{ind}</div>'])
    if env == 'indquotation':
        body, flags = container(inner, ind + T, 'quote')
        return '\n'.join([f'{ind}<div class="quote">'] + body + [f'{ind}</div>'])
    if env == 'centering':   # \centering in a group: the paragraph centred, no space around it
        body, flags = container(inner, ind + T, 'center')
        return '\n'.join([f'{ind}<div class="centering">'] + body + [f'{ind}</div>'])
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
    if env == 'table':   # beamer centres a table; a size declared around the tabular sizes it
        s0 = inner.strip()
        m = re.fullmatch(r'\{\s*\\(tiny|scriptsize|footnotesize|small)(?![A-Za-z])(.*)\}', s0, re.S)
        size, s0 = (m.group(1), m.group(2)) if m else ('', s0)
        body, flags = container(s0, ind + T, 'center')
        out = '\n'.join([f'{ind}<div class="table{" " + size if size else ""}">'] + body + [f'{ind}</div>'])
        return out
    if env == 'tabular':
        return tabular(inner, ind)
    if env == 'tikzpicture':   # externalised by externalize.sh in source order: fig-<k>, or deck.json's "figures" name
        k = TIKZ[0]; TIKZ[0] += 1
        figs = CFG.get('figures', [])
        n = figs[k] if k < len(figs) else f'fig-{k}'
        return f'{ind}<img class="figure tikz fig-{n}" data-asset="{n}" alt="ALT-{n}">'
    if env in ('equation*', 'displaymath'):   # unnumbered: a display, as \[ \]
        return ind + C.inline('\\[' + inner + '\\]').strip('\x00').removeprefix('disp:')
    raise ValueError('env ' + env)

def split_cells(s, sep):
    """split a tabular body at top-level \\\\ (sep '\\\\') or & (sep '&'): not in a group, not in math"""
    parts, depth, math, last, i = [], 0, False, 0, 0
    while i < len(s):
        c = s[i]
        if c == '\\':
            if sep == '\\\\' and s.startswith('\\\\', i) and depth == 0 and not math:
                parts.append(s[last:i]); i += 2; last = i
                continue
            i += 2
            continue
        if c == '$':
            math = not math
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        elif c == '&' and sep == '&' and depth == 0 and not math:
            parts.append(s[last:i]); last = i + 1
        i += 1
    parts.append(s[last:])
    return parts

def tabular(inner, ind):
    """a tabular: the column spec's alignments and vertical rules, \\hline (single or double) above or
    below a row, cells through the inline converter"""
    spec, j = read_group(inner, skip_ws(inner, 0))
    cols, vl = [], [0]
    for c in spec.replace(' ', ''):
        if c == '|':
            vl[-1] += 1
        elif c in 'lcr':
            cols.append(c); vl.append(0)
    rows, hl = [], 0
    for r in split_cells(inner[j:], '\\\\'):
        r = re.sub(r'^(\s*\\par\b)+', '', r.strip()).strip()   # a blank line before \hline (C3b)
        top = 0
        while True:
            m = re.match(r'\\hline\s*', r)
            if not m:
                break
            top += 1; r = r[m.end():]
        if rows and top:
            rows[-1]['below'] = top
        if r:
            rows.append(dict(above=top if not rows else 0, cells=split_cells(r, '&'), below=0))
        elif not rows:
            hl = top
    if rows and hl:
        rows[0]['above'] = hl
    out = [f'{ind}<table class="tabular">']
    for k, row in enumerate(rows):
        cls = ([f'hl{row["above"]}'] if row['above'] else []) + ([f'hb{row["below"]}'] if row['below'] else [])
        out.append(f'{ind}{T}<tr{" class=" + chr(34) + " ".join(cls) + chr(34) if cls else ""}>')
        for q, c in enumerate(row['cells'][:len(cols)]):
            cc = [cols[q]] + (['vl'] if vl[q] else []) + (['vr'] if vl[q + 1] else [])
            out.append(f'{ind}{T}{T}<td class="{" ".join(cc)}">{C.inline(c.strip()).strip()}</td>')
        out.append(f'{ind}{T}</tr>')
    out.append(f'{ind}</table>')
    return '\n'.join(out)

def itemize(inner, ind, tag='ul'):
    # \setlength{\itemsep}{<len>} before the first item: the list's own item spacing, plus beamer's 3pt
    # \parsep-free default is replaced; ex is cmss's x-height at 10.95pt
    sep = re.match(r'\s*\\setlength\{\\itemsep\}\{([0-9.]+)(ex|pt|em)\}', inner)
    style = ''
    if sep:
        inner = inner[sep.end():]
        v = float(sep.group(1)) * {'ex': 4.867, 'em': 10.95, 'pt': 1}[sep.group(2)]
        style = f' style="--itemsep: calc({v:g} * var(--pt))"'
    col = re.match(r'\s*\\color\{(\w+)\}', inner)   # \color{c} before the first item: the list's colour (S5)
    if col:
        inner = inner[col.end():]
        style = (style[:-1] + f'; color: var(--{col.group(1)})"') if style else f' style="color: var(--{col.group(1)})"'
    cov = re.match(r'\s*\\COVLIST ', inner)   # \uncover<...>{the list} off this slide
    if cov:
        inner = inner[cov.end():]
    parts = split_top(inner, 'item')
    parts[0] = re.sub(r'\\par\b', '', parts[0])   # a blank line before the first item (C3a)
    assert not parts[0].strip(), parts[0]
    out = [f'{ind}<{tag}{style}{" class=" + chr(34) + "covered" + chr(34) if cov else ""}>']
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
        cov = re.match(r'\s*\\COV ', p[j:])   # an overlay not shown on this slide: kept, invisible
        if cov:
            j += cov.end()
            attr = attr.replace(' class="', ' class="covered ', 1) if ' class="' in attr else attr + ' class="covered"'
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
    # description[<widest label>]: the labels' column as wide as that label, set in a hidden first row
    wide, j = read_opt(inner, skip_ws(inner, 0)) if inner.lstrip().startswith('[') else (None, 0)
    inner = inner[j:]
    parts = split_top(inner, 'item')
    assert not parts[0].strip(), parts[0]
    out = [f'{ind}<dl>'] if wide is None else [
        f'{ind}<dl class="widest">', f'{ind}{T}<div class="ditem sizer"><dt>{C.inline(wide).strip()}</dt><dd></dd></div>']
    for p in parts[1:]:
        lab, j = read_opt(p, 0)
        cov = re.match(r'\s*\\COV ', p[j:])   # an overlay not shown on this slide
        if cov:
            j += cov.end()
        body, flags = container(p[j:], ind + T * 2, 'li')
        dt = f'<dt>{C.inline(lab or "").strip()}</dt>'
        if len(body) == 1:
            out.append(f'{ind}{T}<div class="ditem{" covered" if cov else ""}">{dt}<dd>{body[0].strip()}</dd></div>')
        else:
            out += [f'{ind}{T}<div class="ditem{" covered" if cov else ""}">{dt}<dd>{body[0].strip()}'] + body[1:] + [f'{ind}{T}</dd></div>']
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
            # scale=<f> on a bitmap: its size as pdfTeX takes it, pixels at 72 dpi times f (pdfTeX ignores a
            # PNG's own resolution: CILC 2016's architecture.png, 182 dpi, is 1820px x 0.15 = 273pt in its PDF)
            sc = re.search(r'scale\s*=\s*([0-9.]+)', o or '')
            bm = next((ROOT / (g + e) for e in ('', '.png', '.jpg') if (ROOT / (g + e)).is_file() and (g + e).endswith(('.png', '.jpg'))), None)
            if sc and bm:
                from PIL import Image
                im = Image.open(bm)
                dpi = 72
                st = f' style="width: calc({im.size[0] * 72 / dpi * float(sc.group(1)):.2f} * var(--pt))"'
            return f'\x00img:<img class="figure fig-{n}" data-asset="{n}" alt="ALT-{n}"{st}>\x00', i
        # \resizebox{<f>\textwidth}{!}{\<macro>}: a TikZ picture drawn by a deck macro, named in
        # deck.json's "tikzmacros" (macro -> asset); the width is the fraction of the text width
        if name == '\\resizebox':
            w, i = read_arg(s, i)
            _, i = read_arg(s, i)
            g, i = read_arg(s, i)
            fw = re.fullmatch(r'\s*([0-9.]*)\s*\\(?:text|line)width\s*', w)
            if False:
                k = TIKZ[0]; TIKZ[0] += 1
                figs = CFG.get('figures', [])
                n = figs[k] if k < len(figs) else f'fig-{k}'
                return (f'\x00img:<img class="figure fig-{n}" data-asset="{n}" alt="ALT-{n}" '
                        f'style="width: calc({round(342.295 * float(fw.group(1) or 1), 3)} * var(--pt))">\x00'), i
            mm = re.fullmatch(r'\s*\\(\w+)\s*', g)
            n = CFG.get('tikzmacros', {}).get(mm.group(1)) if mm else None
            fw = re.fullmatch(r'\s*([0-9.]*)\s*\\(?:text|line)width\s*', w)
            if n and fw:
                f = float(fw.group(1) or 1)
                return (f'\x00img:<img class="figure fig-{n}" data-asset="{n}" alt="ALT-{n}" '
                        f'style="width: calc({round(342.295 * f, 3)} * var(--pt))">\x00'), i
        if name == '\\SETBOX':
            n, i = read_arg(s, i)
            k, i = read_arg(s, i)
            CURBOX[n] = int(k)
            return '', i
        if name == '\\usebox':   # the current saved box of that name, inline (S5)
            n, i = read_arg(s, i)
            raw = expand_macros(LRBOX[CURBOX[n.strip().lstrip('\\')]])
            raw = re.sub(r'\\(begin|end)\{varwidth\}(\{[^}]*\})?', '', raw)
            sz = re.search(r'\\(tiny|scriptsize|footnotesize|small)(?![A-Za-z])', raw)
            body, _ = container(raw, '', 'body')
            h = ''.join(body).replace('<pre ', '<span ').replace('</pre>', '</span>')   # a paragraph holds no <pre>
            return f'<span class="usebox{" " + sz.group(1) if sz else ""}">' + h + '</span>', i
        if name == '\\fcolorbox':   # inline: a 0.4pt rule, the fill, \fboxsep 3pt
            a, i = read_arg(s, i)
            b, i = read_arg(s, i)
            g, i = read_arg(s, i)
            return f'<span class="fcboxi" style="border-color: var(--{a}); background: var(--{b})">{C.inline(g)}</span>', i
        if name == '\\makebox':   # \makebox[<w>][l]{...}: a box that wide
            o, i = read_opt(s, i)
            _, i = read_opt(s, i)
            g, i = read_arg(s, i)
            fw = re.fullmatch(r'\s*([0-9.]*)\s*\\(?:text|line)width\s*', o or '')
            st = f' style="width: calc({342.295 * float(fw.group(1) or 1):.2f} * var(--pt))"' if fw else ''
            return f'<span class="makebox"{st}>{C.inline(g)}</span>', i
        if name == '\\raisebox':   # the raise is left to the corrections
            _, i = read_arg(s, i)
            g, i = read_arg(s, i)
            return C.inline(g), i
        if name in ('\\hspace', '\\hspace*'):
            g, i = read_arg(s, i)
            m = re.fullmatch(r'\s*([0-9.]+)\s*(em|pt|cm|mm)\s*', g)
            v = float(m.group(1)) * {'em': 10.95, 'pt': 1, 'cm': 28.4528, 'mm': 2.84528}[m.group(2)] if m else 0
            return f'<span class="hspace" style="width: calc({v:.2f} * var(--pt))"></span>', i
        if name == '\\structure':   # beamer's structure colour: owblue
            g, i = read_arg(s, i)
            return f'<span class="structure">{C.inline(g)}</span>', i
        if name == '\\tikz':   # \tikz ...; : an externalised picture of its own, in source order (S2)
            d, k = 0, i
            while k < len(s) and not (s[k] == ';' and d == 0):
                d += {'{': 1, '}': -1}.get(s[k], 0)
                k += 1
            n = TIKZ[0]; TIKZ[0] += 1
            figs = CFG.get('figures', [])
            nm = figs[n] if n < len(figs) else f'fig-{n}'
            return f'\x00img:<img class="figure tikz fig-{nm}" data-asset="{nm}" alt="ALT-{nm}">\x00', k + 1
        if name == '\\TIKZW':   # a tikzpicture that \resizebox scaled to a width or a height: its asset, so sized
            w, i = read_arg(s, i)
            hh, i = read_arg(s, i)
            fw = re.fullmatch(r'\s*([0-9.]*)\s*\\(?:text|line)width\s*', w)
            fh = re.fullmatch(r'\s*([0-9.]+)\s*(cm|mm|pt)\s*', hh)
            k = TIKZ[0]; TIKZ[0] += 1
            figs = CFG.get('figures', [])
            n = figs[k] if k < len(figs) else f'fig-{k}'
            st = f' style="width: calc({round(342.295 * float(fw.group(1) or 1), 3)} * var(--pt))"' if fw else ''
            if fw and '\\linewidth' in w:   # \linewidth: the box it sits in, a column's in columns (S5)
                st = f' style="width: {float(fw.group(1) or 1) * 100:g}%"'
            if not fw and fh:
                st = f' style="height: calc({float(fh.group(1)) * {"cm": 28.4528, "mm": 2.84528, "pt": 1}[fh.group(2)]:.2f} * var(--pt)); width: auto"'
            return f'\x00img:<img class="figure fig-{n}" data-asset="{n}" alt="ALT-{n}"{st}>\x00', i
        if name == '\\pgfuseimage':   # \pgfdeclareimage[height=<h>]{name}{file}: the file, inline, that tall
            g, i = read_arg(s, i)
            f, h = PGFIMAGES.get(g, (g, None))
            n = f.split('/')[-1]
            st = f' style="height: calc({h:g} * var(--pt))"' if h else ''
            return f'<img class="pgfimage" data-asset="{n}" alt="ALT-{n}"{st}>', i
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

VERBATIM = []   # the bodies of verbatim and Verbatim, taken out before anything parses the source
VERB = re.compile(r'\\begin\{(verbatim|Verbatim)\}(\[[^\]\n]*\])?(.*?)\\end\{\1\}', re.S)

LST = re.compile(r'\\begin\{lstlisting\}(\[(?:[^\[\]]|\[[^\]]*\])*\])?(.*?)\\end\{lstlisting\}', re.S)

def keep_verbatim(src):
    def put(m):
        VERBATIM.append((m.group(1), m.group(2) or '', m.group(3)))
        return '\\begin{%s}%d\\end{%s}' % (m.group(1), len(VERBATIM) - 1, m.group(1))
    def putl(m):   # an inline lstlisting, its options spanning lines (S1)
        VERBATIM.append(('lstlisting', m.group(1) or '', m.group(2)))
        return '\\begin{lstlisting}%d\\end{lstlisting}' % (len(VERBATIM) - 1)
    return LST.sub(putl, VERB.sub(put, src))

LSTSET = {}   # the deck's \lstset: basicstyle and its moredelim=**[is][<style>]{a}{b}

def lst_html(opt, body, ind):
    """an lstlisting as listings sets it with columns=fixed in a monospaced face: Courier (the deck's
    \\codefont, pcr) as TeX Gyre Cursor, every character 0.6em; the deck's delimiters for colour and bold"""
    o = opt.strip('[]')
    bs = re.search(r'basicstyle=([^,]*(?:\{[^}]*\}[^,]*)*)', o)
    bs = bs.group(1) if bs else LSTSET.get('basicstyle', '')
    size = re.search(r'\\(tiny|scriptsize|footnotesize|small|normalsize)', bs)
    fs = re.search(r'\\fontsize\{([0-9.]+)\}\{([0-9.]+)\}', bs)
    style = ''
    if fs:
        style += f'font-size: calc({fs.group(1)} * var(--pt)); line-height: calc({fs.group(2)} * var(--pt)); '
    fr = 'frame=single' in o
    def mm(k):
        m = re.search(k + r'=([0-9.]+)(mm|pt)', o)
        return float(m.group(1)) * (2.84528 if m.group(2) == 'mm' else 1) if m else 0.0
    if fr:
        xl, xr, sep = mm('xleftmargin'), mm('xrightmargin'), mm('framesep') or 3
        style += (f'margin-left: calc({xl - sep - 0.4:.2f} * var(--pt)); width: calc({342.295 - xl - xr + 2 * (sep + 0.4):.2f} * var(--pt)); '
                  f'padding: calc({sep:g} * var(--pt)); ')
    body = body[1:] if body.startswith('\n') else body
    body = body.rstrip(' \t')
    body = body[:-1] if body.endswith('\n') else body
    h = esc(body)
    for st, a, b in LSTSET.get('delims', []):
        tag = ('<b>', '</b>') if 'bfseries' in st else (f'<span style="color: var(--{re.search(r"color\{(\w+)\}", st).group(1)})">', '</span>')
        h = re.sub(re.escape(esc(a)) + r'(.*?)' + re.escape(esc(b)), lambda m: tag[0] + m.group(1) + tag[1], h)
    cls = 'lstlisting' + (' ' + size.group(1) if size else '') + (' lst-frame' if fr else '')
    return f'{ind}<pre class="{cls}"' + (f' style="{style.strip()}"' if style else '') + f'>{h}</pre>'

def verbatim_html(env, ind, size):
    """a verbatim body as a <pre>, in its size: cmtt's OT1 slots draw ` and ' as curly quotes; with
    fancyvrb's commandchars, \\(..\\) is math"""
    kind, opt, body = VERBATIM[int(env)]
    if kind == 'lstlisting':
        return lst_html(opt, body, ind)
    body = body[1:] if body.startswith('\n') else body
    body = body.rstrip(' \t')
    body = body[:-1] if body.endswith('\n') else body
    def text(x):
        return esc(x).replace('`', '\u2018').replace("'", '\u2019')
    if kind == 'Verbatim' and 'commandchars' in opt:
        # \(..\) is math, and a command with its group (\textit{...}, S4) is TeX's
        parts = re.split(r'(\\\(.*?\\\)|\\[A-Za-z]+\{[^{}\n]*\})', body)
        unesc = lambda q: text(re.sub(r'\\([{}\\])', r'\1', q))   # \{ \} \\ are the characters themselves
        h = ''.join(C.inline('$' + q[2:-2] + '$') if q.startswith('\\(') else C.inline(q) if re.match(r'\\[A-Za-z]', q) else unesc(q)
                    for q in parts)
    else:
        h = text(body)
    cls, style = [], ''
    if kind == 'Verbatim':   # fancyvrb: the deck's \fvset, then this one's options
        fv = dict(FVSET)
        fv.update(fv_options(opt.strip('[]')))
        if fv.get('fontsize'):
            size = fv['fontsize'].lstrip('\\').replace('normalsize', '')
        if fv.get('frame') == 'single':
            cls.append('fv-frame')
        m = re.fullmatch(r'([0-9.]+)(em|pt)', fv.get('xleftmargin', ''))
        if m:
            style = f' style="margin-left: calc({float(m.group(1)) * (10.95 if m.group(2) == "em" else 1):g} * var(--pt))"'
    if size.startswith('fs:'):   # \fontsize{s}{b}\selectfont before it
        _, a, b = size.split(':')
        style, size = f' style="font-size: calc({a} * var(--pt)); line-height: calc({b} * var(--pt))"', ''
    cl = ' '.join([size] + cls if size else cls)
    return f'{ind}<pre class="verbatim{" " + cl if cl else ""}"{style}>{h}</pre>'

LRBOX, CURBOX = [], {}   # the saved boxes' contents; each name's current one
PGFIMAGES = {}   # \pgfdeclareimage: name -> (file, height in pt)
FVSET = {}   # fancyvrb's defaults, from the deck's \fvset{...}

def fv_options(o):
    out = {}
    for part in re.split(r',(?![^{]*\})', o):
        if '=' in part:
            k, v = part.split('=', 1)
            out[k.strip()] = v.strip()
    return out

def expand_macros(s):
    """deck.json's "texmacros": {name: [number of arguments, body with #1 #2 ...]}, expanded in the source
    the way TeX does, before anything reads it: macros the deck defines and the converter need not know"""
    defs = CFG.get('texmacros', {})
    if not defs:
        return s
    pat = re.compile(r'\\(' + '|'.join(sorted(map(re.escape, defs), key=len, reverse=True)) + r')(?![A-Za-z])')
    for _ in range(10):   # bodies may use one another
        out, i, changed = [], 0, False
        for m in pat.finditer(s):
            if m.start() < i:
                continue
            n, body = defs[m.group(1)]
            j, args = m.end(), []
            for _a in range(n):
                g, j = read_arg(s, j)
                args.append(g)
            for k, g in enumerate(args, 1):
                body = body.replace('#%d' % k, g)
            if n == 0 and j < len(s) and s[j] == ' ':
                pass
            out.append(s[i:m.start()] + '{' + body + '}' if n else s[i:m.start()] + body + (' ' if re.match(r'[A-Za-z]', s[j:j + 1]) else ''))
            i, changed = j, True
        out.append(s[i:])
        s = ''.join(out)
        if not changed:
            break
    return s

# ---------------------------------------------------------------- overlays (experiment 8)
OVL = re.compile(r'\\(item|uncover|only|alert|visible|pgfuseimage|footnote|textcolor)(\[[^\]]*\])?\s*<([^>]*)>|\\begin\{(block|alertblock|exampleblock|definition|quote)\}<([^>]*)>')

def _spec(spec, pause):
    """an overlay specification -> (set test, pause after); + is the current pause, then one more"""
    ranges, plus = [], False
    for part in spec.split(','):
        part = part.strip()
        if '+' in part:
            plus = True
            part = part.replace('+', str(pause))
        m = re.fullmatch(r'(\d*)\s*-\s*(\d*)|(\d+)', part)
        if not m:
            continue
        if m.group(3):
            ranges.append((int(m.group(3)), int(m.group(3))))
        else:
            ranges.append((int(m.group(1) or 1), int(m.group(2)) if m.group(2) else None))
    return ranges, pause + (1 if plus else 0)

def overlay_slides(body):
    """beamer's overlays: the frame's text for each of its slides, the parts not shown on a slide
    marked \\COV (covered: invisible, its space kept, as beamer's default) or left out (\\only)"""
    if not OVL.search(body):
        return [body]
    # \uncover<s>{\item ...}: the item's own overlay
    while True:
        m = re.search(r'\\uncover<([^>]*)>(?=\{\s*\\item(?![A-Za-z]))', body)
        if not m:
            break
        g, j = read_group(body, m.end())
        body = body[:m.start()] + '\\item<' + m.group(1) + '>' + g.lstrip()[len('\\item'):] + body[j:]
    pause, n, specs = 1, 1, []
    for m in OVL.finditer(body):
        r, pause = _spec(m.group(3) if m.group(3) is not None else m.group(5), pause)
        specs.append(r)
        for a, b in r:
            n = max(n, a, b or 0)
    ms = list(OVL.finditer(body))

    def render(lo, hi, k):
        # the text from lo to hi for slide k; an overlay's group is rendered the same way, so overlays
        # nested in it (C7's \alert<4>{... \uncover<5->{...}}) take their own specifications
        out, i, q = [], lo, 0
        while q < len(ms):
            m, r = ms[q], specs[q]
            if m.start() < i or m.start() >= hi:
                q += 1
                continue
            on = any(a <= k and (b is None or k <= b) for a, b in r)
            out.append(body[i:m.start()])
            i = m.end()
            q += 1
            if m.group(4):   # an environment: covered after its title, when it has one
                out.append('\\begin{%s}' % m.group(4))
                if not on and m.group(4) in BLOCK_ENVS:
                    t, j = read_group(body, skip_ws(body, i))
                    out.append(body[i:j] + '\\COV ')
                    i = j
                elif not on:
                    out.append('\\COV ')
                continue
            cmd, lab = m.group(1), m.group(2) or ''
            if cmd == 'item':
                if not lab and body.startswith('[', skip_ws(body, i)):   # \item<spec>[label]: the label first
                    o, j = read_opt(body, skip_ws(body, i))
                    lab, i = '[' + o + ']', j
                out.append('\\item' + lab + (' ' if on else ' \\COV '))
                continue
            if cmd == 'textcolor':   # \textcolor<...>{colour}{text}: the colour on its slides only (S5)
                c, i = read_group(body, skip_ws(body, i))
                g0 = skip_ws(body, i)
                g, j = read_group(body, g0)
                g = render(g0 + 1, j - 1, k)
                i = j
                out.append(('\\textcolor{' + c + '}{' + g + '}') if on else ('\\NOALERT{' + g + '}'))
                continue
            g0 = skip_ws(body, i)
            g, j = read_group(body, g0)
            g = render(g0 + 1, j - 1, k)
            i = j
            if cmd == 'footnote':   # \footnote<...>{text}: the mark always, the text on its slides
                out.append(('\\footnote{' if on else '\\FOOTNOTECOV{') + g + '}')
                continue
            if cmd == 'pgfuseimage':   # \pgfuseimage<...>{name}: the picture uncovered
                cmd, g = 'uncover', '\\pgfuseimage{' + g + '}'
            lst = re.fullmatch(r'\s*\\begin\{(itemize|enumerate|description)\}(.*)\\end\{\1\}\s*', g, re.S)
            if cmd in ('uncover', 'visible') and lst:   # a whole list: the list itself covered or not
                out.append('\\begin{%s}%s%s\\end{%s}' % (lst.group(1), '' if on else '\\COVLIST ', lst.group(2), lst.group(1)))
            elif cmd in ('uncover', 'visible'):
                out.append('\\SHOWSPAN{' + g + '}' if on else '\\COVSPAN{' + g + '}')   # a span either way
            elif cmd == 'only':
                out.append(('{' + g + '}' if '\\begin{' not in g else g) if on else '')
            elif cmd == 'alert':
                out.append('\\alert{' + g + '}' if on else '\\NOALERT{' + g + '}')   # a span either way
        out.append(body[i:hi])
        return ''.join(out)

    return [render(0, len(body), k) for k in range(1, n + 1)]

def shrinkage(opts):
    """beamer's shrink=<n>: the percentage the frame's content is shrunk by, at least; 0 when absent"""
    for o in opts:
        m = re.fullmatch(r'shrink(?:=(\d+(?:\.\d+)?))?', o)
        if m:
            return float(m.group(1) or 0)
    return 0

def pages():
    raw = keep_verbatim(open(path('tex')).read())
    # semiverbatim keeps % as a character: escaped before the comments go (C7)
    raw = re.sub(r'(\\begin\{semiverbatim\})(.*?)(\\end\{semiverbatim\})',
                 lambda m: m.group(1) + re.sub(r'(?<!\\)%', r'\\%', m.group(2)) + m.group(3), raw, flags=re.S)
    src = strip_comments(raw)
    # thebibliography inside frames (C3a): numbered labels, each environment from 1
    for tb in re.finditer(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}', src, re.S):
        for k, key in enumerate(re.findall(r'\\bibitem(?:\[[^\]]*\])?\{([^}]*)\}', tb.group(0)), 1):
            C.labels.setdefault(key, str(k))
    # a saved box (lrbox): kept aside, put where \usebox uses it in the body; inside a picture it is part of the
    # externalised picture (S5). Box names are reused from frame to frame: \SETBOX marks which one is current
    def lr(m):
        LRBOX.append(m.group(2))
        return '\\SETBOX{%s}{%d}' % (m.group(1), len(LRBOX) - 1)
    src = re.sub(r'\\begin\{lrbox\}\{\\(\w+)\}(.*?)\\end\{lrbox\}', lr, src, flags=re.S)
    # \fcolorbox{<rule>}{<fill>}{\begin{minipage}...\end{minipage}}: an environment of its own (S5)
    s2, i = [], 0
    for m in re.finditer(r'\\fcolorbox\{(\w+)\}\{(\w+)\}\{(?=\s*\\begin\{minipage\})', src):
        if m.start() < i:
            continue
        g, e = read_group(src, m.end() - 1)
        s2.append(src[i:m.start()] + '\\begin{fcbox}{%s}{%s}%s\\end{fcbox}' % (m.group(1), m.group(2), g))
        i = e
    src = ''.join(s2) + src[i:]
    # \resizebox{<w>}{!}{\begin{tikzpicture}...}: the picture is externalised; here only its width (S5)
    def rbox(m):
        _, e = read_group(src, m.end() - 1)
        return None, e
    out, i = [], 0
    for m in re.finditer(r'\\resizebox\*?\{([^{}]*)\}\{([^{}]*)\}\{(?=\s*\\begin\{tikzpicture\})', src):
        if m.start() < i:
            continue
        _, e = read_group(src, m.end() - 1)
        out.append(src[i:m.start()] + '\\TIKZW{' + m.group(1) + '}{' + m.group(2) + '}')
        i = e
    src = ''.join(out) + src[i:]
    # \column{<w>} ...: beamer's command form, as \begin{column}{<w>} ... \end{column} (C5)
    def cols(m):
        parts = re.split(r'\\column(?=\{)', m.group(2))
        out = parts[0]
        for q in parts[1:]:
            w, j = read_group(q, 0)
            out += '\\begin{column}{' + w + '}' + q[j:] + '\\end{column}\n'
        return m.group(1) + out + m.group(3)
    src = re.sub(r'(\\begin\{columns\}(?:\[[^\]]*\])?)(.*?)(\\end\{columns\})',
                 lambda m: cols(m) if '\\column{' in m.group(2) else m.group(0), src, flags=re.S)
    for m in re.finditer(r'\\pgfdeclareimage(?:\[height=([0-9.]+)(cm|pt|mm)\])?\{([^}]*)\}\{([^}]*)\}', src):
        h = float(m.group(1)) * {'cm': 28.4528, 'mm': 2.84528, 'pt': 1}[m.group(2)] if m.group(1) else None
        PGFIMAGES[m.group(3)] = (m.group(4), h)
    ls = re.search(r'\\lstset\{(.*?)\}\s*\n(?=\S)', src[:src.index('\\begin{document}')], re.S)
    if ls:
        bsm = re.search(r'basicstyle=([^,]*)', ls.group(1))
        LSTSET['basicstyle'] = bsm.group(1) if bsm else ''
        LSTSET['delims'] = re.findall(r'moredelim=\*\*\[is\]\[([^\]]*)\]\{(.)\}\{(.)\}', ls.group(1))
    fvs = re.search(r'\\fvset\{(.*)\}\s*$', src[:src.index('\\begin{document}')], re.M)
    if fvs:
        FVSET.update(fv_options(fvs.group(1)))
    for old, new in CFG.get('replace', []):   # deck.json's literal rewrites, for what texmacros cannot say
        src = src.replace(old, new)
    src = expand_macros(src)
    doc = src[src.index('\\begin{document}') + 16:src.index('\\end{document}')]
    subtocs = '\\AtBeginSubsection' in src[:src.index('\\begin{document}')]
    # a contents frame at each section only where the deck asks for one (every deck before experiment 8 did)
    sectocs = '\\AtBeginSection' in src[:src.index('\\begin{document}')] or any(
        '\\AtBeginSection' in f.read_text(errors='replace') for f in (ROOT / 'sty').glob('*.sty'))
    # the sections, and their subsections, for the contents frames
    secs, subs = [], []
    for m in re.finditer(r'\\(sub)?section(\*?)(\[[^]]*\])?\{', doc):
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
    tok = re.compile(r'\\(sub)?section(\*?)(?:\[([^]]*)\])?\{|\\frame(\[[^]]*\])?\{\\(titlepage|tableofcontents)(\[[^]]*\])?\}|\\begin\{frame\}'
                     r'|\\frame(?![A-Za-z])(\[[^]]*\])?\s*(?=\{)'
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
            section = C.inline(m.group(3) if m.group(3) is not None else g)   # the headline takes the short title
            subsection = ''
            subno = 0
            if not m.group(2):
                secno += 1
                if sectocs:
                    out.append(dict(kind='toc', section=section, current=secno, secs=secs, subs=subs))
            continue
        if m.group(5) == 'titlepage':
            out.append(dict(kind='titlepage', section=section, subsection=subsection))
            i = m.end()
            continue
        if m.group(5) == 'tableofcontents':
            out.append(dict(kind='outline', section=section, subsection=subsection, secs=secs, subs=subs))
            i = m.end()
            continue
        # a frame: \begin{frame} ... \end{frame}, or \frame[<opts>]{...} (the course decks of experiment 8)
        if m.group(0).startswith('\\frame'):
            g, b = read_group(doc, m.end())
            fr = (m.group(7) or '') + g
        else:
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
        lead = ''   # a size declared before \frametitle sizes the body, not the title
        q = re.match(r'\\(tiny|scriptsize|footnotesize|small)(?![A-Za-z])\s*(?=\\frametitle)', fr[j:])
        if q:
            lead, j = fr[j:j + q.end()], j + q.end()
        if fr.startswith('\\frametitle', j):
            j += len('\\frametitle')
            ov = re.match(r'\s*<[^>]*>', fr[j:])   # \frametitle<presentation>{...} (C3a)
            if ov:
                j += ov.end()
        if fr[skip_ws(fr, j):skip_ws(fr, j) + 1] == '{':
            title, j = read_group(fr, skip_ws(fr, j))
        else:   # a frame with no title (S2)
            title = ''
        # a body all in one group opened by a size, {\small ...}: that size declared for the body
        wrapped = re.fullmatch(r'\s*\{\s*\\(tiny|scriptsize|footnotesize|small)(?![A-Za-z])(.*)\}\s*', fr[j:], re.S)
        if wrapped:
            fr = fr[:j] + '\\' + wrapped.group(1) + wrapped.group(2)
        elif re.fullmatch(r'\s*\{.*\}\s*', fr[j:], re.S):   # a body all in one plain group (C4a): the group dropped
            g0 = skip_ws(fr, j)
            g, e = read_group(fr, g0)
            if not fr[e:].strip():
                fr = fr[:j] + g
        fr = fr[:j] + lead + fr[j:]
        opts = [o.strip() for o in (opts or '').split(',')]
        nonum = 'noframenumbering' in opts or nonumber
        broken = 'allowframebreaks' in opts
        parts = split_top(fr[j:], 'framebreak') if broken else overlay_slides(fr[j:])
        roman = 0
        for k, part in enumerate(parts):
            C.reset()
            part = re.sub(r'^\{\}', '', part.strip())
            if '\\bibliography{' in part:
                # the size declared anywhere before \bibliography (after \bibliographystyle in experiment 4);
                # none at all is \normalsize (experiment 8)
                sz = re.search(r'\\(tiny|scriptsize|footnotesize|small)(?![A-Za-z])', part[:part.index('\\bibliography{')])
                out.append(dict(kind='bib', section=section, subsection=subsection, title=C.inline(title),
                                nonum=nonum, top='t' in opts, size=sz.group(1) if sz else 'normalsize'))
                continue
            t = C.inline(title)
            # a size declared first, before any text or environment, sizes the whole body (C6's {\footnotesize ...})
            bsize = re.match(r'\s*\\(scriptsize|footnotesize|small)(?![A-Za-z])\s*(?=\S)(?!\\begin\{verbatim\})', part)
            if bsize:
                part = part[bsize.end():]
            body, flags = container(part, T * 2, 'body')
            if C.footnotes:   # at the frame's foot, each after its mark
                body.append(f'{T}{T}<div class="footnotes">' + ''.join(
                    f'<p class="footnote{" covered" if cov else ""}"><sup class="fnmark">{mk}</sup>{h}</p>' for mk, h, cov in C.footnotes) + '</div>')
            if bsize:
                flags.add('size:' + bsize.group(1))
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
                                top='t' in opts, nonum=nonum, shrink=shrinkage(opts), cont=bool(k) and not broken))
    # the frame number of every page: an overlay's later slides share their frame's (experiment 8)
    no = 0
    for p in out:
        if not p.get('cont') and not p.get('nonum'):
            no += 1
        p['frameno'] = no
    return out

if __name__ == '__main__':
    ps = pages()
    print(len(ps), 'pages;', 'unknown:', C.unknown)
    for n, p in enumerate(ps, 1):
        print(n, p['kind'], p.get('title', '')[:60])
