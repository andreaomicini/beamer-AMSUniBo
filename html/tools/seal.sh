#!/bin/sh
# seal.sh <bologna|cesena> <outdir> [theme] -- the seal as the theme places it, cropped to an alpha PNG
# prints the CSS box (left top width height, in % of the page) to put in .frame::before
set -e
SEAL="$1"; OUT="$(cd "$2" && pwd)"; THEME="${3:-AMSUniBo}"
STYLE="$(cd "$(dirname "$0")/../.." && pwd)"
[ "$THEME" = AMSUniBo ] || STYLE="$(cd "$STYLE/../beamer-$THEME" && pwd)"
TMP="$(mktemp -d)"; cd "$TMP"
printf '\\documentclass[presentation,%s]{beamer}\\usetheme{%s}\n\\begin{document}\\begin{frame}[plain]\\end{frame}\\end{document}\n' "$SEAL" "$THEME" > bg.tex
TEXINPUTS="$STYLE//:" pdflatex -interaction=nonstopmode bg.tex >/dev/null
pdftoppm -r 406.4 -gray -singlefile bg.pdf bg
python3 - "$OUT/seal.png" <<'PY'
import sys
from PIL import Image, ImageOps
im = Image.open('bg.pgm'); W, H = im.size
ink = ImageOps.invert(im); box = ink.getbbox()
la = Image.new('LA', (box[2] - box[0], box[3] - box[1]), 0)
la.putalpha(ink.crop(box)); la.save(sys.argv[1], optimize=True)
l, t, r, b = box
print(f'left: {100*l/W:.2f}%; top: {100*t/H:.2f}%; width: {100*(r-l)/W:.2f}%; height: {100*(b-t)/H:.2f}%;')
PY
rm -rf "$TMP"
