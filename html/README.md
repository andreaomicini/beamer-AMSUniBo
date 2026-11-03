# Beamer decks in HTML

One command turns a Beamer deck into a single self-contained HTML page that matches its PDF page for
page. TeX itself typesets the page: the deck is compiled with `latex` to DVI, `dvisvgm` draws each page
as SVG with the deck's own fonts (WOFF2), and the pages are assembled into one file. Nothing is
translated, so nothing depends on the style: the same command serves every AMS style, and any Beamer
deck in principle. None of this is in `style.zip`: the release zips the top-level files only.

Since 2026-11-01 this is the tool for new HTML pages, in every style. It replaces the translators
(one per style, and the shared one before them), which are kept in the history: AMSUniBo's under the
tag `html-translator-final`, the shared one under `html-shared-final`. Pages already delivered and
corrected by hand stay as they are; when such a deck changes, its page is made again with this command.

## Use

From the root of a deck repository, of any style, through the sibling clone `../beamer-AMSUniBo/`
(never an AMSUniBo deck's `.style/html/`: the pinned submodule lags behind, and `style-lag` ignores `html/`):

```bash
bash ../beamer-AMSUniBo/html/html.sh [<deck>] [--compare]
```

- `<deck>` is the jobname (`l2-lp`, or `tex/l2-lp.tex`); it may be omitted when `tex/` holds one
  `.tex`.
- The page goes to `html/<name>.html`, `<name>` being the PDF's name in `pdf/` (latexmk's
  `aux/<deck>.pdfprev`, else `aux/<deck>.pdfname` turned into a name by `.latexmkrc`'s rules, else the jobname;
  until 2026-11-02 the title was taken raw, and a talk repo without the ledger got `…\\& …\\\\….html`).
- The work is done on a copy of the sources in `aux/html/<deck>/`; the repository is only read.
- `--compare` draws every page in Playwright WebKit and in Firefox headless and measures it against
  `aux/<deck>.pdf` (ImageMagick AE at 12% fuzz): `aux/html/cmp-<deck>/wk.txt` and `ff.txt`, one line
  per page. Never Chrome. Firefox runs on a new empty profile each time (`-no-remote -profile`): with
  Firefox open, a headless run on the usual profile made no picture (2026-11-02).
  The page's address is escaped: a `?` in its name (AS C0, *…Systems?*) cut it, and no browser drew a page
  (2026-11-02).

A deck takes 6–27 s for a talk, about 70 s for a 329-page course deck.

Needs: TeX Live (`latex`, `bibtex`, `dvisvgm`, `dv2dt`, `dt2dv`), and from Homebrew `poppler`
(`pdftocairo`, `pdfinfo`, `pdftoppm`), `ghostscript`, `imagemagick`, `fonttools` (its own interpreter, which
has brotli for WOFF2); for `--compare` also `playwright-cli` with WebKit, and Firefox.

## The page

One `.html` file that loads nothing from the network, so it works offline and can be attached to an
APICe page like the PDF. Each PDF page is a `<section class="frame">` holding the page's SVG; the text
is real text in the deck's fonts (selectable, searchable, read aloud), the links work (internal ones go
to `#<page>`, external ones open a new tab). Keys → ← space PgUp PgDn Home End, `f` for full screen,
`#n` opens page *n*; inside an APICe page it sends the `deck-size` message. The page declares the deck's
language (its `% !TeX spellcheck` line, `en_GB` → `en-GB`; else `en`); each page is a `role="group"`, so
its text and pictures reach a screen reader one by one.

## Text alternatives (2026-11-01)

Every picture a deck places with `\includegraphics` gets a text alternative, `role="img"` with an
`aria-label` (and the deck's `lang`), by these rules, in order:

1. its `alt={…}` key: `\includegraphics[alt={…}]{…}`, always first (graphicx accepts the key and
   ignores it, so the PDF does not change);
   `picturecolumns` and `\creditedpicture` take the same key and pass it on (since 2026-11-03):
   `\begin{picturecolumns}[alt={…}]{…}`, `\creditedpicture[alt={…}]{…}{…}`;
2. else the `\caption` of the `figure` it is in, the official description of the picture;
3. else none, and the conversion names it at the end, `WARNING: no alt and no caption: page <n>, <file>`.
   Never left so: its text is written into the deck's source as `alt=`, after reading the frame (title
   and text, the whole deck if needed) and looking at the picture; from then on rule 1 holds.

