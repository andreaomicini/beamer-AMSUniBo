# AMSUniBo in HTML

How to turn an AMSUniBo Beamer deck into a single HTML page that matches its PDF
page for page, and the tools that do the mechanical part. None of this is in
`style.zip`: the release zips the top-level files only.

Since experiment 4 the same tools translate AMSBolognaFC decks too:
`"style": "AMSBolognaFC"` in the deck's `deck.json` picks that style's theme,
fonts, seal and measuring constants. Since experiment 5, AMSPurpleAndGold decks
as well (`"style": "AMSPurpleAndGold"`), since experiment 6 AMSSilverBlue ones
(`"style": "AMSSilverBlue"`), since experiment 7 AMSRedGrey ones
(`"style": "AMSRedGrey"`), and since experiment 8 AMSCesena ones
(`"style": "AMSCesena"`).

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
| `\frametitle` | `<h2 class="frametitle">`, with its suffix (a space, then `I`, `II` …) copied from the PDF on `allowframebreaks` pages |
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
    if (w > 0 && h > 0) {
      f.style.aspectRatio = `${w} / ${h}`; f.style.height = 'auto';
    }
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
* **Paired commands take the surface's colour**, as in the theme since 1.8 (and
  in the four families' CSS since their 1.11/1.3):
  `.ccite` is `amsgreyline`, `\tiny`, raised 3.3pt; `.uurl` and `.apice` are
  `amsred` Inconsolata at 8pt; in the bibliography the APICe marker is
  `amsgreendark` and `.dddoi`/`.uuurl` are `amsgreyline` at 6pt. In a block or alert
  title they turn `amsgreybg`, and `.alert`/`.aalert` `amsgreyline`; in the
  example title `.ccite`, `.uuurl` and `.dddoi` are `amsgreymid`.
* **Bibliography colours by block**: label `amsgreymid`, authors `amstext`,
  title `amsred` bold, location `amsgreymid`, note `amsgreendark`. The hanging
  indent is 11.75pt.
* **Title page**: a rounded, shadowed `amsgreentint` box holds the title (14.4pt)
  and the subtitle (`amsgreymid`, 10.95pt), both serif. Authors are `amsred`,
  with the speaker bold; the institute is `amsgrey` in `\scriptsize`, and the date
  `amsgreymid`.
* **The seal**: the theme's own placement, rendered and cropped by `seal.sh`,
  which prints the box to put in `.frame::before`.

### AMSBolognaFC

* **One profile, in `tools/tex2html/deck.py`**: `STYLES` holds what the tools must
  know of a style — the theme CSS, the edges of the head, title band and foot, the
  `\ccite` colour, the block fills, a block body's bottom padding. AMSUniBo is the
  default and its values are the ones the tools always had.
* **Faces**: the theme sets no font, so the PDF is in Computer Modern Sans from
  cm-super (`SFSS…`). The page uses Latin Modern, one family per optical size —
  `LM Sans 8` for 6 and 8pt, `9`, `10` for 10 and 10.95pt, `12` for 12 and 14.4pt,
  `17` — plus `LM Mono`, `LM Roman Caps` for `\textsc` (CM Sans has no small caps,
  the theme falls back to the serif ones) and Latin Modern Math for `→` and `𝜙`.
  Math letters are the sans italic, as beamer sets them (`CMSSI10`).
* **Widths**: cm-super's design sizes are not Latin Modern's. Measured on the PDF,
  the ratio of their advance widths is 1.10 at 6pt, 0.994 at 9pt, 0.989 at
  10.95pt, 0.970 at 14.4pt, 1.04 at 6pt bold, about 1 elsewhere; each size class
  in the theme carries its factor in its `font-size`. Without them 6pt text ran
  10% short and a body line up to 3pt.
* **Geometry, on 128 mm paper**: headline 11.03pt, frame title band 27.89pt with
  its 14.4pt text at x 8.5 and baseline 20.22 below the band's top, footline
  8.64pt; text margin and width as AMSUniBo. Head and foot are `palette
  tertiary` (`#15263A`) and grey; the footline's number box is 23.61pt,
  13.66pt when unnumbered.
* **Balls**: PGF radial shadings in `bolognafcred`, highlight at 32% 32%; 5.1pt
  at the first level, 4.14 at the second, 8.99 for enumerate, 12.48 in a table of
  contents, each placed from the baseline as the PDF draws it.
* **Blocks**: the AMSUniBo box, overhang 4pt left and 2.73pt right; the title bar
  16.94pt, its 12pt baseline 11.96pt down; the body opens with a 2.5pt gradient.
* **`description`**: an item per `div.ditem` — the text at 2cm + labelsep, the label
  right-aligned before it, or from the left edge when longer; the other lines at
  the text's indent.
* **Bibliography**: label `bolognafcblue!60!gray`, title bold `bolognafcred!75!black`,
  location `bolognafcblue!75!gray`, note grey; hanging indent 9.62pt, entries
  5.88pt apart.

### AMSPurpleAndGold

