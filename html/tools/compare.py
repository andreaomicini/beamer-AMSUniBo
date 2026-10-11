#!/usr/bin/env python3
"""compare.py <refdir> <shotsdir> <page> [<sheet.png>] -- the PDF page against the HTML one.

<refdir> holds p-NN.png from `pdftoppm -scale-to-x 1024 -scale-to-y 768 -png deck.pdf <refdir>/p`,
<shotsdir> s-NN.png from shoot.sh. Prints each line of ink, PDF beside HTML, as [top, bottom,
left, right] in px of the 1024x768 page, then PDF-minus-HTML top per line: a constant is a
shift of the whole frame, a step is one gap. The optional sheet holds both pages, their overlay
(PDF red, HTML cyan, grey where they agree) and their difference.
"""
import sys
from PIL import Image, ImageChops

ref, shots, p = sys.argv[1], sys.argv[2], f'{int(sys.argv[3]):02d}'
a = Image.open(f'{ref}/p-{p}.png').convert('RGB')
b = Image.open(f'{shots}/s-{p}.png').convert('RGB')

def lines(im, y0=105, y1=740, ink=110):
    g = im.convert('L'); px = g.load(); out = []; cur = None
    for y in range(y0, y1):
        xs = [x for x in range(1024) if px[x, y] < ink]
        if xs:
            cur = [y, y, xs[0], xs[-1]] if cur is None else [cur[0], y, min(cur[2], xs[0]), max(cur[3], xs[-1])]
        elif cur:
            out.append(cur); cur = None
    return out + ([cur] if cur else [])

la, lb = lines(a), lines(b)
for i in range(max(len(la), len(lb))):
    print(la[i] if i < len(la) else '', '\t', lb[i] if i < len(lb) else '')
print('delta top (PDF-HTML):', [x[0] - y[0] for x, y in zip(la, lb)])

if len(sys.argv) > 4:
    s = Image.new('RGB', (2048, 1536), 'white')
    s.paste(a, (0, 0)); s.paste(b, (1024, 0))
    ga, gb = a.convert('L'), b.convert('L')
    s.paste(Image.merge('RGB', (gb, ga, ga)), (0, 768))
    s.paste(ImageChops.difference(a, b), (1024, 768))
    s.save(sys.argv[4])
