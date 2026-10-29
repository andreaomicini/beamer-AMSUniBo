"""TeX to the HTML of AMSUniBo/html: the subset its decks use, grown one deck at a time."""
import re, html as H
from deck import CFG, ROOT, path

# \mathcal: Unicode's mathematical script capitals, but for the eight it keeps in Letterlike Symbols
# cmssi10's italic corrections, in em (tftopl cmssi10): the deck's math letters are sans italic
CMSSI_IC = {'B': 0.0829, 'C': 0.1198, 'D': 0.0755, 'E': 0.1198, 'F': 0.1337, 'G': 0.1198, 'H': 0.0809, 'I': 0.1337,
            'J': 0.0809, 'K': 0.1198, 'M': 0.0809, 'N': 0.0809, 'O': 0.0755, 'P': 0.0829, 'Q': 0.0755, 'R': 0.0829,
            'S': 0.0921, 'T': 0.1337, 'U': 0.0809, 'V': 0.1615, 'W': 0.1615, 'X': 0.1337, 'Y': 0.1726, 'Z': 0.1198,
            'a': 0.0098, 'b': 0.0306, 'c': 0.0834, 'd': 0.0948, 'e': 0.0678, 'f': 0.2171, 'g': 0.1084, 'h': 0.0178,
            'i': 0.0972, 'j': 0.0916, 'k': 0.0834, 'l': 0.0948, 'm': 0.0178, 'n': 0.0178, 'o': 0.0661, 'p': 0.0389,
            'q': 0.0417, 'r': 0.1084, 's': 0.0778, 't': 0.0722, 'u': 0.0417, 'v': 0.1084, 'w': 0.1084, 'x': 0.0917,
            'y': 0.1084, 'z': 0.0875}
# rsfs10's advance widths plus italic corrections, in em (tftopl rsfs10): a math font (space 0), so TeX
# adds each letter's italic correction
RSFS = {'A': 1.0318, 'B': 0.9484, 'C': 0.8351, 'D': 0.8681, 'E': 0.7475, 'F': 1.0318, 'G': 0.7828, 'H': 1.2661,
        'I': 1.001, 'J': 1.2435, 'K': 1.2262, 'L': 1.0656, 'M': 1.2401, 'N': 1.254, 'O': 0.8187, 'P': 1.0934,
        'Q': 0.9159, 'R': 0.9126, 'S': 1.0596, 'T': 1.0378, 'U': 1.0581, 'V': 0.8973, 'W': 1.0805, 'X': 1.2045,
        'Y': 1.0035, 'Z': 1.0616}
MATHCAL = {'B': 'ℬ', 'E': 'ℰ', 'F': 'ℱ', 'H': 'ℋ', 'I': 'ℐ', 'L': 'ℒ', 'M': 'ℳ', 'R': 'ℛ'}

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
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == '\\':               # an escape takes the next character with it: \{ \} and \\ alike
            j += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
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

DELIMS = {'{': '{', '}': '}', 'lbrace': '{', 'rbrace': '}', 'langle': '⟨', 'rangle': '⟩', '|': '‖', 'Vert': '‖',
          'vert': '|', 'lfloor': '⌊', 'rfloor': '⌋', 'lceil': '⌈', 'rceil': '⌉'}

def read_delim(s, i):
    """the delimiter after \\left, \\right or \\big: (its text, index after it); '.' is none"""
    m = re.match(r'\s*(?:\\([A-Za-z]+|.)|(.))', s[i:])
    if not m:
        return '', i
    d = DELIMS.get(m.group(1), '') if m.group(1) else ('' if m.group(2) == '.' else m.group(2))
    return esc(d), i + len(m.group(0))

def skip_verb(s, i):
    """s[i:] starts with \\verb: the index after its closing delimiter"""
    j = i + 5 + (s[i + 5:i + 6] == '*')
    return s.index(s[j], j + 1) + 1

def match_right(s, i):
    """the \\right that closes a \\left whose body starts at i: (its index, index after the word)"""
    depth, j = 1, i
    while j < len(s):
        if s.startswith('\\verb', j):
            j = skip_verb(s, j)
            continue
        m = re.match(r'\\(left|right)(?![A-Za-z])', s[j:])
        if m:
            depth += 1 if m.group(1) == 'left' else -1
            if depth == 0:
                return j, j + len(m.group(0))
            j += len(m.group(0))
            continue
        j += 2 if s[j] == '\\' else 1
    raise ValueError('no \\right for ' + s[i:i + 40])

