#!/usr/bin/env python3
r"""Catch what the build log will not report: content silently dropped by
`allowframebreaks`.  When one block is too tall to split, beamer merges the
remainder into the current page and stops splitting -- the frame's later blocks
are simply absent from the PDF, with exit 0 and a lone "Overfull \vbox" line.

So compare source against rendered text: every verbatim line and every block
title must be there, and no page may come out empty.

  checkdeck.py tex/<deck>.tex aux/<deck>.pdf
"""
import re, subprocess, sys

tex, pdf = sys.argv[1], sys.argv[2]
src = open(tex, encoding='utf-8').read()
txt = subprocess.run(['pdftotext', '-layout', pdf, '-'],
                     capture_output=True, text=True, check=True).stdout

FOLD = {'\u2019': "'", '\u2018': "'", '\u201c': "''", '\u201d': "''",
        '\u2261': '=', '\u2212': '-', '\u2026': '...'}

def norm(s):
    # Inconsolata sets an ASCII apostrophe as U+2019, so the PDF text never
    # matches the source byte for byte; fold the few such pairs before comparing
    s = ''.join(FOLD.get(c, c) for c in s)
    s = re.sub(r'\.\s+\.\s+\.', '...', s)     # CM sets \ldots as spaced dots
    return re.sub(r'\s+', ' ', s).strip()

flat = norm(txt)
pages = txt.split('\f')
bad = 0

# every verbatim line of any substance must be rendered
for block in re.findall(r'\\begin\{verbatim\}(.*?)\\end\{verbatim\}', src, re.S):
    for line in block.split('\n'):
        if len(line.strip()) >= 12 and norm(line) not in flat:
            print(f'MISSING code: {line.strip()}')
            bad += 1

# every TikZ node must render: a tree can be clipped or fall off the page.
# A node set on two lines is two runs in the PDF, so check it line by line
for label in [l for lab in
              re.findall(r'\\node\[[^\]]*\]\s*\([^)]*\)\s*at\s*\([^)]*\)\s*\{(.*?)\};', src)
              for l in lab.split(r'\\')]:
    plain = re.sub(r'\\textbar\{\}', '|', label)
    plain = re.sub(r'\\ldots\{\}', '...', plain)
    plain = re.sub(r'\\([_{}&#%$])', r'\1', plain)
    plain = plain.replace(r'$\equiv$', '=')
    plain = re.sub(r'\\[a-zA-Z]+\{\}?', '', plain)
    if len(plain.strip()) >= 4 and norm(plain) not in flat:
        print(f'MISSING node: {plain}')
        bad += 1

# block titles: the longest plain word in each must be rendered.
# Citations and addresses go first, argument and all: a block title often carries
# a \ccite, and dropping only the command name leaves the bibliography key glued
# to the words, so the search fails on a frame that is perfectly fine.
CITE = re.compile(r'\\(?:c{1,3}cite|cite|labcode|labdir|smallurl|u{1,3}url|d{1,3}doi|url)'
                  r'(?:\[[^\]]*\])?\{[^{}]*\}')
for title in re.findall(r'\\begin\{block\}\{(.*?)\}\s*(?:\n|$)', src):
    title = CITE.sub(' ', title)
    words = [w for w in re.findall(r'[A-Za-z]{6,}', re.sub(r'\\[a-zA-Z@]+', ' ', title))]
    if words and max(words, key=len) not in flat:
        print(f'MISSING block: {title}')
        bad += 1

# a page carrying only the footline is a failed split
for n, page in enumerate(pages[:-1], 1):
    body = [l for l in page.split('\n')
            if l.strip() and '(DISI, Univ. Bologna)' not in l]
    if len(body) <= 1:
        print(f'EMPTY page {n}: {body}')
        bad += 1

print(f'--- {tex}: {bad} problem(s)')
sys.exit(1 if bad else 0)
