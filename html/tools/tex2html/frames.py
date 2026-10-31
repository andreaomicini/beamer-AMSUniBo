"""The deck's .tex -> a list of pages, each the HTML of one PDF page (no line breaks yet)."""
import re
from pathlib import Path
from latex import *
from deck import STYLE

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
        # {\\tiny\\hfill a\\hfill b\\hfill}: the fills inside one size span, at the ends too: spread evenly (M1)
        w = re.fullmatch(r'(\s*(?:\x00[a-z]+\x00\s*)*)<span class="(tiny|scriptsize|footnotesize|small|smaller)">(\s*\x00hfill\x00.*\x00hfill\x00\s*)</span>\s*', q, re.S)
        if w:   # (marks before it, \\medskip say, kept in front)
            pre_, size_, body_ = w.groups()
            inner = [x.strip() for x in body_.split('\x00hfill\x00')]
            if all(balanced(x) for x in inner) and len([x for x in inner if visible(x)]) > 1:
                out.append(pre_ + f'\x00disp:<p class="spread around {size_}">' + ''.join(f'<span>{x}</span>' for x in inner if x) + '</p>\x00')
                continue
        if False:
            inner = [x.strip() for x in w.group(2).split('\x00hfill\x00')]
            if all(balanced(x) for x in inner) and len([x for x in inner if visible(x)]) > 1:
                out.append(f'\x00disp:<p class="spread around {w.group(1)}">' + ''.join(f'<span>{x}</span>' for x in inner if x) + '</p>\x00')
                continue
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

SIZEGROUP = re.compile(r'\{\s*\\(tiny|scriptsize|footnotesize|small)(?![A-Za-z])|\\(tiny|scriptsize|footnotesize|small)\s*(?=\{)')

def item_sizes(s):
    """a size declared at the end of an item's text: TeX's items are no groups, so it holds for the later items of the
    same list too, until a \\normalsize (IAG 26/27's L4: \\item ...\\smaller, then \\item[!] ...; M9's go back)"""
    out, depth, held, i = [], 0, {}, 0
    for m in re.finditer(r'\\(begin|end)\{(?:itemize|enumerate|description)\}|\\item(?:\[[^\]]*\])?'
                         r'|\\(tiny|scriptsize|footnotesize|small|smaller)[ \t]*(?=\n)|\\normalsize(?![A-Za-z])', s):
        out.append(s[i:m.end()])
        i = m.end()
        if m.group(1) == 'begin':
            depth += 1
        elif m.group(1) == 'end':
            held.pop(depth, None)
            depth -= 1
        elif m.group(0).startswith('\\normalsize'):
            held.pop(depth, None)
        elif m.group(2):
            if depth and re.search(r'\\item\b[^\n]*$', s[:m.start()].rsplit('\n', 1)[-1] + ' '):
                held[depth] = m.group(2)
        elif depth in held and not s.startswith(f' \\{held[depth]} ', i):   # once: the frame's body and a block's go through it
            out.append(f' \\{held[depth]} ')
    return ''.join(out) + s[i:]

def size_groups(s):
    """{\\scriptsize ... } around environments, {\\scriptsize{\\begin{verbatim}...\\end{verbatim}}} too: the size
    environment \\begin{scriptsize} ... \\end{scriptsize}, which the container reads as a block (IAG 26/27's L7, M8).
    The closing brace found by skipping the bodies of verbatims, whose braces are not TeX's"""
    out, i = [], 0
    while (m := SIZEGROUP.search(s, i)):
        # {\\size ...}, or \\size{...} (what is left of {\\size{...}} once the frame's own group is taken off)
        size = m.group(1) or m.group(2)
        depth, j = 1, (m.start() if m.group(1) else m.end()) + 1
        while j < len(s) and depth:
            v = re.match(r'\\begin\{(verbatim|Verbatim|lstlisting)\}', s[j:])
            if v:
                j = s.index('\\end{' + v.group(1) + '}', j) + len(v.group(1)) + 6
                continue
            if s[j] == '\\':
                j += 2
                continue
            depth += {'{': 1, '}': -1}.get(s[j], 0)
            j += 1
        inner = s[m.end() + (0 if m.group(1) else 1):j - 1]
        # only around lists and verbatims (L7, M8): a display in a sized group keeps its old reading (blockchain-woa2018)
        if depth or not re.search(r'\\begin\{(verbatim|semiverbatim|itemize|enumerate|description)\}', inner):
            out.append(s[i:m.end()])
            i = m.end()
            continue
        g = re.fullmatch(r'\s*\{(.*)\}\s*', inner, re.S)   # one more group around it all
        out.append(s[i:m.start()] + f'\\begin{{{size}}}' + (g.group(1) if g else inner) + f'\\end{{{size}}}')
        i = j
    return ''.join(out) + s[i:]