In a text, markup is dropped (`\emph{x}` is *x*, `{J}ason` is *Jason*) and escaped characters are printed:
`\%`, `\&`, `\{ \}` (a set, AS C6's `\{on(A,B), on(B,C)\}`, had lost its braces until 2026-11-02).

What Beamer's `background` and `background canvas` templates draw (the styles' seal) is decoration:
`aria-hidden`, no text, no warning. The texts of the pages made by hand (before 2026-11-01) are taken
back into the sources as `alt=` by the image's file name (their `data-asset`), not written again.
Tried on AS P1 (5 texts taken back), S5 (a caption), S4 (12 written): every picture named in WebKit's
accessibility tree and read by VoiceOver, no page changed in WebKit or Firefox.

## The pipeline

`tools/deck2html.zsh <repo> <deck.tex> <out.html>`.

**On the way in**, on the copy:

1. PDF pictures become SVG beside them (`pdftocairo -svg`), which PGF and graphicx then prefer:
   dvisvgm's own PDF route names images by object number, and two PDFs with an image 4 on one page
   swapped their pictures. A PDF whose SVG needs soft-mask or blend filters (`feImage`, which Firefox does not
   draw: ISE M1's IEEE pages, 2026-11-02) becomes a transparent 200-dpi PNG on
   its crop box instead, drawn by Ghostscript (`pngalpha`): `pdftocairo` drew soft-masked bitmaps in horizontal
   stripes (DS M2, M6, the shaded spheres, 2026-11-03), with an `.xbb` of that box (pdflatex reads a PDF on its crop box). A rotated page (`/Rotate` 90 or 270) has its sides swapped in that
   `.xbb`: the page is drawn turned (by Ghostscript as by `pdftocairo`), and the picture came out squeezed into the unturned box (SMA-LS 06·07 C3a,
   *Tropos*, 2026-11-02). Large photo bitmaps inside the SVGs become JPEG when that halves them (`svgjpeg.py`); `\includegraphics{x.pdf}`
   loses its extension so that the choice applies.
2. Bitmaps whose resolution has no unit get an `.xbb` at 72 dpi, pdflatex's reading (`imgbb.py`); so does a bitmap
   whose name has a space, at its own resolution: `extractbb` cuts such a name, graphicx made the picture square,
   and the frame lost its last blocks to `allowframebreaks` (ISE M0, *tuttofuoco-between words.png*, 2026-11-02).
3. Video commands the tool does not handle are named in a WARNING at the start.
4. `latex`, through a wrapper that only sets drivers: PGF `pgfsys-dvisvgm.def`, graphicx and xcolor
   `dvisvgm`, hyperref `hypertex`; PGF's driver is given graphicx's image formats; `\videolink` becomes
   its poster in a marked group; every picture is preceded by an empty marker, `<g class='dvialt' data-alt='n'/>`,
   and its `alt=` key and its figure's caption are written to `__dvi.alt` (`altfix.py` then puts the text on the
   picture's own group, the one after the marker). A TikZ drawing takes its text the same way, from
   `\begin{tikzpicture}[alt={…}]` (TikZ accepts the key and ignores it, so the PDF does not change: AGoT, 2026-11-02);
   a drawing with neither `alt=` nor a caption is named in a warning. The drawing's text is kept apart, local to it, and a
   picture inside a described drawing counts as decoration: until 2026-11-03 the first `\includegraphics` inside took the
   drawing's text and a nested drawing cleared it (SMA-LS 06·07 S4, its agents; S2 p. 9, two drawings in one). Until 2026-11-02 the picture was wrapped in an open and a close
   group: inside a frame that `[shrink]` really scales, `dvisvgm` then put everything after the picture outside the
   scaling, the frame enlarged and shifted (SMA-LS 06·07 C0, the aliCE logo in a block title); `dvips.def` counts as loaded and `\Gin@PS@raw`/`\Gin@PS@restored` are
   given, for `pict2e` (below). `latex` runs until `.aux` and `.nav` settle, as in `zip.sh`: beamer's frame total
   asks for no rerun, and DS M2's footer read 64 for 66 after a fixed three passes (2026-11-03). A fatal latex error stops the conversion.
5. The DVI is repaired in its text form (`dv2dt`/`dt2dv`): colour groups for Beamer's `\color` inside
   pictures, closed before PGF's own `</g>`, and balanced groups (`fixdvi.py`); word spaces marked
   (`spaces.py`); one more page with every character of the deck, font by font (`allglyphs.py`). That includes the characters `dv2dt` writes as `\XX` in hex — in T1 the quotes “ ” (`\10` `\11`), the dashes – — (`\15` `\16`), the ligatures fi fl ff — which until 2026-11-03 were left out: every page then drew them from a fallback font of another width, and the text after them shifted (M1's title read *“I nformation*).

**dvisvgm**: `--font-format=woff2 --linkmark=none --bbox=papersize`, all pages in one run.

**On the way out:**

1. `svgfix.py` per page: Beamer's block shadow (a fading, which PGF's SVG drivers lack) redrawn as a
   blurred rectangle and moved before the block's title, so the block covers it and only its fringe
   shows; glyphs never take the colour groups' stroke; a `<use>` of a `<symbol>` gets its size; linked
   bitmaps and SVGs embedded; the space marks become spaces; a `\videolink`'s MP4 found.
2. `assemble.py`: one page; ids and classes prefixed per page; a repeated picture stored once; the
   extra page's fonts replace every per-page subset (one WOFF2 per font); private-use glyphs
   (old-style figures) given their real characters too, and a drawn glyph of zero width one unit of width
   (`fontfix.py`: WebKit skips a `<text>` whose only glyph has no width, and `\neq`'s slash vanished, ≠ read =,
   DS M2 and M6, 2026-11-03; every `<text>` has its own `x`, so nothing moves); ligatures as plain letters;
   each video embedded once, laid over its poster and played on a click. Before it, `altfix.py` gives
   each marked picture its text (see *Text alternatives*), hides the background's, and makes each page
   `role="group"`.

## Results

Checked against the PDF in WebKit and Firefox on nine decks of all six AMS styles (2026-10-31): no page
above 3.1%, the rest being anti-aliasing; every page smaller than its hand-made predecessor once
gzipped (APICe serves attachments gzipped). Checked by eye since: shadows on AGoT, Blockchain, DS C4,
SMA-LS C1; videos in AS C7; TikZ pictures in IAG L2 and SMA-LS S4.

## Limits

- The text is placed word by word: a paragraph copies as words with spaces, not as flowing lines, and
  a word hyphenated by TeX stays broken. Not relevant: the HTML is for viewing, the PDF for the text.
- A screen reader speaks the texts in the voice its own settings choose: VoiceOver on an Italian Mac read
  `lang="en-GB"` with the Italian voice. The page declares the language; switching voice is the reader's.
- Beamer's shadow is redrawn, not translated: it matches at the eye, a hair darker than the PDF's.
  The block's title is found as the first picture at the block's x since the previous block, **in the
  body's coordinates** (the same transforms around it); if none is found, the shadow goes just before the
  body. Until 2026-11-02 the coordinates were not compared: in a frame that `[shrink]` really scales, the
  first picture at that x was the frame's own scaled picture, and the shadow, moved before it, left the
  scaling: a dark band over the frame title (SA C3 p. 36, SMA-LS 07·08 C6 on 100 pages); where title and
  body sit in sibling groups, the shadow fell over the title or was lost (AS S4 p. 65, T3 p. 39).
- Videos: only `\videolink{<mp4>}{<poster>}`; another video command gets its own method when the
  warning names it.
- Overlays are pages, so a deck with many steps repeats them; gzip folds them. Left as it is.
- No deck of ours uses TikZ animations yet.

## When a deck shows a problem

Find the smallest case (the frame), see what dvisvgm does with it, and fix it in the way in or the
way out, generally (for Beamer or PGF, never for one deck), checked on that frame against the PDF and
then on two or three other decks where it could show.

- **Options with free text**, 2026-11-01: the step that drops `.pdf` from `\includegraphics{x.pdf}` read the
  options up to the first `]`, and an `alt={…}` holding `[10]` stopped it (AS T3 p. 55, a picture missing):
  options are now read with their braces.
- **`transparent.sty`** loads only under pdfTeX: in DVI `\transparent{.1}` printed `.1` at each listing line
  (AS L4, a `backgroundcolor=\transparent{.1}\color{white}`). The wrapper defines `\transparent` as nothing
  and `\texttransparent` as its text when the package did not; in the PDF that background is invisible anyway.
- **`pict2e` (loaded by `qtree`)**, 2026-11-01: in DVI mode its `pict2e.cfg` picks `dvips` and inputs
  `dvips.def` over graphicx's `dvisvgm.def`. The layout then moves: about 2pt after nested lists and
  3pt after blocks (AS S4, pages at 7–8%), and frames with `allowframebreaks` break elsewhere, so pages
  are lost (AS P1 85 of 88, IAG M2 72 of 74). Found by bisecting S4's preamble on one frame (`latex` +
  `dvipdfmx` against `pdflatex`). The wrapper marks `dvips.def` as loaded and gives the two macros
  `p2e-dvips.def` needs, whose PostScript specials dvisvgm draws: S4, P1, M2 all under 3% in WebKit
  and Firefox, page counts and `qtree` trees as in the PDF. Decks loading `qtree`: AS P1, S4; IAG M2;
  ISE M8; SA S0.
