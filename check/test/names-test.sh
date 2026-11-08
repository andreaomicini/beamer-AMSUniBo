#!/bin/bash
# The CI's check of the canonical vocabulary (../names.sty, job `names` in ../../.gitlab-ci.yml), the same run
# locally: every name and every acronym typeset once, in article and in KOMA's scrartcl, so that a broken line, or one
# using a command a class lacks, fails here, before a repository copies it. \texorpdfstring (hyperref, which beamer
# loads) and \addtobeamertemplate get stand-ins.
set -euo pipefail
cd "$(dirname "$0")"
w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
cp ../names.sty "$w/names.sty"
names=$(sed -n 's/^\\newcommand{\\\([A-Za-z@]*\)}.*/\1/p' ../names.sty)
acros=$(sed -n 's/^\\DeclareAcronym{\([^}]*\)}.*/\1/p' ../names.sty)
for class in article scrartcl; do
  {
    printf '%s\n' "\\documentclass{$class}" '\providecommand{\texorpdfstring}[2]{#1}' \
      '\providecommand{\addtobeamertemplate}[3]{}' '\usepackage{names}' '\begin{document}'
    for n in $names; do printf '%s\n' "\\texttt{$n}: \\$n{}\\par"; done
    for a in $acros; do printf '%s\n' "\\texttt{$a}: \\acf{$a}; \\acs{$a}\\par"; done
    printf '%s\n' '\end{document}'
  } > "$w/t.tex"
  (cd "$w" && pdflatex -interaction=nonstopmode -halt-on-error t.tex > t.out 2>&1) ||
    { grep -A3 '^!' "$w/t.log" | head -12; echo "names-test: the canon does not typeset in $class"; exit 1; }
  if grep -q 'Undefined control sequence' "$w/t.log"; then grep -A2 'Undefined control' "$w/t.log" | head; exit 1; fi
  if grep -q 'Package acro Warning' "$w/t.log"; then grep -A2 'Package acro Warning' "$w/t.log" | head; exit 1; fi
done
echo "names-test: $(echo $names | wc -w | tr -d ' ') names and $(echo $acros | wc -w | tr -d ' ') acronyms typeset, in article and scrartcl"
