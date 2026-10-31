#!/bin/sh
# subset-fonts.sh <outdir> -- the faces AMSUniBo sets, as WOFF2, from TeX Live's own OTFs
set -e
OUT="$1"; mkdir -p "$OUT"
SUBSET="${PYFTSUBSET:-pyftsubset}"
TEXT="U+0020-007E,U+00A0-017F,U+2000-2044,U+2190-21FF,U+2200-22FF"
FEAT="kern,liga,onum,pnum,lnum,tnum,smcp,c2sc,ss01,ss02,ss03"
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
