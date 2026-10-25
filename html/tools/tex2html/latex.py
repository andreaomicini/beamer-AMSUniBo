"""TeX to the HTML of AMSUniBo/html: the subset its decks use, grown one deck at a time."""
import re, html as H
from deck import CFG, ROOT, path

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def strip_comments(s):
    return re.sub(r'(?<!\\)%[^\n]*\n[ \t]*', '', s)

# ---------------------------------------------------------------- bracket readers
def skip_ws(s, i):
    while i < len(s) and s[i] in ' \t\n':
        i += 1
    return i

def read_group(s, i):
    """s[i] == '{': return (inner, index after the closing brace)"""
    assert s[i] == '{', s[i:i + 40]
    depth = 0
    for j in range(i, len(s)):
        c = s[j]
        if c == '\\':
            continue
        if c == '{' and (j == 0 or s[j - 1] != '\\'):
            depth += 1
        elif c == '}' and s[j - 1] != '\\':
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
    raise ValueError('unbalanced ' + s[i:i + 60])

def read_arg(s, i):
    i = skip_ws(s, i)
    if s[i] == '{':
        return read_group(s, i)
    if s[i] == '\\':
        m = re.match(r'\\([A-Za-z]+|.)', s[i:])
        return m.group(0), i + len(m.group(0))
    return s[i], i + 1

def read_opt(s, i):
    j = skip_ws(s, i)
    if j < len(s) and s[j] == '[':
        depth = 0
        for k in range(j, len(s)):
            if s[k] == '{':
                depth += 1
            elif s[k] == '}':
                depth -= 1
            elif s[k] == ']' and depth == 0:
                return s[j + 1:k], k + 1
    return None, i

def find_end(s, i, env):
    """index of the \\end{env} matching a \\begin{env} whose body starts at i"""
    depth = 1
    pat = re.compile(r'\\(begin|end)\{' + re.escape(env) + r'\}')
    for m in pat.finditer(s, i):
        depth += 1 if m.group(1) == 'begin' else -1
        if depth == 0:
            return m.start(), m.end()
    raise ValueError('no end for ' + env)

def split_top(s, cmd):
    """split s at top-level occurrences of \\cmd (not inside groups or nested envs)"""
    parts, depth, envd, last, i = [], 0, 0, 0, 0
    pat = re.compile(r'\\' + cmd + r'(?![A-Za-z])')
    while i < len(s):
        c = s[i]
        if c == '\\':
            if s.startswith('\\begin{', i):
                envd += 1
            elif s.startswith('\\end{', i):
                envd -= 1
            elif depth == 0 and envd == 0 and pat.match(s, i):
                parts.append(s[last:i])
                i += len(cmd) + 1
                last = i
                continue
            i += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    parts.append(s[last:])
    return parts

# ---------------------------------------------------------------- acronyms
def parse_kv(s):
    out, i = {}, 0
    while i < len(s):
        i = skip_ws(s, i)
        m = re.match(r'([a-z]+)\s*=\s*', s[i:])
        if not m:
            break
        k = m.group(1)
        i += m.end()
        if s[i] == '{':
            v, j = read_group(s, i)
            # a value like {F}oundation ... keeps running to the comma
            k2 = j
            while k2 < len(s) and s[k2] != ',':
                if s[k2] == '{':
                    _, k2 = read_group(s, k2)
                else:
                    k2 += 1
            if s[j:k2].strip():
                v = s[i:k2]
            i = k2 + 1
        else:
            k2, depth = i, 0
            while k2 < len(s) and not (s[k2] == ',' and depth == 0):
                depth += {'{': 1, '}': -1}.get(s[k2], 0)
                k2 += 1
            v = s[i:k2]
            i = k2 + 1
        out[k] = v.strip()
    return out

def load_acronyms():
    s = ''.join(strip_comments(open(ROOT / f).read()) for f in CFG.get('acronyms', []))
    acr = {}
    for m in re.finditer(r'\\DeclareAcronym\{([^}]+)\}', s):
        body, _ = read_group(s, skip_ws(s, m.end()))
        acr[m.group(1)] = parse_kv(body)
    return acr