* **AMSBolognaFC's profile in another palette.** The two themes are the same file
  but for colours, so the faces, widths, geometry, balls' placement and block
  metrics are AMSBolognaFC's, and `theme-AMSPurpleAndGold.css` is its CSS with the
  `:root` palette of `beamercolorthemepurpleandgold.sty`, named after
  it.
* **Head and foot come from the colour theme**, not from beamer's palette: the
  section on `pggold` with `pgpurpledeep` text, the empty half `pgpurpletint2`;
  the footline author on `pgpurple` (`pggoldpale` text), title on
  `pgpurpletint2`, date on `pgpurpletint` (`pggreymid` text). The frame title
  band is `pgpurpletint`, its text `pgblack`, and the title page box the same
  tint.
* **Balls** in `pggolddark`: the gradient stops are AMSBolognaFC's, each the same
  mix with white or black, taken from `bolognafcred` to `pggolddark`.
* **Blocks** `pgpurple` / `pgpurpledeep` / `pgpurpleborder` over `pgpurpletint`,
  `pggoldfill`, `pgpurplefill`; `\ccite` is `pggreyline`, the bibliography title
  bold `pggolddark`, its note and the APICe marker `pgpurple`.

### AMSSilverBlue

* **AMSBolognaFC's profile again, in the old Cesena blue and silver.** The theme
  is AMSPurpleAndGold's file with the palette of `beamercolorthemesilverblue.sty`;
  `theme-AMSSilverBlue.css` is AMSPurpleAndGold's CSS with that palette, the balls
  in `sbblue` from the same mixes.
* **Head and foot**: the section on `sbblue` in white, the subsection on
  `sbsilvertint2`; the author on `sbbluedeep`, the title on `sbsilvertint2`, the
  date on `sbsilvertint`. Two citation colours, `\ccite` in `sbgreyline` on a light
  surface and `sbgreybg` on a dark title: the profile's `cites` lists both,
  and the tools that leave citations out of the alignment read it.
* **What experiment 6's deck brought** is in this style's CSS only, at its end:
  listings, beamer's columns, figures and captions, `multicols`, `\hint`,
  `\hhref`, the contents frame of a subsection, the bibliography in
  `\scriptsize`, and math beyond letters — scripts, fractions, `\stackrel`,
  `cases`, `array`. The other styles take it when a deck of theirs needs it.

### AMSRedGrey

* **AMSSilverBlue's profile in the old AMSCesena reds and greys.** The two
  themes differ in colour names only; `theme-AMSRedGrey.css` is
  AMSSilverBlue's CSS with the palette of `beamercolorthemeredgrey.sty`, and
  two roles of their own: items (bullets, labels, balls) are `rgreddark`, not
  the identity red, and a block body is `rgsilvertint`, not a red tint. The
  balls take AMSSilverBlue's mixes, each from `sbblue` to `rgreddark`.
* **What experiment 7's deck brought** is in this style's CSS, at its end:
  `verbatim`, tables, `shrink`, the contents with subsections, `\huge`, the
  deck's TikZ arrow, arrays of any column spec, `\big`/`\bigg`, `\widetilde`,
  `\mathscr`, math `\dots`, `\scriptspace`, `\\[<len>]`, TeX's italic
  corrections.

### AMSCesena

* **AMSRedGrey's profile in the blues of CesenaSMA2006.** The theme is
  AMSRedGrey's file with the palette of `beamercolorthemeorchidwhale.sty`;
  `theme-AMSCesena.css` is AMSRedGrey's CSS with that palette, named after it,
  and the balls take AMSSilverBlue's mixes from `sbblue` to `owblue`.
* **Roles of its own**: items are `owblue`; the frame title is `owblue` on
  white; head and foot are whale's black and blues with white text — section
  and author on `owblack`, subsection and title on `owbluedeep`, date on
  `owblue`; the title page is a blue box with white title and subtitle; all
  three block titles are dark (`owbluedeep`, `owreddeep`, `owgreendeep`), so
  the example title takes the dark surface's quiet colours too.
* **What experiment 8's decks brought** is in this style's CSS: `\ldots` with
  its kerns for every deck, `description[<widest>]`, a fourth list level of
  the deck's own, the bibliography at `\normalsize`, and a `tikzpicture` at
  its natural size.

## the tools

Everything comes from Homebrew: `brew install playwright-cli pymupdf fonttools
geckodriver`, with TeX Live, poppler and the Firefox cask. Firefox is driven
headless through `geckodriver`; WebKit is Playwright's, through the Node library
inside `playwright-cli`, whose browser build Playwright downloads once:

```sh
P=$(brew --prefix playwright-cli)/libexec/lib/node_modules/@playwright/cli
node $P/node_modules/playwright-core/cli.js install webkit
```

`tools/browser.py` puts the two behind one interface, for `shoot.sh` and the
measuring tools; Safari itself does not reliably accept automated sessions.

### html.sh, the whole run

From the deck's root:

```sh
../beamer-AMSUniBo/html/html.sh            # tex/ holds one deck
../beamer-AMSUniBo/html/html.sh l2-lp      # tex/ holds several: name one
```

