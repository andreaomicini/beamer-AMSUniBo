# check — what the build log does not report

Shared by every course and talk repository using an AMS Beamer style (decided 2026-10-30: one copy here,
not one per repository; see `../../COURSE-DECKS.md`). Run from the deck repository's root:

| script | catches | run as |
| --- | --- | --- |
| `checkdeck.py` | content silently dropped by `allowframebreaks` (a block too tall to split) | `../beamer-AMSUniBo/check/checkdeck.py tex/<deck>.tex aux/<deck>.pdf` |
| `framebreaks.py` | `allowframebreaks` frames rendering a single page, a lone `I` in the title | `../beamer-AMSUniBo/check/framebreaks.py aux/<deck>.pdf` |
| `vbwidth.py` | verbatim lines that really leave the text area in the built PDF: the long source lines are only the candidates, each looked up in the PDF; a line found fine is not checked again until it changes (`aux/<deck>.vbwidth`) | `../beamer-AMSUniBo/check/vbwidth.py tex/<deck>.tex aux/<deck>.pdf` |

`checkdeck.py` reads the source without its comments (verbatim kept as it is): a commented-out frame is not in
the PDF, and was reported as missing (AS L1 16 times, L4, T1, SA T0) until 2026-11-02.

Since 2026-11-08 it also flags an `@url` entry in any `.bib` the deck reads: `url` is a field, so BibTeX
cannot have a type of that name and prints the entry as `misc`; the type for a web page is `@webpage`
(the `.bst`'s *web pages*, in the README).

They need `pdftotext` (poppler) and `mutool` (mupdf), both from Homebrew. A change here counts for no
deck's `style-lag` (it ignores `check/`, as `html/` and `ci/`).

## `names.sty` — the canonical vocabulary (2026-11-03)

One line per name of a system, model or language the decks print (`\jason`, `\cartago`, `\tuprolog`…), in its
one canonical form. **No deck loads it.** Each repository's `sty/names.sty` is a file of its own, never a link: the
lines it uses, copied as they are, and what is its own, marked `% local`.

Consistency is bound late (Andrea, 2026-11-03): a change here is not propagated. `/course-check` and `/deck-check`
report a name a repository defines otherwise and a name neither here nor marked local, as `later`: never a gap to
fix now. **A name is aligned only when the decks that use it are being rebuilt anyway**, never because one happens
to work in the repository: aligning a name every deck uses would mean redoing them all (Andrea, 2026-11-03). A new
name is copied from here, which changes no existing deck; a name new to the canon is promoted here. A name whose forms in use print differently is marked `% decision:`, its
other forms listed, until Andrea chooses.

The CI job `names` (`../.gitlab-ci.yml`) typesets every name once (`test/names-test.sh`): run it before a push.
