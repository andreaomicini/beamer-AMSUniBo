#!/usr/bin/env python3
"""Give graphicx's dvisvgm driver the natural size pdflatex uses, for bitmaps whose resolution has no
unit: a JPEG with JFIF units 0 (aspect ratio only) or a PNG with a pHYs of unknown unit. pdflatex then
takes 72 dpi, extractbb the bare numbers as dpi, and the picture comes out smaller. Writes <name>.xbb
beside such a file (whatever its extension says), and nothing for the others.
Usage: imgbb.py <file>...   (run with python3 -I)"""
import os, struct, sys
for f in sys.argv[1:]:
    b = open(f, 'rb').read()
    w = h = None
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        i = b.find(b'pHYs')
        if i > 0 and b[i + 12] == 0:
            w, h = struct.unpack('>II', b[16:24])
    elif b[:2] == b'\xff\xd8' and b[6:11] == b'JFIF\0' and b[13] == 0:
        k = 2                                     # the size is in the SOFn segment
        while k < len(b) - 9:
            if b[k] != 0xFF:
                k += 1; continue
            m, L = b[k + 1], struct.unpack('>H', b[k + 2:k + 4])[0]
            if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack('>HH', b[k + 5:k + 9]); break
            k += 2 + L
    if w and h:
        open(os.path.splitext(f)[0] + '.xbb', 'w').write(
            f'%%BoundingBox: 0 0 {w} {h}\n%%HiResBoundingBox: 0.000000 0.000000 {w}.000000 {h}.000000\n')
        print(f'{f}: {w}x{h} at 72 dpi')