It builds the PDF; for a generated page (a `deck.json` with a `title`) it writes
the page with `build.py` and runs `nudge.py` four times (`gaps` three, then
`both`), rebuilding after each; it refills the ASSETS block — fonts, the seal of
the class option, the TikZ pictures listed in `deck.json`'s `figures` in source
order, the deck's own `img/` pictures, PDF ones through `pdftocairo -svg` — and
ends with `stats.py` and `blocks.py` in WebKit and in Firefox, whose rows a
person reads against the checklist. The
deck's inputs are in `html/tex2html/`, or `html/tex2html/<deck>/` in a
repository of several decks; with none there, it writes a starting `deck.json`
and stops.

### one tool at a time

With `A` a scratch folder for the assets:

```sh
T=../beamer-AMSUniBo/html/tools
$T/subset-fonts.sh $A/fonts [style]        # AMSUniBo, or a Computer Modern style
$T/seal.sh cesena $A [style]                # or bologna; prints the CSS box
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
$T/shoot.sh webkit "html/<Title>.html" $A/zoom <pages> 4   # the 4x look
python3 $T/compare.py $A/ref $A/firefox <page> $A/sheet.png  # and webkit
```

### tex2html, the converter

`tools/tex2html/` writes the page instead of a hand: frames from the `.tex`,
references from the `.bbl`, line breaks and per-frame corrections from the PDF.
It knows the TeX subset of the decks it has met and reports any command it does
not; a new deck may need it grown.

