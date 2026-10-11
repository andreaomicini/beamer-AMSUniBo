# AMSUniBo in HTML

How to turn an AMSUniBo Beamer deck into a single HTML page that matches its PDF
page for page, and the tools that do the mechanical part. None of this is in
`style.zip`: the release zips the top-level files only.

The page is a translation, not a conversion. The PDF is the reference: the text,
its line breaks and its geometry are copied from it, and the result is checked
against it by overlay. Each experiment adds to [what we have learnt](#experiments)
at the end of this file.

## the page

One self-contained `.html` file, named like the deck's copy in `pdf/` and kept in
the deck's `html/`. It loads nothing from the network, so it works offline and can
be attached to an APICe page like the PDF. It is laid out in this order:

1. the theme, as CSS in a `<style>` in the head;
2. the frames, one `<section class="frame">` per PDF page;
3. a `<style>` for what belongs to this deck only;
4. a short script that builds the headline and footline, scales the page to the
   window and handles the keys (→ ← space PgUp PgDn Home End, `f` for full
   screen; `#n` opens PDF page *n*);
5. the `<!-- ASSETS -->` block, generated: fonts, seal and pictures as data URIs.

Everything above the assets is written by hand and meant to be read and edited.
The model is `agot-aixia2026-slides/html/Agentic Graph of Thoughts (AGoT).html`.

### the frame

<!-- markdownlint-disable MD013 -->
| Beamer | HTML |
| --- | --- |
| `\section{X}` | `data-section="X"` on each of its frames; the headline is built from it |
| `noframenumbering` | `data-noframenumbering` |
| `\author[short]`, `\institute[short]`, `\title[short]`, `\date[short]` | `data-shortauthor` … `data-shortdate`, and `data-totalframes`, on `<main class="deck">` |
| the paper size | `data-width` and `data-height` on `<main class="deck">`, the drawing size in px: `1024`/`768` for 4:3, `1024`/`576` for 16:9 |
| `\frametitle` | `<h2 class="frametitle">`, with ` I`, ` II` … copied from the PDF on `allowframebreaks` pages |
| frame body | `<div class="body">`, with the size class (`small`, `footnotesize`, `scriptsize`) when the frame sets one |
| `block`, `alertblock`, `exampleblock` | `<div class="block">`, `block alert`, `block example`, holding `h3.block-title` and `div.block-body` |
| `itemize`, `enumerate`, `description` | `ul`, `ol`, `dl` with `dt`/`dd` |
| `\tightitemize` | `class="tight"` on the list |
| `\alert`, `\aalert`, `\emph`, `\textbf`, `\textsc`, `\texttt` | `span.alert`, `span.aalert`, `em`, `b`, `span.sc`, `code` |
| `\ccite{key}` | `<a class="ccite" href="#cite-key">[Label, year]</a>`, the label as the PDF prints it |
| `\uurl`, `\apice{talk}{Name}` | `a.uurl`, `a.apice`, linked to the full address |
| math | written out: `<i>` for variables (always light), `<sub>`, Unicode symbols, `span.rel` around a relation |
| a TikZ picture | `<img class="figure" data-asset="name" alt="…">`, the `alt` describing what it shows |
| the bibliography | `p.bibitem#cite-key` holding `biblabel`, `bib-author`, `bib-title`, `bib-location`, `bib-note`, `bib-links` |

<!-- markdownlint-enable MD013 -->

## the rules

### general, for any Beamer deck

* **Copy TeX's line breaks; do not let the browser reflow.** TeX may shrink the
  interword glue (`fontdimen4`) to fit one more word on a line, which a browser
  never does, so it would wrap that line one word early. Every line the PDF breaks
  gets a `<br>`, and `white-space: nowrap` holds the rest. Take the breaks from
  `pdftotext`.
* **Copy the page breaks too.** An `allowframebreaks` frame becomes as many
  frames as the PDF has pages, each with the PDF's numbering suffix, even when
  that suffix looks wrong.
* **Work in TeX points.** The page is drawn at 1024 × 768 px and scaled to the
  window; `--pt` is one TeX point, `1024px / 362.835` for 128 mm paper. Every
  length in the CSS is `calc(n * var(--pt))`, so a TeX dimension goes in as it is.
* **Measure, never guess.** `pdftotext -bbox` gives every word's box in points;
  margins, indents and label widths come from there. Inked lines come from
  `compare.py`.
* **The sizes of the 11pt class**: `\normalsize` is 10.95pt, not 11, on a 13.6pt
  baseline; `\small` 10/12, `\footnotesize` 9/11, `\scriptsize` 8/9.5, `\tiny`
  6/7, `\large` 12/14, `\Large` 14.4/18.
* **`[c]` is not centred.** beamer's skips are 1fill above and 1.5fill below,
  for `allowframebreaks` pages 0.4 and 0.6 `\paperheight`, so content sits 40/60
  in the free space. `.body::before` and `::after` grow 2 and 3.
* **Spacing starts from beamer's own values**: `\@listi` gives topsep and itemsep
  3pt, `\@listii` topsep 2pt and itemsep 0; leftmargin 2em, labelsep .5em,
  description width 2cm. TeX's stretch and shrink then move these frame by frame.
  The variance is real, so correct it on the frame (`--itemsep`, `--subtopsep`,
  or a `padding` on the body as a nudge) rather than in the theme.
* **A display `\[…\]` opening a paragraph** leaves an empty line above it, and a
  generous `\belowdisplayskip` below. Give it the PDF's space, measured.
* **Pictures come from the deck**: TikZ externalised, then `pdftocairo -svg`.
  Each goes in as an `<img>` data URI, never inline: pdftocairo's glyph ids repeat
  from one SVG to the next and would collide. The SVG keeps the TikZ bounding box,
  so `width` alone sizes it, as `\resizebox{\linewidth}{!}` did.
* **Fonts are the ones the PDF used**: the TeX Live OTFs of the same faces,
  subset to WOFF2, with their OpenType features kept.
* **Check by overlay, in more than one engine.** Every page is shot in Firefox
  (Gecko) and in WebKit, the engine of Safari, and each is compared with
  `pdftoppm` of the PDF at the same size. The target is the same lines within a
  few pixels; a constant offset is the frame's glue, a step is one gap.

* **Embedded, the deck tells its host its shape.** Every HTML deck must do this,
  so that APICe (or any page) can frame it at its own proportions, 4:3, 16:9 or
  anything else. Three parts, all in the deck, copied as they are:

  1. the drawing size on the deck element: `1024`/`768` for 4:3, `1024`/`576` for
     16:9, the same numbers the frame CSS uses:

     ```html
     <main class="deck" data-width="1024" data-height="768" …>
     ```

  2. scaling on the root's size, not on the `resize` event, which a frame resized
     by its host does not reliably fire:

     ```js
     const fit = () => deck.style.setProperty('--scale',
       Math.min(innerWidth / +deck.dataset.width, innerHeight / +deck.dataset.height));
     new ResizeObserver(fit).observe(document.documentElement);
     ```

  3. the announcement, at the end of the deck's script, after the first `fit()`:

     ```js
     if (window.parent !== window)
       window.parent.postMessage({ type: 'deck-size',
         width: +deck.dataset.width, height: +deck.dataset.height }, '*');
     ```

  A message, not a read from outside: the host frames an uploaded file with
  `sandbox="allow-scripts"` and no `allow-same-origin`, which must stay, so it
  cannot look inside. The host side, as APICe's Talks sheet has it for its
  `<iframe id="talkhtml">`:

  ```js
  addEventListener('message', e => {
    const f = document.getElementById('talkhtml');
    if (!f || e.source !== f.contentWindow || e.data?.type !== 'deck-size') return;
    const { width: w, height: h } = e.data;
    if (w > 0 && h > 0) { f.style.aspectRatio = `${w} / ${h}`; f.style.height = 'auto'; }
  });
  ```

  A deck that posts nothing keeps the host's default frame.

### AMSUniBo

* **Palette**: the `--ams*` custom properties copy `beamercolorthemeamsunibo.sty`
  name for name. Use them by name and never write a hex value elsewhere.
* **Faces**: Merriweather Sans light, 300, for the body; regular, 400, for block
  titles; bold, 700, for `\textbf`; Merriweather regular for the frame and page
  titles, and its italic for an `\emph` in a title; Inconsolata for code and
  addresses, with `ss01` and `ss03` (the `varl` and `varqu` options). Oldstyle
  figures everywhere, math included:
  `font-variant-numeric: oldstyle-nums proportional-nums`.
* **`scaled=0.92` is the sans only**: `--fs` is `0.92 * --pt` and sizes Merriweather
  Sans. The serif titles are not scaled, and the math symbols are not either.
* **Math symbols** Merriweather lacks (`→ ⇐ ⇒ ∈ ∙ ∼ ⋅`) come from NewCMMath.
  They are loaded as a second Merriweather Sans face with a `unicode-range` and
  `size-adjust: 108.7%`, declared **after** the text faces or the text faces win.
  `\iff` is ⇐ and ⇒ overlapped, as TeX builds it. `×`, `≠`, `≥` and `−` are
  closer in Merriweather and stay there. `\mathcal` letters are the Unicode
  script ones (`𝒜 𝒞 ℒ`), from the same face.
* **Geometry, measured on 128 mm paper**: headline 12.8pt, frame title band 24.4pt
  with its text at 8.5pt, footline 9.9pt; text margin 10.909pt, text width
  342.295pt; item indent 21.818pt.
* **infolines**: the headline is two halves, the section right-aligned on
  `amsred` and an empty `amsgreentint2`. The footline is three thirds: author
  (institute) on `amsgreendark`, the short title on `amsgreentint2`, the date and
  `n / N` on `amsgreentint`. All of it is in `\tiny`.
* **Blocks**: rounded at 4pt and shadowed. The box overhangs the text 4pt left
  and 2.6pt right, with 4pt of padding. The title is 12pt regular in a bar
  15.76pt tall, its baseline 11.95pt down; the body opens with a 2pt gradient
  from the title colour. An untitled block's text starts 3.5pt into the box. A
  block has 7.5pt above it, 4pt below, and 7pt before a list that follows it.
* **Balls**: radial-gradient spheres in `amsred`, 5.2pt at the first level, 4pt
  at the second. Enumerate balls are 8.4pt with the number in white bold.
* **Paired commands keep their weights**: `.ccite` is `amsgreyline`, `\tiny`,
  raised 3.3pt; `.uurl` and `.apice` are `amsred` Inconsolata at 8pt; in the
  bibliography the APICe marker is `amsgreendark` and `.dddoi`/`.uuurl` are
  `amsgreyline` at 6pt.
* **Bibliography colours by block**: label `amsgreymid`, authors `amstext`, title
  `amsred` bold, location `amsgreymid`, note `amsgreendark`. The hanging indent is
  11.75pt.
* **Title page**: a rounded, shadowed `amsgreentint` box holds the title (14.4pt)
  and the subtitle (`amsgreymid`, 10.95pt), both serif. Authors are `amsred`,
  with the speaker bold; the institute is `amsgrey` in `\scriptsize`, and the date
  `amsgreymid`.
* **The seal**: the theme's own placement, rendered and cropped by `seal.sh`,
  which prints the box to put in `.frame::before`.

## the tools

`tools/` needs TeX Live, poppler (`pdftoppm`, `pdftocairo`, `pdfinfo`), Firefox,
and a Python with `fonttools`, `brotli`, `Pillow` and `playwright`:
`python3 -m venv .venv && .venv/bin/pip install fonttools brotli pillow playwright`
(and `pymupdf` for `tex2html`),
then `.venv/bin/python -m playwright install webkit`, with that venv first on
`PATH`. Playwright's WebKit stands in for Safari, which does not reliably accept
automated sessions. From the deck's root, with `A` a scratch folder for the
assets:

```sh
T=../beamer-AMSUniBo/html/tools
$T/subset-fonts.sh $A/fonts
$T/seal.sh cesena $A                        # or bologna; prints the CSS box
$T/externalize.sh tex/<deck>.tex $A         # fig-0.svg, fig-1.svg … in source order
mv $A/fig-0.svg $A/<name>.svg               # one per data-asset name in the page
cp img/<name>.png $A/                       # the deck's own pictures: .png or .jpg
python3 $T/assets.py "html/<Title>.html" $A # refills the ASSETS block in place
```

and to check:

```sh
pdftoppm -scale-to-x 1024 -scale-to-y 768 -png "pdf/<Title>.pdf" $A/ref/p
$T/shoot.sh firefox "html/<Title>.html" $A/firefox <pages>
$T/shoot.sh webkit "html/<Title>.html" $A/webkit <pages>
python3 $T/compare.py $A/ref $A/firefox <page> $A/sheet.png   # and the same for webkit
```

### tex2html, the converter

`tools/tex2html/` writes the page instead of a hand: frames from the `.tex`,
references from the `.bbl`, line breaks and per-frame corrections from the PDF.
It knows the TeX subset of the decks it has met and reports any command it does
not; a new deck may need it grown. It also needs `pymupdf` in the venv, and
Playwright's Firefox (`playwright install firefox`) to measure.

`theme.css` and `script.js` there are the theme and the deck script every
generated page carries, the deck-size announcement included. What belongs to
one deck lives in that deck, in `html/tex2html/`: `deck.json` (paths, names,
short fields, alt texts, the deck's own name macros), `titlepage.html`,
`deck.css` and `nudges.json`, the per-frame corrections, which `nudge.py` writes.

```sh
export TEX2HTML_DECK=html/tex2html
python3 $T/tex2html/build.py                # writes the page named in deck.json
python3 $T/assets.py "html/<Title>.html" $A
python3 $T/tex2html/nudge.py webkit "" gaps # build; twice more; then "both"
python3 $T/tex2html/stats.py webkit         # worst errors, per page
python3 $T/tex2html/stats.py firefox
python3 $T/tex2html/blocks.py webkit        # every block against the PDF's box
```

`build.py` keeps the page's ASSETS block, so a rebuild needs `assets.py` only
when the assets change. After an edit to a frame, rebuild the PDF, then the
page, and nudge that frame again: its old corrections may no longer fit.

## the checklist

Every page, new or old, before it is called done. Each point is a mistake an
experiment made and Andrea saw; each has the check that catches it. A page made
before a point was added is checked against it when it is next touched.

1. **Text and lines.** The text and its line breaks are identical to the PDF,
   and every baseline is within about 1pt of it, in WebKit and in Firefox:
   `stats.py webkit`, `stats.py firefox`.
2. **Blocks.** Every block's box meets the box the PDF draws within about 1pt,
   top and bottom: `blocks.py webkit`, `blocks.py firefox`. What it caught:
   * a correction on `.block-body` itself. Never put a margin or a padding
     nudge there: under a title bar it opens a light line, or slides the body's
     gradient over the bar and blurs its edge. Correct what is inside the body,
     or move an untitled block as a whole;
   * the title bar's height: 15.76pt, its baseline 11.95pt down, which is a
     padding of 1.03pt and 0.73pt. Pages made before 2026-10-12 have 1.5pt and
     1pt, 0.7pt too tall;
   * the bottom, which TeX sets by the real depth of the last line: a body's
     padding-bottom is 2.8pt less the gap between that line's deepest glyph
     and a `g`. `depth.py` computes it from the PDF and the fonts; by hand, a
     last line with none of `g j p q y , ; ( ) /` takes about 2.44pt less at
     `\normalsize`, 2.2pt in a second-level item;
   * an untitled block: its body's padding-top is 3.5pt.
3. **Bibliography.** An `<i>` in a title is bold italic, as the PDF has it:
   `.bib-title > i { font-weight: 700; }`. The theme's `i` rule makes it light.
4. **Footline.** The date's right edge does not move with the page number.
   Check it against the PDF on a numbered and on an unnumbered page; in
   experiment 2 the number sat in a 28pt box, 18.38pt when unnumbered.
5. **Embedded.** The three parts of the deck-size rule above, copied as they
   are.
6. **Look closely.** Overlays at 1024 × 768 hide half-point faults that show on
   a real screen. Zoom on the block bars at four times, the PDF beside both
   engines: `pdftoppm -scale-to-x 4096 -scale-to-y 3072`, and a Playwright page
   with `device_scale_factor=4`.

The checks run on a page written by hand too: a `deck.json` with `root`,
`tex`, `bbl`, `pdf` and `page` is all `stats.py` and `blocks.py` need. Text
inside a picture (TikZ labels in the PDF) can throw `stats.py`'s alignment off
on that page, and a table can throw off `blocks.py`'s: read the rows, not only
the worst number.

## experiments

### 1 — AGoT @ AIxIA 2026, 2026-10-11

`agot-aixia2026-slides`: 20 pages, three TikZ pictures (two graphs and a pgfplots
chart), one booktabs table, fifteen blocks, a three-page bibliography. Every page
ended within about 5px of the PDF.

* The line-break rule was found here. Reflowed text broke one word early on
  every line TeX had squeezed.
* The 40/60 rule was found here. Centred content sat up to 40px off, and by an
  amount that depended on its height.
* Per-frame corrections were needed on the two `allowframebreaks` pages of
  *From Chain-of-Thought to Graph-of-Thoughts*, where TeX stretched list spacing
  by 8–10px. Smaller nudges, 25–30px of padding, went on four other frames and
  on the three reference pages.
* An `<img>` with a class loses its margin to `img.figure { margin: 0 auto }`.
  Size and space pictures with `img.<class>`.
* `.block-body > :first-child { margin-top: 0 }` beats a plain class on a display
  that opens a block. Qualify it as `.block-body > .displaymath`.
* The page is standard HTML and CSS: no engine prefix, nothing loaded from the
  network. Two `-webkit-` properties were found and removed after the first
  commit; the rule is to write the standard property and nothing else.
* The checks were first made in Chrome alone, which proves nothing about the
  other engines. Redone in Firefox and in Playwright's WebKit 26.6, every page
  matches the PDF within the same few pixels in both. Between the two engines,
  0.3–3% of pixels differ, all of it glyph anti-aliasing, none of it position.
* Safari 27 itself would not open a WebDriver session, with remote automation
  allowed, `safaridriver --enable` done and the driver run from Terminal. Hence
  Playwright's WebKit in `shoot.sh`.
* Still visible, in every engine: NewCMMath's `→` is a little shorter than the
  one in the PDF, so text after it sits a few pixels left.
* Still open: the CSS of the theme and the script live in the deck's page. The
  next deck should take them from here, which means extracting them into this
  folder and having `assets.py` inline them as it does the fonts.

### 2 — MAS tutorial @ AIxIA 2026, 2026-10-12

`mastutorial-aixia2026`: 120 pages, of which 7 contents frames, 5
`allowframebreaks` frames, two pictures (a PNG chart and a JPG cover in
`picturecolumns`) and a bibliography of 108 entries over 21 pages. Every
baseline ended within 1.0pt of the PDF in WebKit and 1.4pt in Firefox; left
edges within 2.6pt, the worst where TeX shrank a line's interword glue.

* Too many pages to write by hand: the page was generated from the `.tex` and
  the `.bbl` by a converter for the deck's TeX subset, then checked like a
  written one. Its text matched the PDF character for character on every page,
  acronym first uses (reset on every page by the deck's `names.sty`) included.
* Line breaks were copied by aligning the page's characters with the PDF's
  (PyMuPDF), not its words: a break after an explicit hyphen has no space to
  turn into a `<br>`.
* The check that counts is the baseline of every text run, read in the
  browser through a zero-height `inline-block` at its start and compared in
  points with the PDF's glyph origins. `compare.py`'s ink lines misread block
  title bars in Firefox and flag pages that are right.
* TeX's glue was corrected per frame as in experiment 1, but computed: a
  `margin-top` on the element where the PDF steps (338 of them) and one padding
  per body (87). On a `[c]` body, a top padding moves the content by 0.6 of
  itself, a bottom one by 0.4.
* An item that wraps before its sub-list takes the sub-list's baselineskip,
  12pt at the first level and 11pt at the second: the sub-list's font is set
  before TeX ends the item's paragraph. `li.wrapsub` carries it.
* Found here: third-level items are `\footnotesize`, 9/11; `\item[label]` is
  right-aligned `.5em` before the text, in the item's size; `indquotation` has a
  2em left margin in a block and none in an item, its first line indented
  1.5em; a lone `$=$`, `$+$` or `$\times$` has no space around it, `\mid` has
  5mu each side; `\smaller` from `\normalsize` in a quotation is
  `\footnotesize`; a `[t]` frame has no top fill; an unnumbered page's date sits
  9.58pt further right.
* An `<i>` in a bibliography title is bold italic, as in the PDF; the theme's
  `i` rule made it light. Experiment 1's page has the same rule and one such
  title, not rechecked.
* Tools: `subset-fonts.sh` and `assets.py` gained Merriweather Italic and the
  three script letters, `assets.py` embeds `.png` and `.jpg` beside `.svg`, and
  `shoot.sh` makes its output folder absolute: given a relative one, headless
  Firefox wrote nothing and said nothing.
* Over 99 pages `pdftoppm` names its files `p-001.png`, while `compare.py` reads
  `p-01.png`: link them under two-digit names.
* The converter, the measuring and the per-frame corrections are kept as
  `tools/tex2html/`, the deck's inputs in its `html/tex2html/`.
* Block bars, seen by Andrea on the live page: a correction put on a block's
  body opened a light line under the title bar, or slid the body's gradient up
  over it, which read as a blurred edge. The nudger now never moves a body,
  only what is inside it, and an untitled block as a whole. The title bar was
  also 0.7pt too tall in both engines: 1.03pt and 0.73pt of padding, not 1.5
  and 1, give the PDF's bar. Experiment 1's page still has the old padding.
* **TeX ends a block at the real depth of its last line**, a browser at the
  font's descent: a last line with no descender (`own`, `social`) ends its
  block 2.44pt higher in the PDF than one with a `g` or a `p`. `depth.py`
  reads each block's last line in the PDF and the glyph outlines of its faces,
  and pads the body by the difference. Every block now meets the PDF's drawn
  box within about 1pt, top and bottom; `compare.py` could not have seen it.
* The deck-size rule came the same night, from APICe: the page carries it
  through the converter's `script.js`, and was checked framed in a sandboxed
  `<iframe>` with the host listener above, in WebKit and Firefox.
