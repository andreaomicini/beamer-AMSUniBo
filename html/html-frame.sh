#!/bin/bash
# html-frame.sh [<deck>] -- after a change to some frames: the deck's page rebuilt, only the frames that changed
# corrected and measured. Run from the deck's root, as html.sh; <deck> may be omitted when tex/ holds one .tex.
#
# In Beamer a frame is independent of the others but for its page number, which the page's script computes. So:
# the PDF is built, the whole page translated again (seconds), and frames_diff.py compares it with the page as it
# was, frame by frame. The unchanged pages keep their corrections, renumbered when a frame gained or lost pages;
# the changed ones alone go through nudge.py and are measured, in both engines. html.sh stays for a new deck, or
# after a change to the translator.
set -euo pipefail

die() { echo "html-frame.sh: $*" >&2; exit 1; }
T="$(cd "$(dirname "$0")/tools" && pwd)"
export PYTHONDONTWRITEBYTECODE=1

[ -f .latexmkrc ] && [ -d tex ] || die "run from the root of a deck repository"
if [ $# -ge 1 ]; then deck=$(basename "$1" .tex); else
	set -- tex/*.tex; [ $# -eq 1 ] && [ -e "$1" ] || die "tex/ holds $# .tex files: name the deck"; deck=$(basename "$1" .tex); fi
if [ -f "html/tex2html/$deck/deck.json" ]; then cfg="html/tex2html/$deck"; else cfg=html/tex2html; fi
[ -f "$cfg/deck.json" ] || die "no $cfg/deck.json: a new deck goes through html.sh"
export TEX2HTML_DECK="$cfg"
page=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['page'])" "$cfg/deck.json")
[ -f "$page" ] && [ -f "$cfg/nudges.json" ] || die "no page or no nudges.json yet: build the deck with html.sh first"

latexmk -pdf "tex/$deck.tex" >/dev/null 2>&1 || die "the deck does not build: see aux/$deck.log"

old=$(mktemp); trap 'rm -f "$old"' EXIT
cp "$page" "$old"
python3 "$T/tex2html/build.py" >/dev/null
changed=$(python3 "$T/tex2html/frames_diff.py" "$old" "$page")
if [ -z "$changed" ]; then echo "no frame changed"; exit 0; fi
echo "changed pages: $changed"

# a picture new to the page: its asset, as html.sh puts it in
missing=$(for n in $(grep -o 'data-asset="[^"]*"' "$page" | sed 's/.*="\(.*\)"/\1/' | sort -u); do
	grep -q "data-name=\"$n\"\|id=\"asset-$n\"\|\"$n\":" "$page" || echo "$n"; done)
[ -z "$missing" ] || echo "html-frame.sh: new pictures ($missing): run html.sh once to embed them" >&2

for mode in gaps gaps gaps both; do
	python3 "$T/tex2html/nudge.py" webkit "$changed" $mode >/dev/null
	python3 "$T/tex2html/build.py" >/dev/null
done
for engine in webkit firefox; do
	echo "== $engine"
	python3 "$T/tex2html/stats.py" $engine "$changed"
done