`theme.css` and `script.js` there are the theme and the deck script every
generated page carries, the deck-size announcement included. What belongs to
one deck lives in that deck, in `html/tex2html/`: `deck.json` (paths, names,
short fields, alt texts, the deck's own name macros, `subtoc_title` and
`toc_centred` for decks with subsections, `toc_subsections` for contents that
list them, `texmacros` for the deck's own TeX macros, expanded in the source,
`shrink` for a frame TeX shrinks more than asked, `italic_corrections` for
TeX's corrections after math letters, `replace` for literal rewrites of the
source that `texmacros` cannot express — a macro with `\ifnum`, say —, `lists`
for the deck's own list environments, each an `itemize` with a class),
`titlepage.html`, `deck.css` and `nudges.json`, the per-frame corrections,
which `nudge.py` writes: a shift per frame, margins keyed by element, and a
`translate` per column. Listings are `listing.py`'s.

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
   engines: `pdftoppm -scale-to-x 4096 -scale-to-y 3072`, and
   `shoot.sh <engine> <page> <outdir> <pages> 4`.

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

* **Brought through the checklist, 2026-10-12**, by hand, measured with
  `stats.py` and `blocks.py` from a `deck.json` alone. Before: blocks off by up
  to 2.4pt and baselines by up to 3.1pt; experiment 1's ink-line overlays had
  read the same page as within 5px. After: every block within 0.5pt of the PDF,
  top and bottom, and every baseline within 0.4pt, in WebKit and Firefox.
* Depth was not the fault here: every block's last line reaches as deep as a
  `g`, and `depth.py` gives about 0 throughout. What moved the blocks was the
  title bar padding, text set about 0.5–1.3pt high under its bar, and the
  frames' glue.
* By hand the corrections are one CSS block, keyed by page
  (`.frame:nth-of-type(n)`), not attributes on the markup: a `translate` per
  top-level element of a body, which moves nothing around it, and a padding on
  the first element inside a block body where its text sits high. A body with
  an inline padding cannot take a second padding from a rule; `translate`
  sidesteps that. Iterate: shortening one element re-centres the frame by 0.4
  of the change.
* Found here: the enumerate's item spacing was 0.8pt short on a stretched page;
  the bibliography's lines are 9.467pt apart, not 9.5pt, its entries 2.88pt
  apart, not 3.5pt; a booktabs body's first row sits 1.36pt nearer the rule.
* The footline number had a gap, not a box: the date moved with the number's
  width, by up to 2.4pt, and an unnumbered page's date sat 8pt off. A 26.9pt
  box with 0.73pt of padding inside it, 19.04pt when unnumbered, puts the date
  within 0.01pt on both kinds of page.
* `stats.py`'s worst numbers on page 8 (+135pt) and `blocks.py`'s on page 12
  (+124pt) are the TikZ labels and the chart throwing the alignment off; the
  rows themselves are right.

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

### 3 — the tools on Homebrew, and `html.sh`, 2026-10-24

No new page: the tools moved off the pip venv, at Andrea's rule that everything
comes from Homebrew, and the run became one command. Checked on experiments 1
and 2, whose pages were rebuilt and measured again.

* `browser.py` drives Firefox through `geckodriver` with plain WebDriver calls,
  and WebKit through a small Node bridge to the Playwright library inside
  `playwright-cli`; `shoot.sh`, `measure.py` and `blocks.py` use it. Playwright's
  own Firefox is no longer needed: the Firefox cask is measured instead.
* The numbers are the logged ones. Experiment 1: baselines within 1pt on every
  page but 8, where the TikZ labels throw the alignment, and the block of page 12
  the same way. Experiment 2: baselines within 1.02pt in WebKit and 1.36pt in
  Firefox, left edges within 2.64pt, blocks within 1.05pt.
* Headless Firefox counts its chrome in the window: a 1024 × 768 window gave a
  683pt-high viewport. `browser.py` grows the window by what is missing.
* **The corrections are not idempotent.** Four more `nudge.py` passes on the
  settled page of experiment 2 added a margin and moved one block from −0.39pt to
  −1.02pt. `html.sh` corrects a page only the first time, when there is no
  `nudges.json`, or when asked with `--nudge`.
* Rebuilt with the corrections it has, experiment 2's page came out byte for byte
  the same, but for the seal, whose PNG is now encoded differently: all 120 pages
  pixel-identical to before in both engines. Experiment 1's assets, refreshed,
  gained Merriweather Italic and the three script letters of experiment 2; its 20
  pages too are pixel-identical. Neither page was replaced.
* The converter against `iag2627-slides`: of 19 decks one reads through
  (`m3-ai`, which still lacks `\prolog`); the others stop at the first
  environment it does not know — `description`, `enumerate`, `verbatim`, `quote`,
  `tabular` — and two have no `.bbl`, which `build.py` still requires.

### 4 — Self-Explaining Agents @ CompuLaw Final 2025, AMSBolognaFC, 2026-10-24

`selfexplaining-compulaw2025-slides`: 34 pages on AMSBolognaFC 1.9, the first deck
not on AMSUniBo — five contents frames, a `description` in two frames, an
`enumerate`, two side-by-side `minipage`s with a PNG, a `\vfill` page, a
five-page bibliography and a frame after it. Every baseline ended within 0.6pt of
the PDF in WebKit and in Firefox, the one block within 0.6pt, left edges within
2pt but on one math line (3.7pt).

* The style became a profile in `deck.py`, so every tool reads its constants from
  there; `html.sh` takes the style from `deck.json`. AMSUniBo pages are unchanged:
  experiment 2's page, rebuilt, is byte for byte the same, and experiment 1
  measures as logged.
* The converter learnt `description`, `enumerate`, `minipage`, `\LARGE`, `\it`,
  `\textsf`, `\rightarrow` and `\phi`, images named with their extension, pages
  without a number after `\setbeamertemplate{page number in head/foot}{}`, a
  `\footnotesize` declared inside `\item` (the item's baselineskip is that
  size's), and a bibliography with frames after it — `build.py` assumed it was
  last, and numbered every following page from the wrong place.
* **TeX skips the spaces after a control word**: `\ldots for` has no space after
  the dots, only `\ldots`' own kern. The converter now drops them after the
  commands it maps to text.
* **A `\vfill` inside `center`** gets the same fil as the frame's top skip: the
  free space goes 1 : 1 : 1.5. The theme lets the `center` dissolve into the body
  (`display: contents`) and gives `.vfill` the top fill's flex.
* The block bar's baseline was first set by reading `blocks.py`'s offsets the
  wrong way round. Measuring the bar in the browser — top, baseline — is direct
  and settled it in one step.

### 5 — Not just for humans @ AI\*IA 2020 DP, AMSPurpleAndGold, 2026-10-25

`explanation-aixia2020dp-slides`: 23 pages on AMSPurpleAndGold 1.1, a 2020 deck
recovered and moved to the current style — a two-line title, three contents
frames, two `description`s, one block, one TikZ picture drawn by a deck macro
inside `\resizebox`, two `<presentation:0>` frames, a four-page bibliography.
Every baseline ended within 0.57pt of the PDF in WebKit and in Firefox, the block
within 1pt, left edges within 2.5pt.

* The style became a profile beside AMSBolognaFC's, with its own theme CSS; the
  fonts and assets tools take both Computer Modern styles alike.
* **`html.sh` now refills the assets before the corrections.** Measured with the
  TikZ picture still missing, its `<img>` had no height, and `nudge.py` made up
  for it with 100pt of margin above the next item, pushing it off the page once
  the picture arrived. A generated page with a picture had not been nudged before.
* **A `\ccite` that TeX moves to a line of its own at the end of an item** got no
  break: the cites are left out of the character alignment, so `align.py` saw the
  break only when text followed the cite in the same paragraph. It now compares
  each cite's first character in the PDF with the text before it.
* The converter learnt frames with an overlay specification — `<presentation:0>`,
  `<beamer:0>`, `<0>` leave them out, as the PDF does — and
  `\resizebox{<f>\textwidth}{!}{\<macro>}` for a TikZ picture drawn by a deck
  macro: `deck.json`'s `tikzmacros` names the asset of each such macro, and the
  `<img>` takes the width.
* **The corrections are keyed by element index**, so a change that adds a `<br>`
  shifts them onto the wrong elements: after it, `--nudge` from scratch.
* The contents frames kept 2.6pt that `nudge.py` does not take off (three sections,
  centred); a `translate` on `ol.toc` in the deck's `deck.css` does. The title page,
  with its two-line title, has its own box and margins there, measured — the same
  values experiment 4 had found for its margins.

### 6 — Blockchain & Smart Contracts @ WOA 2018, AMSSilverBlue, 2026-10-25

`blockchain-woa2018minischool-slides`: 93 pages on AMSSilverBlue 1.2, a 2018 deck
recovered and moved to the current style, the first to have subsections, and the
largest since experiment 2 — eight listings in Java and Solidity, seven PDF
pictures, beamer's `columns` on five pages, `multicols`, a dozen math constructs,
21 `allowframebreaks` frames, all but three broken by TeX alone, a thirteen-page
bibliography in `\scriptsize`. Every baseline ended within 1.5pt of the PDF in
WebKit and in Firefox but on two pages: the display title of page 9, 2.2pt high,
and the `∑` of page 43, whose glyph the PDF places from its top. Left edges are
within 5.3pt, the worst in math, but after a bold italic title in the
bibliography (7.4pt in WebKit); blocks within 1.6pt but page 9's top (2.2pt) and
page 43's bottom (1.9pt).

* **An `allowframebreaks` frame breaks where TeX breaks it**, not only at
  `\framebreak`: the converter counts the frame's pages by their titles in the
  PDF (`X I`, `X II` …) and gives each top-level element the page its text is on;
  a picture without text takes a page no text took. Every page title matched the
  PDF at the first try once the window of text was long enough to tell two
  blocks with the same title apart.
* **Subsections**: `data-subsection` and the headline's right half, and with
  `\AtBeginSubsection` the contents frame of a subsection — every section
  shaded, the current one's subsections listed, the current one shown. A
  margin under the subsections collapsed into the next section's: a padding.
* **Contents frames are `[c]`**, and were corrected as `[t]`: experiment 5 made
  up for it in its `deck.css`. `deck.json`'s `"toc_centred": true` corrects them
  as centred frames; pages made before keep the old way unless they set it.
* **Listings** (`listing.py`): `columns=fixed` sets each token, a run of letters
  and digits or one of other characters, in a box of n × 0.6 of the typewriter
  quad, its characters spread evenly inside; the quad is two characters, so the
  spread is `0.10625em × n / (n + 1)`. A span per token with that letter-spacing
  puts every character within 0.4pt of the PDF. `frame=trBL` draws the doubled
  rules outside, and TeX counts the outer bottom one in the space the listing
  takes.
* **Beamer's columns span the paper, not the text**: an `\hfill` before the
  first column and after each, over the paper width with both margins, so the
  outer gaps are not the text margins. An `\hfill` between columns in the source
  adds one more. A `[t]` set of columns aligns first baselines.
* **Math**: scripts in the script size, 8pt of 10.95; a superscript 0.413em up;
  both scripts 5.03pt up and 3.23pt down; a text fraction's numerator 5.37pt up
  and denominator 3.76pt down; consecutive relations as one, so `::=` has no
  inner space; `,` with a thin space after it; `cases` as an inline-block whose
  last row is its baseline, its rows 1.2 baselineskips apart and their middle
  0.52pt below the line's — the line then grows above and below as TeX's does.
  The PDF writes `\Delta` as `∆`, U+2206: the alignment maps it to `Δ`.
* **`\hfill` has two more meanings**: alone in a paragraph it is an empty line;
  between two pieces of a line it spreads them from margin to margin. Inside a
  group it is left as before.
* **A correction on an element with a `style` added a second `style`
  attribute**, which browsers ignore: `build.py` now writes into the one there
  is. Seen on columns, `multicols` and numbered lists.
* **Corrections and columns**: a step between two columns is no gap, and a
  margin inside `multicols` rebalances them, so `nudge.py` skips both; a column
  moves as a whole by a `translate` in `nudges.json`'s `cols`, which moves
  nothing around it.
* **A citation alone on the last line of a block** reaches no deeper than the
  baseline: `depth.py` measured it as a line of 6pt text and padded the block
  2.7pt too much. Blocks side by side are now paired left first.
* **The footline**: `~~` were written as no-break spaces, which Latin Modern
  draws 1.5 spaces wide in Firefox and WebKit draws as spaces; they are spaces
  now, kept by `white-space: pre`. This deck's number box is 35.2pt, measured,
  not the 23.61pt of experiments 4 and 5.
* **`\symETH`** is `$\mathsf{\Xi}$`, which with T1 fonts takes slot 4 of the
  sans, a dieresis: the PDF shows `¨`, and so does the page.
* Pages of the experiments before, rebuilt with these tools: experiments 2 and 4
  change only in the shared script; experiment 5 also gains a break before a
  citation of two keys, which its PDF has and its page had missed, and its
  corrections, keyed by element, would then need `--nudge`. None was replaced.

### 7 — Labelled Variables @ CILC 2016, AMSRedGrey, 2026-10-26

`labelledvariables-cilc2016-slides`: 31 pages on AMSRedGrey 1.2, a 2016 deck
by four authors recovered with the skill `/recover-deck` — the first deck on
this style. Nine `verbatim`s of Prolog and one fancyvrb `Verbatim`, a 5 × 23
`tabular` in a frame shrunk by 40%, three frames shrunk by 20%, a contents
frame listing subsections, an `array` with `\bigg` braces, `\mathscr`, a TikZ
arrow, two pictures. Measured at the end, both engines: baselines within 1.6pt
but page 18 (the origins of `\bigg{` and `⋀`, not errors) and page 19 (a
prime, 2.6pt, and a 1.5pt drift in a shrunk block); left edges within 3.6pt
but page 18's array (5.9pt) and page 28's bold-italic book title in WebKit
(6.8pt, as experiment 6's); blocks within 1pt but page 18's two (1.9pt);
footline exact.

* **`verbatim` and `Verbatim`**: their bodies are taken out of the source
  before anything parses it (comments included) and come back as a `<pre>` in
  the size declared just before them — and only them: beamer's lists set their
  own. cmtt's OT1 slots draw `` ` `` and `'` as ‘ and ’. With `commandchars`,
  `\(..\)` is math. A line's own newline takes the PDF's break, also after
  trailing spaces; `pre` is a block to the alignment, or the newline between two
  of them became a `<br>` that WebKit and Firefox lay out differently.
* **A paragraph ends where the next `verbatim` begins**: a `\scriptsize` before
  that `verbatim` is already in force, so TeX sets the paragraph at
  scriptsize's baselineskip, which `\lineskip` raises to 11.08pt for 10.95pt
  text. One `deck.css` line.
* **Tables**: `table` centred, `tabular` as a `<table>` with its column spec,
  vertical rules and `\hline` above or below a row; `split_top` serves
  commands, so `&` and `\\` have a splitter of their own. A cell is a flow of
  its own to the alignment.
* **`shrink=<n>`**: beamer sets the content at `\textwidth / f` and scales it
  by `f = 1 - n/100`. CSS `zoom` on each child of the body does exactly that.
  TeX may shrink more than asked; its log says so, and `deck.json`'s `shrink`
  gives that page's real percentage. A block's depth measured on the PDF is
  already scaled, so it goes in divided by `f`.
* **Contents with subsections** (`toc_subsections`): beamer's
  `\tableofcontents` puts `\vspace*{-.5em}` first, a `\vfill` before each
  section and one after the last; the list's items become the body's flex
  items, so those fills share the free space with the frame's own. Subsections
  at 5ex, their ball 1ex before the text. A frame without a title starts under
  the headline.
* **Arrays**: any column spec as a grid of its columns, each cell aligned as
  the spec says and on its row's baseline; a `\bigg` delimiter is a glyph 2.4
  times the size across the axis, so it adds above and below its row what
  TeX's does; a subsup's scripts add about 1pt. Corrections never go inside an
  array. Experiment 6's `{rcl}` form is kept as it was.
* **Widths TeX has and Unicode does not**: `\mathscr` takes rsfs10's advance
  plus its italic correction (a math font, space 0); a math letter in the sans
  italic takes cmssi10's italic correction unless a letter of the same font or
  a subscript follows (`italic_corrections`); math `\dots` are three `\ldotp`
  with a thin space after each; `\scriptspace` is 0.5pt; a binary operator
  alone is an ordinary symbol.
* **The font subsets**: Θ and Λ in the text faces; in LM Math the arrows and
  operators of this deck, the script capitals and italic Greek. A character
  missing from both falls back to a system font, different in each engine:
  that, not the layout, was a 3pt difference between WebKit and Firefox.
* **`depth.py` took a subscript's baseline for the last line's**: the line is
  now its largest characters' baseline, and its depth the lowest any of its
  characters reaches, scripts included.
* **`\\` followed by a `}`** was read as an escaped brace by `read_group`,
  and `\\[<len>]` printed its length: both fixed; a negative length pulls the
  next line up. `\center{...}`, `\huge`, `$$ $$`, `equation*`, `\mbox`,
  `\textasciicircum`, a size before `\frametitle`, frame options with spaces
  after their commas — all were new.
* **Not everything is automatic**: `nudges.json` was set by hand for pages 11,
  18, 19, 27 and 30, now 28 (shifts, and a margin the corrections kept
  misplacing on a page with two lines starting with "where"); `deck.css` holds
  the title page,
  the footline's number box (31.55pt), and pages 6, 11 and 27.
* **The footline**: with no short institute, infolines prints the author alone
  (`\ifblank`), not "Author ()"; `script.js` now does the same.
* Pages of the experiments before, rebuilt with these tools: experiments 2 and 4
  change only in the shared script; experiment 5 as after experiment 6;
  experiment 6 loses a `<br>` that the alignment had put inside the superscript
  of page 43's `∑` — right now, but that page's hand-set corrections were made
  around it and would need checking. None was replaced.
* **The closing as the style's template has it**, at Andrea's word on the day:
  numbering ends on the repeated title page, the references come after it,
  `noframenumbering`. Moving frames moves page numbers: `nudges.json` is keyed
  by page, so re-key it (here old 28–31 → 30, 31, 28, 29), set `totalframes`,
  and re-nudge alone the pages whose frame options changed (`[t,c]` → `[t]`).
  The same for experiment 6, re-keyed only: its page 43, rebuilt with these
  tools, measures as before.

### 8 — SMA-LS 2006/2007, AMSCesena, 2026-10-29

`smals0607-slides`: the sixteen decks of a 2006 course recovered on AMSCesena
1.1 — ten course decks and six seminars, 2,460 pages in all, the first
repository of many decks through the tools and the first decks with overlays.
Every page is checked as before, deck by deck; the decks' own numbers are in
the repository's `CLAUDE.md`. Fourteen decks have pages, 1,966 pages in all,
within 1–5pt in both engines on almost every page; the exceptions are logged
there. C7 (`eqnarray*` grammars) and S6 (inference rules in arrays) needed the
tools' mathematics grown: experiment 9.

* **AMSCesena is AMSRedGrey's profile in the blues of CesenaSMA2006**: the
  same theme file with the palette of `beamercolorthemeorchidwhale.sty`, and a
  few roles of its own (see the style's section above). The contents balls
  take the same mixes as the item balls, to `owblue`.
* **Overlays**: a frame becomes one page per slide. `<+->`, numbers, ranges
  and lists of them on `\item`, blocks, `quote`, `definition`, `\uncover`,
  `\only`, `\alert`, `\textcolor`, `\pgfuseimage` and `\footnote`; `+` counts
  in document order, nested overlays included. A part off its slide is
  *covered*: invisible, its space kept, as beamer's default `invisible`; the
  measuring tools leave it out. Every slide shows its frame's number
  (`data-frameno`, read by `script.js`).
* **A slide is drawn as its frame's full slide**, when one slide shows
  everything: the covered parts have no lines in their own page of the PDF,
  so their line breaks, the corrections and the blocks' depths come from the
  full slide's page, and each slide keeps only its own classes. Off-slide
  `\alert` and on-slide `\uncover` are spans too, so the slides' elements
  line up. A frame whose slides show different parts (`<1>` and `<2>`) keeps
  per-slide corrections; there the covered parts lack breaks, and a few pages
  are set by hand.
* **The course layers' furniture**: `\section[short]{long}` (the headline
  takes the short title), `\frame[label=…]{\titlepage}`, frames written
  `\frame[<opts>]{…}`, contents at each section only where the deck asks,
  subsection contents listing every section's subsections (`subtoc_all`),
  `description[<widest>]` as a grid of subgrid rows, the deck's own list
  levels (`lists`), `\setlength{\itemsep}` opening a list, a body opened by a
  size or wrapped in one group, `quotation`, `quote`, `centering`,
  `semiverbatim`, fancyvrb's `\fvset` and options, `\verb`, `\url` at the
  text's size, `\textrm`, `\textcolor`, `\color`, `\pgfuseimage`,
  `\column{w}`, a two-line frame title, a bibliography at `\normalsize`, a
  deck with no bibliography, `deck.json`'s `replace`.
* **Pictures**: a `tikzpicture` in the body is an asset at its natural size
  (`assets.py` reads the SVG's width); `externalize.sh` finds pictures by
  paths from the deck's root; a bitmap at `scale=` is sized at 72 dpi, as
  pdfTeX ignores a PNG's own resolution — which shows that experiment 7's
  page sizes its two pictures by their pixels, not as its PDF does (not
  rebuilt).
* **A frame title TeX wraps on its own** gets a `<br>` before the second
  line's first word, read on the PDF, and the two-line title's layout.
* **Footnotes**: a letter mark in the item colour, the text at the frame's
  foot in `\footnotesize`; beamer may set it higher, under the content.
* **More of the seminars and C3a/C3b**: inline `lstlisting` in Courier (TeX
  Gyre Cursor) with the deck's colour and bold delimiters; saved boxes
  (`lrbox`) drawn where `\usebox` uses them, inline `\fcolorbox`,
  `\makebox`, `\raisebox`, `\hspace`; `\tikz …;` and `\resizebox`d pictures
  as assets; S2's section frames and API tables; beamer's `thebibliography`
  inside frames, with article icons; `\textcolor[rgb]`; frames TeX shrinks
  further than their `shrink=<n>`, the factor read on the PDF into
  `deck.json`'s `shrink`.
* **Runs of ties** (`~~~`) are kept spaces: Latin Modern's no-break space is
  wider in Firefox than in WebKit, 7pt over three.

### 9 — SMA-LS C7 and S6: alignments and more mathematics, 2026-10-29

The last two SMA-LS decks: C7, 468 pages with sixteen `eqnarray*` grammars
and two tables in arrays, and S6, 26 pages with a grammar in `array`s and
inference rules. What the converter learnt is general, in `latex.py`,
`frames.py`, `build.py` and the AMSCesena and AMSRedGrey themes (the two
with mathematics); the decks' own macros are in their `deck.json`
(`texmacros`). Every value is TeX's, read in `latex.ltx`, `beamerbaseframe.sty`
or the PDF.

* **Alignments, one reader for all**: rows split at the top level only (not
  in a group, a nested environment or a `\verb`), with their `\\[<len>]`,
  `\hline`, `\hline\hline` and `\noalign{\vskip}`; cells split the same way.
  `array` takes its column spec as TeX's preamble does: `l c r p{}`, `|`,
  `@{...}` (spaces only), `*{n}{...}`, each cell padded with `\arraycolsep`
  (5pt) or its `@{}`, no grid gap; `\multicolumn{k}{spec}{...}` spans its
  columns. `\hline` is a 0.4pt rule across, two of them `\doublerulesep` (2pt)
  apart; a nested array is centred on its row (`infrule`).
* **`eqnarray` and `eqnarray*`**: three columns right, centre, left, with
  2`\arraycolsep` before the second and the third, `\jot` (3pt) after every
  `\\` plus its `[<len>]` (`latex.ltx`). Rows are their strut apart, as TeX's
  `\baselineskip`: what is inside a row takes no line height, so a delimiter
  or `\verb` in another font does not push it down. No numbers are drawn.
* **`\left` … `\right`** is an inner atom: its delimiters, `.` for none, and a
  thin space on either side but at the formula's edges. **`\xrightarrow`**
  (amsmath) is an arrow as long as its label with 5mu and 9mu around it,
  the label's baseline 0.62em over the line's (measured), its height the
  row's; a script after a relation stays inside its spacing.
* **More of TeX's maths**: `\verb` and `\textrm`/`\textit`/`\texttt` in
  maths, `\textit{...\/}` with its italic correction, `~` as the text
  font's space, `\kern`, `\quad` and `\qquad` as measured spaces, `\not`,
  every `\mathbb` capital, lowercase and capital Greek, `\bot`, `\land`,
  `\rhd`, `\downarrow`, `\mathtt` holding `\mathit{t}`, `\mathit` setting
  only letters, as words, a script's `\mathbb{C}` taking its argument, `::=`
  opening a cell. In scripts TeX spaces neither relations nor binary
  operators, and now neither does the page.
* **A macro body holding `&` or `\\` is not grouped** by `texmacros`: TeX
  never groups a body, and the group would hide the marks from the
  alignment (`\infrulelab`).
* **TeX shrinking more than asked**: beamer widens `\hsize` by the factor
  asked and scales by the one TeX took (`beamerbaseframe.sty`), so the body
  is narrowed by their ratio (`--shrinkr`). This fixes the centring off on
  C3b's shrunk tables (28pt before, 13.6pt now) and C7's grammar (17.6pt
  before, 1.8pt now).
* **A frame title's second line** is read only in the title's size: a first
  body line can sit in the same band (C7).

Results are in `smals0607-slides`' `CLAUDE.md`. Of the other fourteen SMA-LS
pages only C3b's changes (rebuilt); CILC 2016's page, rebuilt and re-tuned with
these tools, measures as before but for page 18, 14.9pt instead of 12.9pt,
a difference that comes from the re-tuning and is not the new rules: its
committed page is left as it was.

### 10 — SMA-LS C3a: references as `\bibentry`, 2026-10-29

C3a's eight *For Further Reading* frames no longer hold hand-typed
`thebibliography` entries. Each item is now `\readingitem{key}`: an `\item`
labelled with beamer's article or book icon, followed by `\bibentry` of an
APICe record (`bibentry`, `\nobibliography*`). The closing references are the
house frame. What the tools learnt:

* **`\bibentry` as a bibliography item.** An `itemize` whose items are all
  `[\usebeamertemplate*{bibliography item}]\bibentry{key}` becomes one element
  per entry, so `allowframebreaks` can distribute them. The entry's spans come
  from `bib.py` (as the references), and the icon follows the last
  `\beamertemplate{article,book}bibitems`. `\nobibliography*` prints nothing.
* **Beamer's `\newblock` outside `thebibliography`** (`beamerbaselocalstructure`)
  sets each block in the colours of the block before it: the title black, the
  location in the title colour, the note in the location colour. Its first
  `\newblock` adds an empty box 1.5em high. The title therefore runs on after
  the author, behind that box (`.nbstrut`, plus TeX's 1pt `\lineskip`), and
  TeX either keeps it on the author's line or starts a taller line with it.
  `align.py` treats a title marked `data-runon` as part of the author's flow,
  so the page breaks the line where the PDF does. Between entries there is
  only beamer's 3pt `\itemsep`, and the links are a line like any other.
* **An entry TeX breaks across pages** is cut between its blocks at the PDF's
  page break (`split_entries`); the rest continues on the next page without an
  icon.
* **The icons** hang from the author span, so they follow its baseline wherever
  the 1.5em box puts it. The book icon (`\beamertemplatebookbibitems`), new
  here, is an inline SVG drawn after the PDF's.
* **`\section<presentation>*`**, the appendix's, is now read as a section: the
  headline shows *Appendix · For Further Reading*. Before, it went on showing
  the last section (*ADELFE*), in the page of experiment 8 too.
  `\appendixname` is *Appendix*.
* **A macro body holding `\item`** is not grouped by `texmacros`, for the same
  reason as `&`: the group would hide it from the list.
* **A `[c]` references frame** has its nudged shift applied as centred
  (`bib_pages` passed `centred=False`, so the shift landed 0.6 short). This
  holds for AGoT's references too, the next time that page is rebuilt.