def container(s, ind, mode='body'):
    """the block content of s -> list of HTML lines; mode: body | li | block | quote | center"""
    s = size_groups(item_sizes(s))
    s = re.sub(r'\n[ \t]*\n', r'\\par ', s)
    items, i, buf = [], 0, ''
    flags = set()

    def flush_text(t):
        h0 = C.inline(t)
        # a picture then \\quad or \\qquad and text or maths, no other picture: one line, the picture standing on its
        # baseline as TeX sets it (IAG 26/27's M2, an arrow beside a proof tree)
        h0 = re.sub(r'\x00img:<img class="figure (?!tikz)([^>]*)>\x00(\s*<span class="mspace"[^>]*></span>)(?=(?:\s*<span class="mspace"[^>]*></span>)*\s*(?:[^\s\x00<]|<(?!img|br|/|span class="mspace")))',
                    r'<img class="figure inl \1>\2', h0)
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
                elif h == 'framebreak':
                    items.append(('raw', '<!--framebreak-->'))
            elif kind == 'p':
                h2 = h.replace('\x00hfill\x00', '')
                if re.fullmatch(r'\s*(<br>\s*)+', h2) and CFG.get('style') == 'AMSCesena':   # a \\ alone between two boxes
                    # ends their line, no more (C3b); AMSCesena only so far: experiment 6's corrections allow for it
                    continue
                items.append(('p', h2))

    itemfg = None
    while True:
        m = next_env(s, i)
        if not m:
            flush_text(s[i:])
            break
        # only top-level environments: skip ones inside a brace group
        env = m.group(1)
        pre, size, vtopsep = s[i:m.start()], '', None
        if env in ('verbatim', 'Verbatim', 'semiverbatim'):
            # its size, and a \\setlength{\\topsep} after it (\\smaller\\setlength{\\topsep}{2pt}: IAG 26/27's L5)
            q = re.search(r'\\(tiny|scriptsize|footnotesize|small|smaller|normalsize)(?![A-Za-z])\s*(?:\\setlength\{\\topsep\}\{([0-9.]+)pt\})?\s*$', pre)
            if q:
                pre, size = pre[:q.start()], q.group(1).replace('normalsize', '')
                vtopsep = q.group(2)
            q = re.search(r'\\fontsize\{([0-9.]+)\}\{([0-9.]+)\}\\selectfont\s*$', pre)   # S2's
            if q:
                pre, size = pre[:q.start()], f'fs:{q.group(1)}:{q.group(2)}'
        # a size declared just before a list, with nothing after it: the list's (IAG 26/27's \smaller\begin{description})
        lsize = None
        if env in ('itemize', 'enumerate', 'description', 'tabular'):   # a table too (M10's \\tiny\\begin{tabular})
            q = re.search(r'\\(tiny|scriptsize|footnotesize|small|smaller)(?![A-Za-z])\s*$', pre)
            if q:
                pre, lsize = pre[:q.start()], q.group(1)
        # \setbeamercolor{item}{fg=<colour>}: the labels of the lists after it, in this group, take that colour (IAG 26/27)
        q = re.search(r'\\setbeamercolor\{item\}\{fg=(\w+)\}%?', pre)
        if q:
            itemfg = q.group(1)
            pre = pre[:q.start()] + pre[q.end():]
        # \setbeamerfont{itemize/enumerate body|subbody}{size=\<size>} before a list: its items' sizes
        fonts = dict(re.findall(r'\\setbeamerfont\{itemize/enumerate (body|subbody)\}\{size=\\(\w+)\}%?', pre))
        pre = re.sub(r'\\setbeamerfont\{[^}]*\}\{[^}]*\}%?', '', pre)
        flush_text(pre)
        a, b = find_end(s, m.end(), env)
        inner = s[m.end():a]
        i = b
        h = verbatim_html(inner, ind, size) if env in ('verbatim', 'Verbatim', 'lstlisting') else env_html(env, inner, ind)
        if env == 'verbatim' and vtopsep:
            h = h.replace('<pre class="verbatim', f'<pre style="--topsep: calc({vtopsep} * var(--pt))" class="verbatim', 1)
        if env == 'semiverbatim' and size and not size.startswith('fs:'):   # the size declared just before it (S5)
            h = h.replace('<pre class="verbatim semi">', f'<pre class="verbatim semi {size}">', 1)
        elif env == 'semiverbatim' and size:   # \fontsize{s}{b}\selectfont before it
            _, a, b = size.split(':')
            h = h.replace('<pre class="verbatim semi">', f'<pre class="verbatim semi" style="font-size: calc({a} * var(--pt)); '
                          f'line-height: calc({b} * var(--pt))">', 1)
        if lsize:
            h = re.sub(r'<(ul|ol|dl|table)( class="([^"]*)")?', lambda q: f'<{q.group(1)} class="{(q.group(3) + " ") if q.group(3) else ""}{lsize}"', h, count=1)
        if itemfg and env in ('itemize', 'enumerate', 'description'):
            h = re.sub(r'<(ul|ol|dl)(?=[ >])', lambda q: f'<{q.group(1)} data-itemfg', h, count=1)
            h = h.replace(' data-itemfg style="', f' style="--itemfg: var(--{itemfg}); ', 1).replace(
                ' data-itemfg', f' style="--itemfg: var(--{itemfg})"', 1)
        if fonts and env in ('itemize', 'enumerate'):
            cl = ' '.join(f'{"sub" if k == "subbody" else ""}body-{v}' for k, v in fonts.items())
            h = re.sub(r'<(ul|ol)( class="([^"]*)")?', lambda q: f'<{q.group(1)} class="{(q.group(3) + " ") if q.group(3) else ""}{cl}"', h, count=1)
        if env == 'thebibliography' or h.lstrip().startswith('<p class="artitem bibentry'):   # each entry an item of its own, for allowframebreaks (C3a)
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
                # a paragraph that is all one size (\\smaller at its start): the size on the paragraph, whose lines
                # then take its baselines, as TeX's \\baselineskip, not the text's around it (M1's quotation)
                m = re.fullmatch(r'<span class="(tiny|scriptsize|footnotesize|small|smaller)">(.*)</span>', hf.strip(), re.S)
                if m and m.group(2).count('<span') == m.group(2).count('</span>'):
                    lines.append(f'{ind}<p class="{m.group(1)}">{m.group(2).strip()}</p>')
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
    if env == 'minipage':   # [t] or [b]: aligned on its first baseline or its bottom, not centred (C10 of SMA-LS 07/08)
        pos, j = read_opt(inner, 0)
        w, j = read_group(inner, skip_ws(inner, j))
        frac = width_frac(w)
        body, flags = container(inner[j:], ind + T, 'body')
        return '\n'.join([f'{ind}<div class="minipage" style="width: calc({frac:g} * 342.295 * var(--pt)){box_align(pos)}">'] + body
                         + [f'{ind}</div>'])
    if env in ('tiny', 'scriptsize', 'footnotesize', 'small'):   # \begin{small} ... \end{small} (C10 of SMA-LS 07/08)
        body, flags = container(inner, ind + T, 'body')
        return '\n'.join([f'{ind}<div class="{env}">'] + body + [f'{ind}</div>'])
    if env in BLOCK_ENVS:
        title, j = read_group(inner, skip_ws(inner, 0))
        sz = re.match(r'\s*\\(tiny|scriptsize|footnotesize|small|smaller)(?![A-Za-z])', inner[j:])
        if sz:   # a size declared first sizes the whole body (\\smaller too: IAG 26/27's L5)
            j += sz.end()
        cov = re.match(r'\s*\\COV ', inner[j:])   # an overlay not shown on this slide
        if cov:
            j += cov.end()
        th = C.inline(title).strip() if title.strip() else ''   # the title before the body, as TeX reads them: an \\ac there is its first use (M1)
        body, flags = container(inner[j:], ind + T * 2, 'block')
        cls = 'block' + BLOCK_ENVS[env] + ('' if title.strip() else ' notitle') + (' covered' if cov else '')
        bcls = 'block-body' + (' center' if 'center' in flags else '') + (' ' + sz.group(1) if sz else '')
        out = [f'{ind}<div class="{cls}">']
        if title.strip():
            md = re.fullmatch(r'\x00disp:(.*)\x00', th, re.S)   # a display for a title: centred
            gap = ''
            if '\x00hfill\x00' in th:   # \\hfill in a title: what follows at its right end (IAG 26/27's \\labfilebar)
                head, *rest = th.split('\x00hfill\x00')
                # a \\quad after it: the gap between flex items, which a line's ends do not take, as TeX's glue at a
                # break (L6: the second file name wraps to the left of the next line)
                qs = re.compile(r'<span class="mspace" style="--w: ([0-9.]+em)"></span>')
                ws = {w for q in rest for w in qs.findall(q)}
                if len(ws) == 1:
                    gap = f' style="column-gap: {ws.pop()}"'
                th = f'<span>{head.strip()}</span>' + ''.join(
                    '<span class="hfill"></span>' + ''.join(f'<span>{x.strip()}</span>' for x in (qs.split(q)[::2] if gap else [q]))
                    for q in rest)
            out.append(f'{ind}{T}<h3 class="block-title{" display" if md else ""}"{gap}>{md.group(1) if md else th}</h3>')
        out += [f'{ind}{T}<div class="{bcls}">'] + body + [f'{ind}{T}</div>', f'{ind}</div>']
        return '\n'.join(out)
    if env == 'semiverbatim':   # beamer's: typewriter, spaces and lines kept, commands obeyed (overlays too)
        body = inner[1:] if inner.startswith('\n') else inner
        body = body.lstrip(' \t').rstrip(' \t')   # the first line's leading spaces TeX skips (L7: the PDF has none)
        cen = re.match(r'\\centering(?![A-Za-z])\s*', body)   # its lines centred (L7)
        if cen:
            body = body[cen.end():]
        body = body[:-1] if body.endswith('\n') else body
        body = re.sub(r'\\\((.*?)\\\)', r'$\1$', body)   # \(...\) is math (S5)
        body = body.replace('\\\\', '\\textbackslash{}')   # \\ is a backslash there (L7's \\==)
        body = body.replace(' ', ' ').replace('\n', '\\SVNL{}')
        h = C.inline(body).replace('\x00svnl\x00', '\n')
        return f'{ind}<pre class="verbatim semi{" center" if cen else ""}">{h}</pre>'
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
            cpos, q = read_opt(inner, m.end())   # a column's own [t] [c] [b] (C8a of SMA-LS 07/08)
            w, q = read_group(inner, skip_ws(inner, q))
            frac = width_frac(w)
            body, flags = container(inner[q:a], ind + T * 2, 'body')
            c2 = ' center' if 'center' in flags else ''
            if cols:   # beamer's \hfill after the column before, and one more for each \hfill in the source
                fills = 1 + len(re.findall(r'\\hfill', inner[k:m.start()]))
                cols += [f'{ind}{T}<div class="fill"></div>'] * fills
            cols.append('\n'.join([f'{ind}{T}<div class="column{c2}" style="--w: {frac:g}{box_align(cpos)}">'] + body + [f'{ind}{T}</div>']))
            k = b
        os_ = [o.strip() for o in (opt or '').split(',')]   # [t] alone, not the t of onlytextwidth (M1)
        al = (' top' if 't' in os_ else '') + (' onlytextwidth' if 'onlytextwidth' in os_ else '')
        return '\n'.join([f'{ind}<div class="columns{al}">'] + cols + [f'{ind}</div>'])
    if env == 'multicols':
        n, j = read_group(inner, skip_ws(inner, 0))
        body, flags = container(inner[j:], ind + T, 'body')
        return '\n'.join([f'{ind}<div class="multicols" style="--cols: {n}">'] + body + [f'{ind}</div>'])
    if env == 'table':   # beamer centres a table; a size declared around the tabular sizes it
        s0 = re.sub(r'^\s*\[[a-zA-Z!]*\]', '', inner).strip()   # its placement, [h]: nothing on a slide (M6)
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
    if env in ('eqnarray', 'eqnarray*'):   # numbers are not drawn: no deck numbers its displays
        return ind + C.eqnarray(inner)
    if env == 'equation' and re.search(r'\\nonumber(?![A-Za-z])', inner):   # numbered but for \nonumber: as equation* (C10)
        env, inner = 'equation*', re.sub(r'\\nonumber(?![A-Za-z])', '', inner)
    if env in ('equation*', 'displaymath'):   # unnumbered: a display, as \[ \]
        return ind + C.inline('\\[' + inner + '\\]').strip('\x00').removeprefix('disp:')
    raise ValueError('env ' + env)

