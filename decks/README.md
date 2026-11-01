# Decks: the shared recipes

How to write the frames of a talk or course deck with the generic mechanisms every deck shares —
the deck label, the PDF file name, `picturecolumns`, `\creditedpicture`, `\bulletlist`,
`indquotation` — and how to typeset a deck from TeXShop. Written once here, for every deck of every
style; each deck's README says only what is its own.

For talks the mechanisms are `talks.sty`, one file kept in `decks/` of **every** style repository
(`beamer-AMSUniBo`, `beamer-AMSBolognaFC`, `beamer-AMSCesena`, `beamer-AMSPurpleAndGold`,
`beamer-AMSRedGrey`, `beamer-AMSSilverBlue`), the six copies identical; a talk reaches it through
its own `.style` submodule, `sty/talks.sty -> ../.style/decks/talks.sty` (decided, Andrea,
2026-11-01). Courses have their own shared file beside it, `decks/courses.sty`: the same mechanisms (prefix
`\courses@`) plus two link helpers, `\smallurl` — the style's `\uurl` one relsize step down, in the
style's own colour — and `\expandurl`, with the repository hosts `\aorepoprimary` and
`\aoreposecondary`; anything about one course (a lab repository, say) goes in that course's
`sty/course.sty`. The names below hold for both.

## writing a new deck

```latex
\documentclass[presentation,cesena]{beamer}\mode<presentation>{\usetheme{AMSUniBo}}
\usepackage{talks}
\usepackage{talk}
\usepackage{names}                 % only when the deck has name macros
\usepackage{<repo>}

\title[\talktitleshort]{\talktitlelong}
\subtitle{\talksubtitle}
\author[Short]{... \speaker{Andrea Omicini}}
\institute[DISI, Univ.\ Bologna]{...}
\date[\eventshort]{\eventplace, \eventdate}
```

**A project's main files carry the project's name**: `tex/<repo>.tex`, `sty/<repo>.sty` and
`bib/<repo>.bib`. Everything derived in `aux/` follows the `.tex`, while `pdf/`'s copy is named after
the title by the `END` block of `.latexmkrc`. A repository with one deck has nothing to number and
sets no `\decklabel`; a course numbers its decks `<class letter><n>-<topic>`, each with a
`\decklabel` and `\thedecklabel{}` inside the short `\title[...]`, so that furniture, file name and
metadata keep one source. Every deck is standalone with its own `\documentclass`; there are no
shared body fragments.

**The seal**: `cesena` watermarks the slides with the Campus di Cesena seal, `bologna` with the
Ateneo one, and naming neither leaves the deck bare. **The `apice` option** switches on the theme's
`\apicepubpar`, the *APICe* link beside a bibliography entry that has an `apice` field; the `.bib`
keeps its `apice` fields either way, so the switch is purely what the audience sees. Both are one
word in the `\documentclass` line.

`\speaker` marks the actual speaker among the authors, and is safe in `\author`: the style keeps the
name in the PDF `/Author` field and drops only the colouring. It earns its place on a co-authored
deck.

`talks.sty` also loads `relsize`, so `\smaller` and `\larger` are available in any deck. They size
relative to whatever is in force at the point of use, rather than jumping onto the absolute
`\small`/`\footnotesize` ladder — which is what you want inside a `block`, a column or a `center`,
where the surrounding size is already not the body size.

## a picture beside a text

`talks.sty` defines `picturecolumns` for the common frame that puts a picture on one side
and an itemized text on the other:

```latex
\begin{frame}[c]{A Frame Title}
\begin{picturecolumns}{img/foo}
  \begin{itemize}
    \item ...
  \end{itemize}
\end{picturecolumns}
\end{frame}
```

| key | default | meaning |
| --- | --- | --- |
| `width` | `0.43` | the picture's share of `\textwidth` |
| `gap` | `0.02` | the gutter between the two columns |
| `height` | `0.80` | the row's share of `\textheight` |
| `side` | `left` | which side the picture goes on |

So `\begin{picturecolumns}[width=0.5,side=right]{img/foo}`. The text column takes whatever
the other two leave; give the image name without its extension, as `\includegraphics`
prefers.

**The point of it is that the picture's vertical position depends on neither the picture nor
the text.** The row is given a fixed height, which makes beamer typeset each column as a
`minipage[c][<height>]` — whose *inner* position defaults to the outer one, `c`, so the
content is centred inside a box of known height. The image is then constrained on both axes
(`width=\linewidth`, `height=<row height>`, `keepaspectratio`), so any aspect ratio fits and
is centred both ways.

Three things to know:

- Writing the picture column by hand instead — `\begin{center}` inside a `column` — is what
  pushes a picture visibly low. The `center` environment adds its own vertical glue inside
  the minipage, and beamer's own `\leavevmode` at the start of a column opens a paragraph
  before it. Neither happens here.
- Anything put *after* the environment, still inside the frame (a credit line, say), is
  centred together with the row, so the picture then sits that much higher. That is the
  frame's `[c]` doing its job, not the environment losing its alignment.
