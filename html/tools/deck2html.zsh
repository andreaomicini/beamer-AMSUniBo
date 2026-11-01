#!/bin/zsh
# deck2html.zsh <repo> <deck.tex> <out.html> -- a Beamer deck as one self-contained HTML page,
# typeset by TeX itself: latex (DVI) -> fixdvi.py -> dvisvgm (WOFF2 fonts) -> svgfix.py -> assemble.py.
# Works on a copy of the repo's sources in a scratch folder; the repo is only read.
set -e
H="${0:A:h}"
repo="${1:A}"; deck="$2"; out="${3:A}"
name="${deck:t:r}"
W="${DECK2HTML_WORK:-$H/work}/$name"   # html.sh puts it in the deck's aux/html/
rm -rf "$W"; mkdir -p "$W"
rsync -aL --exclude aux --exclude pdf --exclude html --exclude zip --exclude orig --exclude .git "$repo/" "$W/src/"
cd "$W/src"
# video commands this tool does not handle yet (\videolink is handled): named at once, so that a new case
# gets its own method instead of a silent poster
v=$(cat "$deck" $(find sty -name '*.sty' 2>/dev/null) 2>/dev/null | sed 's/%.*//' | grep -oE '\\(movie|includemedia|animategraphics|sound|embedvideo|multiinclude)\b' | sort | uniq -c || true)
[ -z "$v" ] || print "WARNING: video commands not handled by deck2html (they will show their poster only):\n$v"
# every PDF picture becomes an SVG beside it (pdftocairo: its SVG is already on the crop box, as pdflatex reads a PDF), which PGF and graphicx then prefer: dvisvgm's
# own PDF route (mutool) names a PDF's images by object number, and two PDFs with an image 4 on the
# same page swap their pictures
# a picture named with its .pdf extension would bypass the choice below: the extension goes, in this copy
find tex sty -name '*.tex' -o -name '*.sty' 2>/dev/null | while read f; do perl -pi -e 's/(\\includegraphics(?:\[(?:[^\]{}]|\{[^{}]*\})*\])?\{[^}]*?)\.pdf\}/$1}/g' "$f"; done
# bitmaps whose resolution has no unit: the size pdflatex gives them (72 dpi), in an .xbb
find . \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) -not -path './out/*' -print0 | xargs -0 python3 -I "$H/imgbb.py" || true
find . -name '*.pdf' -not -path './out/*' | while read f; do
  timeout 60 pdftocairo -svg "$f" "${f%.pdf}.svg" 2>/dev/null || continue
  if grep -q 'filter-color-to-alpha' "${f%.pdf}.svg"; then
    # soft masks become SVG filters the browsers ignore inside an <img>: a transparent PNG instead
    # (200 dpi, the PDF's own size); the PDF steps aside, in this copy only, so that the PNG is found
    rm "${f%.pdf}.svg"; timeout 120 pdftocairo -cropbox -png -singlefile -transp -r 200 "$f" "${f%.pdf}" 2>/dev/null && mv "$f" "$f.aside" && pdfinfo -box "$f.aside" | LC_ALL=C awk '/^CropBox/{w=$4-$2; h=$5-$3; printf "%%%%BoundingBox: 0 0 %d %d\n%%%%HiResBoundingBox: 0 0 %.2f %.2f\n", w+0.5, h+0.5, w, h}' > "${f%.pdf}.xbb"
  else
    timeout 120 python3 -I "$H/svgjpeg.py" "${f%.pdf}.svg" > /dev/null || true
  fi