def box_align(pos):
    """a minipage's or a column's [t] [c] [b] in a flex line: top on the first baseline, as TeX, or bottom"""
    return {'t': '; align-self: baseline', 'b': '; align-self: flex-end', 'c': '; align-self: center'}.get((pos or '').strip(), '')


def width_frac(w):
    """a minipage's or a column's width as a fraction of \\textwidth (342.295pt): <f>\\textwidth, <f>\\linewidth,
    or a length (\\begin{column}{8cm}, C8a of SMA-LS 07/08)"""
    m = re.fullmatch(r'\s*([\d.]+)\s*(cm|mm|pt|in|bp)\s*', w)
    if m:
        return float(m.group(1)) * {'cm': 28.4528, 'mm': 2.84528, 'pt': 1, 'in': 72.27, 'bp': 1.00375}[m.group(2)] / 342.295
    return float(w.replace('\\textwidth', '').replace('\\linewidth', '') or 1)


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
    inner = re.sub(r'\\tabularnewline(?![A-Za-z])', r'\\\\', inner)   # array's row end, as \\\\ (M9)
    _, j = read_opt(inner, skip_ws(inner, 0))   # [t] [b]: where the table sits on the line
    spec, j = read_group(inner, skip_ws(inner, j))
    # the columns: l c r, p{<width>} (a paragraph that wide, top-aligned: IAG 26/27's M9), | rules, @{...} the
    # space between columns replaced
    cols, vl, widths, nosep = [], [0], [], set()
    k = 0
    sp = spec.replace(' ', '')
    while k < len(sp):
        c = sp[k]
        if c == '|':
            vl[-1] += 1
        elif c in 'lcr':
            cols.append(c); vl.append(0); widths.append(None)
        elif c in 'p@':
            g, k2 = read_group(sp, k + 1)
            if c == 'p':
                cols.append('p'); vl.append(0); widths.append(width_frac(g))
            else:
                nosep.add(len(cols))   # @{} before column len(cols): no space there
            k = k2
            continue
        k += 1
    rows, hl, bk0 = [], 0, ''
    for r in split_cells(inner[j:], '\\\\'):
        r = re.sub(r'^(\s*\\par\b)+', '', r.strip()).strip()   # a blank line before \hline (C3b)
        top, bk = 0, ''
        while True:
            m = re.match(r'\\(hline|toprule|midrule|bottomrule)\s*', r)
            if not m:
                break
            if m.group(1) == 'hline':
                top += 1
            else:   # booktabs' rules: heavy at the top and bottom, light between, with space around (M10)
                bk = m.group(1)[0]
            r = r[m.end():]
        if rows and top:
            rows[-1]['below'] = top
        if rows and bk:
            rows[-1]['bkb'] = bk
        if r:
            rows.append(dict(above=top if not rows else 0, cells=split_cells(r, '&'), below=0, bka=bk, bkb=''))
        elif not rows:
            hl, bk0 = top, bk
    if rows and hl:
        rows[0]['above'] = hl
    if rows and bk0:
        rows[0]['bka'] = bk0
    out = [f'{ind}<table class="tabular">']
    for k, row in enumerate(rows):
        cls = ([f'hl{row["above"]}'] if row['above'] else []) + ([f'hb{row["below"]}'] if row['below'] else []) + \
              ([f'bka-{row["bka"]}'] if row.get('bka') else []) + ([f'bkb-{row["bkb"]}'] if row.get('bkb') else [])
        out.append(f'{ind}{T}<tr{" class=" + chr(34) + " ".join(cls) + chr(34) if cls else ""}>')
        q = 0
        for c in row['cells']:
            if q >= len(cols):
                break
            m = re.match(r'\s*\\multicolumn\s*\{(\d+)\}', c)
            if m:   # \multicolumn{k}{spec}{text}: one cell over k columns, aligned and ruled as its spec says (C10)
                k = int(m.group(1))
                sp, j2 = read_group(c, skip_ws(c, m.end()))
                g, _ = read_group(c, skip_ws(c, j2))
                sp = sp.replace(' ', '')
                cc = [next((x for x in sp if x in 'lcr'), 'c')] + (['vl'] if sp.startswith('|') else []) + (['vr'] if sp.endswith('|') else [])
                out.append(f'{ind}{T}{T}<td colspan="{k}" class="{" ".join(cc)}">{C.inline(g.strip()).strip()}</td>')
                q += k
                continue
            cc = [cols[q]] + (['vl'] if vl[q] else []) + (['vr'] if vl[q + 1] else []) + \
                 (['nol'] if q in nosep else []) + (['nor'] if q + 1 in nosep else [])
            # a p{} column is that wide: a minimum too, or an automatic table narrows it (M6)
            # (2pt more: a line that fills the column exactly in TeX must not wrap on a browser's rounding, M6)
            st = f' style="width: calc(({widths[q]:g} * 342.295 + 2) * var(--pt)); min-width: calc(({widths[q]:g} * 342.295 + 2) * var(--pt))"' if widths[q] else ''
            out.append(f'{ind}{T}{T}<td class="{" ".join(cc)}"{st}>{C.inline(c.strip()).strip()}</td>')
            q += 1
        out.append(f'{ind}{T}</tr>')
    out.append(f'{ind}</table>')
    return '\n'.join(out)

LISTPRE = re.compile(r'\s*(?:\\(tiny|scriptsize|footnotesize|small|smaller|normalsize|large)\b(?:\{\})?'
                     r'|\\setbeamercolor\{item\}\{fg=(\w+)\}%?|\\setcounter\{enumi\}\{(-?\d+)\})')

