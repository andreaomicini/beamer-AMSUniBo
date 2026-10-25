"""\\lstinputlisting -> the HTML of a listing, as the listings package sets it.
columns=fixed: each token (a run of letters and digits, or of other characters) sits in a box of
n x basewidth, 0.6 of the typewriter quad, with its characters spread evenly inside it; a space is a
box of its own. The typewriter quad is two characters, so the box is 0.6375em a character for
0.53125em of glyph: the spread is 0.10625em * n / (n + 1), before and between the characters."""
import re
from latex import esc

JAVA = set('''abstract boolean break byte case catch char class const continue default do double else extends
false final finally float for goto if implements import instanceof int interface label long native new null
package private protected public return short static super switch synchronized this throw throws transient
true try void volatile while'''.split())
SOL1 = set('''anonymous assembly assert balance break call callcode case catch class constant continue contract
debugger default delegatecall delete do else event export external false finally for function gas if implements
import in indexed instanceof interface internal is length library log0 log1 log2 log3 log4 memory modifier new
payable pragma private protected public pure push require return returns revert selfdestruct send storage struct
suicide super switch then this throw transfer true try typeof using value view while with addmod ecrecover
keccak256 mulmod ripemd160 sha256'''.split())
SOL2 = set('''address bool byte bytes enum int mapping string uint var void ether finney szabo wei days hours
minutes seconds weeks years'''.split()) | {f'{t}{k}' for t in ('int', 'uint') for k in range(8, 257, 8)} \
    | {f'bytes{k}' for k in range(1, 33)}
SOL3 = set('''block blockhash coinbase difficulty gaslimit number timestamp msg data gas sender sig value now tx
gasprice origin'''.split())

def classify(lang, tok):
    """the class of an identifier token, '' for none"""
    if lang == 'Solidity':
        t = tok.lower()   # sensitive=false
        return 'kw' if t in SOL1 else 'kw2' if t in SOL2 else 'kw3' if t in SOL3 else 'id'
    return 'kw' if tok in JAVA else ''

def box(text, cls=''):
    n = len(text)
    s = round(0.10625 * n / (n + 1), 5)
    c = f' {cls}' if cls else ''
    return f'<span class="tok{c}" style="--s: {s}em">{esc(text)}</span>'

def line_html(line, lang, state):
    """one source line; state['comment'] carries a /* */ comment across lines"""
    out, i = [], 0
    while i < len(line):
        if state.get('comment'):
            j = line.find('*/', i)
            seg = line[i:] if j < 0 else line[i:j + 2]
            if j >= 0:
                state['comment'] = False
            out += [x for x in tokens(seg, 'com')]
            i += len(seg)
            continue
        if line.startswith('//', i):
            out += tokens(line[i:], 'com')
            break
        if line.startswith('/*', i):
            state['comment'] = True
            continue
        c = line[i]
        if c in '"\'' and (lang == 'Solidity' or c == '"'):
            j = line.find(c, i + 1)
            j = len(line) - 1 if j < 0 else j
            out += tokens(line[i:j + 1], 'str')
            i = j + 1
            continue
        m = re.match(r'[A-Za-z_$@][A-Za-z0-9_$@]*|[0-9]+|[ ]+|[^A-Za-z0-9_$@ "\']+', line[i:])
        t = m.group(0)
        if t[0] == ' ':
            out.append(f'<span class="sp" style="--n: {len(t)}"> </span>')
        elif re.match(r'[A-Za-z_$@]', t):
            out.append(box(t, classify(lang, t)))
        else:
            out.append(box(t))
        i += len(t)
    return ''.join(out)

def tokens(seg, cls):
    out = []
    for m in re.finditer(r'[A-Za-z0-9_$@]+|[ ]+|[^A-Za-z0-9_$@ ]+', seg):
        t = m.group(0)
        out.append(f'<span class="sp" style="--n: {len(t)}"> </span>' if t[0] == ' ' else box(t, cls))
    return out

def listing(src, opts, inline):
    """the listing of file src; opts the optional argument; inline converts TeX text"""
    o = {}
    for m in re.finditer(r'(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|[^,]*)', opts or ''):
        v = m.group(2).strip()
        o[m.group(1)] = v[1:-1] if v.startswith('{') else v
    lang = o.get('language', 'Java')
    size = 'tiny' if '\\tiny' in o.get('basicstyle', '') else 'scriptsize'
    code = open(src).read().expandtabs(2).rstrip('\n').split('\n')
    state = {}
    lines = [line_html(l.rstrip(), lang, state) for l in code]
    title = ''
    if 'title' in o:
        t = inline(o['title'])
        if '\x00hfill\x00' in t:
            a, b = t.split('\x00hfill\x00', 1)
            title = f'<div class="lst-title split"><span>{a.strip()}</span><span>{b.strip()}</span></div>'
        else:
            title = f'<div class="lst-title">{t.strip()}</div>'
    frame = o.get('frame', 'single')
    return (f'<div class="listing {size} lang-{lang.lower()} frame-{frame}">' + title
            + '<pre>' + '\n'.join(lines) + '</pre></div>')
