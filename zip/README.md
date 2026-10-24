# A deck as one flat folder

`zip.sh` packs a Beamer deck into `zip/<deck>.zip`: one folder, `<deck>/`, holding on a
single level only the files the build reads — the `.tex`, the style layers, the theme, the
images, the `.bib` and the `.bst` — and no generated file. Inside it, a plain `pdflatex`,
`bibtex`, `pdflatex`, `pdflatex` gives the deck, with no engine and no configuration: the
archive for APICe's `sources` field of a talk.

From the deck's root, the one with `.latexmkrc`, `tex/` and `aux/`:

```sh
../beamer-AMSUniBo/zip/zip.sh            # tex/ holds one deck
../beamer-AMSUniBo/zip/zip.sh l2-lp      # tex/ holds several: name one
```

It builds the deck with `latexmk`, then takes the list from the build itself: every project
file in `aux/<deck>.fls`, plus the `.bib` and `.bst` named in `aux/<deck>.aux`, found by name
anywhere in the repository. Symlinks are resolved, so the theme arrives as real files. In the
copies, the `% !TEX` lines go, and a file called through a folder — `{img/x}` in any command,
the deck's own macros included — is called by name.

It writes the archive only if the flat folder, built in a scratch directory with an empty
`TEXMFHOME`, stops on no error, reads nothing from `~/Library/texmf`, warns exactly as
`aux/<deck>.log` does, and gives the same pages as `aux/<deck>.pdf`, pixel for pixel at
100 dpi. Otherwise it says why and writes nothing.

`zip/` belongs in the deck's `.gitignore`; the script warns when it is not. Needs TeX Live,
`latexmk`, `perl` and poppler's `pdftoppm`.