def list_size(inner):
    """what a list declares before its first item (IAG 26/27): a size, the whole list's, labels too
    (\\begin{itemize}\\small); its labels' colour (\\setbeamercolor{item}{fg=...}); an enumerate's first number
    less one (\\setcounter{enumi}{-1}). Returns the rest, the size, and the list's own style"""
    size, style = None, []
    while (m := LISTPRE.match(inner)):
        inner = inner[m.end():]
        if m.group(1):
            size = m.group(1)
        elif m.group(2):
            style.append(f'--itemfg: var(--{m.group(2)})')
        else:
            style.append(f'counter-reset: enum {m.group(3)}')
    return inner, size, '; '.join(style)

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
    inner, size, lstyle = list_size(inner)
    if lstyle:
        style = (style[:-1] + '; ' + lstyle + '"') if style else f' style="{lstyle}"'
    cov = re.match(r'\s*\\COVLIST ', inner)   # \uncover<...>{the list} off this slide
    if cov:
        inner = inner[cov.end():]
    parts = split_top(inner, 'item')
    reading = [re.fullmatch(r'\s*\[\\usebeamertemplate\*\{bibliography item\}\]\s*\\bibentry\{([^}]*)\}\s*(\\beamertemplate(book|article)bibitems)?\s*', p, re.S)
               for p in parts[1:]]
    if reading and all(reading):   # beamer's bibliography items, each a \bibentry: one element per entry, for
        from bib import bibentry   # allowframebreaks; the icon as the last \beamertemplate...bibitems before it (C3a)
        book = re.search(r'\\beamertemplate(book|article)bibitems\s*$', parts[0])
        book, out = bool(book and book.group(1) == 'book'), []
        for m in reading:
            out.append(f'{ind}{bibentry(m.group(1), book)}')
            if m.group(3):
                book = m.group(3) == 'book'
        return '\n'.join(out)
    parts[0] = re.sub(r'\\par\b', '', parts[0])   # a blank line before the first item (C3a)
    assert not parts[0].strip(), repr(parts[0][:200])
    cls = ' '.join(c for c in ('covered' if cov else '', size or '') if c)
    out = [f'{ind}<{tag}{style}{" class=" + chr(34) + cls + chr(34) if cls else ""}>']
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
    inner, size, lstyle = list_size(inner[j:])
    lst = f' style="{lstyle}"' if lstyle else ''
    parts = split_top(inner, 'item')
    assert not parts[0].strip(), repr(parts[0][:200])
    sz = f' {size}' if size else ''
    out = [f'{ind}<dl{" class=" + chr(34) + size + chr(34) if size else ""}{lst}>'] if wide is None else [
        f'{ind}<dl class="widest{sz}"{lst}>', f'{ind}{T}<div class="ditem sizer"><dt>{C.inline(wide).strip()}</dt><dd></dd></div>']
    for p in parts[1:]:
        lab, j = read_opt(p, 0)
        cov = re.match(r'\s*\\COV ', p[j:])   # an overlay not shown on this slide
        if cov:
            j += cov.end()
        body, flags = container(p[j:], ind + T * 2, 'li')
        dt = f'<dt>{C.inline(lab or "").strip()}</dt>'
        if len(body) <= 1:   # an item with no text: its label alone (IAG 26/27's M9)
            out.append(f'{ind}{T}<div class="ditem{" covered" if cov else ""}">{dt}<dd>{body[0].strip() if body else ""}</dd></div>')
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
                # its fraction kept too: inside an item a \\textwidth is not the item's width (C9 of SMA-LS 07/08)
                tw = '\\textwidth' in fw.group(0)
                st = f' style="width: {float(fw.group(1) or 1) * 100:g}%{f"; --wf: {float(fw.group(1) or 1):g}" if tw else ""}"'
            # scale=<f> on a bitmap: its size as pdfTeX takes it, pixels at 72 dpi times f (pdfTeX ignores a
            # PNG's own resolution: CILC 2016's architecture.png, 182 dpi, is 1820px x 0.15 = 273pt in its PDF)
            sc = re.search(r'scale\s*=\s*([0-9.]+)', o or '')
            bm = next((ROOT / (g + e) for e in ('', '.png', '.jpg') if (ROOT / (g + e)).is_file() and (g + e).endswith(('.png', '.jpg'))), None)
            if sc and bm:
                from PIL import Image
                im = Image.open(bm)
                dpi = 72
                st = f' style="width: calc({im.size[0] * 72 / dpi * float(sc.group(1)):.2f} * var(--pt))"'
            # height=<len>: that tall, its width in proportion (C8a of SMA-LS 07/08: 1.5in, 5.5cm)
            hh = re.search(r'(?<![a-z])height\s*=\s*([0-9.]+)\s*(cm|mm|pt|in|bp)', o or '')
            if hh and not fw:
                v = float(hh.group(1)) * {'cm': 28.4528, 'mm': 2.84528, 'pt': 1, 'in': 72.27, 'bp': 1.00375}[hh.group(2)]
                st = f' style="height: calc({v:.2f} * var(--pt)); width: auto"'
            # width= and height= in \\textwidth, \\textheight or a length, keepaspectratio too, where the style gives
            # its text sizes (AMSUniBo): the size TeX sets, from the picture's own proportions (IAG 26/27's M9, L6)
            from deck import STYLE
            if 'textwidth' in STYLE and not sc:
                def length(key):
                    m = re.search(r'(?<![a-z])' + key + r'\s*=\s*([0-9.]*)\s*(\\textwidth|\\linewidth|\\textheight|cm|mm|pt|in|bp)', o or '')
                    if not m:
                        return None
                    f = float(m.group(1) or 1)
                    return f * {'\\textwidth': STYLE['textwidth'], '\\linewidth': STYLE['textwidth'], '\\textheight': STYLE['textheight'],
                                'cm': 28.4528, 'mm': 2.84528, 'pt': 1, 'in': 72.27, 'bp': 1.00375}[m.group(2)]
                W, Hh = length('width'), length('height')
                src_ = next((ROOT / (g + e) for e in ('', '.pdf', '.png', '.jpg') if (ROOT / (g + e)).is_file()), None)
                if (W or Hh) and src_:
                    if src_.suffix == '.pdf':
                        import pymupdf
                        r = pymupdf.open(src_)[0].rect   # the crop box as shown: rotated (M10's atlayers, 270°)
                        iw, ih = r.width, r.height
                    else:
                        from PIL import Image
                        iw, ih = Image.open(src_).size
                    if W and Hh and 'keepaspectratio' in (o or ''):
                        k = min(W / iw, Hh / ih)
                    elif W and Hh:
                        k = None
                    else:
                        k = (W / iw) if W else (Hh / ih)
                    w2, h2 = (iw * k, ih * k) if k else (W, Hh)
                    st = f' style="width: calc({w2:.2f} * var(--pt)); height: calc({h2:.2f} * var(--pt))"'
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
    # a title on two lines runs below the band's usual bottom: its lines are the ones in the title's size, the
    # first line's, wherever they are in the top third (IAG 26/27's M9)
    spans = [sp for b in _pdf()[pn - 1].get_text('rawdict')['blocks'] for l in b.get('lines', []) for sp in l['spans']]
    first = [sp for sp in spans if any(STYLE['head'] < ch['origin'][1] < STYLE['title'] for ch in sp['chars'])]
    size = max((sp['size'] for sp in first), default=0)
    t = ''.join(ch['c'] for sp in spans for ch in sp['chars']
                if STYLE['head'] < ch['origin'][1] < STYLE['title'] or (size and ch['origin'][1] < 90 and sp['size'] >= size - 2
                                                                        and sp['font'] == max(first, key=lambda x: x['size'])['font']))
    return re.sub(r'\s+', '', t)

_SHRUNK = []

def log_shrinks():
    """{page: percent} from beamer's "Frame text is shrunk by a factor of <x> percent" in the deck's .log: each
    warning belongs to the next page shipped out, [<n> in the log (C9 of SMA-LS 07/08)"""
    if not _SHRUNK:
        out, pend = {}, None
        try:
            log = path('pdf').with_suffix('.log').read_text(errors='replace')
        except OSError:
            log = ''
        log = re.sub(r'\n(?=\S)', '\n', log)
        for m in re.finditer(r'shrunk by a factor of\s+([\d.]+)\s+percent|(?<![\w{])\[(\d+)(?=[\s{<\]])', log):
            if m.group(1):
                pend = float(m.group(1))
            elif pend is not None:
                out[int(m.group(2))] = pend
                pend = None
        _SHRUNK.append(out)
    return _SHRUNK[0]

def pdf_shrink(pn):
    """the percentage TeX shrank PDF page pn by beyond what its frame asked, as beamer logged it; 0 when it logged
    nothing (TeX then took the frame's own shrink=<n>, or did not need to shrink a bare shrink at all). Text sizes
    are no measure: a frame's commonest text may be a \\small caption (C2, C9 of SMA-LS 07/08)"""
    return round(log_shrinks().get(pn, 0), 3)

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

def broken_pages(pn, first=1):
    """how many PDF pages, from pn on, an allowframebreaks frame fills: its titles end I, II, III ..., from the
    numeral `first` on (after a \\framebreak, the part after it: IAG 26/27's M3)"""
    t0 = pdf_title(pn)
    if not t0.endswith(ROMAN[first]):
        return 1
    base, k = t0[:-len(ROMAN[first])], 1
    while pn + k <= len(_pdf()) and pdf_title(pn + k) == base + ROMAN[first + k]:
        k += 1
    return k

_BG = []
def pdf_pictures(pn):
    """the pictures of PDF page pn, the background (an image on every page, the seal) aside"""
    d = _pdf()
    if not _BG:
        from collections import Counter
        c = Counter(tuple(round(x) for x in im['bbox']) for q in range(min(len(d), 6)) for im in d[q].get_image_info())
        _BG.extend(b for b, n in c.items() if n >= min(len(d), 6) - 1)
    # the blocks' shadows are small images too: a picture is at least 30pt each way
    return [im for im in d[pn - 1].get_image_info() if tuple(round(x) for x in im['bbox']) not in _BG
            and im['bbox'][2] - im['bbox'][0] > 30 and im['bbox'][3] - im['bbox'][1] > 30]

