#!/bin/sh
# style-lag.sh -- is this deck repo's .style behind its style's main? Run from the repo root.
# Counts only the commits a deck builds from: not html/ (decks use it from the style's own folder),
# not ci/ or check/, not the docs. Exit 0 in step, 3 behind (a warning in CI), 1 if it cannot tell.
# STYLE_URL may override the clone URL (a local path, for a test). Shared by every repo using an AMS
# Beamer style: GitLab includes ci/style-lag.gitlab-ci.yml; the templates' GitHub workflows run it.
set -e
url=${STYLE_URL:-$(git config -f .gitmodules submodule..style.url)}
case "$url" in
  ../*) url="https://gitlab-ci-token:${CI_JOB_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_NAMESPACE}/${url#../}" ;;
esac
pin=$(git ls-tree HEAD .style | awk '{print $3}')
[ -n "$pin" ] || { echo "style-lag: no .style submodule pinned"; exit 1; }
tmp=$(mktemp -d)
git clone -q --filter=blob:none --no-checkout "$url" "$tmp/style"
top=$(git -C "$tmp/style" rev-parse origin/main)
n=$(git -C "$tmp/style" rev-list --count "$pin..$top" -- . ':(exclude)html' ':(exclude)ci' ':(exclude)check' ':(exclude)*.md')
name=$(basename "$url" .git)
if [ "$n" -gt 0 ]; then
  echo "style-lag: .style is $n commit(s) of $name behind its main (${pin%"${pin#???????}"} -> ${top%"${top#???????}"}):"
  git -C "$tmp/style" log --oneline "$pin..$top" -- . ':(exclude)html' ':(exclude)ci' ':(exclude)check' ':(exclude)*.md' | sed 's/^/  /'
  echo "Move it: git submodule update --remote .style, rebuild, CI, push, republish."
  exit 3
fi
echo "style-lag: .style in step with $name main (${top%"${top#???????}"})"
