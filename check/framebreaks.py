#!/usr/bin/env python3
"""`allowframebreaks` frames that render a single page.  Beamer numbers the title
of every such frame, so one that never broke still shows a lone roman `I`.

Read off the built PDF, not the source: whether a frame breaks depends on how tall
its content sets, which only the build knows.  A numeral too long for the title line
wraps to one of its own, so the second line is folded back in before matching.

  framebreaks.py aux/<deck>.pdf
"""
import re, subprocess, sys
ROMAN = re.compile(r' (I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)$')
pdf = sys.argv[1]
n = int(subprocess.run(['mutool', 'info', pdf], capture_output=True, text=True)
        .stdout.split('Pages: ')[1].split()[0])
titles = {}
for p in range(1, n + 1):
    txt = subprocess.run(['mutool', 'draw', '-F', 'txt', '-o', '-', pdf, str(p)],
                         capture_output=True, text=True).stdout
    ls = [l.strip() for l in txt.splitlines() if l.strip()]
    t = ls[1] if len(ls) > 1 else ''
    if len(ls) > 2 and ROMAN.match(' ' + ls[2]):   # a numeral wrapped to its own line
        t += ' ' + ls[2]
    titles[p] = t
single = []
for p in range(1, n + 1):
    m = ROMAN.search(titles[p])
    if not m or m.group(1) != 'I':
        continue
    stem = titles[p][:m.start()]
    if titles.get(p + 1, '') != stem + ' II':
        single.append((p, stem))
print(f'{pdf}: {len(single)} allowframebreaks frame(s) rendering a single page')
for p, stem in single:
    print(f'  p{p:>3}  {stem}')