def distribute(items, pn, k):
    """top-level items -> the PDF page (pn .. pn+k-1) each one starts on: TeX broke the frame between them"""
    bodies = [pdf_body(q) for q in range(pn, pn + k)]
    where, cur, fbs = [], 0, set()
    nodig = [re.sub(r'\d', '', b) for b in bodies]
    fbhit = {}
    for h in items:
        t = plain(h)
        page = None
        # a figure by its caption's own words first: what comes before them is not in the PDF, and its last
        # words may be on another page too (C9 of SMA-LS 07/08)
        cap = t[t.index('Figure') + 6:] if 'Figure' in t else ''
        if 'data-fb="1"' in h[:300]:   # after a \\framebreak in an environment: the page after the item before it,
            fbs.add(len(where))         # settled below, once the items without text are; where its text is, too
            tf = t[:30]
            fbhit[len(where)] = next((q for q in range(k) if len(tf) >= 6 and tf in bodies[q]), None)
            where.append(None)
            continue
        vp = re.search(r'data-vpage="(\d+)"', h)   # a piece of a verbatim split_verbatims placed already
        if vp:
            cur = page = int(vp.group(1))
            where.append(page)
            continue
        # a long item: the page holding most of its text, in 12-character pieces; its first words may repeat a
        # page before (two tables with one header, IAG 26/27's M9)
        if len(t) > 120 and not cap:
            pieces = [t[a:a + 12] for a in range(0, len(t) - 12, 12)]
            score = [sum(x in bodies[q] for x in pieces) if q >= cur else -1 for q in range(k)]
            if max(score) > len(pieces) / 2:
                page = score.index(max(score))
                cur = page
                where.append(page)
                continue
        for w in (cap[:40], cap[:16], t[:40], t[:16], t[-16:], t[:8]):
            if len(w) >= 4:
                hits = [q for q in range(cur, k) if w in bodies[q]]
                if not hits:   # digits aside: an enumerate's numbers are in the PDF's text, not in the item's (L1)
                    wd = re.sub(r'\d', '', w)
                    hits = [q for q in range(cur, k) if len(wd) >= 4 and wd in nodig[q]]
                if hits:
                    page = hits[0]
                    break
        if page is not None:
            cur = page
        where.append(page)
    # an item without text (a picture) goes to a page no text item took, else to the page before it
    for a, h in enumerate(items):
        img = '<img' in h or '<svg' in h
        if a in fbs:
            if a - 1 in fbs and where[a - 1] is not None:   # a later piece of the same cut: with the one before, or
                where[a] = max(where[a - 1], fbhit.get(a) if fbhit.get(a) is not None else where[a - 1])   # where its text is (M9)
                continue
            # the first piece: the page after the last item before it that has text (an empty piece is placed after: L1)
            prev = next((where[b] for b in range(a - 1, -1, -1) if where[b] is not None and plain(items[b])), 0)
            where[a] = min(prev + 1, k - 1)
            if fbhit.get(a) is not None and fbhit[a] > where[a]:   # its text further on: a piece with none between (M7)
                where[a] = fbhit[a]
            continue
        if where[a] is None:
            prev = next((where[b] for b in range(a - 1, -1, -1) if where[b] is not None), -1)   # none before it: from the first page (L3)
            nxt = next((where[b] for b in range(a + 1, len(items)) if where[b] is not None), k)
            free = [q for q in range(prev + 1, nxt) if q not in where]
            if not free and img and 0 <= prev < nxt < k and pdf_pictures(pn + nxt) and not pdf_pictures(pn + prev):
                where[a] = nxt   # no page free: the one of its neighbours that has a picture in the PDF (M8)
                continue
            where[a] = free[0] if free else max(prev, 0)
    return where

def split_verbatims(items, pn, k):
    """a verbatim TeX broke across pages between its lines (IAG 26/27's L2): one <pre> per page, each holding the
    lines that page shows, found by their text from the page the last one was on"""
    bodies = [pdf_body(q) for q in range(pn, pn + k)]
    plines = [{re.sub(r'[^0-9A-Za-z]', '', ''.join(sp['text'] for sp in l['spans']))
               for b in _pdf()[q - 1].get_text('dict')['blocks'] for l in b.get('lines', [])} for q in range(pn, pn + k)]
    out, cur = [], 0
    for h in items:
        # a <pre>, or a centred one (\\begin{center}\\begin{verbatim}: L2, L3); its lines end in <br> or a newline
        m = re.match(r'(\s*(?:<div class="center">\s*)?<pre class="verbatim[^"]*"[^>]*>)(.*)(</pre>(?:\s*</div>)?\s*)$', h, re.S)
        if not m:
            t = plain(h)
            hit = next((q for w in (t[:24], t[:10]) if len(w) >= 6 for q in range(cur, k) if w in bodies[q]), None)
            cur = hit if hit is not None else cur
            out.append(h)
            continue
        sep = '<br>' if '<br>' in m.group(2) else '\n'
        lines, pages = m.group(2).split(sep), []
        for ln in lines:
            # a line goes to the first page, from the last one's on, holding a PDF line equal to it; two lines alike
            # as text still go to their own pages (L3); else the old way, by its first characters
            t = re.sub(r'[^0-9A-Za-z]', '', H.unescape(re.sub(r'<[^>]*>', '', ln)))
            if len(t) >= 6:
                hit = next((q for q in range(cur, k) if t in plines[q]), None)
                if hit is None:
                    hit = next((q for q in range(cur, k) if t[:30] in bodies[q]), None)
                cur = hit if hit is not None else cur
            elif len(t) >= 2 and t not in plines[cur]:   # a short line (p :- v.: L3) by an equal PDF line further on
                cur = next((q for q in range(cur + 1, k) if t in plines[q]), cur)
            pages.append(cur)
        if len(set(pages)) == 1:
            out.append(h)
            continue
        for q in sorted(set(pages)):
            out.append(m.group(1).replace('<pre ', f'<pre data-vpage="{q}" ', 1) + sep.join(l for l, w in zip(lines, pages) if w == q) + m.group(3))
    return out

VOID = {'br', 'img', 'hr', 'wbr', 'input', 'meta', 'link'}

def split_framebreaks(items):
    """a \\framebreak inside an environment (\\begin{center} … \\framebreak …, or in a list: IAG 26/27's M7, M9,
    M10): the item cut there, its open elements closed before the cut and opened again after it, each on its own
    line as it was, so the later passes still see lists and blocks; the part after is marked to start a new page"""
    out = []
    for h in items:
        if '<!--framebreak-->' not in h:
            out.append(h)
            continue
        parts = h.split('<!--framebreak-->')
        opened, base = [], 0
        for k, part in enumerate(parts):
            head = ''
            if k:
                lines = [ind + tag for ind, tag in opened]
                if lines:
                    lines[0] = re.sub(r'^(\s*<\w+)', r'\1 data-fb="1"', lines[0], count=1)
                head = '\n'.join(lines) + '\n' if lines else '<i data-fb="1" hidden></i>'
            stack = list(opened)
            for m in re.finditer(r'<(/?)(\w+)([^>]*)>', part):
                if m.group(2) in VOID or m.group(3).endswith('/'):
                    continue
                if m.group(1):
                    if stack:
                        stack.pop()
                else:
                    ls = part.rfind('\n', 0, m.start()) + 1
                    ind = re.match(r'[ \t]*', part[ls:]).group(0) if not part[ls:m.start()].strip() else ''
                    stack.append((ind, m.group(0)))
            closing = '\n'.join(ind + f'</{re.match(r"<(\w+)", t).group(1)}>' for ind, t in reversed(stack))
            body = head + part.strip('\n') if k else part.rstrip()
            if k:   # a cut between two items: the item opened again holds nothing, and would draw a bullet of its own (M10)
                body = re.sub(r'\n[ \t]*<li>\s*</li>(?=\n)', '', body, count=1)
            if re.sub(r'<[^>]*>', '', body).strip() or '<img' in body:
                out.append(body + ('' if k == len(parts) - 1 else '\n' + closing))
            opened = stack
    return out

FNCOUNT = [0]   # LaTeX's footnote counter, through the deck