def split_align(s):
    """an alignment's body (array, eqnarray) as rows: each {'cells': [...], 'pre': [...], 'after': len or None,
    'end': bool}; 'pre' holds what comes before the row: 'hline', or ('vskip', len) from \\noalign{\\vskip ...};
    'end' is whether the row ended with \\\\ (whose [len] is 'after'). Split at the top level only: not in a
    group, a nested environment or a \\verb"""
    rows, i = [], 0
    while True:
        pre = []
        while True:   # the row's leading \hline and \noalign
            i = skip_ws(s, i)
            if re.match(r'\\hline(?![A-Za-z])', s[i:]):
                pre.append('hline'); i += 6
            elif re.match(r'\\noalign(?![A-Za-z])', s[i:]):
                g, i = read_arg(s, i + 8)
                m = re.fullmatch(r'\s*\\vskip\s*(.*?)\s*', g)
                if m:
                    pre.append(('vskip', m.group(1)))
            else:
                break
        cells, last, depth, envd, j, end, after = [], i, 0, 0, i, False, None
        while j < len(s):
            c = s[j]
            if c == '\\':
                if s.startswith('\\verb', j):
                    j = skip_verb(s, j); continue
                if s.startswith('\\begin{', j):
                    envd += 1
                elif s.startswith('\\end{', j):
                    envd -= 1
                elif s.startswith('\\\\', j) and depth == 0 and envd == 0:
                    cells.append(s[last:j]); j += 2; end = True
                    if j < len(s) and s[j] == '*':
                        j += 1
                    if s[skip_ws(s, j):skip_ws(s, j) + 1] == '[':
                        after, j = read_opt(s, j)
                    break
                j += 2; continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            elif c == '&' and depth == 0 and envd == 0:
                cells.append(s[last:j]); last = j + 1
            j += 1
        else:
            cells.append(s[last:])
        i = j
        if not end and not ''.join(cells).strip() and len(cells) == 1:
            if pre:
                rows.append({'cells': [], 'pre': pre, 'after': None, 'end': False})
            break
        rows.append({'cells': cells, 'pre': pre, 'after': after, 'end': end})
        if not end:
            break
    return rows

def at_width(x):
    """the width of an @{...} that holds only spaces (~, \\ , \\, \\; \\quad \\qquad), in em; None for anything else"""
    w = {'~': 0.3333, '\\ ': 0.3333, '\\,': 0.1667, '\\;': 0.2778, '\\:': 0.2222, '\\quad': 1, '\\qquad': 2}
    toks = re.findall(r'\\[A-Za-z]+|\\.|\S', x)
    return sum(w[t] for t in toks) if all(t in w for t in toks) else None

def array_spec(spec):
    """a column spec as columns: [{'al': l|c|r, 'pl': css, 'pr': css, 'bl': bool, 'br': bool}], each with
    \\arraycolsep on either side unless an @{...} stands there, and its vertical rules"""
    while '*{' in spec:   # *{n}{cols}
        m = re.search(r'\*\{(\d+)\}', spec)
        g, k = read_group(spec, m.end())
        spec = spec[:m.start()] + g * int(m.group(1)) + spec[k:]
    cols, i, pending_at, pending_bar = [], 0, None, False
    sep = 'calc(5 * var(--pt))'
    while i < len(spec):
        c = spec[i]
        if c in 'lcrp':
            if c == 'p':
                _, i = read_group(spec, i + 1); i -= 1; c = 'l'
            cols.append({'al': c, 'pl': pending_at if pending_at is not None else sep, 'pr': sep,
                         'bl': pending_bar, 'br': False})
            pending_at, pending_bar = None, False
        elif c == '|':
            if cols and pending_at is None and not pending_bar:
                cols[-1]['br'] = True
            else:
                pending_bar = True
        elif c == '@':
            g, i = read_group(spec, i + 1); i -= 1
            w = at_width(g)
            css = f'{w:g}em' if w is not None else '0px'
            if cols and pending_at is None and not pending_bar and cols[-1]['pr'] == sep and not cols[-1]['br']:
                cols[-1]['pr'] = css
            else:
                pending_at = css
        i += 1
    return cols

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
    if not path('bbl').exists():   # a deck with no bibliography (experiment 8)
        return {}, []
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
           'sim': '∼', 'rightsquigarrow': '⇝', 'Downarrow': '⇓', 'Rightarrow': '⇒', 'equiv': '≡', 'in': '∈',
           'models': '⊨', 'subseteq': '⊆', 'leftarrow': '←', 'gets': '←', 'uparrow': '↑', 'downarrow': '↓'}
