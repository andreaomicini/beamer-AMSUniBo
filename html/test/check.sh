#!/bin/bash
# The CI's check of html.sh (../../.gitlab-ci.yml), the same run locally: from html/test/, the test deck
# made into its page, then the page there, the PDF picture turned into its SVG, and no \includegraphics
# left with .pdf in the working copy (an overlay specification once kept it: SMA-LS 08·09 C7).
set -euo pipefail
cd "$(dirname "$0")"
rm -rf aux html
bash ../html.sh overlay
w=aux/html/overlay/src
[ -s html/overlay.html ] || { echo "check: no html/overlay.html"; exit 1; }
[ -s $w/img/rotated.svg ] || { echo "check: the PDF picture was not turned into an SVG"; exit 1; }
if perl -ne 's/(?<!\\)%.*//; print "$.: $_" if /\\includegraphics(?:<[^>]*>)?\s*(?:\[(?:[^\]{}]|\{[^{}]*\})*\])?\{[^}]*\.pdf\}/' $w/tex/overlay.tex | grep .; then echo "check: a picture kept its .pdf"; exit 1; fi
echo "check: html.sh made the test page, the picture as SVG, no .pdf left"
