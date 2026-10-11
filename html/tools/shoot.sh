#!/bin/sh
# shoot.sh <firefox|webkit> <deck.html> <outdir> <pages> -- one 1024x768 PNG per page, s-01.png ...
# firefox: the installed Firefox, headless, in a throwaway profile
# webkit: Playwright's WebKit, the engine of Safari (python3 with playwright on PATH)
set -e
ENGINE="$1"; H="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"; OUT="$3"; N="$4"
mkdir -p "$OUT"
URL="file://$(printf %s "$H" | sed 's/ /%20/g; s/(/%28/g; s/)/%29/g')"
case "$ENGINE" in
firefox)
	FIREFOX="${FIREFOX:-/Applications/Firefox.app/Contents/MacOS/firefox}"
	PROFILE="$(mktemp -d)"
	for i in $(seq 1 "$N"); do
		"$FIREFOX" --headless --no-remote --profile "$PROFILE" --window-size=1024,768 \
			--screenshot "$OUT/s-$(printf %02d "$i").png" "$URL#$i" >/dev/null 2>&1
	done
	rm -rf "$PROFILE" ;;
webkit)
	python3 - "$URL" "$OUT" "$N" <<'PY'
import sys
from playwright.sync_api import sync_playwright
url, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page(viewport={'width': 1024, 'height': 768}, device_scale_factor=1)
    for i in range(1, n + 1):
        pg.goto(f'{url}#{i}'); pg.wait_for_timeout(400)
        pg.screenshot(path=f'{out}/s-{i:02d}.png')
    b.close()
PY
	;;
*)
	echo "shoot.sh: engine is firefox or webkit" >&2; exit 2 ;;
esac
