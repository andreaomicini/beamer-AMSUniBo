#!/bin/sh
# subset-fonts.sh <outdir> [AMSUniBo|AMSBolognaFC|AMSPurpleAndGold|AMSSilverBlue|AMSRedGrey|AMSCesena] -- the faces the style sets, as WOFF2, from TeX Live's own OTFs
set -e
OUT="$1"; STYLE="${2:-AMSUniBo}"; mkdir -p "$OUT"
SUBSET="${PYFTSUBSET:-pyftsubset}"
TEXT="U+0020-007E,U+00A0-017F,U+2000-2044,U+2190-21FF,U+2200-22FF"
FEAT="kern,liga,onum,pnum,lnum,tnum,smcp,c2sc,ss01,ss02,ss03"
case "$STYLE" in AMSBolognaFC|AMSPurpleAndGold|AMSSilverBlue|AMSRedGrey|AMSCesena)
	# Computer Modern Sans, as cm-super sets it: Latin Modern, one optical size per TeX size
	for f in lmsans8-regular lmsans8-oblique lmsans9-regular lmsans9-oblique lmsans10-regular lmsans10-oblique \
	         lmsans10-bold lmsans10-boldoblique lmsans12-regular lmsans12-oblique lmsans17-regular lmsans17-oblique \
	         lmmono8-regular lmmono10-regular lmromancaps10-regular lmroman10-italic; do
		"$SUBSET" "$(kpsewhich $f.otf)" --unicodes="$TEXT,U+0394,U+0398,U+039B,U+039E" --layout-features="kern,liga" \
			--flavor=woff2 --output-file="$OUT/$f.woff2"
	done
	# the math symbols: \rightarrow and \phi (experiment 4), those of experiment 6, and of experiment 7:
	# arrows, operators, \mathcal and \mathscr capitals, italic Greek, the tilde of \widetilde
	"$SUBSET" "$(kpsewhich latinmodern-math.otf)" --layout-features='' \
		--unicodes="U+2192,U+1D719,U+007B,U+2248,U+27F6,U+27F9,U+21A6,U+2223,U+21D2,U+21D3,U+21DD,U+2713,U+2205,U+2227,U+2260,U+2265,U+22C5,U+221E,U+223C,U+2119,U+1D53C,U+2211,U+27E8,U+27E9,U+1D700,U+007D,U+02DC,U+2190,U+2191,U+2203,U+2208,U+2212,U+2218,U+2286,U+22A8,U+22C0,U+22C4,U+22EF,U+2110,U+2112,U+2113,U+2118,U+210B,U+211B,U+212C,U+2130,U+2131,U+2133,U+1D49C-1D4B5,U+1D6FC-1D71B" \
		--flavor=woff2 --output-file="$OUT/latinmodern-math.woff2"
	exit 0 ;;
esac
for f in MerriweatherSans-Light MerriweatherSans-LightItalic MerriweatherSans-Regular \
         MerriweatherSans-Bold MerriweatherSans-BoldItalic Merriweather-Regular Merriweather-Italic \
         Inconsolatazi4-Regular; do
	"$SUBSET" "$(kpsewhich $f.otf)" --unicodes="$TEXT" --layout-features="$FEAT" \
		--flavor=woff2 --output-file="$OUT/$f.woff2"
done
# the math symbols Merriweather lacks
"$SUBSET" "$(kpsewhich NewCMMath-Book.otf)" \
	--unicodes="U+2192,U+21D0,U+21D2,U+2208,U+2219,U+223C,U+22C5,U+2112,U+1D49C,U+1D49E" --layout-features='' \
	--flavor=woff2 --output-file="$OUT/NewCMMath-Book.woff2"