MATHBIN = {'cdot': '⋅', 'wedge': '∧', 'vee': '∨', 'circ': '∘', 'diamond': '⋄', 'rhd': '⊳', 'lhd': '⊲', 'land': '∧',
           'lor': '∨', 'cup': '∪', 'cap': '∩', 'setminus': '∖', 'oplus': '⊕', 'otimes': '⊗'}
# lowercase Greek: Unicode's mathematical italic, in TeX's order (\epsilon and \phi are the variant forms)
GREEK = {g: chr(0x1D6FC + k) for k, g in enumerate(
    'alpha beta gamma delta varepsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho varsigma '
    'sigma tau upsilon varphi chi psi omega'.split())}
GREEK.update({'epsilon': '\U0001D716', 'vartheta': '\U0001D717', 'phi': '\U0001D719', 'varrho': '\U0001D71A',
              'varpi': '\U0001D71B'})
# capital Greek, upright as TeX sets them; a few more ordinary symbols
GREEK.update({g: c for g, c in zip('Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega'.split(), 'ΓΔΘΛΞΠΣΥΦΨΩ')})
GREEK.update({'bot': '⊥', 'top': '⊤', 'forall': '∀', 'neg': '¬', 'lnot': '¬', 'partial': '∂', 'nabla': '∇', '_': '_',
              '#': '#', '&': '&amp;', '$': '$'})
# \mathbb: Unicode's double-struck capitals, seven of them in Letterlike Symbols
MATHBB = {'C': 'ℂ', 'H': 'ℍ', 'N': 'ℕ', 'P': 'ℙ', 'Q': 'ℚ', 'R': 'ℝ', 'Z': 'ℤ'}

def mathbb(c):
    return MATHBB.get(c) or (chr(0x1D538 + ord(c) - 65) if 'A' <= c <= 'Z' else c)

def tex_len(v):
    """a TeX length as CSS: pt, mm, cm, in in var(--pt); em and ex in the font's own, as TeX's are"""
    m = re.fullmatch(r'\s*(-?[0-9]*\.?[0-9]+)\s*(pt|mm|cm|in|bp|em|ex)\s*', v or '')
    if not m:
        return None
    x, u = float(m.group(1)), m.group(2)
    if u in ('em', 'ex'):
        return f'{x:g}{u}'
    return f'calc({x * {"pt": 1, "mm": 2.84528, "cm": 28.4528, "in": 72.27, "bp": 1.00375}[u]:.2f} * var(--pt))'
MATHORD = {'checkmark': '✓', 'varnothing': '∅', 'emptyset': '∅', 'infty': '∞', 'Delta': 'Δ', 'Xi': 'Ξ',
           'varepsilon': '\U0001D700', 'epsilon': '\U0001D716', 'ldots': '…', '%': '%', 'langle': '⟨', 'rangle': '⟩', 'Lambda': 'Λ',
           'Theta': 'Θ', 'ell': 'ℓ', 'wp': '℘', 'exists': '∃', 'cdots': '⋯', 'dots': '…', 'bigwedge': '⋀',
           'pi': '\U0001D70B', 'beta': '\U0001D6FD', 'theta': '\U0001D703', 'omega': '\U0001D714', 'sigma': '\U0001D70E',
           '{': '{', '}': '}'}
BLOCK_ENVS = {'block': '', 'alertblock': ' alert', 'exampleblock': ' example'}
SIZES = {'tiny', 'scriptsize', 'footnotesize', 'small', 'normalsize', 'large', 'Large', 'LARGE', 'huge', 'smaller'}

