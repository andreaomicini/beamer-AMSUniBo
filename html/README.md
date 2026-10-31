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

From the root of a deck repository: an AMSUniBo deck has this repository as its `.style/` submodule,
a deck of another style reaches it as the sibling clone `../beamer-AMSUniBo/`:

```bash
bash .style/html/html.sh [<deck>] [--compare]               # AMSUniBo decks
bash ../beamer-AMSUniBo/html/html.sh [<deck>] [--compare]   # any style
```

- `<deck>` is the jobname (`l2-lp`, or `tex/l2-lp.tex`); it may be omitted when `tex/` holds one
  `.tex`.
- The page goes to `html/<name>.html`, `<name>` being the PDF's name in `pdf/` (latexmk's
  `aux/<deck>.pdfprev`, else `aux/<deck>.pdfname`, else the jobname).
- The work is done on a copy of the sources in `aux/html/<deck>/`; the repository is only read.
- `--compare` draws every page in Playwright WebKit and in Firefox headless and measures it against
  `aux/<deck>.pdf` (ImageMagick AE at 12% fuzz): `aux/html/cmp-<deck>/wk.txt` and `ff.txt`, one line
  per page. Never Chrome.

A deck takes 6–27 s for a talk, about 70 s for a 329-page course deck.

Needs: TeX Live (`latex`, `bibtex`, `dvisvgm`, `dv2dt`, `dt2dv`), and from Homebrew `poppler`
(`pdftocairo`, `pdfinfo`, `pdftoppm`), `imagemagick`, `fonttools` (its own interpreter, which
has brotli for WOFF2); for `--compare` also `playwright-cli` with WebKit, and Firefox.

## The page

One `.html` file that loads nothing from the network, so it works offline and can be attached to an
APICe page like the PDF. Each PDF page is a `<section class="frame">` holding the page's SVG; the text
is real text in the deck's fonts (selectable, searchable, read aloud), the links work (internal ones go
to `#<page>`, external ones open a new tab). Keys → ← space PgUp PgDn Home End, `f` for full screen,
`#n` opens page *n*; inside an APICe page it sends the `deck-size` message.

## The pipeline

`tools/deck2html.zsh <repo> <deck.tex> <out.html>`.

**On the way in**, on the copy:

1. PDF pictures become SVG beside them (`pdftocairo -svg`), which PGF and graphicx then prefer:
   dvisvgm's own PDF route names images by object number, and two PDFs with an image 4 on one page
   swapped their pictures. A PDF whose SVG needs soft-mask filters becomes a transparent 200-dpi PNG on
   its crop box instead, with an `.xbb` of that box (pdflatex reads a PDF on its crop box). Large photo
   bitmaps inside the SVGs become JPEG when that halves them (`svgjpeg.py`); `\includegraphics{x.pdf}`
   loses its extension so that the choice applies.
2. Bitmaps whose resolution has no unit get an `.xbb` at 72 dpi, pdflatex's reading (`imgbb.py`).
3. Video commands the tool does not handle are named in a WARNING at the start.
4. `latex`, through a wrapper that only sets drivers: PGF `pgfsys-dvisvgm.def`, graphicx and xcolor
   `dvisvgm`, hyperref `hypertex`; PGF's driver is given graphicx's image formats; `\videolink` becomes
   its poster in a marked group. A fatal latex error stops the conversion.
5. The DVI is repaired in its text form (`dv2dt`/`dt2dv`): colour groups for Beamer's `\color` inside
   pictures, closed before PGF's own `</g>`, and balanced groups (`fixdvi.py`); word spaces marked
   (`spaces.py`); one more page with every character of the deck, font by font (`allglyphs.py`).

**dvisvgm**: `--font-format=woff2 --linkmark=none --bbox=papersize`, all pages in one run.

**On the way out:**

1. `svgfix.py` per page: Beamer's block shadow (a fading, which PGF's SVG drivers lack) redrawn as a
   blurred rectangle and moved before the block's title, so the block covers it and only its fringe
   shows; glyphs never take the colour groups' stroke; a `<use>` of a `<symbol>` gets its size; linked
   bitmaps and SVGs embedded; the space marks become spaces; a `\videolink`'s MP4 found.
2. `assemble.py`: one page; ids and classes prefixed per page; a repeated picture stored once; the
   extra page's fonts replace every per-page subset (one WOFF2 per font); private-use glyphs
   (old-style figures) given their real characters too (`fontfix.py`); ligatures as plain letters;
   each video embedded once, laid over its poster and played on a click.

## Results

Checked against the PDF in WebKit and Firefox on nine decks of all six AMS styles (2026-10-31): no page
above 3.1%, the rest being anti-aliasing; every page smaller than its hand-made predecessor once
gzipped (APICe serves attachments gzipped). Checked by eye since: shadows on AGoT, Blockchain, DS C4,
SMA-LS C1; videos in AS C7; TikZ pictures in IAG L2 and SMA-LS S4.

## Limits

- The text is placed word by word: a paragraph copies as words with spaces, not as flowing lines, and
  a word hyphenated by TeX stays broken. Not relevant: the HTML is for viewing, the PDF for the text.
- Images carry no description (`alt`), unlike the hand-made pages.
- Beamer's shadow is redrawn, not translated: it matches at the eye, a hair darker than the PDF's.
  The block's title is found as the first picture at the block's x since the previous block; if none
  is found, the shadow goes just before the body.
- Videos: only `\videolink{<mp4>}{<poster>}`; another video command gets its own method when the
  warning names it.
- Overlays are pages, so a deck with many steps repeats them; gzip folds them. Left as it is.
- No deck of ours uses TikZ animations yet.

## When a deck shows a problem

Find the smallest case (the frame), see what dvisvgm does with it, and fix it in the way in or the
way out, generally (for Beamer or PGF, never for one deck), checked on that frame against the PDF and
then on two or three other decks where it could show.
