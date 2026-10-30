# check — what the build log does not report

Shared by every course and talk repository using an AMS Beamer style (decided 2026-10-30: one copy here,
not one per repository; see `../../COURSE-DECKS.md`). Run from the deck repository's root:

| script | catches | run as |
| --- | --- | --- |
| `checkdeck.py` | content silently dropped by `allowframebreaks` (a block too tall to split) | `../beamer-AMSUniBo/check/checkdeck.py tex/<deck>.tex aux/<deck>.pdf` |
| `framebreaks.py` | `allowframebreaks` frames rendering a single page, a lone `I` in the title | `../beamer-AMSUniBo/check/framebreaks.py aux/<deck>.pdf` |
| `vbwidth.py` | verbatim lines wider than `\textwidth` (62 characters on AMSUniBo, 60 on the others) | `../beamer-AMSUniBo/check/vbwidth.py tex/<deck>.tex` |

They need `pdftotext` (poppler) and `mutool` (mupdf), both from Homebrew. A change here counts for no
deck's `style-lag` (it ignores `check/`, as `html/` and `ci/`).
