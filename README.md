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

This style is [beamer-AMSBolognaFC](https://github.com/andreaomicini/beamer-AMSBolognaFC)
with a different palette. The structure, the commands, the `apice` option, the
workarounds, the release scheme and the template repository beside it are all the
same, background image included; what changes is the colour of every element.

The background is the same file, and deliberately so. It is not a Campus
photograph but the **Alma Mater seal**, which belongs to this identity at least
as squarely as it does to the AMSBolognaFC one, and it is perfectly neutral:
across its 4.36M pixels there is not a single tinted one — white, `#F1F1F1` and
`#E5E5E5` only. `#F1F1F1` is within one unit of this palette's own neutral fill,
`amsgreybg` `#F0F1F1`. So it carries no colour cast into the institutional
palette.

The style stays on **pdfLaTeX**. The web theme pairs Merriweather Sans with
Merriweather serif, which would need LuaLaTeX or XeLaTeX and would restyle a deck
far beyond its colours, so the typography is deliberately left as it is.

## structure

| file | what it is |
|---|---|
| `beamerthemeAMSUniBo.sty` | the theme: the `apice` option, the beamer templates and colour assignments, the commands below, and the workarounds a deck would otherwise have to carry itself |
| `beamercolorthemeamsunibo.sty` | the palette alone — the `@ams-*` variables of the web theme, with the source of each — loaded by the theme |
| `almacesena-background.pdf` | the background image: the Alma Mater seal, as a faint watermark in the lower-right corner |
| `apalike-AMS.bst` | the bibliography style, a renamed derivative of `apalike.bst` (see the licence note below) |

Every release attaches a `style.zip` holding all four plus the `LICENSE`, so
the archive is enough to typeset with on its own.

Beyond the beamer furniture, the theme defines:

| command | for |
|---|---|
| `\speaker` `\sspeaker` | marking the actual speaker among the authors, in the long and short forms. Safe in `\author`: the name still reaches the PDF `/Author` field, only the colouring is dropped |
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
* `\aalert` and `\sspeaker` are light, for dark surfaces.

### the workarounds the theme carries

Both are handled in the theme so that no document has to deal with them.

**Commands that cannot survive hyperref's PDF-string expansion.** Without this,
every deck would have to wrap them in `\texorpdfstring` by hand.

* `\speaker`, `\sspeaker` colour the speaker's name on the title page.
  `\@firstofone` keeps the name and drops only the colouring, so the author still
  reaches the PDF `/Author` field.
* `\translate` is beamer's translator hook. `\refname` is `\translate{References}`,
  so `\section*{\refname}` warns *Token not allowed in a PDF string*.
* `\\` — a line break inside `\title` or `\author` is meaningless in a PDF string.
  hyperref would drop it and run the two sides together, turning
  `Nobody Else\\someone@unibo.it` into `Nobody Elsesomeone@unibo.it`; mapping it
  to a space keeps the metadata readable.

**Small caps under the sans font.** Computer Modern Sans has no small-caps shape,
so every `\textsc` under the default font — `\textsc{Alma Mater Studiorum}` on a
title page, say — falls back to the *serif* small caps and warns
`Font shape `T1/cmss/m/sc' in size <n> not available`. Declaring the substitution
makes it official and silent at every size. `ssub*` is a silent substitution and
the typeset result is the one LaTeX was already producing, so nothing moves on
the slides. To get genuine sans small caps instead, load a font family that has
them (Lato, Fira Sans, Linux Biolinum …) — but that restyles the whole deck, and
the web theme's own answer, Merriweather Sans, would need LuaLaTeX or XeLaTeX.

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
| `amsgreyline` | `#C7C9CB` | `@ams-grey-line`, `table-border-color` | `\ccite`, `\uuurl`, `\dddoi`, `\aalert`, `\sspeaker` — the light-on-dark commands |
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
commands — `\ccite` is 3.82:1 on a block header and `\aalert` and `\sspeaker`
likewise, while `\cccite` reaches 5.61:1. Citations in running text are fainter
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
