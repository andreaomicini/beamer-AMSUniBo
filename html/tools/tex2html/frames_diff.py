"""frames_diff.py <old.html> <new.html> -- which pages of a rebuilt deck changed, frame by frame.

A Beamer frame is independent of the others but for its page number, which the page's script computes: so a
page whose markup is the same as before, its corrections aside, needs nothing. The old and new pages are matched
in order (difflib), the corrections in nudges.json of every unchanged page follow it to its new number (a frame
that gained or lost pages moves those after it), and the changed or new pages are printed, comma-separated, for
nudge.py and stats.py. Their old corrections are dropped: they are measured again.
"""
import difflib, json, re, sys
from deck import DIR

def pages(path):
    h = open(path, encoding='utf-8').read()
    h = h[h.find('<main'):]
    return re.findall(r'<section\b.*?</section>', h, re.S)

# what the corrections write (nudges.json, applied by build.py), and nothing else, is set aside
CORR = re.compile(r'(?:margin-top|margin-bottom|padding-top|padding-bottom|translate): (?:calc\([^)]*\)|[-0-9.]+[a-z]*)(?: [-0-9.]+[a-z]*)?;? ?')

def norm(sec):
    s = CORR.sub('', sec)
    return re.sub(r' style=""', '', s)

old, new = [norm(s) for s in pages(sys.argv[1])], [norm(s) for s in pages(sys.argv[2])]
nj = DIR / 'nudges.json'
nud = json.loads(nj.read_text()) if nj.exists() else {}
moved, changed = {}, []
for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
    if op == 'equal':
        for k in range(a2 - a1):
            if str(a1 + k + 1) in nud:
                moved[str(b1 + k + 1)] = nud[str(a1 + k + 1)]
    else:
        changed += list(range(b1 + 1, b2 + 1))
nj.write_text(json.dumps(moved, indent=0, sort_keys=True, ensure_ascii=False) + '\n')
print(','.join(str(p) for p in changed))
