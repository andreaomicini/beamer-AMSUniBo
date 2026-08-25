# beamer-AMSUniBo

> A simple Beamer-LaTeX style for presentations by Alma Mater Studiorum — Università di Bologna,
> in the colours of the [AMSUniBo](https://apice.unibo.it/xwiki/bin/view/FlamingoThemes/AMSUniBo)
> theme for the APICe wiki

## author

* Andrea Omicini

## usage

```latex
\documentclass[presentation]{beamer}\mode<presentation>{\usetheme{AMSUniBo}}
```

Pass the `apice` option to the document class to enable the APICe BibTeX field:

```latex
\documentclass[presentation,apice]{beamer}\mode<presentation>{\usetheme{AMSUniBo}}
```

A ready-to-use presentation skeleton is available in
[beamer-AMSUniBo-template](https://github.com/andreaomicini/beamer-AMSUniBo-template).

## relation to beamer-AMSBolognaFC

This style began as [beamer-AMSBolognaFC](https://github.com/andreaomicini/beamer-AMSBolognaFC)
with a different palette. The structure, the commands, the `apice` option, the
workarounds, the release scheme and the template repository beside it are all the
same, background image included; what changes is the colour of every element —
and, since 1.2, the faces they are set in.

The background is the same file, and deliberately so. It is not a Campus
photograph but the **Alma Mater seal**, which belongs to this identity at least
as squarely as it does to the AMSBolognaFC one, and it is perfectly neutral:
across its 4.36M pixels there is not a single tinted one — white, `#F1F1F1` and
`#E5E5E5` only. `#F1F1F1` is within one unit of this palette's own neutral fill,
`amsgreybg` `#F0F1F1`. So it carries no colour cast into the institutional
palette.

The colours were the first step, not the whole of it: the style now carries the
web theme's typography as well, and still on **pdfLaTeX** — see
[typography](#typography).

## structure

| file | what it is |
|---|---|
| `beamerthemeAMSUniBo.sty` | the theme: the `apice` option, the beamer templates and colour assignments, the commands below, and the workarounds a deck would otherwise have to carry itself |
| `beamercolorthemeamsunibo.sty` | the palette alone — the `@ams-*` variables of the web theme, with the source of each — loaded by the theme |
| `almacesena-background.pdf` | the background image: the Alma Mater seal, as a faint watermark in the lower-right corner |
| `apalike-AMS.bst` | the bibliography style, a renamed derivative of `apalike.bst` (see the licence note below) |

Every release attaches a `style.zip` holding all four plus the `LICENSE`. The
archive is enough to typeset with, given a TeX installation carrying the four
font packages listed under [typography](#typography) — it does not bundle fonts.

Beyond the beamer furniture, the theme defines:

| command | for |
|---|---|
| `\speaker` `\sspeaker` | marking the actual speaker among the authors, in the long and short forms, both in bold. Safe in `\author`: the name still reaches the PDF `/Author` field, only the markup is dropped |
| `\ccite` `\cccite` | superscript citations, in two weights |
| `\uurl` `\uuurl` | URLs, in two sizes |
| `\ddoi` `\dddoi` | DOIs, linked, in two sizes |
| `\apicepar` | the APICe marker; defined either way, but expands to nothing unless the `apice` option is given |
| `\aalert` | a quieter alternative to `\alert` |

The pairs keep the weights AMSBolognaFC gives them, so that a deck moved from
that style to this one changes hue and nothing else:

* `\ccite` and `\cccite` are **both light**, because a citation marker's usual
  home is a block header, which is dark in both styles. `\cccite` is the lighter
  of the two, for the loudest surfaces. In running text both are faint on
  purpose — as they are under AMSBolognaFC.
* `\uurl`/`\uuurl` and `\ddoi`/`\dddoi` go dark-then-light: the plain one for
  light surfaces, the doubled one for dark.
* `\aalert` is light, for dark surfaces. `\sspeaker` used to be, and is not any
  more: see [typography](#typography).

### the workarounds the theme carries

Both are handled in the theme so that no document has to deal with them.

**Commands that cannot survive hyperref's PDF-string expansion.** Without this,
every deck would have to wrap them in `\texorpdfstring` by hand.

* `\speaker`, `\sspeaker` mark the speaker's name on the title page.
  `\@firstofone` keeps the name and drops only the markup, so the author still
  reaches the PDF `/Author` field.
* `\translate` is beamer's translator hook. `\refname` is `\translate{References}`,
  so `\section*{\refname}` warns *Token not allowed in a PDF string*.
* `\\` — a line break inside `\title` or `\author` is meaningless in a PDF string.
  hyperref would drop it and run the two sides together, turning
  `Nobody Else\\someone@unibo.it` into `Nobody Elsesomeone@unibo.it`; mapping it
  to a space keeps the metadata readable.

## typography

Since 1.2 the style sets the faces as well as the colours, and still on
**pdfLaTeX**: every face below is a Type 1 font with T1 metrics. No Unicode
engine is involved, and a deck needs to do nothing — the theme loads all of it.

This is the style's only hard dependency beyond a TeX installation. It needs
`merriweather`, `inconsolata` and `newtxsf`, from `collection-fontsextra`, and
`anyfontsize`, from `collection-latexextra`. Both collections are in
`scheme-full`, but neither is in a minimal install such as BasicTeX. On TeX Live,
`tlmgr install merriweather inconsolata newtxsf anyfontsize` is enough.

| role | face | how |
|---|---|---|
| body, and anything not listed below | Merriweather Sans | `merriweather`, `sfdefault` |
| title, subtitle, frame titles | Merriweather serif | `merriweather`, `rm`, plus three `\setbeamerfont` |
| `\texttt` and `verbatim` | Inconsolata | `inconsolata`, `varqu,varl` |
| mathematics | sans math | `newtxsf` |

**The pairing is the web theme's own** — Merriweather Sans for body text,
Merriweather serif for `h1`/`h2`. Earlier versions of this file claimed that
needed LuaLaTeX or XeLaTeX. That was simply wrong: the `merriweather` package
supports pdfLaTeX, and both families are complete — regular, bold, italic, bold
italic and small caps in each, with Light and Black besides — so a deck can reach
for any of them and get a real face rather than a silent substitution.

**Computer Modern is gone, deliberately**, because it was the weakest option in
both of the roles it was left holding. As a code face `cmtt` is at once the
*lightest* and the *widest* of the candidates, which is the wrong pair of
properties for frames full of long macro names: Inconsolata matches the body
weight, is 4% narrower, and `varqu` keeps its quotes straight — which matters
when every code sample is LaTeX. In mathematics, CM's delicate serif italic sits
badly beside a sturdy sans body, where `newtxsf` is a complete sans math font,
sums and integrals included. `anyfontsize` is loaded for one reason only: to
absorb the 5.5 pt and 6.5 pt size substitutions `newtxsf` and `wasysym` would
otherwise report.

**Size and weight both follow the web theme.** Merriweather's x-height runs large,
so at the same nominal size it reads bigger than Computer Modern Sans did;
`scaled=0.92` restores the old apparent size, and because the option touches only
the sans family the serif headings keep theirs. The body is then set at **weight
300**, as the web theme sets it.

Getting that weight takes three declarations rather than the obvious one, and the
order of discovery is worth recording. The package's `sflight` option alone does
nothing under Beamer, and neither does adding `\mddefault`: the package **resets
`\seriesdefault` to the serif family's series** near the end of its own code, so
that is the load-bearing one. All three together give a light body while leaving
the serif headings at Regular. Block titles are pulled back to medium
explicitly, so a block header still outweighs its own contents.

A light default has one consequence worth understanding: every font family now
gets asked for a `light` series, and a family that has none warns and falls back.
Two such families turn up here — `OT1/cmss`, the math sans `newtxsf` installs, and
`U/wasy`, if the deck loads `wasysym` — and the theme declares the substitution for
both. Each has to wait for its `.fd` file to load, hence the `\AtBeginDocument`.
**If a deck adds another symbol font that lacks a light series**, the same one-liner
handles it:

```latex
\AtBeginDocument{\DeclareFontShape{<enc>}{<family>}{light}{n}{<->ssub*<family>/m/n}{}}
```

**`\speaker` is bold, and that is a fix rather than a flourish.** The command
existed to single out the speaker among the authors, but it set `amsred` on a title
page whose author colour is *already* `amsred` — so from 1.0 to 1.1 it did nothing
visible at all. Weight is what distinguishes it now, which is only possible because
1.2 has a real bold. Note what it deliberately does **not** do: it leaves the author
colour alone, so decks that never call `\speaker` are untouched by it. Dimming the
co-authors instead would have recoloured every unmarked author in every deck.

`\sspeaker`, the short form that appears in the footline, had the same fault the
other way round. It was `amsgreyline` and italic, on a footline whose own text is
white — so it made the speaker *quieter* than the co-authors beside them, which is
the opposite of the command's purpose. It is now simply bold, with **no colour of
its own**: it inherits whatever surface it sits on, so it reads white-on-green in
the footline and dark on a light surface, and needs no light-and-dark pair.

**Small caps.** Computer Modern Sans has no small-caps shape, so under it every
`\textsc` — `\textsc{Alma Mater Studiorum}` on a title page, say — fell back to
the *serif* small caps and warned
`Font shape `T1/cmss/m/sc' in size <n> not available`. Merriweather Sans has a
real small-caps shape, so this no longer arises. The substitution is still
declared, as a safety net for a deck that overrides the family back to Computer
Modern Sans.

## the palette

Every value is the one used by the AMSUniBo theme on APICe, and each is used in
the role its web counterpart has there. Red is the identity colour — the navbar,
links, primary actions. Green is the structural colour — rules, separators,
headings, tabs.

| colour | value | web theme | where it goes on a slide |
|---|---|---|---|
| `amsred` | `#BB2E29` | `@ams-red`, `navbar-default-bg`, `link-color` | head line, author, bullets, alerted text, URLs, DOIs, alerted block headers |
| `amsreddark` | `#8E2320` | `@ams-red-dark`, `navbar-default-link-active-bg` | reserved for active states |
| `amsblack` | `#000000` | `@ams-black`, `headings-color` | title, frame titles |
| `amstext` | `#040404` | `@ams-text`, `text-color` | body text |
| `amsgreen` | `#56A49A` | `@ams-green`, `brand-success` | separation lines; the base the example-block fills are derived from |
| `amsgreenlight` | `#74BDAD` | `@ams-green-light`, `brand-info` | reserved |
| `amsgreendark` | `#366861` | `@ams-green-dark`, `state-success-text` | structure, block headers, emphasis, section in TOC |
| `amsgreentint` | `#DDEDEB` | `@ams-green-tint`, `breadcrumb-bg`, `.fieldrow1` | frame title band, block bodies, foot line |
| `amsgreentint2` | `#CCE4E1` | `@ams-green-tint2`, selected tabs | foot line, frame title right |
| `amsgrey` | `#464A51` | `@ams-grey` | institute |
| `amsgreymid` | `#535353` | `@ams-grey-mid`, `breadcrumb-color` | secondary text, footnotes, subtitle, date |
| `amsgreyline` | `#C7C9CB` | `@ams-grey-line`, `table-border-color` | `\ccite`, `\uuurl`, `\dddoi`, `\aalert` — the light-on-dark commands |
| `amsgreybg` | `#F0F1F1` | `@ams-grey-bg` | `\cccite`, the lightest of the pair |

`amsredfill`, `amsredborder`, `amsgreenfill` and `amsgreenborder` are the block
fills, computed exactly as the web theme's LESS computes its `@state-danger-*`
and `@state-success-*` values. `block` and `alertblock` take a solid header, as
the wiki's panels and primary buttons do; `exampleblock` takes the lighter
pairing the wiki uses for its own success alerts, `amsgreenborder` over
`amsgreenfill`.

Two contrast facts inherited from the web theme, and observed here: **white on
`#56A49A` is 2.93:1 and fails WCAG AA**, so every full-green surface carries dark
text instead; white on `#BB2E29` is 5.94:1 and passes. Every text-on-fill pair in
this style is at AA or better, except the deliberately quiet light-on-dark
commands — `\ccite` is 3.82:1 on a block header and `\aalert` likewise, while
`\cccite` reaches 5.61:1. `\sspeaker` was in that set until 1.2 and is no longer:
it now inherits its surface's colour, which *raises* its contrast to whatever the
surrounding text has. Citations in running text are fainter
still, which is how AMSBolognaFC renders them too.

### where the colours come from

* **Red and black** — *Sistema di identità di Ateneo*, "I colori istituzionali":
  rosso istituzionale, Pantone 1805, C0 M91 Y100 K23.
* **Grey `#464A51`** — the same manual, p. 16, "La versione in negativo".
* **Green** — *Brochure di Ateneo 2026*, the cover dots and the closing page.
* **Green light** — the official *PPT Unibo 2026* template.
* **Body text** — the same PPT templates.
* The rest are derived, as the table above records.

Note the drift in the sources: the brochure and the PowerPoint templates both
use `#BC2802` / `#BD2B0B`, which is the institutional red as naively converted
from its CMYK build. The manual's own stated HEX, `#BB2E29`, is the one meant
for screen, and is the one used here.

The manual's 16 disciplinary-area colours — for Ambiti, Dipartimenti and Scuole —
are deliberately **not** used: they identify structures, not the Ateneo.

## versioning

The style version is declared in `beamerthemeAMSUniBo.sty` as
`\stylemajor` / `\styleminor` / `\stylepatch`, giving `Major.Minor[.Patch]`.
`\stylepatch` is optional: comment it out to release as `Major.Minor`.

Releases are tagged `Major.Minor[.Patch]-<UTC time-stamp>`, with the time-stamp
appended automatically by the CI at release time. Two commits that both forget
to bump the version therefore still produce two distinct releases instead of
clashing on the same tag.

## licence

This work is distributed under the
[LaTeX Project Public License](LICENSE), version 1.3c or later, and has the
LPPL maintenance status `maintained`.

One file is **not** covered by that licence: `apalike-AMS.bst` is a modified,
renamed derivative of Oren Patashnik's `apalike.bst` (Copyright © 1988, 2010
Oren Patashnik) and remains subject to its own terms, which permit modification
and redistribution provided the resulting file is renamed — as it is here.

The colours are those of the Alma Mater Studiorum's institutional identity, taken
from *Sistema di identità di Ateneo* and the 2026 institutional documents. Their
use is governed by the Ateneo's own rules, not by the licence above.
