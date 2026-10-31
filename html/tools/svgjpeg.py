#!/usr/bin/env python3
"""Re-encode the large PNG bitmaps inside an SVG (pdftocairo output) as JPEG, when JPEG is less than
half their size: photographs and shaded pictures; line art stays PNG. Usage: svgjpeg.py <file.svg>"""
import base64, re, subprocess, sys
p = sys.argv[1]; s = open(p, encoding='utf-8').read(); n = 0
def jpeg(m):
    global n
    png = base64.b64decode(m.group(1))
    if len(png) < 50000 or png[25] in (4, 6):   # small, or with an alpha channel (IHDR colour type 4, 6)
        return m.group(0)
    jpg = subprocess.run(['magick', 'png:-', '-quality', '88', 'jpg:-'], input=png, capture_output=True, timeout=120).stdout
    if not jpg or len(jpg) > 0.5 * len(png):
        return m.group(0)
    n += 1
    return 'data:image/jpeg;base64,' + base64.b64encode(jpg).decode()
s = re.sub(r'data:image/png;base64,([A-Za-z0-9+/=]+)', jpeg, s)
# (no rounding of coordinates: these drawings are often scaled up by a matrix, 2026-10-31)
open(p, 'w', encoding='utf-8').write(s)
print(n)