class Conv:
    def __init__(self):
        self.acr = load_acronyms()
        self.labels, self.bbl = load_bbl()
        self.used = set()
        self.unknown = set()

    def reset(self):
        self.used = set()
        self.footnotes = []   # this frame's footnotes: (mark, html, covered)

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

    # ---- alignments
    def alignment(self, rows, cols, kind):
        """an array or an eqnarray as a grid of its columns: \\hline as a rule across them (two, \\doublerulesep
        apart), \\noalign{\\vskip} and \\\\[<len>] as space between rows; an eqnarray adds \\jot after every
        \\\\ (latex.ltx), and sets its middle column in the text style"""
        sep, two, none = 'calc(5 * var(--pt))', 'calc(10 * var(--pt))', '0px'
        if kind == 'eqnarray':   # latex.ltx: \hskip 2\arraycolsep before the second and the third column
            cols = [{'al': a, 'pl': pl, 'pr': none, 'bl': False, 'br': False} for a, pl in zip(cols, (none, two, two))]
        elif cols and isinstance(cols[0], str):   # \arraycolsep on either side
            cols = [{'al': a, 'pl': sep, 'pr': sep, 'bl': False, 'br': False} for a in cols]
        n, body, mt = len(cols), [], []
        for r in rows:
            k = 0
            while k < len(r['pre']):
                if r['pre'][k] == 'hline':
                    two = k + 1 < len(r['pre']) and r['pre'][k + 1] == 'hline'
                    body.append(f'<span class="hline{" double" if two else ""}"></span>')
                    k += 2 if two else 1
                    continue
                v = tex_len(r['pre'][k][1])
                if v and not v.startswith('-'):
                    body.append(f'<span class="vskip" style="height: {v}"></span>')
                elif v:
                    mt.append(v)
                k += 1
            if not r['cells']:
                continue
            after = tex_len(r['after']) if r['after'] else None
            if kind == 'eqnarray' and r['end']:
                after = f'calc(3 * var(--pt) + {after})' if after else 'calc(3 * var(--pt))'
            st = ([f'margin-top: {" + ".join(mt) if len(mt) == 1 else "calc(" + " + ".join(mt) + ")"}'] if mt else []) + (
                [f'margin-bottom: {after}'] if after else [])
            st = f' style="{"; ".join(st)}"' if st else ''
            mt = []
            q = 0
            for c in r['cells'] + [''] * n:
                if q >= n:
                    break
                m = re.match(r'\s*\\multicolumn\s*\{(\d+)\}', c)
                if m:   # \multicolumn{k}{spec}{text}: one cell over k columns, aligned and ruled as its spec says
                    k = int(m.group(1))
                    sp, j = read_group(c, skip_ws(c, m.end()))
                    g, _ = read_group(c, skip_ws(c, j))
                    mc = array_spec(sp)[0]
                    pad = f'padding: 0 {mc["pr"]} 0 {mc["pl"]}'
                    body.append(f'<span class="a{mc["al"]}" style="grid-column: span {k}; {pad}{st[8:-1] and "; " + st[8:-1]}">{self.math(g)}</span>')
                    q += k
                    continue
                col = cols[q]
                cs = [f'padding: 0 {col["pr"]} 0 {col["pl"]}']
                cs += ['border-left: calc(0.4 * var(--pt)) solid'] if col['bl'] else []
                cs += ['border-right: calc(0.4 * var(--pt)) solid'] if col['br'] else []
                st2 = st[:-1] + '; ' + '; '.join(cs) + '"' if st and cs else (f' style="{"; ".join(cs)}"' if cs else st)
                body.append(f'<span class="a{col["al"]}"{st2}>{self.math(c)}</span>')
                q += 1
        cls = 'array cols tex' + (' eqnarray' if kind == 'eqnarray' else '')
        return f'<span class="{cls}" style="--cols: {n}">{"".join(body)}</span>'

    def eqnarray(self, inner):
        """eqnarray(*): a display of three columns, right, centre, left, 2\\arraycolsep apart"""
        return f'<div class="displaymath">{self.alignment(split_align(inner), ["r", "c", "l"], "eqnarray")}</div>'

    # ---- math
    def math(self, s):
        s = s.strip()
        # a lone symbol has no neighbours, so TeX puts no space around it
        lone = {'=': '=', '+': '+', '\\times': '×'}
        if s in lone:
            return lone[s]
        m = re.fullmatch(r'\\([A-Za-z]+)', s)   # a binary operator alone is an ordinary symbol: no spaces
        if m and m.group(1) in MATHBIN:
            return MATHBIN[m.group(1)]
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
                elif name in ('textrm', 'textit', 'textbf', 'textsf', 'texttt', 'mbox'):   # text in math, as in text
                    g, i = read_arg(s, i)
                    out.append(self.inline(g) if name == 'mbox' else self.inline(f'\\{name}{{{g}}}'))
                elif name == 'verb':   # \verb|...|: the text as it is, in the typewriter face
                    k = s.index(s[i], i + 1)
                    out.append(f'<code>{esc(s[i + 1:k])}</code>')
                    i = k + 1
                elif name == 'left':   # \left ... \right: an inner atom, its delimiters at their natural size
                    d1, i = read_delim(s, i)
                    a, b = match_right(s, i)
                    d2, b = read_delim(s, b)
                    out.append(f'<span class="minner">{d1}{self.math(s[i:a])}{d2}</span>')
                    i = b
                elif name == 'kern':   # \kern<len>: that much space, or less
                    m2 = re.match(r'\s*(-?[0-9]*\.?[0-9]+\s*(?:pt|mm|cm|em|ex))', s[i:])
                    if m2:
                        i += len(m2.group(0))
                        out.append(f'<span class="mkern" style="margin-left: {tex_len(m2.group(1))}"></span>')
                elif name == 'not':   # a negated relation: Unicode's own where it has one, else a slash over it
                    m2 = re.match(r'\s*(?:\\([A-Za-z]+)|(.))', s[i:])
                    i += len(m2.group(0))
                    neg = {'rightarrow': '↛', 'to': '↛', 'leftarrow': '↚', 'in': '∉', 'equiv': '≢', 'subseteq': '⊈',
                           'models': '⊭', '=': '≠', 'sim': '≁'}
                    k2 = m2.group(1) or m2.group(2)
                    out.append(f'<span class="rel">{neg.get(k2) or (MATHREL.get(k2, k2) + chr(0x338))}</span>')
                elif name in ('xrightarrow', 'xleftarrow'):   # amsmath's: an arrow as long as its label, the label over it
                    _, i = read_opt(s, i)
                    g, i = read_arg(s, i)
                    out.append(f'<span class="rel"><span class="xarrow"><span class="over">{self.math(g)}</span>'
                               f'<span class="xa {name[1:5]}">{"→" if name == "xrightarrow" else "←"}</span></span></span>')
                elif name in ('quad', 'qquad'):   # 1em, 2em
                    out.append(f'<span class="mspace" style="--w: {1 if name == "quad" else 2}em"></span>')
                elif name in ('hline', 'noalign'):   # outside an alignment: nothing to draw
                    if name == 'noalign':
                        _, i = read_arg(s, i)
                elif name == 'mid':
                    out.append('<span class="rel thick">|</span>')
                elif name in ('big', 'Big', 'bigg', 'Bigg'):   # a delimiter at 1.2, 1.8, 2.4, 3 times its size
                    m2 = re.match(r'\s*(?:\\([A-Za-z]+|.)|(.))', s[i:])
                    i += len(m2.group(0))
                    d = (MATHORD.get(m2.group(1), m2.group(1)) if m2.group(1) else m2.group(2)) or ''
                    out.append(f'<span class="delim {name}">{esc(d)}</span>' if d != '.' else '')
                elif name == 'hspace':
                    g, i = read_arg(s, i)
                    out.append(f'<span class="mspace" style="--w: {g}"></span>')
                elif name == 'widetilde':
                    g, i = read_arg(s, i)
                    out.append(f'<span class="wtilde">{self.math(g)}</span>')
                elif name in ('arrowdown', 'arrowup', 'arrowleft'):   # the deck's TikZ arrows
                    out.append(f'<span class="{name}"></span>')
                elif name == 'mathscr':   # rsfs: Unicode's script capitals in rsfs10's widths
                    g, i = read_arg(s, i)
                    out.append(''.join(f'<span class="mscr" style="width: {RSFS[c]}em">'
                                       f'{MATHCAL.get(c, chr(0x1D49C + ord(c) - 65))}</span>' if c in RSFS else c for c in g))
                elif name in ('dots', 'ldots', 'cdots'):   # \mathinner of three \ldotp or \cdotp: punctuation, a thin space after each
                    out.append(f'<span class="mdots">{"..." if name != "cdots" else "⋅⋅⋅"}</span>')
                elif name == 'mathcal':
                    g, i = read_arg(s, i)
                    out.append(''.join(MATHCAL.get(c, chr(0x1D49C + ord(c) - 65) if 'A' <= c <= 'Z' else c) for c in g))
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
                elif name in GREEK:
                    out.append(GREEK[name])
                elif name == 'implies':
                    out.append('<span class="rel implies">⟹</span>' if out else '⟹')
                elif name in ('mathbb', 'mathtt', 'mathsf', 'mathit', 'mathrm', 'terminal', 'variable'):
                    g, i = read_arg(s, i)
                    if name == 'mathbb':
                        out.append(''.join(mathbb(c) for c in g if not c.isspace()))
                    elif name in ('mathtt', 'terminal'):   # typewriter, but for the math inside it, \mathit{t} say
                        for part in re.split(r'(\\math(?:it|rm|sf|bf|tt)\s*\{[^{}]*\})', g):
                            if part.startswith('\\math'):
                                out.append(self.math(part))
                            elif part:
                                out.append(f'<code>{esc(re.sub(r"\\([_{}%&#$])", r"\1", part))}</code>')
                    elif name == 'mathsf':
                        out.append(f'<span class="msf">{self.math(g)}</span>')
                    elif name == 'variable':   # the deck's \left\langle{#1\/}\right\rangle
                        out.append(f'⟨{self.math(g.replace(chr(92) + "/", ""))}⟩')
                    else:   # \mathit, \mathrm: a word in a text font, its letters not math letters
                        h = re.sub(r'<i(?: class="ic" style="[^"]*")?>([A-Za-z])</i>', r'\1', self.math(g))
                        # \mathit sets the letters in the text italic, as words; anything else keeps its math font
                        out.append(re.sub(r'(?<![<&#/])\b([A-Za-z]+)\b(?![^<]*>)', r'<i class="mit">\1</i>', h) if name == 'mathit'
                                   else f'<span class="mrm">{h}</span>')
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
                    spec = ''
                    if env == 'array':
                        _, k = read_opt(inner, 0)
                        spec, k = read_arg(inner, k)
                        inner = inner[k:]
                    al = split_align(inner)
                    rows = [r for r in al if ''.join(r['cells']).strip()]
                    cells = lambda: [[self.math(c) for c in r['cells']] for r in rows]
                    cs = array_spec(spec) if env == 'array' else []
                    cols = [c['al'] for c in cs]
                    plain = all(c['pl'] == c['pr'] == 'calc(5 * var(--pt))' and not c['bl'] and not c['br'] for c in cs)
                    if env == 'array' and (cols != ['r', 'c', 'l'] or not plain or any(r['pre'] or r['after'] for r in al)):
                        # any column spec: a grid of its columns, each aligned as the spec says; a short
                        # row's missing cells are empty (the {rcl} form below is experiment 6's)
                        out.append(self.alignment(al, cs, 'array'))
                    elif env == 'cases':
                        body = '<br>'.join(''.join(r) for r in cells())
                        out.append(f'<span class="cases" style="--rows: {len(rows)}"><span class="brace">{{</span><span class="rows">{body}</span></span>')
                    else:
                        out.append('<span class="array">' + ''.join(f'<span>{c}</span>' for r in cells() for c in r) + '</span>')
                elif name in (',', ';', ' ', '!'):
                    out.append({',': '\u2009', ';': '\u2005', ' ': ' ', '!': ''}[name])
                else:
                    self.unknown.add('math\\' + name)
            elif c in '_^':
                g, i = read_arg(s, i + 1)
                if re.fullmatch(r'\\(math[a-z]+|text[a-z]*|mbox)', g):   # _\mathbb{C}: the command takes its argument
                    g2, i = read_arg(s, i)
                    g += '{' + g2 + '}'
                g = self.math(g)
                tag = 'sub' if c == '_' else 'sup'
                # both: TeX stacks them after the base
                nxt = skip_ws(s, i)
                if nxt < len(s) and s[nxt] in '_^' and s[nxt] != c:
                    g2, i = read_arg(s, nxt + 1)
                    sub, sup = (g, self.math(g2)) if c == '_' else (self.math(g2), g)
                    out.append(f'<span class="subsup"><sup>{sup}</sup><sub>{sub}</sub></span>')
                elif out and re.fullmatch(r'<span class="rel[^"]*">.*</span>', out[-1], re.S) and out[-1].count('<span') == out[-1].count('</span>'):
                    out[-1] = out[-1][:-7] + f'<{tag}>{g}</{tag}></span>'   # a script on a relation: inside its spacing
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
            elif c == ':' and not out:   # relations opening a formula: no space before them, none between them
                m2 = re.match(r'[:=]+', s[i:])
                out.append(m2.group(0)); i += len(m2.group(0))
            elif c == ':':
                out.append('<span class="rel">:</span>'); i += 1
            elif c == '=':
                out.append('<span class="rel">=</span>'); i += 1
            elif c == '+':
                out.append('<span class="rel">+</span>'); i += 1
            elif c.isalpha():
                out.append(f'<i>{c}</i>'); i += 1
            elif c in ' \t\n':
                i += 1
            elif c == '~':   # \nobreakspace: the text font's interword space
                out.append('\u00a0'); i += 1
            else:
                out.append(esc(c)); i += 1
        h = ''.join(out)
        if CFG.get('italic_corrections'):
            # TeX's italic correction after a math letter in a text font (space > 0, cmssi here): kept unless
            # another letter of the font follows it (one word) or a subscript sits under it
            h = re.sub(r'<i>([A-Za-z])</i>(?!<i>|<sub>|<span class="subsup">)',
                       lambda m: f'<i class="ic" style="--ic: {CMSSI_IC[m.group(1)]}em">{m.group(1)}</i>'
                       if m.group(1) in CMSSI_IC else m.group(0), h)
        return h

    # ---- inline text
    def inline(self, s):
        out, i = [], 0
        while i < len(s):
            c = s[i]
            if c == '\\':
                m = re.match(r'\\([A-Za-z]+\*?|.)', s[i:], re.S)   # a backslash before a newline is a control space (C3b)
                name = m.group(0) if m.group(0) != '\\\n' else '\\ '
                i += len(name)
                r, i = self.command(name, s, i)
                out.append(r)
            elif c == '{':
                g, i = read_group(s, i)
                out.append(self.group(g))
            elif s.startswith('$$', i):   # plain TeX's display, as \[ \]
                j = s.index('$$', i + 2)
                out.append(f'\x00disp:<div class="displaymath">{self.math(s[i + 2:j])}</div>\x00')
                i = j + 2
            elif c == '$':
                j = s.index('$', i + 1)
                out.append(self.math(s[i + 1:j]))
                i = j + 1
            elif c == '~' and s.startswith('~~', i) and CFG.get('style') == 'AMSCesena':
                # a run of ties: spaces kept as they are, since Latin Modern's no-break space is wider than its
                # space in Firefox and not in WebKit (experiment 6's footline; AMSCesena only, so far)
                k = i
                while k < len(s) and s[k] == '~':
                    k += 1
                out.append('<span class="ties">' + ' ' * (k - i) + '</span>'); i = k
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
        c = re.match(r'\s*\\color\{([A-Za-z0-9]+)\}\s*', g)   # a palette colour (S5)
        if c:
            return f'<span style="color: var(--{c.group(1)})">' + self.group(g[c.end():]) + '</span>'
        m = re.match(r'\s*\\(tiny|scriptsize|footnotesize|small|large|Large|LARGE|smaller|bfseries|em|it|sl|sf|sc|itshape|ttfamily|normalfont|sffamily)(?![A-Za-z])\s*', g)
        if m:
            d = m.group(1)
            inner = self.group(g[m.end():])   # declarations may follow one another
            if d in SIZES and inner.strip().startswith('\x00disp:<div class="displaymath">') and inner.strip().endswith('\x00'):
                return inner.strip().replace('class="displaymath"', f'class="displaymath {d}"', 1)
            tag = {'bfseries': ('<b>', '</b>'), 'em': ('<i>', '</i>'), 'it': ('<span class="it">', '</span>'), 'sl': ('<i>', '</i>'), 'itshape': ('<i>', '</i>'),
                   'sf': ('', ''), 'sc': ('<span class="sc">', '</span>'), 'ttfamily': ('<code>', '</code>'), 'normalfont': ('', ''),
                   'sffamily': ('', '')}.get(d, (f'<span class="{d}">', '</span>'))
            return tag[0] + inner + tag[1]
        return self.inline(g)

    def command(self, name, s, i):
        A = lambda: read_arg(s, i)
        simple = {'\\&': '&amp;', '\\_': '_', '\\%': '%', '\\#': '#', '\\ ': ' ', '\\,': '\u2009',
                  '\\ldots': '<span class="ldots">...</span>', '\\dots': '<span class="ldots">...</span>', '\\\\': '<br>', '\\-': '',
                  '\\refname': 'References', '\\appendixname': 'Appendix', '\\/': '', '\\allowbreak': '<wbr>', '\\par': '\n\n', '\\relax': '', '\\{': '{', '\\}': '}', '\\selectfont': '',
                  '\\beamertemplatebookbibitems': '', '\\beamertemplatearticlebibitems': ''}
        if name == '\\\\' and re.match(r'\s*\[', s[i:]):   # \\[<len>]: the break, and that much more space
            o, j = read_opt(s, i)
            m = re.fullmatch(r'\s*(-?[0-9.]+)\s*(cm|mm|pt|em|ex)\s*', o or '')
            if m:
                v = float(m.group(1)) * {'cm': 28.4528, 'mm': 2.84528, 'pt': 1, 'em': 10.95, 'ex': 4.7}[m.group(2)]
                return f'<br><span class="brskip" style="--v: calc({v:.2f} * var(--pt))"></span>', j
        if name in ('\\footnote', '\\FOOTNOTECOV'):   # beamer's: a letter mark, the text at the frame's foot
            g, i = read_arg(s, i)
            mark = 'abcdefghij'[len(self.footnotes)]
            self.footnotes.append((mark, self.inline(g).strip(), name == '\\FOOTNOTECOV'))
            return f'<sup class="fnmark">{mark}</sup>', i
        if name == '\\SVNL':   # a line of a semiverbatim
            return '\x00svnl\x00', i + 2 if s.startswith('{}', i) else i
        if name == '\\NOALERT':   # \alert<...> off this slide: a span still, so the slides' elements line up
            g, i = read_arg(s, i)
            return f'<span class="noalert">{self.inline(g)}</span>', i
        if name == '\\SHOWSPAN':   # \uncover<...>{...} on this slide
            g, i = read_arg(s, i)
            return f'<span class="shown">{self.inline(g)}</span>', i
        if name == '\\COVSPAN':   # \uncover<...>{...} off this slide: its space kept, invisible
            g, i = read_arg(s, i)
            return f'<span class="covered">{self.inline(g)}</span>', i
        if name == '\\fontsize':   # \fontsize{s}{b}\selectfont: left to the corrections (S2)
            _, i = read_arg(s, i)
            _, i = read_arg(s, i)
            return '', i
        if name in ('\\frenchspacing', '\\nonfrenchspacing'):
            return '', i
        if name == '\\color':   # \color{c} outside a group: what follows in the container, in that colour
            c, i = read_arg(s, i)
            return f'<span style="color: var(--{c})">' + self.inline(s[i:]) + '</span>', len(s)
        if name == '\\textcolor':   # a palette colour of the theme, by its name: var(--<name>); or [rgb]{r,g,b} (C3b)
            model, i = read_opt(s, i) if s.startswith('[', i) else (None, i)
            c, i = read_arg(s, i)
            g, i = read_arg(s, i)
            if model == 'rgb':
                r, gg, b = (round(float(x) * 255) for x in c.split(','))
                return f'<span style="color: rgb({r}, {gg}, {b})">{self.inline(g)}</span>', i
            c = re.sub(r'[^A-Za-z0-9]', '', c)
            return f'<span style="color: var(--{c})">{self.inline(g)}</span>', i
        if name == '\\verb' and i < len(s):   # \verb|...|: the text as it is, in the typewriter face
            k = s.index(s[i], i + 1)
            return f'<code>{esc(s[i + 1:k])}</code>', k + 1
        if name in simple:
            if name in ('\\ldots', '\\dots') and s.startswith('{}', i):
                i += 2
            elif re.match(r'\\[A-Za-z]+$', name):
                while i < len(s) and s[i] in ' \t\n':   # TeX skips the spaces after a control word
                    i += 1
            return simple[name], i
        n = name[1:]
        if n == 'textit' and re.search(r'\\/\s*$', read_arg(s, i)[0]):   # \textit{...\/}: the last letter's italic correction
            g, i = A()
            g = re.sub(r'\\/\s*$', '', g)
            ic = CMSSI_IC.get(g[-1:])
            return (f'<i class="ic" style="--ic: {ic}em">' if ic else '<i>') + self.inline(g) + '</i>', i
        if n in ('emph', 'alert', 'aalert', 'textbf', 'textsc', 'texttt', 'textit', 'textsf', 'textrm'):
            g, i = A()
            t = {'emph': ('<em>', '</em>'), 'alert': ('<span class="alert">', '</span>'),
                 'aalert': ('<span class="aalert">', '</span>'), 'textbf': ('<b>', '</b>'),
                 'textsc': ('<span class="sc">', '</span>'), 'texttt': ('<code>', '</code>'), 'textrm': ('<span class="rm">', '</span>'),
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
        if n == 'mbox':
            g, i = A()
            return self.inline(g), i
        if n == 'center':   # \center{...} as a command: the center environment's list, its text centred
            g, i = A()
            return f'\x00disp:<p class="center">{self.inline(g)}</p>\x00', i
        if n == 'textasciicircum':
            if s.startswith('{}', i):
                i += 2
            return '^', i
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
