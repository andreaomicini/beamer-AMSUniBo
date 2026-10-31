#!/bin/bash
# zip.sh [<deck>] -- the deck as one flat folder, zipped to zip/<deck>.zip
# run from the deck's root; <deck> may be omitted when tex/ holds a single .tex
set -euo pipefail

die() { echo "zip.sh: $*" >&2; exit 1; }

[ -f .latexmkrc ] && [ -d tex ] || die "run from the root of a deck repository"
if [ $# -ge 1 ]; then
	deck=$(basename "$1" .tex)
else
	set -- tex/*.tex
	[ $# -eq 1 ] && [ -e "$1" ] || die "tex/ holds $# .tex files: name the deck"
	deck=$(basename "$1" .tex)
fi
[ -f "tex/$deck.tex" ] || die "no tex/$deck.tex"
git check-ignore -q zip/ 2>/dev/null || echo "zip.sh: warning: zip/ is not gitignored here" >&2

## build, so that aux/ lists what the deck reads now
latexmk -pdf "tex/$deck.tex" >/dev/null 2>&1 || die "the deck does not build: see aux/$deck.log"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
dir="$work/$deck"
mkdir -p "$dir" "$work/texmf"

## the .tex without its TeXShop magic comments
grep -v '^% *!TEX' "tex/$deck.tex" > "$dir/$deck.tex"

## every project file the build read, symlinks resolved
put() {
	local n
	n=$(basename "$1")
	if [ -e "$dir/$n" ]; then
		cmp -s "$1" "$dir/$n" || die "two different files named $n"
	else
		cp -L "$1" "$dir/"
	fi
}
## one name per line, read whole: a name may hold spaces
grep '^INPUT ' "aux/$deck.fls" | cut -c7- | sed 's|^\./||' | sort -u |
	grep -v -e '^/' -e '^aux/' -e "^tex/$deck.tex\$" | while IFS= read -r f; do
	put "$f"
done

## bibtex's inputs, which the .fls does not see: found by name anywhere in the repository
find_one() {
	local hits
	hits=$(find . \( -path ./aux -o -path ./pdf -o -path ./src -o -path ./zip -o -path ./.git \) -prune \
		-o -name "$1" -print)
	[ -n "$hits" ] || die "$1 not found in the repository"
	for h in $hits; do put "$h"; done
}
for b in $(sed -n 's/^\\bibdata{\(.*\)}$/\1/p' "aux/$deck.aux" | tr , ' '); do find_one "$b.bib"; done
for s in $(sed -n 's/^\\bibstyle{\(.*\)}$/\1/p' "aux/$deck.aux"); do find_one "$s.bst"; done

## a file called through a folder is called by name, now that all sit side by side:
## {img/x} becomes {x} wherever x, with or without its extension, is one of the files here (x may hold spaces)
for f in "$dir"/*.tex "$dir"/*.sty; do
	[ -e "$f" ] || continue
	perl -pi -e 'BEGIN { $d = shift } s{\{[^{}%#\\]*/([^{}/%#\\]+)\}}{ (-e "$d/$1" || (() = glob("\Q$d/$1\E.*"))) ? "{$1}" : $& }ge' "$dir" "$f"
done

## check: a plain build in a copy, no local tree, same warnings and same pages as aux/
cp -R "$dir" "$work/test"
(
	cd "$work/test"
	unset TEXINPUTS BIBINPUTS BSTINPUTS
	export TEXMFHOME="$work/texmf"
	pdflatex -interaction=nonstopmode "$deck" >/dev/null || true
	if grep -q '^\\bibdata' "$deck.aux"; then bibtex "$deck" >/dev/null || die "bibtex fails in the flat folder"; fi
	## rerun until .aux and .nav settle: beamer's frame total changes them without asking for a rerun
	for i in 1 2 3 4 5; do
		before=$(cat "$deck.aux" "$deck.nav" 2>/dev/null | cksum)
		pdflatex -interaction=nonstopmode -recorder "$deck" >/dev/null || true
		if [ "$before" = "$(cat "$deck.aux" "$deck.nav" 2>/dev/null | cksum)" ] &&
			! grep -q 'Rerun to get' "$deck.log"; then break; fi
	done
	grep -q '^!' "$deck.log" && die "the flat build stops with an error"
	grep -q 'Library/texmf' "$deck.fls" && die "the flat build reads ~/Library/texmf"
	exit 0
)
warns() { grep -E '^(Package|LaTeX|Class).*Warning|Overfull|Underfull' "$1" | sed 's/[0-9.]//g' | sort; }
[ "$(warns "aux/$deck.log")" = "$(warns "$work/test/$deck.log")" ] ||
	die "the flat build warns differently from aux/$deck.log"
mkdir -p "$work/a" "$work/b"
pdftoppm -r 100 -png "aux/$deck.pdf" "$work/a/p"
pdftoppm -r 100 -png "$work/test/$deck.pdf" "$work/b/p"
[ "$(ls "$work/a" | wc -l)" -eq "$(ls "$work/b" | wc -l)" ] || die "page count differs"
for p in "$work"/a/*.png; do
	cmp -s "$p" "$work/b/$(basename "$p")" || die "page $(basename "$p" .png) differs"
done

## the archive
mkdir -p zip
rm -f "zip/$deck.zip"
(cd "$work" && zip -X -q -r - "$deck") > "zip/$deck.zip"
echo "zip/$deck.zip: $(ls "$dir" | wc -l | tr -d ' ') files, $(ls "$work/a" | wc -l | tr -d ' ') pages identical"
