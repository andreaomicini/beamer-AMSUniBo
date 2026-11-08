#!/usr/bin/env python3
"""The APICe records each deck cites: the `pub` (and `talk`) fields of its Coursedeck record.

    deckpubs.py <Course>                  pubs.json for Coursedeck.<Course>, on stdout
    deckpubs.py <Course> -o <file>        the same, into <file>

Run from a course repository's root, after the decks are built. Per deck, in its aux/<deck>.bbl order,
each cited key's `apice` field in the one bib/<course>.bib, as Publication.<Name> or Talk.<Name> after
the Publication and Talk XARs (~/APICe/publications/Publication.WebHome.xar, ~/APICe/talks/Talk.WebHome.xar;
only their file lists are read). Labels as the deck declares them, \\decklabel{CX}; without one, the house
style: the deck's file prefix, first letter capital (c8a-soda -> C8a; until 2026-11-08 always so, and DS's CX
came out Cx). On stderr, every key left out: no `apice` field, or a name in neither XAR.

The entries are split by bibimpact.parse, which counts braces. Written 2026-10-31: until then each run copied
the last run's script, and DS 25·26's regex split some sa.bib entries wrongly and lost six `apice` fields.
"""
import json
import os
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bibimpact import course_bib, decks, parse

XARS = {'Publication': '~/APICe/publications/Publication.WebHome.xar', 'Talk': '~/APICe/talks/Talk.WebHome.xar'}


def names(space):
    xar = zipfile.ZipFile(os.path.expanduser(XARS[space]))
    return {m.group(1) for n in xar.namelist() if (m := re.fullmatch(space + r'/([^/]+)\.xml', n))}


def main(argv):
    if not argv or argv[0].startswith('-'):
        sys.exit(__doc__)
    course, out = argv[0], argv[argv.index('-o') + 1] if '-o' in argv else None
    entries, _, _ = parse(Path(course_bib()).read_text(encoding='utf-8'))
    apice = {k: m.group(1).strip() for k, (body, _) in entries.items()
             if (m := re.search(r',\s*apice\s*=\s*[{"]([^}"]*)[}"]', body, re.I))}   # parse() makes each body one line
    known = {space: names(space) for space in XARS}
    pubs, left = {}, []
    for d in decks():
        tex = Path(f'tex/{d}.tex')   # the label the deck declares, \decklabel{CX}; else from its file name
        m = re.search(r'\\decklabel\{([^}]*)\}', tex.read_text(encoding='utf-8')) if tex.exists() else None
        label = m.group(1) if m else d.split('-')[0][:1].upper() + d.split('-')[0][1:]
        bbl = Path(f'aux/{d}.bbl')
        keys = re.findall(r'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}', bbl.read_text(encoding='utf-8'), re.S) if bbl.exists() else []
        pubs[label] = []
        for k in keys:
            a = apice.get(k.strip().lower())
            space = next((s for s in XARS if a in known[s]), None) if a else None
            if space:
                pubs[label].append(f'{space}.{a}')
            else:
                left.append(f'{label} {k}: ' + (f'{a} in neither XAR' if a else 'no apice field'))
    text = json.dumps({course: pubs}, indent=1, ensure_ascii=False) + '\n'
    Path(out).write_text(text, encoding='utf-8') if out else sys.stdout.write(text)
    for line in left:
        print('left out:', line, file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1:])