- If the text is too tall for `height`, it overflows symmetrically rather than pushing the
  picture down, and the log says `Overfull \vbox`. Fix the text, or raise `height`.

## a picture with a credit line

`talks.sty` also defines `\creditedpicture` for a picture that stands on its own, centred on
the frame with its source credited underneath:

```latex
\creditedpicture{img/foo}{bibkey}
```

The second argument is a BibTeX key, and the credit line is set in the deck's own text
colour, not in the theme's grey — `\ccite` and `\cccite` are both light greys meant for the
dark `block` headers, and neither reads on the slide background.

| key | default | meaning |
| --- | --- | --- |
| `width` | `1.00` | the picture's share of the width available |
| `height` | `0.70` | the picture's share of the height available |
| `credit` | *(empty)* | wording put ahead of the citation marker |

With no `credit`, the line is the citation marker alone — `[Sagan et al., 1980]` — which is
all a picture needs when it already carries its own caption. Give the key to spell the credit
out:

```latex
\creditedpicture[credit={Carl Sagan, \emph{Cosmos}, Episode 1}]%
  {img/foo}{bibkey}
```

`width` and `height` bound the picture on both axes with `keepaspectratio`, as
`picturecolumns` does, so any aspect ratio fits inside them; lower `height` when the credit
needs more room. The image name goes without its extension.

**It also works inside `picturecolumns`**, in the text column, which is how a frame gets two
credited pictures side by side, or a credited picture beside a plain one. Both fractions are
then read against the column rather than the frame: `width` is the text column's width, and
`height` is the *row's* height — so the default `0.70` inside a default `0.80` row is 0.56 of
the frame, and the picture cannot outgrow the box it sits in. Nothing has to be passed
between the two: the environment publishes the row height and `\creditedpicture` picks it up,
falling back to the frame's height everywhere else.

**`\creditedpicture` cites its second argument**, so the set of works a deck cites is not what a
grep of the `.tex` for `\cite` finds. Take it from the deck's `.aux`.

## a bulleted list inside a line

`talks.sty` defines `\bulletlist` for a run of short items separated by bullets, the shape a
subtitle or a credit line often wants:

```latex
\bulletlist{Perugia, 7 October 2026, Andrea Omicini}
```

prints `Perugia • 7 October 2026 • Andrea Omicini`. The argument is a comma-separated list of
any length, zero included; each item is stripped of the spaces around it and wrapped in an
`\mbox`, so no item breaks across a line, and the separator goes only *between* items — never
before the first or after the last. An empty argument prints nothing at all.

Three things to know:

- **Empty items disappear.** `\bulletlist{a,,b}` gives `a • b`, not a stray bullet. That
  follows from the underlying comma list, and is almost always what a list assembled from
  macros wants.
- **A comma inside braces is not a separator**, so `\bulletlist{{a,b}, c}` is two items.
  Otherwise the comma is the separator and cannot appear in an item.
- **It is not expandable**, so it must not go in `\title`, `\subtitle` or anything else
  hyperref turns into a PDF string.

It takes no position of its own on size or alignment, so the usual frame is
`\begin{center}\smaller{}` around it when the run is an aside under an `\item`.

## a long quotation, with its translation

`talks.sty` defines `indquotation` for the quotations that carry a deck's epigraphs — long
enough to want ragged-right setting, and usually followed by a translation:

```latex
\begin{block}{Friedrich Nietzsche, ``Ecce Homo''\ccite{nietzsche1908}}
  \begin{indquotation}
    % LTeX: language=de-DE
    Wie viel Wahrheit ertragt, wie viel Wahrheit wagt ein Geist?
    % LTeX: language=#
    \par\medskip{}
    \smaller\emph{How much truth can a spirit bear, how much truth can it dare?}
  \end{indquotation}
\end{block}
```

It is a `quotation` with two lines set inside it, and nothing else — but they are an ordered
pair, and neither works without the other:

```latex
\raggedright
\setlength{\parindent}{\listparindent}
```

`\raggedright` is there because justifying a narrow quotation on a slide opens rivers. The
second line looks redundant, since `quotation` already sets `\parindent` to `\listparindent`
— measured at 15.11pt under this theme — and it is not: LaTeX's `\raggedright` ends with
`\parindent\z@`, so it destroys that indentation on its way past. Without the restore, the
first paragraph keeps its indent anyway, because `quotation` applies it through `\itemindent`
at `\begin`, before `\raggedright` runs; every *later* paragraph then starts flush, and the
quotation goes out of step with itself.

It takes no arguments and no keys. Three conventions go with it rather than in it, because
they are the writer's choice and not the environment's:

- **`\par\medskip{}` before a translation**, and `\smaller\emph{...}` for the translation
  itself, so the original stays the dominant text.
- **`% LTeX: language=xx-XX` around a foreign passage**, closed with `% LTeX: language=#`.
  Without it LTeX+ spell-checks German or Italian against `ltex.language`, which is `en-GB`,
  and fills `.vscode/ltex.hiddenFalsePositives.en-GB.txt` with the quotation. **A language
  LanguageTool does not have gets `% LTeX: enabled=false` instead**, closed with
  `enabled=true`: the server ships 27 language modules — Esperanto among them — and Latin is
  not one of them, so Cicero cannot be checked, only exempted. Words that keep being flagged
  despite that go in `.vscode/ltex.dictionary.<language>.txt`, and **the language in the file
  name matters**: a word listed under `en-GB` is still flagged inside an Italian passage.
