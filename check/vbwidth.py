#!/usr/bin/env python3
r"""Verbatim lines that really leave the text area in the built PDF.

Counting characters cannot decide it: how wide a line sets depends on the style's monospaced font,
on the size it is set at, and on what TeX does with it (a line too long for its box may be squeezed).
So the count is only the precondition: the source's verbatim lines longer than --min characters
(default 50) are the candidates, and each is looked up in the built PDF; only a line whose box starts
left of the text area or ends right of it is reported (Andrea, 2026-10-30: "il controllo dei
caratteri va fatto solo come precondizione per eventuali errori che poi si trovino effettivamente
nei PDF"). The text area is \textwidth, 342.30pt in every AMS style, centred on the page.

  vbwidth.py tex/<deck>.tex aux/<deck>.pdf [--min N]

Exit 1 when a line overflows. A candidate not found in the PDF (an overlay never shown, a line the
PDF text splits differently) is listed on stderr and not counted. Needs mutool (mupdf).

A line checked once is not checked again until it changes (Andrea, 2026-10-30: a suspicious line must
not raise a check on every run): the lines found inside the text area, or not found, are remembered
by their text in aux/<deck>.vbwidth, beside the build; a line that overflows is reported until it is
fixed. --all checks every candidate again.
"""
import hashlib, html, json, os, re, subprocess, sys
TEXTWIDTH = 342.2953
SLACK = 0.5

args = sys.argv[1:]
minimum = 50
recheck = '--all' in args
if recheck: args.remove('--all')
if '--min' in args:
    i = args.index('--min'); minimum = int(args[i + 1]); del args[i:i + 2]
tex, pdf = args

candidates, inside = [], False
for n, line in enumerate(open(tex, encoding='utf-8', errors='replace'), 1):
    s = line.rstrip('\n')
    if not inside and '\\begin{verbatim}' in s:
        inside = True
        continue
    if inside:
        if '\\end{verbatim}' in s:
            inside = False
            s = s.split('\\end{verbatim}')[0]
        if len(s) > minimum:
            candidates.append((n, s))
memo_path = os.path.join(os.path.dirname(pdf) or '.', os.path.splitext(os.path.basename(pdf))[0] + '.vbwidth')
key_of = lambda line: hashlib.sha1(line.encode('utf-8')).hexdigest()
try:
    memo = {} if recheck else json.load(open(memo_path))
except (OSError, ValueError):
    memo = {}
candidates = [(n, s) for n, s in candidates if memo.get(key_of(s)) not in ('ok', 'not found')]
if not candidates:
    sys.exit(0)

squash = lambda t: re.sub(r'\s+', '', t)
stext = subprocess.run(['mutool', 'draw', '-F', 'stext', '-o', '-', pdf], capture_output=True, text=True).stdout
lines = []                                   # (page, width, x0, y0, x1, text without blanks)
for p, page in enumerate(stext.split('<page ')[1:], 1):
    width = float(re.search(r'width="([\d.]+)"', page).group(1))
    for m in re.finditer(r'<line bbox="([\d.-]+) ([\d.-]+) ([\d.-]+) [\d.-]+"[^>]*text="([^"]*)"', page):
        lines.append((p, width, float(m.group(1)), float(m.group(2)), float(m.group(3)), squash(html.unescape(m.group(4)))))


def found(piece, text):
    """the PDF line shows this piece: whole, inside a longer line, or cut at the page edge"""
    return piece == text or (len(piece) > 20 and piece in text) or (len(text) >= 20 and piece.startswith(text))


over, missing = 0, []
for n, s in candidates:
    # a line set in columns (runs of blanks) comes out of the PDF as several pieces on one baseline
    pieces = [squash(x) for x in re.split(r'\s{2,}', s.strip()) if squash(x)]
    starts = [l for l in lines if found(pieces[0], l[5])]
    if not starts:
        missing.append((n, s)); continue
    for p, width, x0, y0, x1, text in starts:
        same = [l for l in lines if l[0] == p and abs(l[3] - y0) < 2 and any(found(q, l[5]) for q in pieces)]
        lo, hi = min(l[2] for l in same), max(l[4] for l in same)
        # cut: the PDF holds only the start of the line, and it ends at the page's edge
        cut = len(pieces) == 1 and text != pieces[0] and pieces[0].startswith(text) and hi > width - 3
        left = (width - TEXTWIDTH) / 2; right = left + TEXTWIDTH
        if lo < left - SLACK or hi > right + SLACK or cut:
            print(f'{tex}:{n}: page {p}: {lo:.1f}-{hi:.1f}pt, text area {left:.1f}-{right:.1f}pt'
                  f'{" (cut at the page edge)" if cut else ""} | {s}')
            over += 1
            memo[key_of(s)] = 'overflows'
        elif memo.get(key_of(s)) != 'overflows':
            memo[key_of(s)] = 'ok'
for n, s in missing:
    memo[key_of(s)] = 'not found'
    print(f'{tex}:{n}: not found in the PDF (not checked) | {s}', file=sys.stderr)
try:
    json.dump(memo, open(memo_path, 'w'), indent=0)
except OSError:
    pass
sys.exit(1 if over else 0)