def split_minipages(items):
    """a row of minipages TeX set as several lines (their widths add up to more than \\textwidth): one element per
    line, so allowframebreaks can share them out (IAG 26/27's L1: block and logo, block and logo)"""
    out = []
    for h in items:
        m = re.match(r'(\s*<div class="minipages">\n)(.*)(\n\s*</div>\s*)$', h, re.S)
        if not m:
            out.append(h)
            continue
        ind = re.match(r'\s*', m.group(2)).group(0)
        kids = re.split(r'\n(?=' + re.escape(ind) + r'<div class="minipage")', m.group(2))
        rows, cur, w = [], [], 0.0
        for kid in kids:
            f = re.search(r'width: calc\(([0-9.]+) \*', kid)
            x = float(f.group(1)) if f else 1.0
            if cur and w + x > 1.0001:
                rows.append(cur)
                cur, w = [], 0.0
            cur.append(kid)
            w += x
        rows.append(cur)
        if len(rows) == 1:
            out.append(h)
            continue
        out += [m.group(1) + '\n'.join(r) + m.group(3) for r in rows]
    return out

def split_entries(items, pn, k):
    """a \\bibentry item TeX broke across pages: cut between its blocks, the rest on the next page, no icon (C3a)"""
    bodies = [pdf_body(q) for q in range(pn, pn + k)]
    out, cur = [], 0
    for h in items:
        m = re.match(r'(\s*<p class="artitem bibentry[^"]*">)(.*)</p>\s*$', h, re.S)
        if not m:
            out.append(h)
            continue
        blocks = [x for x in re.split(r'(?=<span class="bib-)', m.group(2)) if x]
        pages = []
        for x in blocks:
            t = plain(x)
            hit = next((q for w in (t[:24], t[:10]) if len(w) >= 4 for q in range(cur, k) if w in bodies[q]), None)
            cur = hit if hit is not None else cur
            pages.append(cur)
        for q in sorted(set(pages)):
            body = ''.join(x for x, w in zip(blocks, pages) if w == q).strip()
            head = m.group(1) if q == pages[0] else m.group(1).replace('bibentry', 'bibentry cont', 1)
            out.append(f'{head}{body}</p>')
    return out

def split_lists(items):
    """a top-level itemize TeX broke across pages between its items (C8 of SMA-LS 07/08): each item a list
    of its own, marked with the list it came from, so that distribute can share them out"""
    out = []
    for n, h in enumerate(items):
        m = re.match(r'(\s*)(<(ul|dl|ol)\b[^>]*)>\n(.*)\n\1</\3>\s*$', h, re.S)   # a description too (C8's rules), an enumerate (M8)
        lis = re.split(r'\n(?=' + re.escape(m.group(1) + T) + r'(?:<li\b|<div class="ditem(?! sizer)))', m.group(4)) if m else []
        if len(lis) < 2:
            out.append(h)
            continue
        if lis[0].lstrip().startswith('<div class="ditem sizer"'):   # the widest label's sizer goes with every piece
            sizer, first = lis[0].split('\n', 1) if '\n' in lis[0] else (lis[0], '')
            lis = [first] + lis[1:] if first else lis[1:]
            lis = [sizer + '\n' + x for x in lis]
        pieces = []
        for x in lis:   # an item whose own list TeX broke too: that list cut item by item, one level down (C8)
            nm = re.search(r'^(\s*)(<(ul|dl)\b[^>]*)>\n(.*?)\n\1</\3>$', x, re.S | re.M)
            kids = re.split(r'\n(?=' + re.escape(nm.group(1) + T) + r'(?:<li\b|<div class="ditem(?! sizer)))', nm.group(4)) if nm else []
            if len(kids) < 2:
                pieces.append(x)
                continue
            sizer = ''
            if kids[0].lstrip().startswith('<div class="ditem sizer"'):
                sizer, rest = kids[0].split('\n', 1) if '\n' in kids[0] else (kids[0], '')
                kids = ([rest] if rest else []) + kids[1:]
                sizer += '\n'
            head, tail = x[:nm.start()], x[nm.end():]
            nopen = f'{nm.group(1)}{nm.group(2)} data-nest="{n}">'
            li_ind = re.match(r'\s*', x).group(0)
            for q, kid in enumerate(kids):
                inner = f'{nopen}\n{sizer}{kid}\n{nm.group(1)}</{nm.group(3)}>'
                pieces.append(f'{head}{inner}{tail}' if q == 0 else f'{li_ind}<li class="cont">\n{inner}\n{li_ind}</li>')
        # an enumerate's piece goes on counting from the items before it (M8)
        start = lambda q: (f' style="counter-reset: enum {q}"' if m.group(3) == 'ol' and q and 'style=' not in m.group(2) else '')
        out += [f'{m.group(1)}{m.group(2)}{start(q)} data-split="{n}">\n{x}\n{m.group(1)}</{m.group(3)}>' for q, x in enumerate(pieces)]
    return out

def split_blocks(items, pn, k):
    """a block TeX broke across pages (IAG 26/27's L3, M7, M8): its body's elements, its lists item by item, each
    a part of the block of its own, marked with the block it came from; the title stays with the first part"""
    out = []
    for n, h in enumerate(items):
        m = re.match(r'(\s*)(<div class="block[^"]*">)\n(\s*<h3 [^\n]*</h3>\n)?(\s*<div class="block-body[^"]*"[^>]*>)\n(.*)\n(\s*</div>)\n\1</div>\s*$', h, re.S)
        if not m:
            out.append(h)
            continue
        kind = re.match(r'\s*', m.group(4)).group(0) + T
        pieces = split_lists(split_verbatims(re.split(r'\n(?=' + re.escape(kind) + r'<(?!/))', m.group(5)), pn, k))
        if len(pieces) < 2:
            out.append(h)
            continue
        for k, x in enumerate(pieces):
            head = m.group(2).replace('<div class="block', f'<div data-bsplit="{n}" class="block', 1)
            out.append('\n'.join([m.group(1) + head] + ([m.group(3).rstrip('\n')] if m.group(3) and k == 0 else [])
                                  + [m.group(4), x, m.group(6), m.group(1) + '</div>']))
    return out

def join_blocks(items):
    """split_blocks undone on one page: the parts of a block on it are one block again, titled if its first part
    is there, else a continuation with no title"""
    out = []
    for h in items:
        m = re.match(r'(\s*)<div data-bsplit="(\d+)" class="(block[^"]*)">\n(.*)\n(\s*</div>)\n\1</div>\s*$', h, re.S)
        if not m:
            out.append(h)
            continue
        t = re.match(r'(\s*<h3 [^\n]*</h3>\n)?(\s*<div class="block-body[^"]*"[^>]*>)\n(.*)$', m.group(4), re.S)
        if out and isinstance(out[-1], dict) and out[-1]['id'] == m.group(2):
            out[-1]['body'].append(t.group(3))
        else:
            out.append(dict(id=m.group(2), ind=m.group(1), cls=m.group(3), title=t.group(1), open=t.group(2), body=[t.group(3)], close=m.group(5)))
    res = []
    for b in out:
        if not isinstance(b, dict):
            res.append(b)
            continue
        cls = b['cls'] if b['title'] else b['cls'] + ' notitle cont'
        res.append('\n'.join([f'{b["ind"]}<div class="{cls}">'] + ([b['title'].rstrip('\n')] if b['title'] else [])
                              + [b['open'], '\n'.join(join_lists(b['body'])), b['close'], f'{b["ind"]}</div>']))
    return res

