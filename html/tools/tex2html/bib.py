"""The .bbl -> p.bibitem paragraphs, as in the AGoT page."""
import re
from latex import read_group, skip_ws
from frames import C

LINKS = re.compile(r'\\(apicepubpar|dddoi|uuurl)\{')

def spans(rest):
    """an entry's blocks as spans: author, title, location, notes, links"""
    C.reset()
    links = []
    while True:
        m = LINKS.search(rest)
        if not m:
            break
        g, j = read_group(rest, m.end() - 1)
        links.append(C.inline(rest[m.start():j]))
        rest = rest[:m.start()] + rest[j:]
    chunks = [c.strip() for c in rest.split('\\newblock')]
    chunks = [c for c in chunks if c]
    out = [f'<span class="bib-author">{C.inline(chunks[0]).strip()}</span>']
    t = chunks[1]
    m = re.match(r'\{\\bfseries\s*', t)
    if m:
        inner, j = read_group(t, 0)
        title = C.inline(inner.replace('\\bfseries', '', 1)).strip()
        nb = C.inline(t[j:]).strip()
        if nb:
            title += f'<span class="nb">{nb}</span>'
    else:
        title = C.inline(t).strip()
    out.append(f'<span class="bib-title">{title}</span>')
    for k, c in enumerate(chunks[2:]):
        cls = 'bib-location' if k == 0 else 'bib-note'
        out.append(f'<span class="{cls}">{C.inline(c).strip()}</span>')
    if links:
        out.append(f'<span class="bib-links">{"".join(links)}</span>')
    h = ''.join(out).replace('class="bibref"', '')
    return h.replace('<a  href', '<a href')

def entry(key, lab, rest):
    h = spans(rest)
    return f'<p class="bibitem" id="cite-{key}"><span class="biblabel">[{C.inline(lab)}]</span>{h}</p>'

def bibentry(key, book=False):
    """\\bibentry{key} as an item of beamer's bibliography list: the entry in full, with the article or book icon"""
    rest = {k: r for k, _, r in C.bbl}[key]
    # the title runs on after the author, behind beamer's \\newblock box 1.5em high: the PDF breaks the line where TeX did
    h = spans(rest).replace('</span><span class="bib-title">',
                            '</span> <span class="bib-title" data-runon><span class="nbstrut"></span>', 1)
    return f'<p class="artitem bibentry{" book" if book else ""}">{h}</p>'

def entries():
    return [(k, entry(k, l, r)) for k, l, r in C.bbl]

if __name__ == '__main__':
    for k, h in entries()[:6]:
        print(h)
