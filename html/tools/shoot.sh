#!/bin/sh
# shoot.sh <deck.html> <outdir> <pages> -- one 1024x768 PNG per page, s-01.png ..., by headless Chrome
set -e
H="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; OUT="$2"; mkdir -p "$OUT"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
URL="file://$(printf %s "$H" | sed 's/ /%20/g; s/(/%28/g; s/)/%29/g')"
for i in $(seq 1 "$3"); do
	"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
		--window-size=1024,768 --virtual-time-budget=3000 \
		--screenshot="$OUT/s-$(printf %02d "$i").png" "$URL#$i" >/dev/null 2>&1
done