# ---------------------------------------------------------------- bibliography labels
def load_bbl():
    s = open(path('bbl')).read()
    items = re.split(r'\\bibitem', s)[1:]
    labels, entries = {}, []
    for it in items:
        lab, i = read_opt(it, 0)
        key, j = read_group(it, skip_ws(it, i))
        labels[key] = lab
        rest = it[j:].replace('\\end{thebibliography}', '')
        entries.append((key, lab, rest.strip()))
    return labels, entries

ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV',
         'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX', 'XXI', 'XXII']

# ---------------------------------------------------------------- the converter
# math symbols: relations, binary operators, ordinary symbols
MATHREL = {'approx': '≈', 'longrightarrow': '⟶', 'mapsto': '↦', 'neq': '≠', 'ne': '≠', 'geq': '≥', 'ge': '≥', 'leq': '≤',
           'sim': '∼', 'rightsquigarrow': '⇝', 'Downarrow': '⇓', 'Rightarrow': '⇒', 'equiv': '≡', 'in': '∈'}
MATHBIN = {'cdot': '⋅', 'wedge': '∧', 'vee': '∨'}
MATHORD = {'checkmark': '✓', 'varnothing': '∅', 'emptyset': '∅', 'infty': '∞', 'Delta': 'Δ', 'Xi': 'Ξ',
           'varepsilon': '\U0001D700', 'epsilon': '\U0001D716', 'ldots': '…', '%': '%', 'langle': '⟨', 'rangle': '⟩', 'Lambda': 'Λ'}
BLOCK_ENVS = {'block': '', 'alertblock': ' alert', 'exampleblock': ' example'}
SIZES = {'tiny', 'scriptsize', 'footnotesize', 'small', 'normalsize', 'large', 'Large', 'LARGE', 'smaller'}

