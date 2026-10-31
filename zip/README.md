# A deck as one flat folder

`zip.sh` packs a Beamer deck into `zip/<deck>.zip`: one folder, `<deck>/`, holding on a
single level only the files the build reads — the `.tex`, the style layers, the theme, the
images, the `.bib` and the `.bst` — and no generated file. Inside it, a plain `pdflatex`,
`bibtex`, `pdflatex`, `pdflatex` gives the deck, with no engine and no configuration (one
`pdflatex` more when the references change the frame total, as in DS 25·26's M2): the
archive for APICe's `sources` field of a talk or a course deck.

From the deck's root, the one with `.latexmkrc`, `tex/` and `aux/`:

```sh
../beamer-AMSUniBo/zip/zip.sh            # tex/ holds one deck
../beamer-AMSUniBo/zip/zip.sh l2-lp      # tex/ holds several: name one
```

It builds the deck with `latexmk`, then takes the list from the build itself: every project
file in `aux/<deck>.fls`, plus the `.bib` and `.bst` named in `aux/<deck>.aux`, found by name
anywhere in the repository. Symlinks are resolved, so the theme arrives as real files. In the
copies, the `% !TEX` lines go, and a file called through a folder — `{img/x}` in any command,
the deck's own macros included — is called by name. A name may hold spaces
(`{img/tuttofuoco-between words}`, ISE 25·26's M0) and is taken literally: `{/*}` in a
listings style is no path and stays as it is (until 2026-10-31 it became `{*}`, in DS
25·26's `my-listings.sty`).

It writes the archive only if the flat folder, built in a scratch directory with an empty
`TEXMFHOME` — pdflatex, bibtex, then pdflatex until `.aux` and `.nav` stop changing, since
beamer's frame total changes them without asking for a rerun — stops on no error, reads nothing from `~/Library/texmf`, warns exactly as
`aux/<deck>.log` does, and gives the same pages as `aux/<deck>.pdf`, pixel for pixel at
100 dpi. Otherwise it says why and writes nothing.

`zip/` belongs in the deck's `.gitignore`; the script warns when it is not. Needs TeX Live,
`latexmk`, `perl` and poppler's `pdftoppm`.
