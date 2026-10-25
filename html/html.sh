#!/bin/bash
# html.sh [--nudge] [<deck>] -- the deck's HTML page, rebuilt from its PDF and measured against it
# run from the deck's root; <deck> may be omitted when tex/ holds a single .tex
set -euo pipefail

die() { echo "html.sh: $*" >&2; exit 1; }
T="$(cd "$(dirname "$0")/tools" && pwd)"
export PYTHONDONTWRITEBYTECODE=1   # no __pycache__ in the style repository

[ -f .latexmkrc ] && [ -d tex ] || die "run from the root of a deck repository"
nudge=
[ "${1:-}" = --nudge ] && { nudge=1; shift; }
if [ $# -ge 1 ]; then
	deck=$(basename "$1" .tex)
else
	set -- tex/*.tex
	[ $# -eq 1 ] && [ -e "$1" ] || die "tex/ holds $# .tex files: name the deck"
	deck=$(basename "$1" .tex)
fi
[ -f "tex/$deck.tex" ] || die "no tex/$deck.tex"

## the deck's inputs: html/tex2html/<deck>/ when the repository holds several decks
if [ -f "html/tex2html/$deck/deck.json" ]; then cfg="html/tex2html/$deck"; else cfg=html/tex2html; fi
export TEX2HTML_DECK="$cfg"
if [ ! -f "$cfg/deck.json" ]; then
	mkdir -p "$cfg"
	cat > "$cfg/deck.json" <<-EOF
	{
	  "root": "$(python3 -c "import os,sys; print(os.path.relpath('.', sys.argv[1]))" "$cfg")",
	  "tex": "tex/$deck.tex",
	  "bbl": "aux/$deck.bbl",
	  "pdf": "aux/$deck.pdf",
	  "page": "html/$deck.html",
	  "figures": []
	}
	EOF
	die "wrote $cfg/deck.json: set its page name, and see html/README.md for what a generated page needs"
fi
field() { python3 -c "import json,sys; v=json.load(open(sys.argv[1])).get(sys.argv[2]); print('' if v is None else (' '.join(v) if isinstance(v, list) else v))" "$cfg/deck.json" "$1"; }
page=$(field page)
generated=$(field title)
style=$(field style); style=${style:-AMSUniBo}

## the PDF, so that aux/ is the reference
latexmk -pdf "tex/$deck.tex" >/dev/null 2>&1 || die "the deck does not build: see aux/$deck.log"

## a generated page is written again
## the assets go in before any correction is measured: a picture still missing has no height, and the
## corrections would make up for it (experiment 5, a TikZ figure: 100pt of margin, the text pushed off)
if [ -n "$generated" ]; then
	[ -f "$cfg/nudges.json" ] || nudge=1
	python3 "$T/tex2html/build.py"
fi
[ -f "$page" ] || die "no $page: write it, or give deck.json the fields of a generated page"

## the assets: fonts, the seal of the class option, the TikZ pictures, the deck's own images
A=$(mktemp -d)
trap 'rm -rf "$A"' EXIT
"$T/subset-fonts.sh" "$A/fonts" "$style" >/dev/null 2>&1
seal=$(sed -n 's/^\\documentclass\[\([^]]*\)\].*/\1/p' "tex/$deck.tex" | tr , '\n' | grep -xE 'bologna|cesena' || true)
[ -n "$seal" ] && "$T/seal.sh" "$seal" "$A" "$style" >/dev/null
figs=($(field figures))
if [ ${#figs[@]} -gt 0 ]; then
	"$T/externalize.sh" "tex/$deck.tex" "$A" >/dev/null
	for i in "${!figs[@]}"; do mv "$A/fig-$i.svg" "$A/${figs[$i]}.svg"; done
fi
for name in $(grep -o 'data-asset="[^"]*"' "$page" | sed 's/.*="\(.*\)"/\1/' | sort -u); do
	ls "$A/$name".* >/dev/null 2>&1 && continue
	src=$(find -L img -name "$name.png" -o -name "$name.jpg" | head -1)
	if [ -n "$src" ]; then cp -L "$src" "$A/"; continue; fi
	# a PDF picture, as pdflatex took it: to SVG, its text as outlines
	src=$(find -L img -name "$name.pdf" | head -1)
	[ -n "$src" ] || die "no picture for data-asset $name: list the TikZ ones in figures, in source order"
	pdftocairo -svg "$src" "$A/$name.svg"
done
python3 "$T/assets.py" "$page" "$A"

## corrected frame by frame the first time, or with --nudge: the corrections are not idempotent, and a
## second round on a settled page moves it off. build.py keeps the ASSETS block it finds
if [ -n "$generated" ] && [ -n "$nudge" ]; then
	for mode in gaps gaps gaps both; do
		python3 "$T/tex2html/nudge.py" webkit "" $mode >/dev/null
		python3 "$T/tex2html/build.py" >/dev/null
	done
fi

## the checks of the checklist that a program can make; the rows are read by a person
for engine in webkit firefox; do
	echo "== $engine"
	python3 "$T/tex2html/stats.py" $engine
	python3 "$T/tex2html/blocks.py" $engine
done
