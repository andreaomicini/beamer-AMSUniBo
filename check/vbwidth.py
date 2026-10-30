#!/usr/bin/env python3
r"""Flag verbatim lines too wide for the frame.  A deck's verbatim is the style's monospaced font at the
body size; the characters that fit in \textwidth (342.30pt in every AMS style) were measured on
2026-10-30 by building, in each style's course context, frames with lines of 56 to 68 characters:
the first Overfull \hbox came at 63 on AMSUniBo (Inconsolata, 5.475pt a character) and at 61 on the
others (5.658pt). Beamer relaxes \vbadness, so a wide line reports only as an Overfull \hbox -- and
not even that when it is centred, since it then hangs into the margin (iag2627-slides, L8).

  vbwidth.py tex/<deck>.tex ...        run from the repository root: the style is read from .gitmodules
  vbwidth.py --limit N tex/<deck>.tex  an explicit limit
"""
import os, re, subprocess, sys
LIMITS = {'AMSUniBo': 62}           # every other AMS style: 60
DEFAULT = 60


def style():
    r = subprocess.run(['git', 'config', '-f', '.gitmodules', 'submodule..style.url'], capture_output=True, text=True)
    m = re.search(r'beamer-(\w+?)(?:\.git)?$', r.stdout.strip())
    return m.group(1) if m else None


args = sys.argv[1:]
if args[:1] == ['--limit']:
    limit, args = int(args[1]), args[2:]
else:
    limit = LIMITS.get(style(), DEFAULT)
bad = 0
for path in args:
    inside = False
    for n, line in enumerate(open(path, encoding='utf-8'), 1):
        s = line.rstrip('\n')
        if not inside and '\\begin{verbatim}' in s:
            inside = True
            continue
        if inside:
            if '\\end{verbatim}' in s:
                inside = False
                s = s.split('\\end{verbatim}')[0]
            if len(s) > limit:
                print(f'{path}:{n}: {len(s)} cols (limit {limit}) | {s}')
                bad += 1
sys.exit(1 if bad else 0)
