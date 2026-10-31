#!/bin/bash
# html.sh [<deck>] [--compare] -- the deck's HTML page, typeset by TeX itself (latex -> dvisvgm)
# run from the deck's root; <deck> may be omitted when tex/ holds a single .tex
set -euo pipefail

die() { echo "html.sh: $*" >&2; exit 1; }
T="$(cd "$(dirname "$0")/tools" && pwd)"

[ -f .latexmkrc ] && [ -d tex ] || die "run from the root of a deck repository"
cmp=
args=()
for a in "$@"; do [ "$a" = --compare ] && cmp=1 || args+=("$a"); done
if [ ${#args[@]} -ge 1 ]; then
	deck=$(basename "${args[0]}" .tex)
else
	set -- tex/*.tex
	[ $# -eq 1 ] && [ -e "$1" ] || die "tex/ holds $# .tex files: name the deck"
	deck=$(basename "$1" .tex)
fi
[ -f "tex/$deck.tex" ] || die "no tex/$deck.tex"

## the page is named like the deck's PDF in pdf/: the name latexmk gave it last (aux/<deck>.pdfprev),
## or the title it read (aux/<deck>.pdfname), or else the jobname
name=$deck
for f in "aux/$deck.pdfprev" "aux/$deck.pdfname"; do
	[ -s "$f" ] && { name=$(head -1 "$f"); break; }
done
mkdir -p html
page="html/$name.html"

## the work: a copy of the sources in aux/html/, the repository is only read
export DECK2HTML_WORK="$PWD/aux/html"
mkdir -p "$DECK2HTML_WORK"
zsh "$T/deck2html.zsh" "$PWD" "tex/$deck.tex" "$page"
echo "html.sh: $page"

## --compare: every page in WebKit and Firefox against the PDF (needs aux/<deck>.pdf)
if [ -n "$cmp" ]; then
	[ -f "aux/$deck.pdf" ] || die "no aux/$deck.pdf to compare with: build the deck first"
	zsh "$T/compare.zsh" "aux/$deck.pdf" "$page" "$deck"
	echo "html.sh: comparison in aux/html/cmp-$deck/"
fi
