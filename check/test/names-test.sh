#!/bin/bash
# The CI's check of the canonical vocabulary (../names.sty, job `names` in ../../.gitlab-ci.yml), the same run
# locally: every name typeset once in a plain document, so that a broken line fails here, before a repository
# copies it. \acs (acronym) and \texorpdfstring (hyperref, which beamer loads) get stand-ins.
set -euo pipefail
cd "$(dirname "$0")"
w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
cp ../names.sty "$w/names.sty"
names=$(sed -n 's/^\\newcommand{\\\([A-Za-z@]*\)}.*/\1/p' ../names.sty)
{
  printf '%s\n' '\documentclass{article}' '\providecommand{\acs}[1]{#1}' '\providecommand{\texorpdfstring}[2]{#1}' '\usepackage{names}' '\begin{document}'
  for n in $names; do printf '%s\n' "\\texttt{$n}: \\$n{}\\par"; done
  printf '%s\n' '\end{document}'
} > "$w/t.tex"
(cd "$w" && pdflatex -interaction=nonstopmode -halt-on-error t.tex > t.out 2>&1) ||
  { grep -A3 '^!' "$w/t.log" | head -12; echo "names-test: the canon does not typeset"; exit 1; }
if grep -q 'Undefined control sequence' "$w/t.log"; then grep -A2 'Undefined control' "$w/t.log" | head; exit 1; fi
echo "names-test: $(echo $names | wc -w | tr -d ' ') names typeset"
