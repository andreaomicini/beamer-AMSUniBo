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

def container(s, ind, mode='body'):
    """the block content of s -> list of HTML lines; mode: body | li | block | quote | center"""
    s = re.sub(r'\n[ \t]*\n', r'\\par ', s)
    items, i, buf = [], 0, ''
    flags = set()

    def flush_text(t):
        h0 = C.inline(t)
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
                elif h.startswith('img:'):
                    items.append(('raw', h[4:]))
            elif kind == 'p':
                h2 = h.replace('\x00hfill\x00', '')
                items.append(('p', h2))

    while True:
        m = re.compile(r'\\begin\{([a-z]+)\}').search(s, i)
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

def env_html(env, inner, ind):
    if env in ('itemize', 'enumerate'):
        return itemize(inner, ind, 'ol' if env == 'enumerate' else 'ul')
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
        body, flags = container(inner[j:], ind + T * 2, 'block')
        cls = 'block' + BLOCK_ENVS[env] + ('' if title.strip() else ' notitle')
        bcls = 'block-body' + (' center' if 'center' in flags else '')
        out = [f'{ind}<div class="{cls}">']
        if title.strip():
            out.append(f'{ind}{T}<h3 class="block-title">{C.inline(title).strip()}</h3>')
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
            attr = f' data-label="{text}"' + (' class="lbl-small"' if small else '')
        body, flags = container(p[j:], ind + T * 2, 'li')
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
            _, i = read_opt(s, i)
            g, i = read_arg(s, i)
            n = re.sub(r'\.(png|jpe?g|pdf|svg)$', '', g.split('/')[-1])
            return f'\x00img:<img class="figure fig-{n}" data-asset="{n}" alt="ALT-{n}">\x00', i
        return orig(name, s, i)
    C.command = command
includegraphics_hook()

def pages():
    src = strip_comments(open(path('tex')).read())
    doc = src[src.index('\\begin{document}') + 16:src.index('\\end{document}')]
    # the sections, for the contents frames
    secs = []
    for m in re.finditer(r'\\section(\*?)\{', doc):
        g, _ = read_group(doc, m.end() - 1)
        C.reset()
        if not m.group(1):
            secs.append(C.inline(g))
    out = []
    section = ''
    i = 0
    tok = re.compile(r'\\section(\*?)\{|\\frame(\[[a-z,]*\])?\{\\(titlepage|tableofcontents)\}|\\begin\{frame\}'
                     r'|\\setbeamertemplate\{page number in head/foot\}\{\}')
    nonumber = False
    secno = 0
    while True:
        m = tok.search(doc, i)
        if not m:
            break
        if m.group(0).startswith('\\setbeamertemplate'):
            nonumber = True
            i = m.end()
            continue
        if m.group(0).startswith('\\section'):
            g, i = read_group(doc, m.end() - 1)
            C.reset()
            section = C.inline(g)
            if not m.group(1):
                secno += 1
                out.append(dict(kind='toc', section=section, current=secno, secs=secs))
            continue
        if m.group(3) == 'titlepage':
            out.append(dict(kind='titlepage', section=section))
            i = m.end()
            continue
        if m.group(3) == 'tableofcontents':
            out.append(dict(kind='outline', section=section, secs=secs))
            i = m.end()
            continue
        # a frame
        a, b = find_end(doc, m.end(), 'frame')
        fr = doc[m.end():a]
        i = b
        opts, j = read_opt(fr, 0)
        title, j = read_group(fr, skip_ws(fr, j))
        opts = (opts or '').split(',')
        parts = split_top(fr[j:], 'framebreak') if 'allowframebreaks' in opts else [fr[j:]]
        for k, part in enumerate(parts):
            C.reset()
            part = re.sub(r'^\{\}', '', part.strip())
            if '\\bibliography{' in part:
                out.append(dict(kind='bib', section=section, title=C.inline(title)))
                continue
            t = C.inline(title)
            if 'allowframebreaks' in opts:
                t += ' ' + ROMAN[k + 1]
            body, flags = container(part, T * 2, 'body')
            out.append(dict(kind='frame', section=section, title=t, body=body, flags=flags,
                            top='t' in opts, nonum='noframenumbering' in opts or nonumber))
    return out

if __name__ == '__main__':
    ps = pages()
    print(len(ps), 'pages;', 'unknown:', C.unknown)
    for n, p in enumerate(ps, 1):
        print(n, p['kind'], p.get('title', '')[:60])
