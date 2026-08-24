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

In each pair, the plain command is for light surfaces — the white slide, the pale
green fills — and the doubled one for the dark surfaces, which here are the
green-dark block headers, the red alerted headers and the red head line.

The theme also declares a small-caps substitution for the sans font and
neutralises `\speaker`, `\sspeaker`, `\translate` and `\\` inside hyperref's
PDF strings, so decks build without the font-shape and PDF-string warnings that
otherwise appear.

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
| `amsgreymid` | `#535353` | `@ams-grey-mid`, `breadcrumb-color` | secondary text, footnotes, citations |
| `amsgreyline` | `#C7C9CB` | `@ams-grey-line`, `table-border-color` | the light half of each command pair |
| `amsgreybg` | `#F0F1F1` | `@ams-grey-bg` | reserved |

`amsredfill`, `amsredborder`, `amsgreenfill` and `amsgreenborder` are the block
fills, computed exactly as the web theme's LESS computes its `@state-danger-*`
and `@state-success-*` values. `block` and `alertblock` take a solid header, as
the wiki's panels and primary buttons do; `exampleblock` takes the lighter
pairing the wiki uses for its own success alerts, `amsgreenborder` over
`amsgreenfill`.

Two contrast facts inherited from the web theme, and observed here: **white on
`#56A49A` is 2.93:1 and fails WCAG AA**, so every full-green surface carries dark
text instead; white on `#BB2E29` is 5.94:1 and passes. Every text-on-fill pair in
this style is at AA or better, except the deliberately quiet `\cccite`,
`\uuurl`, `\dddoi`, `\aalert` and `\sspeaker`, which sit at AA-large on their dark
surfaces by design.

The provenance of each value, and the drift between the identity manual's stated
red and the one the institutional documents actually use, is documented at the
top of `beamercolorthemeamsunibo.sty`.

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