def join_lists(items):
    """split_lists undone on one page: the items of a list that fell on it are one list again"""
    out = []
    for h in items:
        m = re.match(r'(\s*)(<(ul|dl|ol)\b[^>]*?) data-split="(\d+)">\n(.*)\n\1</\3>$', h, re.S)
        body = m.group(5) if m else ''
        if m and out and isinstance(out[-1], list) and out[-1][0] == m.group(4):
            if body.lstrip().startswith('<div class="ditem sizer"'):   # one sizer per list
                body = body.split('\n', 1)[1]
            c = re.match(r'(\s*)<li class="cont">\n(\s*)<(ul|dl)\b[^>]*data-nest="([^"]+)">\n(.*)\n\2</\3>\n\1</li>$', body, re.S)
            close = re.search(r'\n(\s*)</(ul|dl)>\n(\s*)(?:</li>|</dd></div>)$', out[-1][1])   # a description item's too (M8)
            if c and close and f'data-nest="{c.group(4)}"' in out[-1][1]:   # the same nested list: its items join it
                kid = c.group(5)
                if kid.lstrip().startswith('<div class="ditem sizer"'):
                    kid = kid.split('\n', 1)[1]
                out[-1][1] = out[-1][1][:close.start()] + '\n' + kid + out[-1][1][close.start():]
            else:
                out[-1][1] += '\n' + body
        elif m:
            out.append([m.group(4), body, m.group(1), m.group(2), m.group(3)])
        else:
            out.append(h)
    return [f'{x[2]}{x[3]}>\n{x[1]}\n{x[2]}</{x[4]}>' if isinstance(x, list) else x for x in out]

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
    from deck import STYLE
    def text(x):
        if STYLE.get('straightquotes'):
            return esc(x)
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
    defs = dict(CFG.get('texmacros', {}))
    # a \\newcommand in the document's body, a frame's own macro (a \\renewcommand stays: it may redefine what the
    # converter reads, \\figurename in blockchain-woa2018): taken out and expanded as the deck.json ones are
    # (IAG 26/27's M9: \\plancell, \\planheader in a frame)
    if '\\begin{document}' in s:
        k0 = s.index('\\begin{document}')
        while (m := re.compile(r'\\newcommand\*?\{\\([A-Za-z]+)\}(?:\[(\d)\])?').search(s, k0)):
            body, e = read_group(s, skip_ws(s, m.end()))
            defs.setdefault(m.group(1), [int(m.group(2) or 0), body])
            s = s[:m.start()] + s[e:]
            k0 = m.start()
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
            # TeX had tokenised the body: a control word before #k ends there (\it#1 is \it, then the argument)
            body = re.sub(r'(\\[A-Za-z]+)(?=#\d)', r'\1 ', body)
            for k, g in enumerate(args, 1):
                body = body.replace('#%d' % k, g)
            if n == 0 and j < len(s) and s[j] == ' ':
                pass
            # grouped, so that a script after it takes it whole; but not when it holds alignment marks or an \item,
            # which a group would hide from the alignment or the list (TeX itself never groups a macro's body)
            top = re.sub(r"\\[{}]", "", body)   # \{ \} are not groups
            while re.search(r'\{[^{}]*\}', top):
                top = re.sub(r'\{[^{}]*\}', '', top)
            grp = n and not re.search(r'(?<!\\)&|\\\\|\\item(?![A-Za-z])', top)
            out.append(s[i:m.start()] + '{' + body + '}' if grp else s[i:m.start()] + body + (' ' if re.match(r'[A-Za-z]', s[j:j + 1]) else ''))
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
    # \\color{c} just before a semiverbatim, \\color{...} just after: its text in that colour, the colour inside it, or an
    # empty coloured line stands before it (IAG 26/27's L7)
    src = re.sub(r'\\color\{([^}]*)\}\s*\\begin\{semiverbatim\}(.*?)\\end\{semiverbatim\}(?:\s*\\color\{[^}]*\})?',
                 lambda m: '\\begin{semiverbatim}\\textcolor{' + m.group(1) + '}{' + re.sub(r'\n[ \t]*$', '', re.sub(r'^\n[ \t]*', '', m.group(2)))
                 + '}\\end{semiverbatim}', src, flags=re.S)
    src = re.sub(r'\\nobibliography\*', '', src)   # bibentry reads the .bbl here: nothing printed (C3a)
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
    # \\AtBeginSubsection in the deck, or in a style layer of its own that it loads (IAG 26/27's sty/iag.sty, not a link
    # into the style: a subtoc_title alone makes no pages, SMA-LS 06/07's C4a)
    pre = src[:src.index('\\begin{document}')]
    own = [Path('sty') / (n.strip() + '.sty') for m in re.finditer(r'\\usepackage(?:\[[^\]]*\])?\{([^}]*)\}', pre)
           for n in m.group(1).split(',')]
    subtocs = '\\AtBeginSubsection' in pre or any(f.is_file() and not f.is_symlink() and '\\AtBeginSubsection' in f.read_text(errors='replace')
                                                 for f in own)
    # its frame [shrink]ed: TeX scales each of those outlines to fit, by the factor pdf_shrink reads (C9, C10 of SMA-LS 07/08)
    sm = re.search(r'\\AtBeginSubsection(?:\[[^\]]*\])?\s*\{\s*\\begin\{frame\}(?:<[^>]*>)?\[([^\]]*)\]', src)
    subshrink = bool(sm) and any(o.strip().startswith('shrink') for o in sm.group(1).split(','))
    subshrinkby = shrinkage([o.strip() for o in sm.group(1).split(',')]) if sm else 0   # shrink=10 (C3 of SMA-LS 07/08)
    # the \\AtBeginSection frame [shrink]ed too (IAG 26/27's M7, eight sections: shrink=10)
    ss = re.search(r'\\AtBeginSection(?:\[[^\]]*\])?\s*\{\s*\\begin\{frame\}(?:<[^>]*>)?\[([^\]]*)\]', src)
    secshrink = bool(ss) and any(o.strip().startswith('shrink') for o in ss.group(1).split(','))
    secshrinkby = shrinkage([o.strip() for o in ss.group(1).split(',')]) if ss else 0
    # a contents frame at each section only where the deck asks for one (every deck before experiment 8 did)
    sectocs = '\\AtBeginSection' in src[:src.index('\\begin{document}')] or any(
        '\\AtBeginSection' in f.read_text(errors='replace') for f in (ROOT / 'sty').glob('*.sty'))
    # the sections, and their subsections, for the contents frames
    # and the subsubsections of each subsection, beamer's third level (C8 of SMA-LS 07/08)
    secs, subs, subsubs = [], [], []
    for m in re.finditer(r'\\(sub|subsub)?section(?:<presentation>)?(\*?)(\[[^]]*\])?\s*\{', doc):   # <presentation>: C3a's appendix
        g, _ = read_group(doc, m.end() - 1)
        C.reset()
        if m.group(2):
            continue
        if m.group(1) == 'subsub':
            if subsubs and subsubs[-1]:
                subsubs[-1][-1].append(C.inline(g))
        elif m.group(1):
            if subs:
                subs[-1].append(C.inline(g))
                subsubs[-1].append([])
        else:
            secs.append(C.inline(g))
            subs.append([])
            subsubs.append([])
    # \\part: each section's part, by position (C4 of DS 25/26); a deck with no parts has them all in part 0
    partat = [m.start() for m in re.finditer(r'\\part(?:\[[^]]*\])?\s*\{', doc)]
    partof = [sum(1 for a in partat if a < m.start())
              for m in re.finditer(r'\\section(?:<presentation>)?(\*?)(\[[^]]*\])?\s*\{', doc) if not m.group(1)]

    def inpart(n, extra=None):
        """beamer's contents within a part: only that part's sections, still numbered across the deck; n is the
        part, 0 before any"""
        ks = [k for k, q in enumerate(partof) if q == n] if partat else list(range(len(secs)))
        if not ks:
            return dict(secs=[], subs=[], subsubs=[], start=1)
        a, b = ks[0], ks[-1] + 1
        return dict(secs=secs[a:b], subs=subs[a:b], subsubs=subsubs[a:b], start=a + 1, **(extra or {}))
    # \\AtBeginPart{\\frame{\\partpage}}: a page for each part (ds.sty)
    partpages = bool(partat) and bool(re.search(r'\\AtBeginPart\s*\{[^}]*\\partpage', pre + ''.join(
        f.read_text(errors='replace') for f in (ROOT / 'sty').glob('*.sty') if f.is_file())))
    partno = 0
    out = []
    section = subsection = ''
    i = 0
    tok = re.compile(r'\\(sub)?section(?:<presentation>)?(\*?)(?:\[([^]]*)\])?\s*\{|\\frame(\[[^]]*\])?\{\\(titlepage|tableofcontents)(\[[^]]*\])?\}|\\begin\{frame\}'
                     r'|\\frame(?![A-Za-z])(\[[^]]*\])?\s*(?=\{)'
                     r'|\\setbeamertemplate\{page number in head/foot\}\{\}'
                     r'|\\part(?:\[[^]]*\])?\s*\{')
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
        if m.group(0).startswith('\\part'):
            g, i = read_group(doc, m.end() - 1)
            C.reset()
            partno += 1
            section = subsection = ''   # a part page has no section in its headline
            if partpages:
                out.append(dict(kind='part', section='', subsection='', number=partno, title=C.inline(g)))
            continue
        if m.group(0).startswith('\\subsection'):
            g, i = read_group(doc, m.end() - 1)
            C.reset()
            subsection = C.inline(m.group(3) if m.group(3) is not None else g)   # the headline takes the short title (C9)
            if not m.group(2):
                subno += 1
                if subtocs:
                    ip = inpart(partno)
                    out.append(dict(kind='subtoc', section=section, subsection=subsection, current=secno - ip['start'] + 1,
                                    shrink_auto=subshrink, shrink=subshrinkby, currentsub=subno, **ip))
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
                    ip = inpart(partno)
                    out.append(dict(kind='toc', section=section, current=secno - ip['start'] + 1,
                                    shrink_auto=secshrink, shrink=secshrinkby, **ip))
            continue
        if m.group(5) == 'titlepage':
            out.append(dict(kind='titlepage', section=section, subsection=subsection))
            i = m.end()
            continue
        if m.group(5) == 'tableofcontents':
            out.append(dict(kind='outline', section=section, subsection=subsection, secs=secs, subs=subs, subsubs=subsubs))
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
        # a frame holding only \\tableofcontents[...]: an outline under the frame's own title; part=<n> lists that
        # part's sections, hideallsubsections drops the subsections (C4 of DS 25/26's outlines of its three parts)
        tm = re.fullmatch(r'\s*\\tableofcontents(?:\[([^\]]*)\])?\s*', fr[j:])
        if tm:
            o = [x.strip() for x in (tm.group(1) or '').split(',')]
            pt = next((int(x.split('=')[1]) for x in o if x.startswith('part=')), None)
            ip = inpart(pt) if pt is not None else dict(secs=secs, subs=subs, subsubs=subsubs, start=1)
            if 'hideallsubsections' in o:
                ip.update(subs=[[] for _ in ip['secs']], subsubs=[[] for _ in ip['secs']])
            C.reset()
            out.append(dict(kind='outline', section=section, subsection=subsection, title=C.inline(title), **ip))
            continue
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
        broken = any(o.split('=')[0].strip() == 'allowframebreaks' for o in opts)   # allowframebreaks=<fraction> too (IAG 26/27)
        if broken:   # typeset once: an overlay specification shows its content and makes no slide (C10 of SMA-LS 07/08)
            fr = fr[:j] + re.sub(r'(\\begin\{\w+\*?\}|\\item)\s*<[^>]*>', r'\1', fr[j:])
        parts = split_top(fr[j:], 'framebreak') if broken else overlay_slides(fr[j:])
        if broken:   # a \\framebreak with nothing after it makes no page (IAG 26/27's M9)
            parts = [q for q in parts if re.sub(r'^\s*\{\}', '', q).strip()] or parts[:1]   # \\framebreak{} too (M1)
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
            C.in_title = True
            t = C.inline(title)
            C.in_title = False
            # a size declared first, before any text or environment, sizes the whole body (C6's {\footnotesize ...})
            bsize = re.match(r'\s*\\(scriptsize|footnotesize|small)(?![A-Za-z])\s*(?=\S)(?!\\begin\{verbatim\})', part)
            if bsize:
                part = part[bsize.end():]
            body, flags = container(part, T * 2, 'body')
            if not broken:   # a \\framebreak in a frame that does not break: nothing (M9)
                body = [x.replace('<!--framebreak-->', '') for x in body if x.strip() != '<!--framebreak-->']
            if not broken:   # a \\framebreak in a frame that does not break: nothing (M9)
                body = [x.replace('<!--framebreak-->', '') for x in body if x.strip() != '<!--framebreak-->']
            if C.title_footnotes:   # the title's, at the page's foot (C10 of SMA-LS 07/08)
                body.append(f'{T}{T}<div class="footnotes page">' + ''.join(
                    f'<p class="footnote"><sup class="fnmark">{mk}</sup>{h}</p>' for mk, h in C.title_footnotes) + '</div>')
            if C.footnotes:   # at the frame's foot, each after its mark; at the foot of the block holding the marks (C10)
                fns = ''.join(f'<p class="footnote{" covered" if cov else ""}"><sup class="fnmark">{mk}</sup>{h}</p>'
                              for mk, h, cov in C.footnotes)
                held = next((q for q, h in enumerate(body) if h.lstrip().startswith('<div class="block')
                             and all(f'<sup class="fnmark">{mk}</sup>' in h for mk, _, _ in C.footnotes)), None)
                if held is not None:
                    h = body[held]
                    e = h.rfind('</div>', 0, h.rfind('</div>'))   # the block body's end (not k: the slide's index)
                    ind = re.match(r'\s*', h[h.rfind('\n', 0, e) + 1:]).group(0)
                    body[held] = h[:e] + f'{T}<div class="footnotes inblock">{fns}</div>\n{ind}' + h[e:]
                elif STYLE.get('fnarabic'):
                    # AMSUniBo (IAG 26/27's L7): a footnote out of any block is LaTeX's, numbered through the deck, its
                    # text at the page's foot under \\footnoterule; inside a block it stays beamer's letter
                    marks = {}
                    for mk, _, _ in C.footnotes:
                        FNCOUNT[0] += 1
                        marks[mk] = str(FNCOUNT[0])
                    body = [re.sub(r'<sup class="fnmark">([a-j])</sup>', lambda q: f'<sup class="fnmark">{marks.get(q.group(1), q.group(1))}</sup>', h)
                            for h in body]
                    fns = ''.join(f'<p class="footnote{" covered" if cov else ""}"><sup class="fnmark">{marks[mk]}</sup>{h}</p>'
                                  for mk, h, cov in C.footnotes)
                    body.append(f'{T}{T}<div class="footnotes page">{fns}</div>')
                else:
                    body.append(f'{T}{T}<div class="footnotes">{fns}</div>')
            if bsize:
                flags.add('size:' + bsize.group(1))
            groups = [body]
            if broken:
                pn = len(out) + 1
                n = broken_pages(pn, roman + 1)
                if n > 1 and k + 1 < len(parts):
                    # \framebreak and TeX's own breaks in one frame: this part ends where the next one starts
                    # (IAG 26/27's M3), found by its first words, its markup taken off
                    nxt = re.sub(r'\\(begin|end)\{[^}]*\}|\\[A-Za-z]+\*?', '', parts[k + 1])
                    nxt = re.sub(r'[^0-9A-Za-z]', '', nxt)[:12]
                    hit = next((q for q in range(1, n) if len(nxt) >= 6 and nxt in pdf_body(pn + q)), None)
                    if hit:
                        n = hit
                    else:   # the next part not found by its text (a picture, TikZ source: L3): a page left for each part after
                        n = max(1, n - sum(1 for q in parts[k + 1:] if re.sub(r'^\s*\{\}', '', q).strip()))
                if n > 1:
                    body = split_lists(split_entries(split_verbatims(split_minipages(split_framebreaks(body)), pn, n), pn, n))
                    where = distribute(body, pn, n)
                    if len(set(where)) < n:   # a page left empty: TeX broke a block, cut it then (L3, M7, M8)
                        b2 = split_blocks(body, pn, n)
                        w2 = distribute(b2, pn, n)
                        # better only if pages are filled by pieces with text: a piece with none goes anywhere free
                        if len({w for h, w in zip(b2, w2) if plain(h)}) > len(set(where)):
                            body, where = b2, w2
                    groups = [join_blocks(join_lists([h for h, w in zip(body, where) if w == q])) for q in range(n)]
                    groups = [g for g in groups if g] or [body]
            for g in groups:
                g = [x.replace('<!--framebreak-->', '') for x in g if x.strip() != '<!--framebreak-->']   # used, or not needed
                roman += 1
                out.append(dict(kind='frame', section=section, subsection=subsection,
                                title=t + (' ' + ROMAN[roman] if broken else ''), body=g, flags=flags,
                                top='t' in opts, nonum=nonum, shrink=shrinkage(opts), shrink_auto='shrink' in opts,
                                cont=bool(k) and not broken))
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
