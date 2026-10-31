#!/bin/zsh
# compare.zsh <deck.pdf> <deck.html> <tag> -- every page in WebKit and Firefox against the PDF
pdf="${1:A}"; html="${2:A}"; t="$3"; cd "${DECK2HTML_WORK:-${0:A:h}}"; C="cmp-$t"; rm -rf $C; mkdir -p $C
n=$(pdfinfo "$pdf" | awk '/^Pages/{print $2}')
w=1088; h=$(python3 -I -c "import re,subprocess;s=subprocess.run(['pdfinfo','$pdf'],capture_output=True,text=True).stdout;a,b=map(float,re.search(r'Page size:\s+([\d.]+) x ([\d.]+)',s).groups());print(round($w*b/a))")
timeout 300 pdftoppm -scale-to-x $w -scale-to-y $h -png "$pdf" $C/ref >/dev/null
cat > $C/shot.mjs <<JS
import { createRequire } from 'module';
const require = createRequire('/opt/homebrew/opt/playwright-cli/libexec/lib/node_modules/@playwright/cli/package.json');
const { webkit } = require('playwright');
const b = await webkit.launch(); const p = await (await b.newContext({ viewport: { width: $w, height: $h } })).newPage();
await p.goto('file://$html#1'); await p.waitForTimeout(800);
for (let i = 1; i <= $n; i++) { await p.evaluate(k => { location.hash = '#' + k; }, i); await p.waitForTimeout(200); await p.screenshot({ path: '$C/wk-' + String(i).padStart(${#n}, '0') + '.png' }); }
await b.close();
JS
timeout 900 node $C/shot.mjs
[ -n "$SKIPFF" ] || for i in $(seq 1 $n); do j=$(printf "%0${#n}d" $i); timeout 60 /Applications/Firefox.app/Contents/MacOS/firefox --headless --window-size=$w,$h --screenshot "$PWD/$C/ff-$j.png" "file://$html#$i" >/dev/null 2>&1; done
engines=(wk); [ -z "$SKIPFF" ] && engines+=(ff)
for e in $engines; do
  for i in $(seq 1 $n); do j=$(printf "%0${#n}d" $i); r=$(ls $C/ref-*$j.png | head -1); printf "%s %s\n" $j "$(compare -metric AE -fuzz 12% $r $C/$e-$j.png null: 2>&1 | sed 's/.*(\(.*\))/\1/')"; done > $C/$e.txt
  echo "$e: worst $(LC_ALL=C sort -k2 -g $C/$e.txt | tail -3 | tr '\n' ' ')"
done