done
# the drivers: PGF and graphicx write dvisvgm specials, hyperref hypertex links (dvisvgm turns them
# into SVG links); PGF's dvisvgm driver lists no image formats, so it is given graphicx's;
# \videolink (an MP4 embedded in the PDF, pdfTeX only) becomes its poster in a marked group;
# pict2e (qtree loads it) would input dvips.def over graphicx's dvisvgm.def, which moves the layout
# (AS S4, P1, IAG M2, 2026-11-01): dvips.def counts as loaded, and pict2e gets its two PostScript macros
# every image placed in a marked group, its alt= key and its figure's caption written to __dvi.alt for
# altfix.py; what Beamer's background templates draw is marked as decoration
# \transparent (transparent.sty, pdfTeX only) would print its argument in DVI: harmless if undefined
cat > tex/__dvi.tex <<EOF
\\def\\pgfsysdriver{pgfsys-dvisvgm.def}
\\PassOptionsToPackage{dvisvgm}{graphicx}
\\PassOptionsToPackage{dvisvgm}{xcolor}
\\PassOptionsToPackage{hypertex}{hyperref}
\\makeatletter
\\@namedef{ver@dvips.def}{}
\\providecommand\\Gin@PS@raw[1]{\\special{ps: #1}}
\\providecommand\\Gin@PS@restored[1]{\\special{" #1}}
\\AddToHook{file/pgfsys-dvisvgm.def/after}{\\def\\pgfsys@imagesuffixlist{.svg:.pdf:.png:.jpg:.jpeg:.eps:}}
\\newwrite\\dvialt@out\\immediate\\openout\\dvialt@out=\\jobname.alt
\\newcount\\dvialt@n\\newcount\\dvialt@figs\\newcount\\dvialt@fig\\gdef\\dvialt@cur{}\\gdef\\dvialt@deco{0}
\\AddToHook{package/graphicx/after}{\\define@key{Gin}{alt}{\\gdef\\dvialt@cur{#1}}}
\\def\\dvialt@setfileX#1#2#3{\\global\\advance\\dvialt@n\\@ne\\protected@edef\\dvialt@t{\\dvialt@cur}%
\\edef\\dvialt@f{#3}\\immediate\\write\\dvialt@out{I \\the\\dvialt@n\\space\\ifnum\\dvialt@deco=1 D\\else\\the\\dvialt@fig\\fi\\space\\detokenize\\expandafter{\\dvialt@f}\\space|\\space\\detokenize\\expandafter{\\dvialt@t}}%
\\special{dvisvgm:raw <g class='dvialt' data-alt='\\the\\dvialt@n'>}\\dvialt@setfile{#1}{#2}{#3}\\special{dvisvgm:raw </g>}\\gdef\\dvialt@cur{}}
\\NewDocumentCommand\\dvialt@captionX{om}{\\protected@edef\\dvialt@t{#2}\\immediate\\write\\dvialt@out{C \\the\\dvialt@fig\\space|\\space\\detokenize\\expandafter{\\dvialt@t}}\\IfValueTF{#1}{\\dvialt@caption[#1]{#2}}{\\dvialt@caption{#2}}}
\\AddToHook{env/figure/begin}{\\global\\advance\\dvialt@figs\\@ne\\global\\dvialt@fig\\dvialt@figs}
\\AddToHook{env/figure/end}{\\global\\dvialt@fig\\z@}
\\AtBeginDocument{\\let\\dvialt@setfile\\Gin@setfile\\let\\Gin@setfile\\dvialt@setfileX\\NewCommandCopy\\dvialt@caption\\caption\\let\\caption\\dvialt@captionX\\ifdefined\\addtobeamertemplate\\addtobeamertemplate{background}{\\gdef\\dvialt@deco{1}}{\\gdef\\dvialt@deco{0}}\\addtobeamertemplate{background canvas}{\\gdef\\dvialt@deco{1}}{\\gdef\\dvialt@deco{0}}\\fi}
\\makeatother
\\AtBeginDocument{\\providecommand\\transparent[1]{}\\providecommand\\texttransparent[2]{#2}}
\\AtBeginDocument{\\ifdefined\\videolink\\renewcommand{\\videolink}[2]{\\leavevmode\\special{dvisvgm:raw <g class='videolink' data-video='#1'>}#2\\special{dvisvgm:raw </g>}}\\fi}
\\input{$name.tex}
EOF
export TEXINPUTS="./img//:./sty//:./tex//:./code//:" BSTINPUTS="./bst//:./sty//:" BIBINPUTS="./bib//:"
mkdir -p out
timeout 600 latex -interaction=nonstopmode -output-directory=out tex/__dvi.tex > out/latex1.txt 2>&1 || true
if grep -q '\\bibdata' out/__dvi.aux 2>/dev/null; then (cd out && BIBINPUTS="../bib//:" BSTINPUTS="../bst//:../sty//:" timeout 120 bibtex __dvi > bibtex.txt 2>&1 || true); fi
for k in 1 2; do timeout 600 latex -interaction=nonstopmode -output-directory=out tex/__dvi.tex > out/latex2.txt 2>&1 || true; done
grep -E '^!' out/__dvi.log | sort | uniq -c | sed 's/^/latex: /' || true
grep -qE 'Fatal error occurred|Emergency stop' out/__dvi.log && { echo "latex stopped on a fatal error: see $W/src/out/__dvi.log"; exit 1; }
[ -s out/__dvi.dvi ] || { echo "no DVI"; exit 1; }
timeout 120 dv2dt out/__dvi.dvi ../dvi.dt
timeout 120 python3 -I "$H/fixdvi.py" ../dvi.dt ../fixed.dt
n=$(grep -c '^bop' ../fixed.dt)
# one more page, with every character of the deck: its fonts stand in for the per-page subsets
timeout 120 python3 -I "$H/spaces.py" ../fixed.dt ../spaced.dt
g=$(timeout 120 python3 -I "$H/allglyphs.py" ../spaced.dt ../glyphs.dt)
timeout 120 dt2dv ../glyphs.dt out/fixed.dvi 2>/dev/null
mkdir -p ../svg ../svgf
# all pages in one run (dvisvgm writes p<n>.svg); then the extra page alone, for its fonts
timeout 1800 dvisvgm --page=1-$n --font-format=woff2 --linkmark=none --bbox=papersize -o "../svg/p%p.svg" out/fixed.dvi > /dev/null 2> ../svg/all.err || true
grep -i 'error' ../svg/all.err | head -5 || true
for f in ../svg/p0*.svg(N); do b=${f:t:r}; mv "$f" "../svg/p$((10#${b#p})).svg"; done
for p in $(seq 1 $n); do
  [ -s "../svg/p$p.svg" ] && timeout 60 python3 -I "$H/svgfix.py" "../svg/p$p.svg" "../svgf/p$p.svg" "$W/src" > /dev/null
done
# the deck's language: its "% !TeX spellcheck" line (en_GB -> en-GB), else en
lang=$(sed -n 's/^% *!TeX spellcheck *= *\([A-Za-z_]*\).*/\1/p' "$deck" | head -1 | tr _ -); lang=${lang:-en}
timeout 60 python3 -I "$H/altfix.py" out/__dvi.alt ../svgf $n $lang
timeout 120 dvisvgm --page=$g --font-format=woff2 --bbox=papersize -o ../glyphs.svg out/fixed.dvi > /dev/null 2>&1 || { echo "dvisvgm failed on the glyph page ($g)"; exit 1; }
timeout 300 python3 -I "$H/assemble.py" ../svgf $n "$name" "$out" ../glyphs.svg
sed -i '' "s/<html lang=\"en\">/<html lang=\"$lang\">/" "$out"
echo "gzip: $(gzip -9 -c "$out" | wc -c | tr -d ' ') bytes"