- **A lone `%` between paragraphs**, the usual separator between paragraphs.

## what LTeX+ must not read as prose

`.vscode/settings.json` declares the deck's own commands to LTeX+ under `ltex.latex.commands`,
because the checker reads command arguments as text unless told otherwise. Two failures make
it obvious: a citation key ends up glued to the word before it — `\ccite` after *methodology*
is reported as the misspelling `methodologypopper-scientificdiscovery` — and an acronym key
like `\acs{mas}` is read as a word.

Two actions matter. **`ignore`** drops the argument, which is right for citations, ids and
paths (`\ccite`, `\cccite`, `\decklabel`, `\creditedpicture`, `\usetheme`,
`\bibliographystyle`, and the theme's `\uurl`/`\ddoi` family). **`dummy`** replaces the
command with a placeholder word, which is right for acro's `\ac`, `\acs`, `\acp` and their
capitalised and plural forms: those *do* expand to text, so dropping them outright would
break the sentence around them and invent grammar errors instead.

A command whose argument really is prose stays undeclared — `\emph`, `\alert`, `\aalert`, and
`\bulletlist`, whose argument is a comma-list of phrases.

## typesetting from TeXShop

TeXShop runs its typesetting command in the folder holding the `.tex` file, so the plain `latexmk`
line in its preferences cannot build these decks: from `tex/`, every relative path in `.latexmkrc`
misses, and `-auxdir`/`-outdir` would make a second `tex/aux/` and `tex/pdf/`. A custom engine does
the job, the same for every talk repository: it names no deck, knows only the layout, and reads
whatever `.latexmkrc` it finds at the root. Put this in `~/Library/TeXShop/Engines/talks.engine` and
make it executable (courses have `courses.engine`, its twin but for the comments):

```bash
#!/bin/bash
# TeXShop engine -- talks: latexmk runs from the project root, the preview is
# left beside the source. See README.md, "building".
# A copy of courses.engine, taken 2026-09-29 and identical to it so far, so
# that a talk can say "% !TEX TS-program = talks" and the two can diverge.
src="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
dir="$(dirname "$src")"
root="$(dirname "$dir")"
base="$(basename "${src%.tex}")"

# The layout is <root>/{tex,sty,bib,img,aux,pdf} with .latexmkrc at the root.
# A file outside it is built where it lies, as a plain latexmk would.
if [ "$(basename "$dir")" = tex ] && [ -e "$root/.latexmkrc" ] ; then
    cd "$root" || exit 1
else
    root="$dir"
    cd "$dir" || exit 1
fi

latexmk -pdf "$src"
status=$?

for ext in pdf synctex.gz ; do
    out="$root/aux/$base.$ext"
    if [ -e "$out" ] && [ "$out" != "$dir/$base.$ext" ] ; then
        cp "$out" "$dir/$base.$ext"
    fi
done
exit $status
```

A deck then selects it with a first line of its own:

```latex
% !TEX TS-program = talks
```

That line overrides TeXShop's preference for this file only, so the general `latexmk` line in
*Preferences → Engine* stays as it is and keeps serving every other project. TeXShop reads
the *Engines* folder once, at launch, and the directive when a document is **opened**: after
installing the engine, quit and reopen TeXShop, and close and reopen any deck that was
already open, or the typeset silently falls back to the preference line and no `.sty` is
found.

The build itself is the normal one — root directory, `aux/`, and the renamed copy in `pdf/`.
The engine then copies the PDF and its `.synctex.gz` next to the deck, because that is the
only place TeXShop looks for them; `latexmk` is given the deck's absolute path, so SyncTeX
records absolute source names and Cmd-click works on that copy. Both files are gitignored,
and VS Code, which previews `aux/` directly, never sees them.

**Typeset (⌘T) is the command that reads the directive.** The Typeset menu's **LaTeX** item
(⌘⇧L) chooses a program explicitly and therefore bypasses it, running the *Preferences →
Engine → Latex* line in `tex/` — where no `.sty` is found. Use ⌘T for the decks.

**The directive also has to be neutralised on the VS Code side.** LaTeX Workshop reads the
same magic comment and takes `TS-program` as naming a *program to spawn*, so it tries to
execute a binary called `talks` and the recipe dies before LaTeX runs — `Recipe terminated
with fatal error: spawn talks ENOENT` in the extension's log, and no compiler log at all,
which is the tell. `.vscode/settings.json` therefore sets
`latex-workshop.latex.build.enableMagicComments` to `false`: VS Code then uses its own
`latexmk` recipe and never looks at the line, while TeXShop keeps reading it. Do not remove
the directive to silence this — ⌘T needs it. It has to be that setting and not
`forceRecipeUsage`, which sounds like the one and is not: it defaults to `true` already, and
the code path that spawns the magic program does not consult it.