class Conv:
    def __init__(self):
        self.acr = load_acronyms()
        self.labels, self.bbl = load_bbl()
        self.used = set()
        self.unknown = set()

    def reset(self):
        self.used = set()

    # ---- acronyms
    def acro(self, cmd, key):
        a = self.acr[key]
        star = cmd.endswith('*')
        c = cmd.rstrip('*')
        short = self.inline(a['short'])
        long_ = self.inline(a['long'])
        plural = c.endswith('p') and c not in ('\\acp',) or c == '\\acp'
        if c in ('\\acp', '\\acsp', '\\aclp', '\\Aclp', '\\acfp'):
            short_p, long_p = short + 's', long_ + 's'
        else:
            short_p, long_p = short, long_
        if c in ('\\Acl', '\\Aclp', '\\Ac', '\\Acp'):
            long_p = cap(long_p)
        first = key not in self.used
        if not star:
            self.used.add(key)
        if c in ('\\acs', '\\acsp'):
            return short_p
        if c in ('\\acl', '\\aclp', '\\Acl', '\\Aclp'):
            return long_p
        if c in ('\\acf', '\\acfp'):
            return f'{long_p} ({short_p})'
        if c in ('\\ac', '\\acp', '\\Ac', '\\Acp'):
            return f'{long_p} ({short_p})' if first else short_p
        raise ValueError(cmd)

    def cite(self, keys, cls='ccite', note=None):
        keys = [k.strip() for k in keys.split(',')]
        labs = [self.inline(self.labels[k]) for k in keys]
        if note:
            labs[-1] += ', ' + self.inline(note)
        if len(keys) == 1:
            return f'<a class="{cls}" href="#cite-{keys[0]}">[{labs[0]}]</a>'
        inner = ', '.join(f'<a href="#cite-{k}">{l}</a>' for k, l in zip(keys, labs))
        return f'<span class="{cls}">[{inner}]</span>'

    # ---- math
    def math(self, s):
        s = s.strip()
        # a lone symbol has no neighbours, so TeX puts no space around it
        lone = {'=': '=', '+': '+', '\\times': '×'}
        if s in lone:
            return lone[s]
        out, i = [], 0
        while i < len(s):
            c = s[i]
            if c == '\\':
                m = re.match(r'\\([A-Za-z]+|.)', s[i:])
                name = m.group(1)
                i += len(m.group(0))
                if name == 'text':
                    g, i = read_arg(s, i)
                    out.append(self.inline(g))
                elif name == 'mid':
                    out.append('<span class="rel thick">|</span>')
                elif name == 'mathcal':
                    g, i = read_arg(s, i)
                    out.append(''.join({'A': '𝒜', 'C': '𝒞', 'L': 'ℒ'}[c] for c in g))
                elif name == 'times':
                    out.append('<span class="rel">×</span>')
                elif name in ('rightarrow', 'to'):
                    out.append('<span class="rel">→</span>' if out else '→')
                elif name == 'phi':
                    out.append('\U0001D719')
                elif name in MATHREL:
                    out.append(f'<span class="rel">{MATHREL[name]}</span>' if out else MATHREL[name])
                elif name in MATHBIN:
                    out.append(f'<span class="bin">{MATHBIN[name]}</span>')
                elif name in MATHORD:
                    out.append(MATHORD[name])
                elif name == 'implies':
                    out.append('<span class="rel implies">⟹</span>' if out else '⟹')
                elif name in ('mathbb', 'mathtt', 'mathsf', 'mathit', 'mathrm', 'terminal', 'variable'):
                    g, i = read_arg(s, i)
                    if name == 'mathbb':
                        out.append(''.join({'P': 'ℙ', 'E': '𝔼', 'N': 'ℕ', 'R': 'ℝ'}[c] for c in g.strip()))
                    elif name in ('mathtt', 'terminal'):
                        out.append(f'<code>{esc(g)}</code>')
                    elif name == 'mathsf':
                        out.append(f'<span class="msf">{self.math(g)}</span>')
                    elif name == 'variable':   # the deck's \left\langle{#1\/}\right\rangle
                        out.append(f'⟨{self.math(g.replace(chr(92) + "/", ""))}⟩')
                    else:
                        out.append(self.math(g))
                elif name in ('frac',):
                    a, i = read_arg(s, i)
                    b, i = read_arg(s, i)
                    out.append(f'<span class="frac"><span class="num">{self.math(a)}</span><span class="den">{self.math(b)}</span></span>')
                elif name == 'stackrel':
                    a, i = read_arg(s, i)
                    b, i = read_arg(s, i)
                    out.append(f'<span class="rel stack"><span class="over">{self.math(a)}</span>{self.math(b)}</span>')
                elif name in ('left', 'right', 'big', 'Big'):
                    m2 = re.match(r'\\([A-Za-z]+)|(.)', s[i:])
                    i += len(m2.group(0))
                    d = MATHORD.get(m2.group(1), '') if m2.group(1) else ('' if m2.group(2) == '.' else esc(m2.group(2)))
                    out.append(d)
                elif name in ('sum', 'lim'):
                    out.append('<span class="op">∑</span>' if name == 'sum' else '<span class="op lim">lim</span>')
                elif name == 'begin':
                    env, i = read_arg(s, i)
                    a, b = find_end(s, i, env)
                    inner = s[i:a]
                    i = b
                    if env == 'array':
                        _, inner = read_arg(inner, 0)[0], inner[read_arg(inner, 0)[1]:]
                    rows = [r for r in re.split(r'\\\\', inner) if r.strip()]
                    cells = [[self.math(c) for c in r.split('&')] for r in rows]
                    if env == 'cases':
                        body = '<br>'.join(''.join(r) for r in cells)
                        out.append(f'<span class="cases" style="--rows: {len(rows)}"><span class="brace">{{</span><span class="rows">{body}</span></span>')
                    else:
                        out.append('<span class="array">' + ''.join(f'<span>{c}</span>' for r in cells for c in r) + '</span>')
                elif name in (',', ';', ' ', '!', 'quad'):
                    out.append({',': '\u2009', ';': '\u2005', ' ': ' ', '!': '', 'quad': '\u2003'}[name])
                else:
                    self.unknown.add('math\\' + name)
            elif c in '_^':
                g, i = read_arg(s, i + 1)
                g = self.math(g)
                tag = 'sub' if c == '_' else 'sup'
                # both: TeX stacks them after the base
                nxt = skip_ws(s, i)
                if nxt < len(s) and s[nxt] in '_^' and s[nxt] != c:
                    g2, i = read_arg(s, nxt + 1)
                    sub, sup = (g, self.math(g2)) if c == '_' else (self.math(g2), g)
                    out.append(f'<span class="subsup"><sup>{sup}</sup><sub>{sub}</sub></span>')
                else:
                    out.append(f'<{tag}>{g}</{tag}>')
            elif c == '{':
                g, i = read_group(s, i)
                out.append(self.math(g))
            elif c == '-' and out:
                out.append('<span class="bin">−</span>'); i += 1
            elif c == '-':
                out.append('−'); i += 1
            elif c in '<>':
                out.append(f'<span class="rel">{esc(c)}</span>'); i += 1
            elif c == "'":
                out.append('′'); i += 1
            elif c in ',;' and out and i + 1 < len(s):   # punctuation: a thin space after it, 3mu
                out.append(f'{c}<span class="mthin"></span>'); i += 1
            elif c == '=' and out and re.fullmatch(r'<span class="rel">[^<]*</span>', out[-1]):
                out[-1] = out[-1][:-7] + '=</span>'; i += 1   # consecutive relations: one spacing, as ::=
            elif c == ':' and out and re.fullmatch(r'<span class="rel">[^<]*</span>', out[-1]):
                out[-1] = out[-1][:-7] + ':</span>'; i += 1
            elif c == ':':
                out.append('<span class="rel">:</span>' if out else ':'); i += 1
            elif c == '=':
                out.append('<span class="rel">=</span>'); i += 1
            elif c == '+':
                out.append('<span class="rel">+</span>'); i += 1
            elif c.isalpha():
                out.append(f'<i>{c}</i>'); i += 1
            elif c in ' \t\n':
                i += 1
            else:
                out.append(esc(c)); i += 1
        return ''.join(out)

    # ---- inline text
    def inline(self, s):
        out, i = [], 0
        while i < len(s):
            c = s[i]
            if c == '\\':
                m = re.match(r'\\([A-Za-z]+\*?|.)', s[i:])
                name = m.group(0)
                i += len(name)
                r, i = self.command(name, s, i)
                out.append(r)
            elif c == '{':
                g, i = read_group(s, i)
                out.append(self.group(g))
            elif c == '$':
                j = s.index('$', i + 1)
                out.append(self.math(s[i + 1:j]))
                i = j + 1
            elif c == '~':
                out.append('\u00a0'); i += 1
            elif s.startswith('---', i):
                out.append('—'); i += 3
            elif s.startswith('--', i):
                out.append('–'); i += 2
            elif s.startswith('``', i):
                out.append('“'); i += 2
            elif s.startswith("''", i):
                out.append('”'); i += 2
            elif c == '`':
                out.append('‘'); i += 1
            elif c == "'":
                out.append('’'); i += 1
            elif c in ' \t\n':
                j = i
                while j < len(s) and s[j] in ' \t\n':
                    j += 1
                out.append(' ')
                i = j
            else:
                out.append(esc(c)); i += 1
        return ''.join(out)

    def group(self, g):
        """a brace group: a declaration inside it scopes to it"""
        m = re.match(r'\s*\\(tiny|scriptsize|footnotesize|small|large|Large|LARGE|smaller|bfseries|em|it|sl|sf|sc|itshape)(?![A-Za-z])\s*', g)
        if m:
            d = m.group(1)
            inner = self.inline(g[m.end():])
            if d in SIZES and inner.strip().startswith('\x00disp:<div class="displaymath">') and inner.strip().endswith('\x00'):
                return inner.strip().replace('class="displaymath"', f'class="displaymath {d}"', 1)
            tag = {'bfseries': ('<b>', '</b>'), 'em': ('<i>', '</i>'), 'it': ('<span class="it">', '</span>'), 'sl': ('<i>', '</i>'), 'itshape': ('<i>', '</i>'),
                   'sf': ('', ''), 'sc': ('<span class="sc">', '</span>')}.get(d, (f'<span class="{d}">', '</span>'))
            return tag[0] + inner + tag[1]
        return self.inline(g)

    def command(self, name, s, i):
        A = lambda: read_arg(s, i)
        simple = {'\\&': '&amp;', '\\_': '_', '\\%': '%', '\\#': '#', '\\ ': ' ', '\\,': '\u2009',
                  '\\ldots': '<span class="ldots">...</span>', '\\\\': '<br>', '\\-': '',
                  '\\refname': 'References', '\\par': '\n\n', '\\relax': ''}
        if name in simple:
            if name == '\\ldots' and s.startswith('{}', i):
                i += 2
            elif re.match(r'\\[A-Za-z]+$', name):
                while i < len(s) and s[i] in ' \t\n':   # TeX skips the spaces after a control word
                    i += 1
            return simple[name], i
        n = name[1:]
        if n in ('emph', 'alert', 'aalert', 'textbf', 'textsc', 'texttt', 'textit', 'textsf'):
            g, i = A()
            t = {'emph': ('<em>', '</em>'), 'alert': ('<span class="alert">', '</span>'),
                 'aalert': ('<span class="aalert">', '</span>'), 'textbf': ('<b>', '</b>'),
                 'textsc': ('<span class="sc">', '</span>'), 'texttt': ('<code>', '</code>'),
                 'textit': ('<i>', '</i>'), 'textsf': ('<span class="sf">', '</span>')}[n]
            return t[0] + self.inline(g) + t[1], i
        if re.match(r'[aA]c[a-z]*\*?$', n) and n.rstrip('*') in (
                'ac', 'acs', 'acl', 'acf', 'acp', 'acsp', 'aclp', 'Aclp', 'Acl', 'Ac', 'Acp', 'acfp'):
            g, i = A()
            return self.acro(name, g), i
        if n == 'ccite':
            note, i = read_opt(s, i)
            g, i = read_arg(s, i)
            return self.cite(g, 'ccite', note), i
        if n == 'cccite':
            note, i = read_opt(s, i)
            g, i = read_arg(s, i)
            return self.cite(g, 'ccite cccite', note), i
        if name == '\\[':   # a display: its own line, centred
            j = s.index('\\]', i)
            return f'\x00disp:<div class="displaymath">{self.math(s[i:j])}</div>\x00', j + 2
        if n == 'href':
            u, i = A()
            g, i = read_arg(s, i)
            return f'<a href="{H.escape(u.replace(chr(92), ""))}">{self.inline(g)}</a>', i
        if n == 'hhref':   # the deck's: grey, scriptsize, typewriter, underlined
            u, i = A()
            g, i = read_arg(s, i)
            return f'<a class="hhref" href="{H.escape(u.replace(chr(92), ""))}">{self.inline(g)}</a>', i
        if n == 'hint':   # the deck's: \hfill{\scriptsize \alert{!} {\color{gray}#1}}
            g, i = A()
            return f'\x00disp:<p class="hint"><span class="alert">!</span> <span class="grey">{self.inline(g)}</span></p>\x00', i
        if n == 'vspace':
            g, i = A()
            m = re.fullmatch(r'\s*(-?[0-9.]+)\s*(cm|mm|pt|em|ex)\s*', g)
            v = float(m.group(1)) * {'cm': 28.4528, 'mm': 2.84528, 'pt': 1, 'em': 10.95, 'ex': 4.7}[m.group(2)]
            return f'\x00vspace:{v:.2f}\x00', i
        if n == 'setcounter':
            c, i = A()
            v, i = read_arg(s, i)
            return f'\x00counter:{v.strip()}\x00', i
        if n == '@':
            return '', i
        if n in ('newcommand', 'renewcommand'):   # a local definition: it prints nothing
            _, i = A()
            _, i = read_arg(s, i)
            return '', i
        if n == 'cite':
            g, i = A()
            return self.cite(g, 'bibref'), i
        if n == 'texorpdfstring':
            g, i = A()
            _, i = read_arg(s, i)
            return self.inline(g), i
        if n in ('uurl', 'url', 'uuurl'):
            g, i = A()
            cls = {'uurl': 'uurl', 'url': 'url', 'uuurl': 'uuurl'}[n]
            return f'<a class="{cls}" href="{H.escape(g.replace(chr(92), ""))}">{esc(g.replace(chr(92), ""))}</a>', i
        if n == 'apice':
            kind, i = A()
            nm, i = read_arg(s, i)
            host = {'talk': 'talks', 'pub': 'pubs', 'course': 'courses', 'event': 'events'}[kind]
            return f'<a class="apice" href="https://{host}.apice.unibo.it/{nm}">{host}.apice.unibo.it/{nm}</a>', i
        names = CFG.get('macros', {})   # the deck's own name macros, as plain text
        if n in names:
            if s.startswith('{}', i):
                i += 2
            return names[n], i
        if n in ('medskip', 'smallskip', 'bigskip'):
            if s.startswith('{}', i):
                i += 2
            return f'\x00{n}\x00', i
        if n in ('centering', 'vfill', 'hfill'):
            if s.startswith('{}', i):
                i += 2
            return f'\x00{n}\x00', i
        if n in SIZES:
            if s.startswith('{}', i):
                i += 2
            # a declaration: scope it to the rest of the current text
            rest = self.inline(s[i:])
            return f'<span class="{n}">{rest}</span>', len(s)
        if n == 'tt':
            return '<code>' + self.inline(s[i:]) + '</code>', len(s)
        if n in ('bfseries', 'em', 'it', 'sf', 'sc'):
            rest = self.inline(s[i:])
            return self.group('\\' + n + ' ' + s[i:]), len(s)
        if n == 'ensuremath':
            g, i = A()
            return self.math(g), i
        if n == 'i':
            return 'ı', i
        if n in ('L', 'l', 'o', 'O', 'ss', 'aa'):
            return {'L': 'Ł', 'l': 'ł', 'o': 'ø', 'O': 'Ø', 'ss': 'ß', 'aa': 'å'}[n], i
        if n in ("'", '"', '`', '^', '~', 'u', 'v', 'c'):
            g, i = A()
            g = g.strip('{}')
            acc = {"'": '\u0301', '"': '\u0308', '`': '\u0300', '^': '\u0302', '~': '\u0303', 'u': '\u0306', 'v': '\u030c', 'c': '\u0327'}[n]
            import unicodedata
            base = 'i' if g in ('\\i', 'ı') else g
            return unicodedata.normalize('NFC', base + acc), i
        if n == 'newblock':
            return '\x00newblock\x00', i
        if n == 'apicepubpar':
            g, i = A()
            return f'<a class="apicepubpar" href="https://pubs.apice.unibo.it/{g}">APICe</a>', i
        if n == 'dddoi':
            g, i = A()
            g = g.replace('\\', '')
            return f'<a class="dddoi" href="https://doi.org/{H.escape(g)}">DOI:{esc(g)}</a>', i
        self.unknown.add(name)
        return '', i


def cap(h):
    """capitalise the first letter of an HTML string"""
    m = re.match(r'((?:<[^>]+>)*)(.)', h)
    return m.group(1) + m.group(2).upper() + h[m.end():]
