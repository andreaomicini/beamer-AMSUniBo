#!/bin/sh
# externalize.sh <tex/deck.tex> <outdir> -- every tikzpicture of the deck as an SVG, fig-N.svg in order
# run from the deck's root; the search paths are the usual tex/ sty/ img/ of these decks
set -e
ROOT="$(pwd)"; DECK="$(basename "$1" .tex)"; OUT="$(cd "$2" && pwd)"
TMP="$(mktemp -d)"; cd "$TMP"
printf '\\AddToHook{package/tikz/after}{\\usetikzlibrary{external}\\tikzexternalize[prefix=fig-]}\n\\input{%s.tex}\n' "$DECK" > figs.tex
TEXINPUTS="$ROOT/img//:$ROOT/sty//:$ROOT/tex//:.:" pdflatex -shell-escape -interaction=nonstopmode figs.tex >/dev/null || true
for f in fig-figs-figure*.pdf; do
	n="${f#fig-figs-figure}"; n="${n%.pdf}"
	pdftocairo -svg "$f" "$OUT/fig-$n.svg"
	echo "fig-$n.svg  $(pdfinfo "$f" | sed -n 's/^Page size: *//p')"
done
rm -rf "$TMP"
